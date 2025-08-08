from celery import shared_task
from django.utils import timezone
from django.core.management import call_command
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string
from .models import Announcement
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def archive_expired_announcements(self):
    """
    Celery task to automatically archive expired announcements
    """
    try:
        # Call the management command
        call_command('archive_expired_announcements', verbosity=1)
        logger.info("Successfully ran archive_expired_announcements command")
        return "Archive task completed successfully"
    
    except Exception as exc:
        logger.error(f"Error in archive_expired_announcements task: {str(exc)}")
        # Retry the task with exponential backoff
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task(bind=True, max_retries=3)
def send_announcement_notifications(self, announcement_id):
    """
    Send email notifications for new announcements
    """
    try:
        announcement = Announcement.objects.get(id=announcement_id)
        
        if not announcement.send_email:
            return "Email notification not enabled for this announcement"
        
        # Get recipient list
        recipients = []
        if hasattr(settings, 'ANNOUNCEMENT_ADMIN_EMAILS'):
            recipients.extend(settings.ANNOUNCEMENT_ADMIN_EMAILS.split(','))
        
        if not recipients:
            logger.warning("No recipients configured for announcement notifications")
            return "No recipients configured"
        
        # Prepare email content
        subject = f"Yeni Duyuru: {announcement.title}"
        
        # HTML email
        html_message = render_to_string('emails/announcement_notification.html', {
            'announcement': announcement,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        # Plain text email
        plain_message = render_to_string('emails/announcement_notification.txt', {
            'announcement': announcement,
            'site_url': getattr(settings, 'SITE_URL', 'http://localhost:8000'),
        })
        
        # Send email
        send_mail(
            subject=subject,
            message=plain_message,
            from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portall.com'),
            recipient_list=recipients,
            html_message=html_message,
            fail_silently=False
        )
        
        logger.info(f"Sent notification email for announcement: {announcement.title}")
        return f"Email sent successfully to {len(recipients)} recipients"
        
    except Announcement.DoesNotExist:
        logger.error(f"Announcement with ID {announcement_id} not found")
        return "Announcement not found"
    
    except Exception as exc:
        logger.error(f"Error sending announcement notification: {str(exc)}")
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))


@shared_task
def daily_announcement_maintenance():
    """
    Daily maintenance task for announcements
    - Archive expired announcements
    - Clean up old view records
    - Generate statistics
    """
    try:
        # Archive expired announcements
        archive_expired_announcements.delay()
        
        # Clean up old announcement views (older than 1 year)
        from .models import AnnouncementView
        one_year_ago = timezone.now() - timezone.timedelta(days=365)
        deleted_count = AnnouncementView.objects.filter(
            viewed_at__lt=one_year_ago
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old announcement view records")
        
        # Update announcement statistics
        total_announcements = Announcement.objects.count()
        published_announcements = Announcement.objects.filter(status='published').count()
        draft_announcements = Announcement.objects.filter(status='draft').count()
        archived_announcements = Announcement.objects.filter(status='archived').count()
        
        logger.info(f"Announcement statistics - Total: {total_announcements}, "
                   f"Published: {published_announcements}, Draft: {draft_announcements}, "
                   f"Archived: {archived_announcements}")
        
        return "Daily maintenance completed successfully"
        
    except Exception as exc:
        logger.error(f"Error in daily announcement maintenance: {str(exc)}")
        raise exc


@shared_task
def weekly_announcement_report():
    """
    Generate weekly announcement activity report
    """
    try:
        from django.db.models import Count
        from datetime import timedelta
        
        now = timezone.now()
        week_ago = now - timedelta(days=7)
        
        # Get weekly statistics
        new_announcements = Announcement.objects.filter(
            created_at__gte=week_ago
        ).count()
        
        published_this_week = Announcement.objects.filter(
            published_at__gte=week_ago
        ).count()
        
        archived_this_week = Announcement.objects.filter(
            status='archived',
            updated_at__gte=week_ago
        ).count()
        
        # Most viewed announcements this week
        from .models import AnnouncementView
        popular_announcements = AnnouncementView.objects.filter(
            viewed_at__gte=week_ago
        ).values('announcement__title').annotate(
            view_count=Count('id')
        ).order_by('-view_count')[:5]
        
        # Prepare report data
        report_data = {
            'week_start': week_ago.strftime('%Y-%m-%d'),
            'week_end': now.strftime('%Y-%m-%d'),
            'new_announcements': new_announcements,
            'published_this_week': published_this_week,
            'archived_this_week': archived_this_week,
            'popular_announcements': list(popular_announcements),
            'total_active': Announcement.objects.filter(status='published').count(),
        }
        
        # Send report email to admins
        recipients = []
        if hasattr(settings, 'ANNOUNCEMENT_ADMIN_EMAILS'):
            recipients.extend(settings.ANNOUNCEMENT_ADMIN_EMAILS.split(','))
        
        if recipients:
            subject = f"Haftalık Duyuru Raporu - {week_ago.strftime('%d.%m.%Y')} - {now.strftime('%d.%m.%Y')}"
            
            html_message = render_to_string('emails/weekly_announcement_report.html', report_data)
            plain_message = render_to_string('emails/weekly_announcement_report.txt', report_data)
            
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@portall.com'),
                recipient_list=recipients,
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Weekly announcement report sent to {len(recipients)} recipients")
        
        return f"Weekly report generated and sent to {len(recipients)} recipients"
        
    except Exception as exc:
        logger.error(f"Error generating weekly announcement report: {str(exc)}")
        raise exc
