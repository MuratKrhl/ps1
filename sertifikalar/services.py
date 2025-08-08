"""
Certificate Management Services
"""
import os
import re
import json
import subprocess
import paramiko
import requests
from datetime import datetime, timedelta
from django.utils import timezone
from django.db import transaction
from django.core.cache import cache
from django.conf import settings
from .models import KdbCertificate, JavaCertificate
import logging

logger = logging.getLogger(__name__)


class KdbSyncService:
    """Service for syncing KDB certificates from various sources"""
    
    def __init__(self):
        self.cache_key = 'kdb_sync_last_run'
    
    def has_recent_sync(self, hours=1):
        """Check if sync was run recently"""
        last_sync = cache.get(self.cache_key)
        if last_sync:
            return timezone.now() - last_sync < timedelta(hours=hours)
        return False
    
    def update_last_sync(self):
        """Update last sync timestamp"""
        cache.set(self.cache_key, timezone.now(), 86400)  # 24 hours
    
    def sync_from_sql(self, dry_run=False, environment=None, server=None):
        """Sync KDB certificates from SQL database"""
        results = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # This would connect to external SQL database
            # For now, using placeholder data
            certificates_data = self._fetch_sql_certificates(environment, server)
            
            for cert_data in certificates_data:
                try:
                    if not dry_run:
                        certificate, created = KdbCertificate.objects.update_or_create(
                            serial_number=cert_data['serial_number'],
                            defaults={
                                'common_name': cert_data['common_name'],
                                'issuer': cert_data['issuer'],
                                'subject': cert_data['subject'],
                                'valid_from': cert_data['valid_from'],
                                'valid_to': cert_data['valid_to'],
                                'server_hostname': cert_data['server_hostname'],
                                'application_name': cert_data['application_name'],
                                'environment': cert_data['environment'],
                                'kdb_file_path': cert_data['kdb_file_path'],
                                'kdb_label': cert_data['kdb_label'],
                                'sync_source': 'sql',
                                'external_id': cert_data.get('external_id', ''),
                                'last_sync': timezone.now(),
                            }
                        )
                        
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    else:
                        # Dry run - just count what would be processed
                        existing = KdbCertificate.objects.filter(
                            serial_number=cert_data['serial_number']
                        ).exists()
                        if existing:
                            results['updated'] += 1
                        else:
                            results['created'] += 1
                            
                except Exception as e:
                    logger.error(f'Error processing certificate {cert_data.get("serial_number", "unknown")}: {str(e)}')
                    results['errors'] += 1
                    
        except Exception as e:
            logger.error(f'SQL sync failed: {str(e)}')
            results['errors'] += 1
            
        return results
    
    def sync_from_appviewx(self, dry_run=False, environment=None, server=None):
        """Sync KDB certificates from AppViewX API"""
        results = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # This would connect to AppViewX API
            certificates_data = self._fetch_appviewx_certificates(environment, server)
            
            for cert_data in certificates_data:
                try:
                    if not dry_run:
                        certificate, created = KdbCertificate.objects.update_or_create(
                            serial_number=cert_data['serial_number'],
                            defaults={
                                'common_name': cert_data['common_name'],
                                'issuer': cert_data['issuer'],
                                'subject': cert_data['subject'],
                                'valid_from': cert_data['valid_from'],
                                'valid_to': cert_data['valid_to'],
                                'server_hostname': cert_data['server_hostname'],
                                'application_name': cert_data['application_name'],
                                'environment': cert_data['environment'],
                                'appviewx_id': cert_data.get('appviewx_id', ''),
                                'appviewx_status': cert_data.get('status', ''),
                                'sync_source': 'appviewx',
                                'last_sync': timezone.now(),
                            }
                        )
                        
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    else:
                        existing = KdbCertificate.objects.filter(
                            serial_number=cert_data['serial_number']
                        ).exists()
                        if existing:
                            results['updated'] += 1
                        else:
                            results['created'] += 1
                            
                except Exception as e:
                    logger.error(f'Error processing AppViewX certificate {cert_data.get("serial_number", "unknown")}: {str(e)}')
                    results['errors'] += 1
                    
        except Exception as e:
            logger.error(f'AppViewX sync failed: {str(e)}')
            results['errors'] += 1
            
        return results
    
    def sync_from_ansible(self, dry_run=False, environment=None, server=None):
        """Sync KDB certificates from Ansible output"""
        results = {'created': 0, 'updated': 0, 'errors': 0}
        
        try:
            # This would run Ansible playbook and parse output
            certificates_data = self._fetch_ansible_certificates(environment, server)
            
            for cert_data in certificates_data:
                try:
                    if not dry_run:
                        certificate, created = KdbCertificate.objects.update_or_create(
                            serial_number=cert_data['serial_number'],
                            defaults={
                                'common_name': cert_data['common_name'],
                                'issuer': cert_data['issuer'],
                                'subject': cert_data['subject'],
                                'valid_from': cert_data['valid_from'],
                                'valid_to': cert_data['valid_to'],
                                'server_hostname': cert_data['server_hostname'],
                                'application_name': cert_data['application_name'],
                                'environment': cert_data['environment'],
                                'kdb_file_path': cert_data['kdb_file_path'],
                                'sync_source': 'ansible',
                                'last_sync': timezone.now(),
                            }
                        )
                        
                        if created:
                            results['created'] += 1
                        else:
                            results['updated'] += 1
                    else:
                        existing = KdbCertificate.objects.filter(
                            serial_number=cert_data['serial_number']
                        ).exists()
                        if existing:
                            results['updated'] += 1
                        else:
                            results['created'] += 1
                            
                except Exception as e:
                    logger.error(f'Error processing Ansible certificate {cert_data.get("serial_number", "unknown")}: {str(e)}')
                    results['errors'] += 1
                    
        except Exception as e:
            logger.error(f'Ansible sync failed: {str(e)}')
            results['errors'] += 1
            
        return results
    
    def _fetch_sql_certificates(self, environment=None, server=None):
        """Fetch certificates from SQL database (placeholder implementation)"""
        # This would use pyodbc or SQLAlchemy to connect to external database
        # For now, returning sample data
        sample_data = [
            {
                'serial_number': '1234567890ABCDEF',
                'common_name': 'app1.example.com',
                'issuer': 'CN=Internal CA, O=Company',
                'subject': 'CN=app1.example.com, O=Company',
                'valid_from': timezone.now() - timedelta(days=30),
                'valid_to': timezone.now() + timedelta(days=365),
                'server_hostname': 'server1.example.com',
                'application_name': 'WebApp1',
                'environment': 'production',
                'kdb_file_path': '/opt/IBM/HTTPServer/ssl/app1.kdb',
                'kdb_label': 'app1_cert',
                'external_id': 'sql_001'
            }
        ]
        
        # Apply filters
        if environment:
            sample_data = [cert for cert in sample_data if cert['environment'] == environment]
        if server:
            sample_data = [cert for cert in sample_data if server in cert['server_hostname']]
            
        return sample_data
    
    def _fetch_appviewx_certificates(self, environment=None, server=None):
        """Fetch certificates from AppViewX API (placeholder implementation)"""
        # This would use requests to call AppViewX API
        sample_data = [
            {
                'serial_number': 'FEDCBA0987654321',
                'common_name': 'api.example.com',
                'issuer': 'CN=External CA, O=TrustedCA',
                'subject': 'CN=api.example.com, O=Company',
                'valid_from': timezone.now() - timedelta(days=60),
                'valid_to': timezone.now() + timedelta(days=300),
                'server_hostname': 'server2.example.com',
                'application_name': 'API Gateway',
                'environment': 'production',
                'appviewx_id': 'avx_12345',
                'status': 'active'
            }
        ]
        
        if environment:
            sample_data = [cert for cert in sample_data if cert['environment'] == environment]
        if server:
            sample_data = [cert for cert in sample_data if server in cert['server_hostname']]
            
        return sample_data
    
    def _fetch_ansible_certificates(self, environment=None, server=None):
        """Fetch certificates from Ansible playbook output (placeholder implementation)"""
        # This would run ansible-playbook command and parse JSON output
        sample_data = [
            {
                'serial_number': 'ANSIBLE123456789',
                'common_name': 'web.example.com',
                'issuer': 'CN=Company Root CA, O=Company',
                'subject': 'CN=web.example.com, O=Company',
                'valid_from': timezone.now() - timedelta(days=90),
                'valid_to': timezone.now() + timedelta(days=275),
                'server_hostname': 'server3.example.com',
                'application_name': 'WebServer',
                'environment': 'production',
                'kdb_file_path': '/opt/IBM/HTTPServer/ssl/web.kdb'
            }
        ]
        
        if environment:
            sample_data = [cert for cert in sample_data if cert['environment'] == environment]
        if server:
            sample_data = [cert for cert in sample_data if server in cert['server_hostname']]
            
        return sample_data


class JavaSyncService:
    """Service for syncing Java certificates from keystore files"""
    
    def __init__(self, timeout=30):
        self.timeout = timeout
        self.cache_key = 'java_sync_last_run'
    
    def has_recent_sync(self, hours=2):
        """Check if sync was run recently"""
        last_sync = cache.get(self.cache_key)
        if last_sync:
            return timezone.now() - last_sync < timedelta(hours=hours)
        return False
    
    def update_last_sync(self):
        """Update last sync timestamp"""
        cache.set(self.cache_key, timezone.now(), 86400)  # 24 hours
    
    def get_target_servers(self, environment=None, server_hostname=None):
        """Get list of servers to scan for Java certificates"""
        # This would typically come from inventory system or configuration
        # For now, using sample server list
        servers = [
            {
                'hostname': 'java-app1.example.com',
                'ip_address': '192.168.1.10',
                'environment': 'production',
                'ssh_user': 'appuser',
                'ssh_key_path': '/path/to/ssh/key'
            },
            {
                'hostname': 'java-app2.example.com',
                'ip_address': '192.168.1.11',
                'environment': 'staging',
                'ssh_user': 'appuser',
                'ssh_key_path': '/path/to/ssh/key'
            }
        ]
        
        # Apply filters
        if environment:
            servers = [s for s in servers if s['environment'] == environment]
        if server_hostname:
            servers = [s for s in servers if server_hostname in s['hostname']]
            
        return servers
    
    def sync_server_certificates(self, hostname, ip_address, environment='', keystore_type_filter=None, dry_run=False):
        """Sync certificates from a specific server"""
        results = {
            'keystores_found': 0,
            'created': 0,
            'updated': 0,
            'errors': 0
        }
        
        try:
            # Find keystore files on the server
            keystores = self._find_keystores_on_server(hostname, ip_address)
            results['keystores_found'] = len(keystores)
            
            for keystore_info in keystores:
                try:
                    # Skip if keystore type filter is specified and doesn't match
                    if keystore_type_filter and keystore_info['type'] != keystore_type_filter:
                        continue
                    
                    # Extract certificates from keystore
                    certificates = self._extract_certificates_from_keystore(
                        hostname, ip_address, keystore_info
                    )
                    
                    for cert_data in certificates:
                        try:
                            cert_data.update({
                                'server_hostname': hostname,
                                'environment': environment,
                                'keystore_path': keystore_info['path'],
                                'keystore_type': keystore_info['type'],
                                'sync_source': 'ssh_keytool',
                                'last_sync': timezone.now(),
                            })
                            
                            if not dry_run:
                                certificate, created = JavaCertificate.objects.update_or_create(
                                    serial_number=cert_data['serial_number'],
                                    keystore_path=cert_data['keystore_path'],
                                    defaults=cert_data
                                )
                                
                                if created:
                                    results['created'] += 1
                                else:
                                    results['updated'] += 1
                            else:
                                # Dry run - check if would be created or updated
                                existing = JavaCertificate.objects.filter(
                                    serial_number=cert_data['serial_number'],
                                    keystore_path=cert_data['keystore_path']
                                ).exists()
                                if existing:
                                    results['updated'] += 1
                                else:
                                    results['created'] += 1
                                    
                        except Exception as e:
                            logger.error(f'Error processing certificate from {keystore_info["path"]}: {str(e)}')
                            results['errors'] += 1
                            
                except Exception as e:
                    logger.error(f'Error processing keystore {keystore_info["path"]}: {str(e)}')
                    results['errors'] += 1
                    
        except Exception as e:
            logger.error(f'Error scanning server {hostname}: {str(e)}')
            results['errors'] += 1
            
        return results
    
    def _find_keystores_on_server(self, hostname, ip_address):
        """Find keystore files on remote server via SSH"""
        # This would use paramiko to SSH to the server and find keystore files
        # For now, returning sample keystore locations
        sample_keystores = [
            {
                'path': '/opt/tomcat/conf/keystore.jks',
                'type': 'JKS',
                'application': 'Tomcat WebApp'
            },
            {
                'path': '/opt/app/ssl/app.p12',
                'type': 'PKCS12',
                'application': 'Java Application'
            }
        ]
        
        return sample_keystores
    
    def _extract_certificates_from_keystore(self, hostname, ip_address, keystore_info):
        """Extract certificate information from keystore using keytool"""
        # This would SSH to the server and run keytool commands
        # For now, returning sample certificate data
        sample_certificates = [
            {
                'common_name': f'java-app.{hostname.split(".")[1]}.com',
                'serial_number': f'JAVA{hostname.replace(".", "").upper()}001',
                'issuer': 'CN=Java App CA, O=Company',
                'subject': f'CN=java-app.{hostname.split(".")[1]}.com, O=Company',
                'valid_from': timezone.now() - timedelta(days=45),
                'valid_to': timezone.now() + timedelta(days=320),
                'alias_name': 'server_cert',
                'java_application': keystore_info['application'],
                'signature_algorithm': 'SHA256withRSA',
                'key_size': 2048,
                'is_server_auth': True,
                'is_client_auth': False,
                'is_code_signing': False
            }
        ]
        
        return sample_certificates


class CertificateStatsService:
    """Service for certificate statistics and dashboard data"""
    
    @staticmethod
    def get_dashboard_stats():
        """Get certificate statistics for dashboard"""
        today = timezone.now()
        
        # KDB Statistics
        kdb_total = KdbCertificate.objects.filter(is_active=True).count()
        kdb_expired = KdbCertificate.objects.filter(is_active=True, valid_to__lt=today).count()
        kdb_expiring_30 = KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today
        ).count()
        
        # Java Statistics
        java_total = JavaCertificate.objects.filter(is_active=True).count()
        java_expired = JavaCertificate.objects.filter(is_active=True, valid_to__lt=today).count()
        java_expiring_30 = JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today
        ).count()
        
        return {
            'kdb': {
                'total': kdb_total,
                'expired': kdb_expired,
                'expiring_30': kdb_expiring_30,
                'valid': kdb_total - kdb_expired - kdb_expiring_30
            },
            'java': {
                'total': java_total,
                'expired': java_expired,
                'expiring_30': java_expiring_30,
                'valid': java_total - java_expired - java_expiring_30
            },
            'total': {
                'certificates': kdb_total + java_total,
                'expired': kdb_expired + java_expired,
                'expiring_30': kdb_expiring_30 + java_expiring_30
            }
        }
    
    @staticmethod
    def get_expiring_certificates(days=30, limit=10):
        """Get certificates expiring within specified days"""
        today = timezone.now()
        cutoff_date = today + timedelta(days=days)
        
        # Get expiring KDB certificates
        kdb_certs = list(KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=cutoff_date,
            valid_to__gte=today
        ).order_by('valid_to').values(
            'id', 'common_name', 'server_hostname', 'application_name', 
            'valid_to', 'environment'
        )[:limit])
        
        # Get expiring Java certificates
        java_certs = list(JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=cutoff_date,
            valid_to__gte=today
        ).order_by('valid_to').values(
            'id', 'common_name', 'server_hostname', 'java_application', 
            'valid_to', 'environment'
        )[:limit])
        
        # Add certificate type
        for cert in kdb_certs:
            cert['type'] = 'kdb'
        for cert in java_certs:
            cert['type'] = 'java'
            cert['application_name'] = cert.get('java_application', '')
        
        # Combine and sort by expiry date
        all_certs = kdb_certs + java_certs
        all_certs.sort(key=lambda x: x['valid_to'])
        
        return all_certs[:limit]
