"""
Management command for checking application health status
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from envanter.models import Application
from envanter.services import HealthCheckService
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Check health status of applications by testing their ports'

    def add_arguments(self, parser):
        parser.add_argument(
            '--app-id',
            type=int,
            help='Check specific application by ID',
        )
        parser.add_argument(
            '--code-name',
            type=str,
            help='Check specific application by code name',
        )
        parser.add_argument(
            '--critical-only',
            action='store_true',
            help='Check only critical applications',
        )
        parser.add_argument(
            '--unhealthy-only',
            action='store_true',
            help='Check only currently unhealthy applications',
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=5,
            help='Connection timeout in seconds (default: 5)',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting application health checks...')
        )
        
        app_id = options.get('app_id')
        code_name = options.get('code_name')
        critical_only = options['critical_only']
        unhealthy_only = options['unhealthy_only']
        timeout = options['timeout']
        
        try:
            health_service = HealthCheckService()
            health_service.timeout = timeout
            
            # Determine which applications to check
            if app_id:
                applications = Application.objects.filter(id=app_id)
                if not applications.exists():
                    raise CommandError(f'Application with ID {app_id} not found')
            elif code_name:
                applications = Application.objects.filter(code_name=code_name)
                if not applications.exists():
                    raise CommandError(f'Application with code name {code_name} not found')
            else:
                # Build queryset based on filters
                applications = Application.objects.filter(
                    sync_enabled=True,
                    port__isnull=False
                ).select_related('environment').prefetch_related('servers')
                
                if critical_only:
                    applications = applications.filter(business_criticality='critical')
                
                if unhealthy_only:
                    applications = applications.filter(health_check_status='unhealthy')
            
            if not applications.exists():
                self.stdout.write(
                    self.style.WARNING('No applications found matching criteria')
                )
                return
            
            self.stdout.write(f'Checking {applications.count()} applications...')
            
            results = {
                'healthy': 0,
                'unhealthy': 0,
                'unknown': 0,
                'total': 0
            }
            
            for app in applications:
                self.stdout.write(f'Checking {app.name} ({app.code_name})...', ending='')
                
                try:
                    status = health_service.check_application_health(app)
                    results[status] += 1
                    results['total'] += 1
                    
                    # Show status with color
                    if status == 'healthy':
                        self.stdout.write(self.style.SUCCESS(' ✓ Healthy'))
                    elif status == 'unhealthy':
                        self.stdout.write(self.style.ERROR(' ✗ Unhealthy'))
                        
                        # Show server and port info for unhealthy apps
                        server = app.get_primary_server()
                        if server:
                            self.stdout.write(
                                f'   Server: {server.hostname} ({server.ip_address}:{app.port})'
                            )
                    else:
                        self.stdout.write(self.style.WARNING(' ? Unknown'))
                        
                except Exception as e:
                    self.stdout.write(self.style.ERROR(f' Error: {str(e)}'))
                    results['unknown'] += 1
                    results['total'] += 1
            
            # Print summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Health Check Summary:'))
            self.stdout.write(f'Total checked: {results["total"]}')
            self.stdout.write(
                self.style.SUCCESS(f'Healthy: {results["healthy"]}')
            )
            self.stdout.write(
                self.style.ERROR(f'Unhealthy: {results["unhealthy"]}')
            )
            self.stdout.write(
                self.style.WARNING(f'Unknown: {results["unknown"]}')
            )
            
            # Show unhealthy applications if any
            if results['unhealthy'] > 0:
                self.stdout.write('\n' + self.style.ERROR('Unhealthy Applications:'))
                unhealthy_apps = health_service.get_unhealthy_applications()
                for app in unhealthy_apps:
                    server = app.get_primary_server()
                    server_info = f'{server.hostname}:{app.port}' if server else 'No server'
                    self.stdout.write(f'  - {app.name} ({app.code_name}) on {server_info}')
            
            # Set exit code based on results
            if results['unhealthy'] > 0:
                self.stdout.write(
                    self.style.WARNING(
                        f'\nWarning: {results["unhealthy"]} unhealthy applications found'
                    )
                )
                # Exit with code 1 to indicate issues (useful for monitoring)
                exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS('\nAll applications are healthy!')
                )
                
        except Exception as e:
            logger.error(f'Health check failed: {str(e)}')
            raise CommandError(f'Health check failed: {str(e)}')
