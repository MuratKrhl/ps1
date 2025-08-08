"""
Sertifika modülü için Celery görevleri
"""
from celery import shared_task
from django.core.management import call_command
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_kdb_certificates(self, source=None, force=False):
    """
    KDB sertifikalarını senkronize et
    """
    try:
        logger.info(f"KDB sertifika senkronizasyonu başlatıldı - Kaynak: {source}")
        
        # Management command'ı çalıştır
        command_args = []
        if source:
            command_args.extend(['--source', source])
        if force:
            command_args.append('--force')
        
        call_command('sync_kdb_certificates', *command_args)
        
        logger.info("KDB sertifika senkronizasyonu başarıyla tamamlandı")
        return {
            'success': True,
            'message': 'KDB sertifikaları başarıyla senkronize edildi',
            'source': source,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"KDB sertifika senkronizasyonu hatası: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Yeniden denenecek ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        return {
            'success': False,
            'message': f'KDB sertifika senkronizasyonu başarısız: {str(exc)}',
            'source': source,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=3)
def sync_java_certificates(self, server_filter=None, force=False):
    """
    Java sertifikalarını senkronize et
    """
    try:
        logger.info(f"Java sertifika senkronizasyonu başlatıldı - Sunucu filtresi: {server_filter}")
        
        # Management command'ı çalıştır
        command_args = []
        if server_filter:
            command_args.extend(['--server', server_filter])
        if force:
            command_args.append('--force')
        
        call_command('sync_java_certificates', *command_args)
        
        logger.info("Java sertifika senkronizasyonu başarıyla tamamlandı")
        return {
            'success': True,
            'message': 'Java sertifikaları başarıyla senkronize edildi',
            'server_filter': server_filter,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Java sertifika senkronizasyonu hatası: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Yeniden denenecek ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=60 * (2 ** self.request.retries), exc=exc)
        
        return {
            'success': False,
            'message': f'Java sertifika senkronizasyonu başarısız: {str(exc)}',
            'server_filter': server_filter,
            'timestamp': timezone.now().isoformat()
        }


@shared_task(bind=True, max_retries=2)
def send_certificate_expiry_alerts(self, alert_type=None, force=False):
    """
    Sertifika süre dolumu uyarılarını gönder
    """
    try:
        logger.info(f"Sertifika süre uyarıları gönderimi başlatıldı - Tip: {alert_type}")
        
        # Management command'ı çalıştır
        command_args = []
        if alert_type:
            command_args.extend(['--alert-type', alert_type])
        if force:
            command_args.append('--force')
        
        call_command('send_certificate_alerts', *command_args)
        
        logger.info("Sertifika süre uyarıları başarıyla gönderildi")
        return {
            'success': True,
            'message': 'Sertifika süre uyarıları başarıyla gönderildi',
            'alert_type': alert_type,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as exc:
        logger.error(f"Sertifika süre uyarıları gönderimi hatası: {str(exc)}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Yeniden denenecek ({self.request.retries + 1}/{self.max_retries})")
            raise self.retry(countdown=300, exc=exc)  # 5 dakika bekle
        
        return {
            'success': False,
            'message': f'Sertifika süre uyarıları gönderimi başarısız: {str(exc)}',
            'alert_type': alert_type,
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def daily_certificate_sync():
    """
    Günlük sertifika senkronizasyonu (tüm kaynaklar)
    """
    logger.info("Günlük sertifika senkronizasyonu başlatıldı")
    
    results = {
        'kdb_sync': None,
        'java_sync': None,
        'timestamp': timezone.now().isoformat()
    }
    
    # KDB sertifikaları senkronize et
    try:
        kdb_result = sync_kdb_certificates.delay()
        results['kdb_sync'] = kdb_result.get(timeout=1800)  # 30 dakika timeout
    except Exception as e:
        logger.error(f"KDB günlük senkronizasyon hatası: {str(e)}")
        results['kdb_sync'] = {'success': False, 'error': str(e)}
    
    # Java sertifikaları senkronize et
    try:
        java_result = sync_java_certificates.delay()
        results['java_sync'] = java_result.get(timeout=1800)  # 30 dakika timeout
    except Exception as e:
        logger.error(f"Java günlük senkronizasyon hatası: {str(e)}")
        results['java_sync'] = {'success': False, 'error': str(e)}
    
    logger.info("Günlük sertifika senkronizasyonu tamamlandı")
    return results


@shared_task
def daily_certificate_alerts():
    """
    Günlük sertifika süre uyarıları
    """
    logger.info("Günlük sertifika süre uyarıları başlatıldı")
    
    results = {
        'expired_alerts': None,
        'expiring_7_alerts': None,
        'expiring_30_alerts': None,
        'timestamp': timezone.now().isoformat()
    }
    
    # Süresi dolmuş sertifikalar için uyarı
    try:
        expired_result = send_certificate_expiry_alerts.delay(alert_type='expired')
        results['expired_alerts'] = expired_result.get(timeout=600)  # 10 dakika timeout
    except Exception as e:
        logger.error(f"Süresi dolmuş sertifika uyarıları hatası: {str(e)}")
        results['expired_alerts'] = {'success': False, 'error': str(e)}
    
    # 7 gün içinde dolacak sertifikalar için uyarı
    try:
        expiring_7_result = send_certificate_expiry_alerts.delay(alert_type='expiring_7')
        results['expiring_7_alerts'] = expiring_7_result.get(timeout=600)
    except Exception as e:
        logger.error(f"7 gün içinde dolacak sertifika uyarıları hatası: {str(e)}")
        results['expiring_7_alerts'] = {'success': False, 'error': str(e)}
    
    # 30 gün içinde dolacak sertifikalar için uyarı (haftalık)
    if timezone.now().weekday() == 0:  # Pazartesi günleri
        try:
            expiring_30_result = send_certificate_expiry_alerts.delay(alert_type='expiring_30')
            results['expiring_30_alerts'] = expiring_30_result.get(timeout=600)
        except Exception as e:
            logger.error(f"30 gün içinde dolacak sertifika uyarıları hatası: {str(e)}")
            results['expiring_30_alerts'] = {'success': False, 'error': str(e)}
    
    logger.info("Günlük sertifika süre uyarıları tamamlandı")
    return results


@shared_task
def weekly_certificate_report():
    """
    Haftalık sertifika raporu
    """
    try:
        from .models import KdbCertificate, JavaCertificate, CertificateNotification
        from .services import CertificateStatsService
        
        logger.info("Haftalık sertifika raporu oluşturuluyor")
        
        # İstatistikleri al
        stats_service = CertificateStatsService()
        kdb_stats = stats_service.get_kdb_stats()
        java_stats = stats_service.get_java_stats()
        
        # Son hafta bildirimleri
        last_week = timezone.now() - timedelta(days=7)
        weekly_notifications = CertificateNotification.objects.filter(
            sent_at__gte=last_week
        ).count()
        
        # Rapor içeriği
        report_data = {
            'week_start': last_week.strftime('%d.%m.%Y'),
            'week_end': timezone.now().strftime('%d.%m.%Y'),
            'kdb_stats': kdb_stats,
            'java_stats': java_stats,
            'total_certificates': kdb_stats['total'] + java_stats['total'],
            'total_expiring': kdb_stats['expiring_30'] + java_stats['expiring_30'],
            'total_expired': kdb_stats['expired'] + java_stats['expired'],
            'weekly_notifications': weekly_notifications,
            'portal_url': getattr(settings, 'SITE_URL', 'http://localhost:8000')
        }
        
        # E-posta gönder
        subject = f"Portall - Haftalık Sertifika Raporu ({report_data['week_start']} - {report_data['week_end']})"
        
        # HTML ve text versiyonları
        html_message = render_to_string('emails/weekly_certificate_report.html', report_data)
        plain_message = render_to_string('emails/weekly_certificate_report.txt', report_data)
        
        # Yönetici e-postalarına gönder
        admin_emails = getattr(settings, 'CERTIFICATE_ADMIN_EMAILS', [])
        if not admin_emails:
            admin_emails = [admin[1] for admin in settings.ADMINS]
        
        if admin_emails:
            send_mail(
                subject=subject,
                message=plain_message,
                html_message=html_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=admin_emails,
                fail_silently=False
            )
            
            logger.info(f"Haftalık sertifika raporu {len(admin_emails)} yöneticiye gönderildi")
        
        return {
            'success': True,
            'message': f'Haftalık rapor {len(admin_emails)} yöneticiye gönderildi',
            'report_data': report_data,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Haftalık sertifika raporu hatası: {str(e)}")
        return {
            'success': False,
            'message': f'Haftalık rapor oluşturulamadı: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }


@shared_task
def cleanup_old_notifications():
    """
    Eski bildirimleri temizle (90 günden eski)
    """
    try:
        from .models import CertificateNotification
        
        cutoff_date = timezone.now() - timedelta(days=90)
        deleted_count, _ = CertificateNotification.objects.filter(
            sent_at__lt=cutoff_date
        ).delete()
        
        logger.info(f"90 günden eski {deleted_count} bildirim temizlendi")
        
        return {
            'success': True,
            'deleted_count': deleted_count,
            'cutoff_date': cutoff_date.isoformat(),
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Bildirim temizleme hatası: {str(e)}")
        return {
            'success': False,
            'message': f'Bildirim temizleme başarısız: {str(e)}',
            'timestamp': timezone.now().isoformat()
        }
