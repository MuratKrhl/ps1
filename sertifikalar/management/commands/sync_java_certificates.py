"""
Management command for syncing Java certificates from keystore files
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from sertifikalar.models import JavaCertificate
from sertifikalar.services import JavaSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Java certificates from keystore files via SSH'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be synced without making changes',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if recent sync exists',
        )
        parser.add_argument(
            '--environment',
            type=str,
            help='Sync only specific environment',
        )
        parser.add_argument(
            '--server',
            type=str,
            help='Sync only specific server hostname',
        )
        parser.add_argument(
            '--keystore-type',
            type=str,
            choices=['JKS', 'PKCS12', 'JCEKS'],
            help='Sync only specific keystore type',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='SSH connection timeout in seconds (default: 30)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting Java certificate synchronization...')
        )
        
        dry_run = options['dry_run']
        force = options['force']
        environment = options.get('environment')
        server = options.get('server')
        keystore_type = options.get('keystore_type')
        timeout = options['timeout']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            sync_service = JavaSyncService(timeout=timeout)
            
            # Check if recent sync exists
            if not force and not dry_run:
                if sync_service.has_recent_sync(hours=2):
                    self.stdout.write(
                        self.style.WARNING(
                            'Recent sync found within 2 hours. Use --force to override.'
                        )
                    )
                    return
            
            # Get server list to scan
            servers = sync_service.get_target_servers(
                environment=environment,
                server_hostname=server
            )
            
            if not servers:
                self.stdout.write(
                    self.style.WARNING('No servers found matching criteria')
                )
                return
            
            self.stdout.write(f'Scanning {len(servers)} servers for Java certificates...')
            
            results = {
                'servers_scanned': 0,
                'servers_failed': 0,
                'keystores_found': 0,
                'certificates_created': 0,
                'certificates_updated': 0,
                'certificates_errors': 0
            }
            
            for server_info in servers:
                server_hostname = server_info['hostname']
                server_ip = server_info.get('ip_address', server_hostname)
                
                self.stdout.write(f'Scanning server: {server_hostname} ({server_ip})')
                
                try:
                    server_result = sync_service.sync_server_certificates(
                        hostname=server_hostname,
                        ip_address=server_ip,
                        environment=server_info.get('environment', ''),
                        keystore_type_filter=keystore_type,
                        dry_run=dry_run
                    )
                    
                    results['servers_scanned'] += 1
                    results['keystores_found'] += server_result.get('keystores_found', 0)
                    results['certificates_created'] += server_result.get('created', 0)
                    results['certificates_updated'] += server_result.get('updated', 0)
                    results['certificates_errors'] += server_result.get('errors', 0)
                    
                    self.stdout.write(
                        f'  ✓ Found {server_result.get("keystores_found", 0)} keystores, '
                        f'{server_result.get("created", 0)} new certificates, '
                        f'{server_result.get("updated", 0)} updated'
                    )
                    
                except Exception as e:
                    results['servers_failed'] += 1
                    self.stdout.write(
                        self.style.ERROR(f'  ✗ Failed to scan {server_hostname}: {str(e)}')
                    )
                    logger.error(f'Failed to scan server {server_hostname}: {str(e)}')
            
            # Update last sync timestamp
            if not dry_run:
                sync_service.update_last_sync()
            
            # Print summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Java Certificate Sync Summary:'))
            self.stdout.write(f'Servers scanned: {results["servers_scanned"]}')
            self.stdout.write(f'Servers failed: {results["servers_failed"]}')
            self.stdout.write(f'Keystores found: {results["keystores_found"]}')
            self.stdout.write(f'Certificates created: {results["certificates_created"]}')
            self.stdout.write(f'Certificates updated: {results["certificates_updated"]}')
            self.stdout.write(f'Errors: {results["certificates_errors"]}')
            
            if results['servers_failed'] > 0 or results['certificates_errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'Completed with {results["servers_failed"]} server failures '
                        f'and {results["certificates_errors"]} certificate errors'
                    )
                )
                exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS('Sync completed successfully!')
                )
                
        except Exception as e:
            logger.error(f'Java certificate sync failed: {str(e)}')
            raise CommandError(f'Sync failed: {str(e)}')
