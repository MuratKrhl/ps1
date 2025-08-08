from celery import shared_task
from django.core.management import call_command
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from datetime import timedelta
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_duty_schedule_task(self, source_url=None, source_type='csv'):
    """
    Nöbet listesi senkronizasyon görevi
    """
    try:
        logger.info("Starting duty schedule sync task")
        
        # Management command'ı çalıştır
        call_command(
            'sync_duty_schedule',
            source_url=source_url or getattr(settings, 'DUTY_SCHEDULE_URL', ''),
            source_type=source_type,
            timeout=30
        )
        
        logger.info("Duty schedule sync completed successfully")
        return "Duty schedule sync completed"
        
    except Exception as exc:
        logger.error(f"Duty schedule sync failed: {exc}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying duty schedule sync, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (self.request.retries + 1), exc=exc)
        
        # Son deneme de başarısızsa e-posta gönder
        send_sync_error_notification.delay(str(exc))
        raise exc


@shared_task
def send_sync_error_notification(error_message):
    """
    Senkronizasyon hatası bildirim e-postası gönder
    """
    try:
        admin_emails = getattr(settings, 'DUTY_SCHEDULE_ADMIN_EMAILS', [])
        if not admin_emails:
            logger.warning("No admin emails configured for duty schedule notifications")
            return
        
        subject = "Nöbet Listesi Senkronizasyon Hatası"
        
        context = {
            'error_message': error_message,
            'timestamp': timezone.now(),
            'server_name': getattr(settings, 'SERVER_NAME', 'Portall'),
        }
        
        # HTML e-posta
        html_message = render_to_string('emails/duty_sync_error.html', context)
        
        # Plaintext e-posta
        plain_message = render_to_string('emails/duty_sync_error.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=getattr(settings, 'DUTY_SCHEDULE_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
            recipient_list=admin_emails,
            fail_silently=False
        )
        
        logger.info(f"Duty sync error notification sent to {len(admin_emails)} admins")
        
    except Exception as e:
        logger.error(f"Failed to send duty sync error notification: {e}")


@shared_task
def send_daily_duty_notification():
    """
    Günlük nöbetçi bildirim e-postası gönder
    """
    try:
        from .models import Nobetci
        
        current_duty = Nobetci.get_current_duty()
        next_duty = Nobetci.get_next_duty()
        
        if not current_duty and not next_duty:
            logger.info("No current or next duty found, skipping notification")
            return
        
        # Bildirim alacak e-posta listesi
        notification_emails = getattr(settings, 'DUTY_NOTIFICATION_EMAILS', [])
        if not notification_emails:
            logger.warning("No notification emails configured for daily duty notifications")
            return
        
        subject = f"Günlük Nöbet Bildirimi - {timezone.now().strftime('%d.%m.%Y')}"
        
        context = {
            'current_duty': current_duty,
            'next_duty': next_duty,
            'date': timezone.now().date(),
            'server_name': getattr(settings, 'SERVER_NAME', 'Portall'),
        }
        
        # HTML e-posta
        html_message = render_to_string('emails/daily_duty_notification.html', context)
        
        # Plaintext e-posta
        plain_message = render_to_string('emails/daily_duty_notification.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=getattr(settings, 'DUTY_SCHEDULE_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
            recipient_list=notification_emails,
            fail_silently=False
        )
        
        logger.info(f"Daily duty notification sent to {len(notification_emails)} recipients")
        
    except Exception as e:
        logger.error(f"Failed to send daily duty notification: {e}")


@shared_task
def cleanup_old_duty_records():
    """
    Eski nöbet kayıtlarını temizle (6 ay öncesi)
    """
    try:
        from .models import Nobetci
        
        # 6 ay öncesi
        cutoff_date = timezone.now().date() - timedelta(days=180)
        
        # Eski kayıtları sil
        deleted_count = Nobetci.objects.filter(tarih__lt=cutoff_date).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old duty records older than {cutoff_date}")
        return f"Cleaned up {deleted_count} old duty records"
        
    except Exception as e:
        logger.error(f"Failed to cleanup old duty records: {e}")
        raise e


@shared_task
def generate_weekly_duty_report():
    """
    Haftalık nöbet raporu oluştur ve gönder
    """
    try:
        from .models import Nobetci
        
        # Bu hafta ve gelecek hafta
        today = timezone.now().date()
        week_start = today - timedelta(days=today.weekday())
        week_end = week_start + timedelta(days=6)
        next_week_start = week_end + timedelta(days=1)
        next_week_end = next_week_start + timedelta(days=6)
        
        # Bu hafta nöbetçileri
        this_week_duties = Nobetci.objects.filter(
            tarih__gte=week_start,
            tarih__lte=week_end
        ).order_by('tarih')
        
        # Gelecek hafta nöbetçileri
        next_week_duties = Nobetci.objects.filter(
            tarih__gte=next_week_start,
            tarih__lte=next_week_end
        ).order_by('tarih')
        
        # Rapor alacak e-posta listesi
        report_emails = getattr(settings, 'DUTY_REPORT_EMAILS', [])
        if not report_emails:
            logger.warning("No report emails configured for weekly duty reports")
            return
        
        subject = f"Haftalık Nöbet Raporu - {week_start.strftime('%d.%m.%Y')} - {week_end.strftime('%d.%m.%Y')}"
        
        context = {
            'week_start': week_start,
            'week_end': week_end,
            'next_week_start': next_week_start,
            'next_week_end': next_week_end,
            'this_week_duties': this_week_duties,
            'next_week_duties': next_week_duties,
            'total_duties': Nobetci.objects.count(),
            'server_name': getattr(settings, 'SERVER_NAME', 'Portall'),
        }
        
        # HTML e-posta
        html_message = render_to_string('emails/weekly_duty_report.html', context)
        
        # Plaintext e-posta
        plain_message = render_to_string('emails/weekly_duty_report.txt', context)
        
        send_mail(
            subject=subject,
            message=plain_message,
            html_message=html_message,
            from_email=getattr(settings, 'DUTY_SCHEDULE_FROM_EMAIL', settings.DEFAULT_FROM_EMAIL),
            recipient_list=report_emails,
            fail_silently=False
        )
        
        logger.info(f"Weekly duty report sent to {len(report_emails)} recipients")
        
    except Exception as e:
        logger.error(f"Failed to generate weekly duty report: {e}")
        raise e
