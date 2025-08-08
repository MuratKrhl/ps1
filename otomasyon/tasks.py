from celery import shared_task
from django.utils import timezone
from .models import PlaybookExecution, AutomationSchedule, AutomationLog
from .services import AnsibleService, ScheduleManager
import logging

logger = logging.getLogger(__name__)


@shared_task(bind=True)
def execute_ansible_playbook(self, execution_id):
    """Ansible playbook çalıştırma task'ı"""
    try:
        execution = PlaybookExecution.objects.get(id=execution_id)
        
        # Task ID'yi kaydet
        execution.task_id = self.request.id
        execution.save()
        
        # Ansible servisini başlat
        ansible_service = AnsibleService()
        result = ansible_service.execute_playbook(execution_id)
        
        # Sonucu döndür
        return {
            'execution_id': execution_id,
            'status': result.status,
            'return_code': result.return_code,
            'duration': str(result.duration) if result.duration else None
        }
        
    except PlaybookExecution.DoesNotExist:
        logger.error(f"PlaybookExecution bulunamadı: {execution_id}")
        return {'error': 'Execution not found'}
    
    except Exception as e:
        logger.error(f"Playbook çalıştırma hatası: {str(e)}")
        return {'error': str(e)}


@shared_task
def process_scheduled_playbooks():
    """Programlı playbook'ları kontrol et ve çalıştır"""
    try:
        now = timezone.now()
        
        # Çalıştırılacak programları bul
        due_schedules = AutomationSchedule.objects.filter(
            is_enabled=True,
            next_run__lte=now
        )
        
        executed_count = 0
        
        for schedule in due_schedules:
            try:
                # Yeni çalıştırma kaydı oluştur
                execution = PlaybookExecution.objects.create(
                    playbook=schedule.playbook,
                    executor_id=1,  # System user
                    execution_id=f"scheduled_{schedule.id}_{now.strftime('%Y%m%d_%H%M%S')}",
                    variables=schedule.variables,
                    status='approved'  # Programlı görevler otomatik onaylı
                )
                
                # Playbook'ı çalıştır
                execute_ansible_playbook.delay(execution.id)
                
                # Program istatistiklerini güncelle
                schedule.last_run = now
                schedule.run_count += 1
                
                # Sonraki çalıştırma zamanını hesapla
                schedule.next_run = ScheduleManager.calculate_next_run(schedule)
                schedule.save()
                
                executed_count += 1
                
                # Log kaydet
                AutomationLog.objects.create(
                    level='info',
                    message=f"Programlı görev çalıştırıldı: {schedule.name}",
                    playbook_execution=execution
                )
                
            except Exception as e:
                logger.error(f"Programlı görev çalıştırma hatası {schedule.id}: {str(e)}")
                AutomationLog.objects.create(
                    level='error',
                    message=f"Programlı görev hatası {schedule.name}: {str(e)}"
                )
        
        return {
            'processed_schedules': executed_count,
            'timestamp': now.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Programlı görev işleme hatası: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_executions():
    """Eski çalıştırma kayıtlarını temizle"""
    try:
        from datetime import timedelta
        
        # 30 günden eski kayıtları sil
        cutoff_date = timezone.now() - timedelta(days=30)
        
        old_executions = PlaybookExecution.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['completed', 'failed', 'cancelled']
        )
        
        deleted_count = old_executions.count()
        old_executions.delete()
        
        # Log kaydet
        AutomationLog.objects.create(
            level='info',
            message=f"Eski çalıştırma kayıtları temizlendi: {deleted_count} kayıt"
        )
        
        return {
            'deleted_executions': deleted_count,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Temizlik hatası: {str(e)}")
        return {'error': str(e)}


@shared_task
def cleanup_old_logs():
    """Eski log kayıtlarını temizle"""
    try:
        from datetime import timedelta
        
        # 7 günden eski debug logları sil
        cutoff_date = timezone.now() - timedelta(days=7)
        old_debug_logs = AutomationLog.objects.filter(
            created_at__lt=cutoff_date,
            level='debug'
        )
        debug_deleted = old_debug_logs.count()
        old_debug_logs.delete()
        
        # 30 günden eski info logları sil
        cutoff_date = timezone.now() - timedelta(days=30)
        old_info_logs = AutomationLog.objects.filter(
            created_at__lt=cutoff_date,
            level='info'
        )
        info_deleted = old_info_logs.count()
        old_info_logs.delete()
        
        return {
            'deleted_debug_logs': debug_deleted,
            'deleted_info_logs': info_deleted
        }
        
    except Exception as e:
        logger.error(f"Log temizlik hatası: {str(e)}")
        return {'error': str(e)}


@shared_task
def send_execution_notification(execution_id, notification_type='completed'):
    """Çalıştırma bildirimi gönder"""
    try:
        execution = PlaybookExecution.objects.select_related(
            'playbook', 'executor'
        ).get(id=execution_id)
        
        # E-posta bildirimi (opsiyonel)
        if hasattr(execution.executor, 'email') and execution.executor.email:
            from django.core.mail import send_mail
            from django.conf import settings
            
            subject = f"Playbook {notification_type.title()}: {execution.playbook.name}"
            
            if notification_type == 'completed':
                if execution.is_successful:
                    message = f"Playbook başarıyla tamamlandı.\n\nDetaylar:\n- Playbook: {execution.playbook.name}\n- Çalıştırma ID: {execution.execution_id}\n- Süre: {execution.duration}\n- Durum: Başarılı"
                else:
                    message = f"Playbook tamamlandı ancak hatalar var.\n\nDetaylar:\n- Playbook: {execution.playbook.name}\n- Çalıştırma ID: {execution.execution_id}\n- Süre: {execution.duration}\n- Return Code: {execution.return_code}"
            elif notification_type == 'failed':
                message = f"Playbook çalıştırma başarısız.\n\nDetaylar:\n- Playbook: {execution.playbook.name}\n- Çalıştırma ID: {execution.execution_id}\n- Hata: {execution.stderr[:500]}"
            else:
                message = f"Playbook durumu: {notification_type}\n\nDetaylar:\n- Playbook: {execution.playbook.name}\n- Çalıştırma ID: {execution.execution_id}"
            
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [execution.executor.email],
                fail_silently=True
            )
        
        # Log kaydet
        AutomationLog.objects.create(
            level='info',
            message=f"Bildirim gönderildi: {notification_type} - {execution.playbook.name}",
            playbook_execution=execution,
            user=execution.executor
        )
        
        return {
            'execution_id': execution_id,
            'notification_type': notification_type,
            'sent': True
        }
        
    except PlaybookExecution.DoesNotExist:
        return {'error': 'Execution not found'}
    except Exception as e:
        logger.error(f"Bildirim gönderme hatası: {str(e)}")
        return {'error': str(e)}
