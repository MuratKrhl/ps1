"""
Management command for syncing inventory data from external SQL database
"""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from envanter.models import Server, Application, Environment, OperatingSystem, ApplicationType, Technology
from envanter.services import InventorySyncService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync inventory data from external SQL database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Run without making any changes to the database',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force sync even if last sync was recent',
        )
        parser.add_argument(
            '--servers-only',
            action='store_true',
            help='Sync only server data',
        )
        parser.add_argument(
            '--applications-only',
            action='store_true',
            help='Sync only application data',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting inventory data synchronization...')
        )
        
        dry_run = options['dry_run']
        force = options['force']
        servers_only = options['servers_only']
        applications_only = options['applications_only']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No changes will be made')
            )
        
        try:
            sync_service = InventorySyncService()
            
            # Check if sync is needed
            if not force and sync_service.is_recent_sync():
                self.stdout.write(
                    self.style.WARNING(
                        'Recent sync detected. Use --force to override.'
                    )
                )
                return
            
            stats = {
                'servers_created': 0,
                'servers_updated': 0,
                'applications_created': 0,
                'applications_updated': 0,
                'errors': 0
            }
            
            with transaction.atomic():
                if not applications_only:
                    # Sync servers
                    self.stdout.write('Syncing servers...')
                    server_stats = sync_service.sync_servers(dry_run=dry_run)
                    stats['servers_created'] += server_stats['created']
                    stats['servers_updated'] += server_stats['updated']
                    stats['errors'] += server_stats['errors']
                
                if not servers_only:
                    # Sync applications
                    self.stdout.write('Syncing applications...')
                    app_stats = sync_service.sync_applications(dry_run=dry_run)
                    stats['applications_created'] += app_stats['created']
                    stats['applications_updated'] += app_stats['updated']
                    stats['errors'] += app_stats['errors']
                
                if dry_run:
                    # Rollback transaction in dry run mode
                    transaction.set_rollback(True)
            
            # Print results
            self.stdout.write(
                self.style.SUCCESS(
                    f'\nSync completed successfully!'
                )
            )
            self.stdout.write(f'Servers created: {stats["servers_created"]}')
            self.stdout.write(f'Servers updated: {stats["servers_updated"]}')
            self.stdout.write(f'Applications created: {stats["applications_created"]}')
            self.stdout.write(f'Applications updated: {stats["applications_updated"]}')
            
            if stats['errors'] > 0:
                self.stdout.write(
                    self.style.WARNING(f'Errors encountered: {stats["errors"]}')
                )
            
            if not dry_run:
                # Update last sync time
                sync_service.update_last_sync()
                
        except Exception as e:
            logger.error(f'Inventory sync failed: {str(e)}')
            raise CommandError(f'Sync failed: {str(e)}')
