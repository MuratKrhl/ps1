from celery import shared_task
from django.core.management import call_command
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from django.db.models import Count
from datetime import timedelta
import logging

from .models import AskGTDocument

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=3)
def sync_documents_from_api(self):
    """
    Harici API'den AskGT dokümanlarını senkronize et
    """
    try:
        logger.info("AskGT doküman senkronizasyonu başlatılıyor...")
        
        # Management command'ı çalıştır
        call_command('sync_askgt_documents')
        
        logger.info("AskGT doküman senkronizasyonu tamamlandı")
        return "AskGT documents synced successfully"
        
    except Exception as exc:
        logger.error(f"AskGT sync error: {exc}")
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying in 60 seconds... (attempt {self.request.retries + 1})")
            raise self.retry(countdown=60, exc=exc)
        else:
            logger.error("Max retries reached for AskGT sync")
            return f"AskGT sync failed after {self.max_retries} retries: {exc}"


@shared_task
def send_weekly_stats_report():
    """
    AskGT haftalık istatistik raporu gönder
    """
    try:
        # Son 7 günün istatistikleri
        week_ago = timezone.now() - timedelta(days=7)
        
        # Bu hafta eklenen dokümanlar
        new_documents = AskGTDocument.objects.filter(
            is_active=True,
            eklenme_tarihi__gte=week_ago
        ).order_by('-eklenme_tarihi')
        
        # Bu hafta en çok görüntülenen dokümanlar
        popular_this_week = AskGTDocument.objects.filter(
            is_active=True,
            view_count__gt=0
        ).order_by('-view_count')[:10]
        
        # Kategori dağılımı
        category_stats = (
            AskGTDocument.objects
            .filter(is_active=True)
            .values('kategori')
            .annotate(count=Count('id'))
            .order_by('-count')
        )
        
        # Genel istatistikler
        total_documents = AskGTDocument.objects.filter(is_active=True).count()
        total_categories = category_stats.count()
        total_views = sum(doc.view_count for doc in AskGTDocument.objects.filter(is_active=True))
        
        # E-posta içeriği hazırla
        context = {
            'week_start': week_ago.strftime('%d.%m.%Y'),
            'week_end': timezone.now().strftime('%d.%m.%Y'),
            'new_documents': new_documents,
            'new_documents_count': new_documents.count(),
            'popular_documents': popular_this_week,
            'category_stats': category_stats,
            'total_documents': total_documents,
            'total_categories': total_categories,
            'total_views': total_views,
        }
        
        # HTML ve text versiyonları
        html_message = render_to_string('emails/askgt_weekly_report.html', context)
        text_message = render_to_string('emails/askgt_weekly_report.txt', context)
        
        # E-posta gönder
        recipient_list = [
            settings.ASKGT_ADMIN_EMAIL,
            settings.DEFAULT_FROM_EMAIL,
        ]
        
        send_mail(
            subject=f'AskGT Haftalık Raporu - {week_ago.strftime("%d.%m.%Y")} / {timezone.now().strftime("%d.%m.%Y")}',
            message=text_message,
            from_email=settings.ASKGT_FROM_EMAIL,
            recipient_list=recipient_list,
            html_message=html_message,
            fail_silently=False,
        )
        
        logger.info(f"AskGT haftalık raporu gönderildi: {len(recipient_list)} alıcı")
        return f"Weekly report sent to {len(recipient_list)} recipients"
        
    except Exception as e:
        logger.error(f"AskGT weekly report error: {e}")
        return f"Weekly report failed: {e}"


@shared_task
def cleanup_old_documents():
    """
    Eski ve kullanılmayan dokümanları temizle
    """
    try:
        # 6 ay önce
        six_months_ago = timezone.now() - timedelta(days=180)
        
        # Hiç görüntülenmemiş ve 6 aydan eski dokümanlar
        old_documents = AskGTDocument.objects.filter(
            view_count=0,
            eklenme_tarihi__lt=six_months_ago,
            is_active=True
        )
        
        count = old_documents.count()
        
        if count > 0:
            # Pasif yap (silme)
            old_documents.update(is_active=False)
            logger.info(f"AskGT: {count} eski doküman pasif yapıldı")
            return f"Deactivated {count} old documents"
        else:
            logger.info("AskGT: Temizlenecek eski doküman bulunamadı")
            return "No old documents to cleanup"
            
    except Exception as e:
        logger.error(f"AskGT cleanup error: {e}")
        return f"Cleanup failed: {e}"


@shared_task
def update_document_stats():
    """
    Doküman istatistiklerini güncelle ve cache'i temizle
    """
    try:
        from django.core.cache import cache
        
        # Cache anahtarlarını temizle
        cache.delete('askgt_categories_menu')
        cache.delete('askgt_stats')
        
        # Yeni istatistikleri hesapla ve cache'e koy
        categories = (
            AskGTDocument.objects
            .filter(is_active=True)
            .values('kategori')
            .annotate(count=Count('id'))
            .order_by('kategori')
        )
        
        cache.set('askgt_categories_menu', list(categories), 60 * 15)
        
        stats = {
            'total_documents': AskGTDocument.objects.filter(is_active=True).count(),
            'total_categories': len(categories),
        }
        
        cache.set('askgt_stats', stats, 60 * 30)
        
        logger.info("AskGT istatistikleri güncellendi ve cache temizlendi")
        return "Document stats updated and cache cleared"
        
    except Exception as e:
        logger.error(f"AskGT stats update error: {e}")
        return f"Stats update failed: {e}"
