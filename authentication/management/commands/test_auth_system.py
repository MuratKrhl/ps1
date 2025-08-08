from django.core.management.base import BaseCommand
from django.contrib.auth.models import User, Group
from django.contrib.auth import authenticate
from django.conf import settings
from django.test import RequestFactory
from django.contrib.sessions.middleware import SessionMiddleware
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Test Portall authentication system functionality'

    def add_arguments(self, parser):
        parser.add_argument(
            '--verbose',
            action='store_true',
            help='Show detailed test output',
        )

    def handle(self, *args, **options):
        """Test authentication system functionality"""
        
        self.verbose = options['verbose']
        self.stdout.write(
            self.style.SUCCESS('🧪 Testing Portall Authentication System...')
        )
        
        test_results = {
            'passed': 0,
            'failed': 0,
            'warnings': 0
        }
        
        # Test 1: Settings Configuration
        self._test_settings_configuration(test_results)
        
        # Test 2: Authentication Backends
        self._test_authentication_backends(test_results)
        
        # Test 3: Session Configuration
        self._test_session_configuration(test_results)
        
        # Test 4: Security Settings
        self._test_security_settings(test_results)
        
        # Test 5: Groups and Permissions
        self._test_groups_and_permissions(test_results)
        
        # Test 6: LDAP Configuration (if enabled)
        self._test_ldap_configuration(test_results)
        
        # Test 7: Django Axes Configuration
        self._test_axes_configuration(test_results)
        
        # Summary
        self._print_test_summary(test_results)

    def _test_settings_configuration(self, results):
        """Test basic settings configuration"""
        self._print_test_header("Settings Configuration")
        
        # Check LOGIN_URL
        if hasattr(settings, 'LOGIN_URL') and settings.LOGIN_URL == '/auth/login/':
            self._test_pass("LOGIN_URL correctly set")
            results['passed'] += 1
        else:
            self._test_fail("LOGIN_URL not properly configured")
            results['failed'] += 1
        
        # Check LOGIN_REDIRECT_URL
        if hasattr(settings, 'LOGIN_REDIRECT_URL') and settings.LOGIN_REDIRECT_URL == '/':
            self._test_pass("LOGIN_REDIRECT_URL correctly set")
            results['passed'] += 1
        else:
            self._test_fail("LOGIN_REDIRECT_URL not properly configured")
            results['failed'] += 1

    def _test_authentication_backends(self, results):
        """Test authentication backends configuration"""
        self._print_test_header("Authentication Backends")
        
        backends = getattr(settings, 'AUTHENTICATION_BACKENDS', [])
        
        if 'django.contrib.auth.backends.ModelBackend' in backends:
            self._test_pass("ModelBackend is configured")
            results['passed'] += 1
        else:
            self._test_fail("ModelBackend not found in AUTHENTICATION_BACKENDS")
            results['failed'] += 1
        
        # Check LDAP backend if LDAP is enabled
        ldap_enabled = getattr(settings, 'PORTALL_SETTINGS', {}).get('LDAP_ENABLED', False)
        if ldap_enabled:
            if 'django_auth_ldap.backend.LDAPBackend' in backends:
                self._test_pass("LDAP Backend is configured")
                results['passed'] += 1
            else:
                self._test_fail("LDAP Backend not found but LDAP is enabled")
                results['failed'] += 1

    def _test_session_configuration(self, results):
        """Test session configuration"""
        self._print_test_header("Session Configuration")
        
        # Check session age
        session_age = getattr(settings, 'SESSION_COOKIE_AGE', None)
        if session_age == 1800:  # 30 minutes
            self._test_pass(f"Session timeout correctly set to {session_age} seconds (30 minutes)")
            results['passed'] += 1
        else:
            self._test_warning(f"Session timeout is {session_age} seconds (expected 1800)")
            results['warnings'] += 1
        
        # Check HttpOnly
        if getattr(settings, 'SESSION_COOKIE_HTTPONLY', False):
            self._test_pass("SESSION_COOKIE_HTTPONLY is enabled")
            results['passed'] += 1
        else:
            self._test_fail("SESSION_COOKIE_HTTPONLY should be enabled for security")
            results['failed'] += 1

    def _test_security_settings(self, results):
        """Test security settings"""
        self._print_test_header("Security Settings")
        
        # Check CSRF settings
        if 'django.middleware.csrf.CsrfViewMiddleware' in getattr(settings, 'MIDDLEWARE', []):
            self._test_pass("CSRF middleware is enabled")
            results['passed'] += 1
        else:
            self._test_fail("CSRF middleware not found")
            results['failed'] += 1
        
        # Check if in DEBUG mode
        if getattr(settings, 'DEBUG', True):
            self._test_warning("DEBUG mode is enabled (should be False in production)")
            results['warnings'] += 1
        else:
            self._test_pass("DEBUG mode is disabled")
            results['passed'] += 1

    def _test_groups_and_permissions(self, results):
        """Test groups and permissions setup"""
        self._print_test_header("Groups and Permissions")
        
        expected_groups = ['Admins', 'Users', 'Operators', 'Moderators', 'Viewers']
        
        for group_name in expected_groups:
            try:
                group = Group.objects.get(name=group_name)
                self._test_pass(f"Group '{group_name}' exists")
                results['passed'] += 1
            except Group.DoesNotExist:
                self._test_warning(f"Group '{group_name}' not found (run setup_auth_groups command)")
                results['warnings'] += 1

    def _test_ldap_configuration(self, results):
        """Test LDAP configuration if enabled"""
        self._print_test_header("LDAP Configuration")
        
        ldap_enabled = getattr(settings, 'PORTALL_SETTINGS', {}).get('LDAP_ENABLED', False)
        
        if not ldap_enabled:
            self._test_pass("LDAP is disabled")
            results['passed'] += 1
            return
        
        # Check LDAP settings
        ldap_settings = [
            'AUTH_LDAP_SERVER_URI',
            'AUTH_LDAP_USER_SEARCH',
            'AUTH_LDAP_USER_ATTR_MAP',
        ]
        
        for setting in ldap_settings:
            if hasattr(settings, setting):
                self._test_pass(f"{setting} is configured")
                results['passed'] += 1
            else:
                self._test_fail(f"{setting} is missing")
                results['failed'] += 1

    def _test_axes_configuration(self, results):
        """Test Django Axes configuration"""
        self._print_test_header("Django Axes (Brute-force Protection)")
        
        if 'axes' in getattr(settings, 'INSTALLED_APPS', []):
            self._test_pass("Django Axes is installed")
            results['passed'] += 1
        else:
            self._test_fail("Django Axes not found in INSTALLED_APPS")
            results['failed'] += 1
        
        # Check Axes settings
        if getattr(settings, 'AXES_ENABLED', False):
            self._test_pass("Axes is enabled")
            results['passed'] += 1
            
            failure_limit = getattr(settings, 'AXES_FAILURE_LIMIT', None)
            if failure_limit == 5:
                self._test_pass(f"Failure limit set to {failure_limit}")
                results['passed'] += 1
            else:
                self._test_warning(f"Failure limit is {failure_limit} (expected 5)")
                results['warnings'] += 1
        else:
            self._test_warning("Axes is disabled")
            results['warnings'] += 1

    def _print_test_header(self, title):
        """Print test section header"""
        if self.verbose:
            self.stdout.write(f"\n📋 {title}")
            self.stdout.write("-" * (len(title) + 4))

    def _test_pass(self, message):
        """Print passed test"""
        if self.verbose:
            self.stdout.write(f"  ✅ {message}")

    def _test_fail(self, message):
        """Print failed test"""
        self.stdout.write(
            self.style.ERROR(f"  ❌ {message}")
        )

    def _test_warning(self, message):
        """Print warning test"""
        self.stdout.write(
            self.style.WARNING(f"  ⚠️  {message}")
        )

    def _print_test_summary(self, results):
        """Print test summary"""
        total = results['passed'] + results['failed'] + results['warnings']
        
        self.stdout.write('\n' + '='*60)
        self.stdout.write(
            self.style.SUCCESS('🧪 AUTHENTICATION SYSTEM TEST SUMMARY')
        )
        self.stdout.write('='*60)
        
        self.stdout.write(f"📊 Total Tests: {total}")
        self.stdout.write(
            self.style.SUCCESS(f"✅ Passed: {results['passed']}")
        )
        
        if results['failed'] > 0:
            self.stdout.write(
                self.style.ERROR(f"❌ Failed: {results['failed']}")
            )
        
        if results['warnings'] > 0:
            self.stdout.write(
                self.style.WARNING(f"⚠️  Warnings: {results['warnings']}")
            )
        
        # Overall status
        if results['failed'] == 0:
            if results['warnings'] == 0:
                self.stdout.write(
                    self.style.SUCCESS('\n🎉 All tests passed! Authentication system is ready.')
                )
            else:
                self.stdout.write(
                    self.style.WARNING('\n✅ Tests passed with warnings. Review warnings above.')
                )
        else:
            self.stdout.write(
                self.style.ERROR('\n❌ Some tests failed. Please fix the issues above.')
            )
        
        self.stdout.write('\n🔧 Recommended next steps:')
        self.stdout.write('  1. python manage.py migrate')
        self.stdout.write('  2. python manage.py setup_auth_groups')
        self.stdout.write('  3. python manage.py createsuperuser')
        self.stdout.write('  4. Configure LDAP settings in .env file')
        self.stdout.write('  5. Test login functionality')
