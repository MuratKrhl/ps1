"""
Envanter modülü için servis sınıfları
"""
import socket
import logging
from datetime import datetime, timedelta
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from .models import Server, Application, Environment, OperatingSystem, ApplicationType, Technology

logger = logging.getLogger(__name__)


class InventorySyncService:
    """Envanter verilerinin harici sistemlerle senkronizasyonu için servis"""
    
    LAST_SYNC_CACHE_KEY = 'inventory_last_sync'
    SYNC_INTERVAL_HOURS = 6  # 6 saatte bir sync
    
    def __init__(self):
        self.stats = {
            'created': 0,
            'updated': 0,
            'errors': 0
        }
    
    def is_recent_sync(self):
        """Son sync yakın zamanda mı yapılmış kontrol eder"""
        last_sync = cache.get(self.LAST_SYNC_CACHE_KEY)
        if not last_sync:
            return False
        
        time_diff = timezone.now() - last_sync
        return time_diff.total_seconds() < (self.SYNC_INTERVAL_HOURS * 3600)
    
    def update_last_sync(self):
        """Son sync zamanını günceller"""
        cache.set(self.LAST_SYNC_CACHE_KEY, timezone.now(), timeout=86400)  # 24 saat
    
    def sync_servers(self, dry_run=False):
        """Sunucu verilerini senkronize eder"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Örnek harici veri - gerçek implementasyonda SQL bağlantısından gelecek
            external_servers = self._fetch_external_servers()
            
            for server_data in external_servers:
                try:
                    with transaction.atomic():
                        server, created = self._sync_server(server_data, dry_run)
                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                            
                except Exception as e:
                    logger.error(f"Server sync error for {server_data.get('hostname', 'unknown')}: {str(e)}")
                    stats['errors'] += 1
                    
        except Exception as e:
            logger.error(f"Server sync failed: {str(e)}")
            stats['errors'] += 1
            
        return stats
    
    def sync_applications(self, dry_run=False):
        """Uygulama verilerini senkronize eder"""
        stats = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # Örnek harici veri - gerçek implementasyonda SQL bağlantısından gelecek
            external_apps = self._fetch_external_applications()
            
            for app_data in external_apps:
                try:
                    with transaction.atomic():
                        app, created = self._sync_application(app_data, dry_run)
                        if created:
                            stats['created'] += 1
                        else:
                            stats['updated'] += 1
                            
                except Exception as e:
                    logger.error(f"Application sync error for {app_data.get('name', 'unknown')}: {str(e)}")
                    stats['errors'] += 1
                    
        except Exception as e:
            logger.error(f"Application sync failed: {str(e)}")
            stats['errors'] += 1
            
        return stats
    
    def _fetch_external_servers(self):
        """Harici sistemden sunucu verilerini çeker"""
        # TODO: Gerçek SQL bağlantısı implementasyonu
        # Şimdilik örnek veri döndürüyoruz
        return [
            {
                'hostname': 'app-server-01',
                'ip_address': '192.168.1.10',
                'environment': 'Production',
                'os_name': 'Ubuntu',
                'os_version': '20.04',
                'cpu_cores': 8,
                'memory_gb': 32,
                'external_id': 'SRV001'
            },
            {
                'hostname': 'db-server-01',
                'ip_address': '192.168.1.20',
                'environment': 'Production',
                'os_name': 'CentOS',
                'os_version': '8',
                'cpu_cores': 16,
                'memory_gb': 64,
                'external_id': 'SRV002'
            }
        ]
    
    def _fetch_external_applications(self):
        """Harici sistemden uygulama verilerini çeker"""
        # TODO: Gerçek SQL bağlantısı implementasyonu
        # Şimdilik örnek veri döndürüyoruz
        return [
            {
                'name': 'Portal Web Uygulaması',
                'code_name': 'PORTAL-WEB',
                'description': 'Ana web portal uygulaması',
                'environment': 'Production',
                'server_hostname': 'app-server-01',
                'port': 8080,
                'ssl_enabled': True,
                'url': 'https://portal.company.com',
                'version': '2.1.0',
                'status': 'active',
                'external_id': 'APP001'
            },
            {
                'name': 'API Gateway',
                'code_name': 'API-GW',
                'description': 'Merkezi API gateway servisi',
                'environment': 'Production',
                'server_hostname': 'app-server-01',
                'port': 9090,
                'ssl_enabled': True,
                'url': 'https://api.company.com',
                'version': '1.5.2',
                'status': 'active',
                'external_id': 'APP002'
            }
        ]
    
    def _sync_server(self, server_data, dry_run=False):
        """Tek bir sunucuyu senkronize eder"""
        if dry_run:
            # Dry run modunda sadece kontrol et
            existing = Server.objects.filter(hostname=server_data['hostname']).first()
            return existing, existing is None
        
        # Environment'ı bul veya oluştur
        environment, _ = Environment.objects.get_or_create(
            name=server_data['environment'],
            defaults={'short_name': server_data['environment'][:3].upper()}
        )
        
        # Operating System'ı bul veya oluştur
        os_obj = None
        if server_data.get('os_name'):
            os_obj, _ = OperatingSystem.objects.get_or_create(
                name=server_data['os_name'],
                version=server_data.get('os_version', ''),
                defaults={'family': 'linux'}  # Default olarak linux
            )
        
        # Server'ı güncelle veya oluştur
        server, created = Server.objects.update_or_create(
            hostname=server_data['hostname'],
            defaults={
                'ip_address': server_data['ip_address'],
                'environment': environment,
                'operating_system': os_obj,
                'cpu_cores': server_data.get('cpu_cores'),
                'memory_gb': server_data.get('memory_gb'),
                'external_id': server_data.get('external_id', ''),
                'updated_at': timezone.now()
            }
        )
        
        return server, created
    
    def _sync_application(self, app_data, dry_run=False):
        """Tek bir uygulamayı senkronize eder"""
        if dry_run:
            # Dry run modunda sadece kontrol et
            existing = Application.objects.filter(code_name=app_data['code_name']).first()
            return existing, existing is None
        
        # Environment'ı bul veya oluştur
        environment, _ = Environment.objects.get_or_create(
            name=app_data['environment'],
            defaults={'short_name': app_data['environment'][:3].upper()}
        )
        
        # Server'ı bul
        server = None
        if app_data.get('server_hostname'):
            server = Server.objects.filter(hostname=app_data['server_hostname']).first()
        
        # Application'ı güncelle veya oluştur
        app, created = Application.objects.update_or_create(
            code_name=app_data['code_name'],
            defaults={
                'name': app_data['name'],
                'description': app_data.get('description', ''),
                'environment': environment,
                'port': app_data.get('port'),
                'ssl_enabled': app_data.get('ssl_enabled', False),
                'url': app_data.get('url', ''),
                'version': app_data.get('version', ''),
                'status': app_data.get('status', 'active'),
                'external_id': app_data.get('external_id', ''),
                'sync_enabled': True,
                'updated_at': timezone.now()
            }
        )
        
        # Server ilişkisini kur
        if server:
            app.servers.add(server)
        
        return app, created


class HealthCheckService:
    """Uygulama sağlık kontrolleri için servis"""
    
    def __init__(self):
        self.timeout = 5  # 5 saniye timeout
    
    def check_application_health(self, application):
        """Tek bir uygulamanın sağlık durumunu kontrol eder"""
        if not application.port or not application.sync_enabled:
            return 'unknown'
        
        server = application.get_primary_server()
        if not server:
            return 'unknown'
        
        try:
            # Port kontrolü
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.timeout)
            result = sock.connect_ex((server.ip_address, application.port))
            sock.close()
            
            if result == 0:
                # Port açık
                application.health_check_status = 'healthy'
                application.status = 'active'
            else:
                # Port kapalı
                application.health_check_status = 'unhealthy'
                application.status = 'error'
            
            application.last_health_check = timezone.now()
            application.save(update_fields=['health_check_status', 'status', 'last_health_check'])
            
            return application.health_check_status
            
        except Exception as e:
            logger.error(f"Health check failed for {application.name}: {str(e)}")
            application.health_check_status = 'unhealthy'
            application.status = 'error'
            application.last_health_check = timezone.now()
            application.save(update_fields=['health_check_status', 'status', 'last_health_check'])
            
            return 'unhealthy'
    
    def check_all_applications(self):
        """Tüm uygulamaların sağlık durumunu kontrol eder"""
        applications = Application.objects.filter(
            sync_enabled=True,
            port__isnull=False
        ).select_related('servers')
        
        results = {
            'healthy': 0,
            'unhealthy': 0,
            'unknown': 0,
            'total': applications.count()
        }
        
        for app in applications:
            if app.needs_health_check():
                status = self.check_application_health(app)
                results[status] += 1
            else:
                results[app.health_check_status] += 1
        
        return results
    
    def get_unhealthy_applications(self):
        """Sağlıksız uygulamaları döndürür"""
        return Application.objects.filter(
            health_check_status='unhealthy'
        ).select_related('environment').prefetch_related('servers')


class InventoryStatsService:
    """Envanter istatistikleri için servis"""
    
    @staticmethod
    def get_dashboard_stats():
        """Dashboard için envanter istatistiklerini döndürür"""
        return {
            'total_servers': Server.objects.count(),
            'total_applications': Application.objects.count(),
            'active_applications': Application.objects.filter(status='active').count(),
            'error_applications': Application.objects.filter(status='error').count(),
            'maintenance_applications': Application.objects.filter(status='maintenance').count(),
            'critical_applications': Application.objects.filter(business_criticality='critical').count(),
        }
    
    @staticmethod
    def get_environment_stats():
        """Ortam bazlı istatistikleri döndürür"""
        from django.db.models import Count
        
        return Environment.objects.annotate(
            server_count=Count('servers'),
            application_count=Count('applications')
        ).order_by('name')
    
    @staticmethod
    def get_technology_stats():
        """Teknoloji bazlı istatistikleri döndürür"""
        from django.db.models import Count
        
        return Technology.objects.annotate(
            application_count=Count('application')
        ).order_by('-application_count')[:10]
