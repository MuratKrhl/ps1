"""
Management command for syncing KDB certificates from external sources
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
from sertifikalar.models import KdbCertificate
from sertifikalar.services import KdbSyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync KDB certificates from external data sources (SQL, AppViewX API, Ansible)'

    def add_arguments(self, parser):
        parser.add_argument(
            '--source',
            type=str,
            choices=['sql', 'appviewx', 'ansible', 'all'],
            default='all',
            help='Data source to sync from',
        )
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

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting KDB certificate synchronization...')
        )
        
        source = options['source']
        dry_run = options['dry_run']
        force = options['force']
        environment = options.get('environment')
        server = options.get('server')
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            sync_service = KdbSyncService()
            
            # Check if recent sync exists
            if not force and not dry_run:
                if sync_service.has_recent_sync(hours=1):
                    self.stdout.write(
                        self.style.WARNING(
                            'Recent sync found within 1 hour. Use --force to override.'
                        )
                    )
                    return
            
            results = {
                'sql': {'created': 0, 'updated': 0, 'errors': 0},
                'appviewx': {'created': 0, 'updated': 0, 'errors': 0},
                'ansible': {'created': 0, 'updated': 0, 'errors': 0}
            }
            
            # Sync from SQL Database
            if source in ['sql', 'all']:
                self.stdout.write('Syncing from SQL database...')
                try:
                    sql_result = sync_service.sync_from_sql(
                        dry_run=dry_run,
                        environment=environment,
                        server=server
                    )
                    results['sql'] = sql_result
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'SQL sync: {sql_result["created"]} created, '
                            f'{sql_result["updated"]} updated, '
                            f'{sql_result["errors"]} errors'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'SQL sync failed: {str(e)}')
                    )
                    results['sql']['errors'] += 1
            
            # Sync from AppViewX API
            if source in ['appviewx', 'all']:
                self.stdout.write('Syncing from AppViewX API...')
                try:
                    appviewx_result = sync_service.sync_from_appviewx(
                        dry_run=dry_run,
                        environment=environment,
                        server=server
                    )
                    results['appviewx'] = appviewx_result
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'AppViewX sync: {appviewx_result["created"]} created, '
                            f'{appviewx_result["updated"]} updated, '
                            f'{appviewx_result["errors"]} errors'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'AppViewX sync failed: {str(e)}')
                    )
                    results['appviewx']['errors'] += 1
            
            # Sync from Ansible output
            if source in ['ansible', 'all']:
                self.stdout.write('Syncing from Ansible output...')
                try:
                    ansible_result = sync_service.sync_from_ansible(
                        dry_run=dry_run,
                        environment=environment,
                        server=server
                    )
                    results['ansible'] = ansible_result
                    self.stdout.write(
                        self.style.SUCCESS(
                            f'Ansible sync: {ansible_result["created"]} created, '
                            f'{ansible_result["updated"]} updated, '
                            f'{ansible_result["errors"]} errors'
                        )
                    )
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Ansible sync failed: {str(e)}')
                    )
                    results['ansible']['errors'] += 1
            
            # Update last sync timestamp
            if not dry_run:
                sync_service.update_last_sync()
            
            # Print summary
            total_created = sum(r['created'] for r in results.values())
            total_updated = sum(r['updated'] for r in results.values())
            total_errors = sum(r['errors'] for r in results.values())
            
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('KDB Certificate Sync Summary:'))
            self.stdout.write(f'Total created: {total_created}')
            self.stdout.write(f'Total updated: {total_updated}')
            self.stdout.write(f'Total errors: {total_errors}')
            
            if total_errors > 0:
                self.stdout.write(
                    self.style.WARNING(f'Completed with {total_errors} errors')
                )
                exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS('Sync completed successfully!')
                )
                
        except Exception as e:
            logger.error(f'KDB certificate sync failed: {str(e)}')
            raise CommandError(f'Sync failed: {str(e)}')
