from django.core.management.base import BaseCommand
from django.utils import timezone
from django.db.models import Q
from duyurular.models import Announcement


class Command(BaseCommand):
    help = 'Archive expired announcements automatically'

    def add_arguments(self, parser):
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be archived without actually doing it',
        )
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed output',
        )

    def handle(self, *args, **options):
        now = timezone.now()
        dry_run = options['dry_run']
        verbose = options['verbose']

        # Find announcements that should be archived
        expired_announcements = Announcement.objects.filter(
            status='published',
            yayin_bitis_tarihi__lte=now
        )

        count = expired_announcements.count()

        if count == 0:
            self.stdout.write(
                self.style.SUCCESS('No announcements to archive.')
            )
            return

        if verbose or dry_run:
            self.stdout.write(f'Found {count} announcement(s) to archive:')
            for announcement in expired_announcements:
                expiry_date = announcement.yayin_bitis_tarihi.strftime('%Y-%m-%d %H:%M')
                self.stdout.write(
                    f'  - "{announcement.title}" (expired: {expiry_date})'
                )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f'DRY RUN: Would archive {count} announcement(s). '
                    'Run without --dry-run to actually archive them.'
                )
            )
            return

        # Archive the announcements
        updated_count = expired_announcements.update(
            status='archived',
            updated_at=now
        )

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully archived {updated_count} announcement(s).'
            )
        )

        if verbose:
            # Log the archived announcements
            for announcement in expired_announcements:
                self.stdout.write(
                    f'Archived: "{announcement.title}"'
                )
