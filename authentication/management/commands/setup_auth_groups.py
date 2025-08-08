from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.db import transaction
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Setup authentication groups and permissions for Portall'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Reset existing groups and recreate them',
        )

    def handle(self, *args, **options):
        """Setup authentication groups and permissions"""
        
        self.stdout.write(
            self.style.SUCCESS('🔐 Setting up Portall authentication groups...')
        )
        
        # Group definitions with permissions
        groups_config = {
            'Admins': {
                'description': 'System administrators with full access',
                'permissions': [
                    # Django admin permissions
                    'auth.add_user',
                    'auth.change_user',
                    'auth.delete_user',
                    'auth.view_user',
                    'auth.add_group',
                    'auth.change_group',
                    'auth.delete_group',
                    'auth.view_group',
                    
                    # All app permissions
                    'envanter.*',
                    'askgt.*',
                    'nobetci.*',
                    'duyurular.*',
                    'linkler.*',
                    'performans.*',
                    'otomasyon.*',
                ]
            },
            'Users': {
                'description': 'Standard users with read access',
                'permissions': [
                    # View permissions for all apps
                    'envanter.view_*',
                    'askgt.view_*',
                    'nobetci.view_*',
                    'duyurular.view_*',
                    'linkler.view_*',
                    'performans.view_*',
                    'otomasyon.view_*',
                ]
            },
            'Operators': {
                'description': 'Operations team with automation access',
                'permissions': [
                    # View permissions for all apps
                    'envanter.view_*',
                    'askgt.view_*',
                    'nobetci.view_*',
                    'duyurular.view_*',
                    'linkler.view_*',
                    'performans.view_*',
                    
                    # Full automation access
                    'otomasyon.*',
                    
                    # Limited management access
                    'duyurular.add_announcement',
                    'duyurular.change_announcement',
                    'linkler.add_link',
                    'linkler.change_link',
                ]
            },
            'Moderators': {
                'description': 'Content moderators for AskGT and announcements',
                'permissions': [
                    # View permissions for all apps
                    'envanter.view_*',
                    'askgt.view_*',
                    'nobetci.view_*',
                    'duyurular.view_*',
                    'linkler.view_*',
                    'performans.view_*',
                    'otomasyon.view_*',
                    
                    # AskGT management
                    'askgt.add_question',
                    'askgt.change_question',
                    'askgt.add_answer',
                    'askgt.change_answer',
                    'askgt.add_knowledgearticle',
                    'askgt.change_knowledgearticle',
                    
                    # Announcements management
                    'duyurular.add_announcement',
                    'duyurular.change_announcement',
                    'duyurular.add_maintenancenotice',
                    'duyurular.change_maintenancenotice',
                ]
            },
            'Viewers': {
                'description': 'Read-only access to all modules',
                'permissions': [
                    # View permissions only
                    'envanter.view_*',
                    'askgt.view_*',
                    'nobetci.view_*',
                    'duyurular.view_*',
                    'linkler.view_*',
                    'performans.view_*',
                    'otomasyon.view_ansibleplaybook',
                    'otomasyon.view_playbookexecution',
                ]
            }
        }
        
        try:
            with transaction.atomic():
                # Reset groups if requested
                if options['reset']:
                    self.stdout.write('🔄 Resetting existing groups...')
                    for group_name in groups_config.keys():
                        Group.objects.filter(name=group_name).delete()
                
                # Create groups
                created_groups = []
                for group_name, config in groups_config.items():
                    group, created = Group.objects.get_or_create(name=group_name)
                    
                    if created:
                        created_groups.append(group_name)
                        self.stdout.write(
                            self.style.SUCCESS(f'✅ Created group: {group_name}')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'⚠️  Group already exists: {group_name}')
                        )
                    
                    # Add permissions (this will be implemented when apps are migrated)
                    self._add_permissions_to_group(group, config['permissions'])
                
                # Summary
                self.stdout.write('\n' + '='*50)
                self.stdout.write(
                    self.style.SUCCESS(
                        f'🎉 Successfully setup {len(groups_config)} authentication groups!'
                    )
                )
                
                if created_groups:
                    self.stdout.write(
                        f'📝 New groups created: {", ".join(created_groups)}'
                    )
                
                self.stdout.write('\n📋 Group Summary:')
                for group_name, config in groups_config.items():
                    self.stdout.write(f'  • {group_name}: {config["description"]}')
                
                self.stdout.write('\n🔧 Next Steps:')
                self.stdout.write('  1. Run migrations for all apps')
                self.stdout.write('  2. Create superuser: python manage.py createsuperuser')
                self.stdout.write('  3. Assign users to groups via admin panel')
                self.stdout.write('  4. Test LDAP integration')
                
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'❌ Error setting up groups: {str(e)}')
            )
            logger.error(f'Error setting up authentication groups: {str(e)}')
            raise

    def _add_permissions_to_group(self, group, permission_patterns):
        """Add permissions to group based on patterns"""
        # This method will add permissions when the apps are migrated
        # For now, we'll store the patterns and apply them later
        
        # Note: Permissions will be applied after migrations
        # when the actual Permission objects exist in the database
        pass

    def _get_permissions_by_pattern(self, pattern):
        """Get permissions matching a pattern like 'app.*' or 'app.view_*'"""
        permissions = []
        
        if '.' not in pattern:
            return permissions
            
        app_label, perm_pattern = pattern.split('.', 1)
        
        try:
            # Get all content types for the app
            content_types = ContentType.objects.filter(app_label=app_label)
            
            for ct in content_types:
                if perm_pattern == '*':
                    # All permissions for this content type
                    perms = Permission.objects.filter(content_type=ct)
                    permissions.extend(perms)
                elif perm_pattern.endswith('*'):
                    # Pattern matching like 'view_*'
                    prefix = perm_pattern[:-1]
                    perms = Permission.objects.filter(
                        content_type=ct,
                        codename__startswith=prefix
                    )
                    permissions.extend(perms)
                else:
                    # Exact permission match
                    try:
                        perm = Permission.objects.get(
                            content_type=ct,
                            codename=perm_pattern
                        )
                        permissions.append(perm)
                    except Permission.DoesNotExist:
                        pass
                        
        except ContentType.DoesNotExist:
            pass
            
        return permissions
