"""
Management command for sending certificate expiry alerts
"""
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from sertifikalar.models import KdbCertificate, JavaCertificate, CertificateAlert, CertificateNotification
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Send certificate expiry alerts via email'

    def add_arguments(self, parser):
        parser.add_argument(
            '--alert-type',
            type=str,
            choices=['90_days', '60_days', '30_days', '15_days', '7_days', '1_day', 'expired', 'all'],
            default='all',
            help='Specific alert type to send',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what alerts would be sent without actually sending them',
        )
        parser.add_argument(
            '--force',
            action='store_true',
            help='Send alerts even if they were sent recently',
        )
        parser.add_argument(
            '--certificate-type',
            type=str,
            choices=['kdb', 'java', 'all'],
            default='all',
            help='Certificate type to check',
        )

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS('Starting certificate expiry alert check...')
        )
        
        alert_type = options['alert_type']
        dry_run = options['dry_run']
        force = options['force']
        cert_type = options['certificate_type']
        
        if dry_run:
            self.stdout.write(
                self.style.WARNING('DRY RUN MODE - No emails will be sent')
            )
        
        try:
            # Get active alert configurations
            alert_configs = CertificateAlert.objects.filter(is_active=True)
            
            if alert_type != 'all':
                alert_configs = alert_configs.filter(alert_type=alert_type)
            
            if not alert_configs.exists():
                self.stdout.write(
                    self.style.WARNING('No active alert configurations found')
                )
                return
            
            total_alerts_sent = 0
            total_errors = 0
            
            for alert_config in alert_configs:
                self.stdout.write(f'Processing {alert_config.get_alert_type_display()} alerts...')
                
                try:
                    # Get certificates matching this alert type
                    certificates = self._get_certificates_for_alert(
                        alert_config.alert_type, cert_type
                    )
                    
                    if not certificates:
                        self.stdout.write(f'  No certificates found for {alert_config.alert_type}')
                        continue
                    
                    self.stdout.write(f'  Found {len(certificates)} certificates')
                    
                    # Filter out certificates that already have recent notifications (unless forced)
                    if not force:
                        certificates = self._filter_recent_notifications(
                            certificates, alert_config.alert_type
                        )
                        self.stdout.write(f'  {len(certificates)} certificates after filtering recent notifications')
                    
                    if not certificates:
                        continue
                    
                    # Send alerts for each certificate
                    for cert_info in certificates:
                        try:
                            if not dry_run:
                                self._send_certificate_alert(cert_info, alert_config)
                            
                            self.stdout.write(
                                f'    ✓ Alert sent for {cert_info["common_name"]} '
                                f'({cert_info["type"]}) - expires {cert_info["valid_to"].strftime("%Y-%m-%d")}'
                            )
                            total_alerts_sent += 1
                            
                        except Exception as e:
                            self.stdout.write(
                                self.style.ERROR(
                                    f'    ✗ Failed to send alert for {cert_info["common_name"]}: {str(e)}'
                                )
                            )
                            total_errors += 1
                            logger.error(f'Failed to send alert for certificate {cert_info["id"]}: {str(e)}')
                
                except Exception as e:
                    self.stdout.write(
                        self.style.ERROR(f'Error processing {alert_config.alert_type}: {str(e)}')
                    )
                    total_errors += 1
            
            # Print summary
            self.stdout.write('\n' + '='*50)
            self.stdout.write(self.style.SUCCESS('Certificate Alert Summary:'))
            self.stdout.write(f'Total alerts sent: {total_alerts_sent}')
            self.stdout.write(f'Total errors: {total_errors}')
            
            if total_errors > 0:
                self.stdout.write(
                    self.style.WARNING(f'Completed with {total_errors} errors')
                )
                exit(1)
            else:
                self.stdout.write(
                    self.style.SUCCESS('Alert check completed successfully!')
                )
                
        except Exception as e:
            logger.error(f'Certificate alert check failed: {str(e)}')
            raise CommandError(f'Alert check failed: {str(e)}')
    
    def _get_certificates_for_alert(self, alert_type, cert_type):
        """Get certificates that match the alert criteria"""
        today = timezone.now()
        certificates = []
        
        # Define date ranges for each alert type
        alert_days = {
            '90_days': 90,
            '60_days': 60,
            '30_days': 30,
            '15_days': 15,
            '7_days': 7,
            '1_day': 1,
            'expired': 0
        }
        
        if alert_type == 'expired':
            # Expired certificates
            cutoff_date = today
            filter_condition = {'valid_to__lt': cutoff_date, 'is_active': True, 'is_monitored': True}
        else:
            # Expiring certificates
            days = alert_days.get(alert_type, 30)
            cutoff_date = today + timedelta(days=days)
            next_alert_cutoff = today + timedelta(days=alert_days.get(alert_type, 30) + 1) if alert_type != '90_days' else None
            
            filter_condition = {
                'valid_to__lte': cutoff_date,
                'valid_to__gte': today,
                'is_active': True,
                'is_monitored': True
            }
            
            if next_alert_cutoff:
                filter_condition['valid_to__gt'] = next_alert_cutoff
        
        # Get KDB certificates
        if cert_type in ['kdb', 'all']:
            kdb_certs = KdbCertificate.objects.filter(**filter_condition).values(
                'id', 'common_name', 'serial_number', 'server_hostname', 
                'application_name', 'valid_to', 'environment', 'days_until_expiry'
            )
            for cert in kdb_certs:
                cert['type'] = 'kdb'
                certificates.append(cert)
        
        # Get Java certificates
        if cert_type in ['java', 'all']:
            java_certs = JavaCertificate.objects.filter(**filter_condition).values(
                'id', 'common_name', 'serial_number', 'server_hostname', 
                'java_application', 'valid_to', 'environment', 'days_until_expiry'
            )
            for cert in java_certs:
                cert['type'] = 'java'
                cert['application_name'] = cert.get('java_application', '')
                certificates.append(cert)
        
        return certificates
    
    def _filter_recent_notifications(self, certificates, alert_type):
        """Filter out certificates that have recent notifications"""
        filtered_certificates = []
        
        for cert_info in certificates:
            # Check if notification was sent recently (within 24 hours for same alert type)
            recent_notification = CertificateNotification.objects.filter(
                certificate_type=cert_info['type'],
                certificate_id=cert_info['id'],
                alert_type=alert_type,
                is_sent=True,
                sent_at__gte=timezone.now() - timedelta(hours=24)
            ).exists()
            
            if not recent_notification:
                filtered_certificates.append(cert_info)
        
        return filtered_certificates
    
    def _send_certificate_alert(self, cert_info, alert_config):
        """Send email alert for a specific certificate"""
        # Prepare email context
        context = {
            'common_name': cert_info['common_name'],
            'serial_number': cert_info['serial_number'],
            'server_hostname': cert_info['server_hostname'],
            'application_name': cert_info.get('application_name', ''),
            'valid_to': cert_info['valid_to'],
            'days_until_expiry': cert_info.get('days_until_expiry', 0),
            'environment': cert_info.get('environment', ''),
            'certificate_type': cert_info['type'].upper(),
            'alert_type': alert_config.get_alert_type_display(),
        }
        
        # Format email subject and body
        subject = alert_config.email_subject_template.format(**context)
        body = alert_config.email_body_template.format(**context)
        
        # Get recipients
        recipients = alert_config.get_recipient_list()
        
        if not recipients:
            raise ValueError('No email recipients configured')
        
        # Create notification record
        notification = CertificateNotification.objects.create(
            certificate_type=cert_info['type'],
            certificate_id=cert_info['id'],
            certificate_common_name=cert_info['common_name'],
            alert_type=alert_config.alert_type,
            sent_to=', '.join(recipients),
            email_subject=subject,
            is_sent=False
        )
        
        try:
            # Send email
            send_mail(
                subject=subject,
                message=body,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portall.local'),
                recipient_list=recipients,
                fail_silently=False,
            )
            
            # Update notification record
            notification.is_sent = True
            notification.sent_at = timezone.now()
            notification.save()
            
        except Exception as e:
            # Update notification record with error
            notification.error_message = str(e)
            notification.save()
            raise e
