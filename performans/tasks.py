from celery import shared_task
from django.utils import timezone
from datetime import timedelta
from .monitoring_service import MetricsCollectorService, MetricsAnalysisService
from .models import ServerMetric, ApplicationMetric, Alert, PerformanceReport
import logging

logger = logging.getLogger(__name__)


@shared_task
def collect_server_metrics():
    """Sunucu metriklerini topla"""
    try:
        collector = MetricsCollectorService()
        collected_count = collector.collect_server_metrics()
        
        logger.info(f"Sunucu metrikleri toplandı: {collected_count} kayıt")
        
        return {
            'success': True,
            'collected_metrics': collected_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Sunucu metrik toplama hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def collect_application_metrics():
    """Uygulama metriklerini topla"""
    try:
        collector = MetricsCollectorService()
        collected_count = collector.collect_application_metrics()
        
        logger.info(f"Uygulama metrikleri toplandı: {collected_count} kayıt")
        
        return {
            'success': True,
            'collected_metrics': collected_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Uygulama metrik toplama hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def sync_monitoring_alerts():
    """Monitoring uyarılarını senkronize et"""
    try:
        collector = MetricsCollectorService()
        synced_count = collector.sync_alerts()
        
        logger.info(f"Uyarılar senkronize edildi: {synced_count} kayıt")
        
        return {
            'success': True,
            'synced_alerts': synced_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Uyarı senkronizasyon hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def cleanup_old_metrics():
    """Eski metrikleri temizle"""
    try:
        # 30 günden eski metrikleri sil
        cutoff_date = timezone.now() - timedelta(days=30)
        
        # Sunucu metrikleri
        old_server_metrics = ServerMetric.objects.filter(timestamp__lt=cutoff_date)
        server_deleted = old_server_metrics.count()
        old_server_metrics.delete()
        
        # Uygulama metrikleri
        old_app_metrics = ApplicationMetric.objects.filter(timestamp__lt=cutoff_date)
        app_deleted = old_app_metrics.count()
        old_app_metrics.delete()
        
        logger.info(f"Eski metrikler temizlendi: {server_deleted} sunucu, {app_deleted} uygulama")
        
        return {
            'success': True,
            'deleted_server_metrics': server_deleted,
            'deleted_app_metrics': app_deleted,
            'cutoff_date': cutoff_date.isoformat()
        }
        
    except Exception as e:
        logger.error(f"Metrik temizlik hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def generate_performance_reports():
    """Performans raporları oluştur"""
    try:
        from envanter.models import Server, Application
        from django.contrib.auth.models import User
        
        # Sistem kullanıcısı (raporlar için)
        system_user = User.objects.filter(is_staff=True).first()
        if not system_user:
            return {'success': False, 'error': 'Sistem kullanıcısı bulunamadı'}
        
        reports_created = 0
        
        # Haftalık sunucu raporu
        week_ago = timezone.now() - timedelta(days=7)
        
        for server in Server.objects.filter(is_active=True):
            try:
                # Son hafta metrikleri
                metrics = ServerMetric.objects.filter(
                    server=server,
                    timestamp__gte=week_ago
                ).select_related('metric_type')
                
                if not metrics.exists():
                    continue
                
                # Rapor verisi hazırla
                report_data = {}
                for metric in metrics:
                    metric_name = metric.metric_type.name
                    if metric_name not in report_data:
                        report_data[metric_name] = []
                    
                    report_data[metric_name].append({
                        'value': metric.value,
                        'timestamp': metric.timestamp.isoformat(),
                        'status': metric.status
                    })
                
                # Özet hesapla
                summary = {}
                for metric_name, values in report_data.items():
                    metric_values = [v['value'] for v in values]
                    summary[metric_name] = {
                        'avg': sum(metric_values) / len(metric_values),
                        'min': min(metric_values),
                        'max': max(metric_values),
                        'count': len(metric_values)
                    }
                
                # Rapor oluştur
                PerformanceReport.objects.create(
                    title=f"{server.name} Haftalık Performans Raporu",
                    description=f"{server.name} sunucusunun {week_ago.strftime('%d.%m.%Y')} - {timezone.now().strftime('%d.%m.%Y')} tarihleri arası performans raporu",
                    report_type='weekly',
                    period_start=week_ago,
                    period_end=timezone.now(),
                    report_data=report_data,
                    summary=summary,
                    created_by=system_user
                )
                
                reports_created += 1
                
            except Exception as e:
                logger.error(f"Sunucu raporu oluşturulamadı {server.name}: {str(e)}")
        
        logger.info(f"Performans raporları oluşturuldu: {reports_created} rapor")
        
        return {
            'success': True,
            'reports_created': reports_created,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Rapor oluşturma hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def check_metric_thresholds():
    """Metrik eşik değerlerini kontrol et"""
    try:
        from envanter.models import Server, Application
        
        alerts_created = 0
        
        # Son 5 dakikadaki metrikleri kontrol et
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        
        # Sunucu metrikleri
        recent_server_metrics = ServerMetric.objects.filter(
            timestamp__gte=five_minutes_ago
        ).select_related('server', 'metric_type')
        
        for metric in recent_server_metrics:
            if metric.status in ['warning', 'critical']:
                # Aynı uyarının zaten açık olup olmadığını kontrol et
                existing_alert = Alert.objects.filter(
                    source_type='threshold',
                    source_id=f"server_{metric.server.id}_{metric.metric_type.name}",
                    status='open'
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        title=f"{metric.server.name} - {metric.metric_type.name} Eşik Aşımı",
                        description=f"{metric.metric_type.name} değeri {metric.value}{metric.metric_type.unit} olarak ölçüldü.",
                        severity=metric.status,
                        source_type='threshold',
                        source_id=f"server_{metric.server.id}_{metric.metric_type.name}",
                        alert_data={
                            'resource_type': 'server',
                            'resource_id': metric.server.id,
                            'resource_name': metric.server.name,
                            'metric_name': metric.metric_type.name,
                            'metric_value': metric.value,
                            'metric_unit': metric.metric_type.unit
                        }
                    )
                    alerts_created += 1
        
        # Uygulama metrikleri
        recent_app_metrics = ApplicationMetric.objects.filter(
            timestamp__gte=five_minutes_ago
        ).select_related('application', 'metric_type')
        
        for metric in recent_app_metrics:
            if metric.status in ['warning', 'critical']:
                # Aynı uyarının zaten açık olup olmadığını kontrol et
                existing_alert = Alert.objects.filter(
                    source_type='threshold',
                    source_id=f"application_{metric.application.id}_{metric.metric_type.name}",
                    status='open'
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        title=f"{metric.application.name} - {metric.metric_type.name} Eşik Aşımı",
                        description=f"{metric.metric_type.name} değeri {metric.value}{metric.metric_type.unit} olarak ölçüldü.",
                        severity=metric.status,
                        source_type='threshold',
                        source_id=f"application_{metric.application.id}_{metric.metric_type.name}",
                        alert_data={
                            'resource_type': 'application',
                            'resource_id': metric.application.id,
                            'resource_name': metric.application.name,
                            'metric_name': metric.metric_type.name,
                            'metric_value': metric.value,
                            'metric_unit': metric.metric_type.unit
                        }
                    )
                    alerts_created += 1
        
        logger.info(f"Eşik kontrolü tamamlandı: {alerts_created} yeni uyarı")
        
        return {
            'success': True,
            'alerts_created': alerts_created,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Eşik kontrolü hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }


@shared_task
def auto_resolve_alerts():
    """Otomatik uyarı çözme"""
    try:
        # 24 saatten eski threshold uyarılarını otomatik çöz
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        old_threshold_alerts = Alert.objects.filter(
            source_type='threshold',
            status='open',
            created_at__lt=cutoff_time
        )
        
        resolved_count = 0
        
        for alert in old_threshold_alerts:
            # Son metrikleri kontrol et
            alert_data = alert.alert_data or {}
            resource_type = alert_data.get('resource_type')
            resource_id = alert_data.get('resource_id')
            metric_name = alert_data.get('metric_name')
            
            if resource_type and resource_id and metric_name:
                # Son 10 dakikadaki metrikleri kontrol et
                ten_minutes_ago = timezone.now() - timedelta(minutes=10)
                
                if resource_type == 'server':
                    recent_metrics = ServerMetric.objects.filter(
                        server_id=resource_id,
                        metric_type__name=metric_name,
                        timestamp__gte=ten_minutes_ago
                    )
                else:  # application
                    recent_metrics = ApplicationMetric.objects.filter(
                        application_id=resource_id,
                        metric_type__name=metric_name,
                        timestamp__gte=ten_minutes_ago
                    )
                
                # Eğer son metriklerde sorun yoksa uyarıyı çöz
                if recent_metrics.filter(status='normal').exists():
                    alert.status = 'resolved'
                    alert.resolved_at = timezone.now()
                    alert.resolution_notes = 'Otomatik çözüldü: Metrik değerleri normale döndü'
                    alert.save()
                    resolved_count += 1
            else:
                # Veri eksikse eski uyarıyı çöz
                alert.status = 'resolved'
                alert.resolved_at = timezone.now()
                alert.resolution_notes = 'Otomatik çözüldü: Eski uyarı'
                alert.save()
                resolved_count += 1
        
        logger.info(f"Otomatik uyarı çözme tamamlandı: {resolved_count} uyarı çözüldü")
        
        return {
            'success': True,
            'resolved_alerts': resolved_count,
            'timestamp': timezone.now().isoformat()
        }
        
    except Exception as e:
        logger.error(f"Otomatik uyarı çözme hatası: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
