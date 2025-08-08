import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.utils import timezone
from .models import ServerMetric, ApplicationMetric, MetricType, Alert
from envanter.models import Server, Application
import logging

logger = logging.getLogger(__name__)


class MonitoringAPIService:
    """Monitoring API entegrasyon servisi"""
    
    def __init__(self):
        self.api_base_url = getattr(settings, 'MONITORING_API_URL', 'http://localhost:9090')
        self.api_key = getattr(settings, 'MONITORING_API_KEY', '')
        self.timeout = getattr(settings, 'MONITORING_API_TIMEOUT', 30)
        
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Portall-Monitor/1.0'
        }
        
        if self.api_key:
            self.headers['Authorization'] = f'Bearer {self.api_key}'
    
    def get_server_metrics(self, server_hostname, metric_names=None, time_range='1h'):
        """Sunucu metriklerini al"""
        try:
            if metric_names is None:
                metric_names = ['cpu_usage', 'memory_usage', 'disk_usage', 'network_io']
            
            metrics_data = {}
            
            for metric_name in metric_names:
                query = f'avg(node_{metric_name}{{instance="{server_hostname}:9100"}}[{time_range}])'
                
                response = self._make_request('GET', '/api/v1/query', {
                    'query': query
                })
                
                if response and response.get('status') == 'success':
                    data = response.get('data', {})
                    result = data.get('result', [])
                    
                    if result:
                        value = float(result[0]['value'][1])
                        metrics_data[metric_name] = value
                    else:
                        metrics_data[metric_name] = None
                else:
                    metrics_data[metric_name] = None
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Sunucu metrikleri alınamadı {server_hostname}: {str(e)}")
            return {}
    
    def get_application_metrics(self, app_name, metric_names=None, time_range='1h'):
        """Uygulama metriklerini al"""
        try:
            if metric_names is None:
                metric_names = ['response_time', 'request_rate', 'error_rate', 'availability']
            
            metrics_data = {}
            
            for metric_name in metric_names:
                if metric_name == 'response_time':
                    query = f'avg(http_request_duration_seconds{{job="{app_name}"}}[{time_range}])'
                elif metric_name == 'request_rate':
                    query = f'rate(http_requests_total{{job="{app_name}"}}[{time_range}])'
                elif metric_name == 'error_rate':
                    query = f'rate(http_requests_total{{job="{app_name}",status=~"5.."}}[{time_range}])'
                elif metric_name == 'availability':
                    query = f'up{{job="{app_name}"}}'
                else:
                    continue
                
                response = self._make_request('GET', '/api/v1/query', {
                    'query': query
                })
                
                if response and response.get('status') == 'success':
                    data = response.get('data', {})
                    result = data.get('result', [])
                    
                    if result:
                        value = float(result[0]['value'][1])
                        metrics_data[metric_name] = value
                    else:
                        metrics_data[metric_name] = None
                else:
                    metrics_data[metric_name] = None
            
            return metrics_data
            
        except Exception as e:
            logger.error(f"Uygulama metrikleri alınamadı {app_name}: {str(e)}")
            return {}
    
    def get_alerts(self, severity=None, state='active'):
        """Aktif uyarıları al"""
        try:
            params = {'state': state}
            if severity:
                params['severity'] = severity
            
            response = self._make_request('GET', '/api/v1/alerts', params)
            
            if response and response.get('status') == 'success':
                return response.get('data', [])
            else:
                return []
                
        except Exception as e:
            logger.error(f"Uyarılar alınamadı: {str(e)}")
            return []
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """API isteği yap"""
        try:
            url = f"{self.api_base_url.rstrip('/')}{endpoint}"
            
            if method == 'GET':
                response = requests.get(
                    url, 
                    headers=self.headers, 
                    params=params, 
                    timeout=self.timeout
                )
            elif method == 'POST':
                response = requests.post(
                    url, 
                    headers=self.headers, 
                    json=data, 
                    timeout=self.timeout
                )
            else:
                return None
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API isteği başarısız {url}: {str(e)}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"JSON parse hatası: {str(e)}")
            return None


class MetricsCollectorService:
    """Metrikleri toplama ve kaydetme servisi"""
    
    def __init__(self):
        self.monitoring_api = MonitoringAPIService()
    
    def collect_server_metrics(self, server_id=None):
        """Sunucu metriklerini topla"""
        servers = Server.objects.filter(is_active=True)
        if server_id:
            servers = servers.filter(id=server_id)
        
        collected_count = 0
        
        for server in servers:
            try:
                # API'den metrikleri al
                metrics_data = self.monitoring_api.get_server_metrics(server.hostname)
                
                if not metrics_data:
                    continue
                
                # Her metrik için kayıt oluştur
                for metric_name, value in metrics_data.items():
                    if value is not None:
                        metric_type, created = MetricType.objects.get_or_create(
                            name=metric_name,
                            defaults={
                                'category': 'server',
                                'unit': self._get_metric_unit(metric_name),
                                'warning_threshold': self._get_warning_threshold(metric_name),
                                'critical_threshold': self._get_critical_threshold(metric_name)
                            }
                        )
                        
                        # Metrik kaydı oluştur
                        ServerMetric.objects.create(
                            server=server,
                            metric_type=metric_type,
                            value=value,
                            timestamp=timezone.now()
                        )
                        
                        collected_count += 1
                        
                        # Uyarı kontrolü
                        self._check_metric_thresholds(server, metric_type, value)
                
            except Exception as e:
                logger.error(f"Sunucu metrikleri toplanamadı {server.name}: {str(e)}")
        
        return collected_count
    
    def collect_application_metrics(self, app_id=None):
        """Uygulama metriklerini topla"""
        applications = Application.objects.filter(is_active=True)
        if app_id:
            applications = applications.filter(id=app_id)
        
        collected_count = 0
        
        for app in applications:
            try:
                # API'den metrikleri al
                metrics_data = self.monitoring_api.get_application_metrics(app.name)
                
                if not metrics_data:
                    continue
                
                # Her metrik için kayıt oluştur
                for metric_name, value in metrics_data.items():
                    if value is not None:
                        metric_type, created = MetricType.objects.get_or_create(
                            name=metric_name,
                            defaults={
                                'category': 'application',
                                'unit': self._get_metric_unit(metric_name),
                                'warning_threshold': self._get_warning_threshold(metric_name),
                                'critical_threshold': self._get_critical_threshold(metric_name)
                            }
                        )
                        
                        # Metrik kaydı oluştur
                        ApplicationMetric.objects.create(
                            application=app,
                            metric_type=metric_type,
                            value=value,
                            timestamp=timezone.now()
                        )
                        
                        collected_count += 1
                        
                        # Uyarı kontrolü
                        self._check_metric_thresholds(app, metric_type, value)
                
            except Exception as e:
                logger.error(f"Uygulama metrikleri toplanamadı {app.name}: {str(e)}")
        
        return collected_count
    
    def sync_alerts(self):
        """Monitoring sistemindeki uyarıları senkronize et"""
        try:
            # API'den uyarıları al
            alerts_data = self.monitoring_api.get_alerts()
            
            synced_count = 0
            
            for alert_data in alerts_data:
                try:
                    # Uyarı kaydını oluştur veya güncelle
                    alert_id = alert_data.get('fingerprint', '')
                    
                    alert, created = Alert.objects.get_or_create(
                        external_id=alert_id,
                        defaults={
                            'title': alert_data.get('labels', {}).get('alertname', 'Bilinmeyen Uyarı'),
                            'description': alert_data.get('annotations', {}).get('description', ''),
                            'severity': self._map_severity(alert_data.get('labels', {}).get('severity', 'warning')),
                            'source_type': 'monitoring_api',
                            'alert_data': alert_data
                        }
                    )
                    
                    if not created:
                        # Mevcut uyarıyı güncelle
                        alert.title = alert_data.get('labels', {}).get('alertname', alert.title)
                        alert.description = alert_data.get('annotations', {}).get('description', alert.description)
                        alert.alert_data = alert_data
                        alert.save()
                    
                    synced_count += 1
                    
                except Exception as e:
                    logger.error(f"Uyarı senkronize edilemedi: {str(e)}")
            
            return synced_count
            
        except Exception as e:
            logger.error(f"Uyarı senkronizasyonu başarısız: {str(e)}")
            return 0
    
    def _get_metric_unit(self, metric_name):
        """Metrik birimini al"""
        units = {
            'cpu_usage': '%',
            'memory_usage': '%',
            'disk_usage': '%',
            'network_io': 'MB/s',
            'response_time': 'ms',
            'request_rate': 'req/s',
            'error_rate': '%',
            'availability': '%'
        }
        return units.get(metric_name, '')
    
    def _get_warning_threshold(self, metric_name):
        """Uyarı eşik değerini al"""
        thresholds = {
            'cpu_usage': 80.0,
            'memory_usage': 85.0,
            'disk_usage': 90.0,
            'response_time': 1000.0,
            'error_rate': 5.0,
            'availability': 95.0
        }
        return thresholds.get(metric_name)
    
    def _get_critical_threshold(self, metric_name):
        """Kritik eşik değerini al"""
        thresholds = {
            'cpu_usage': 95.0,
            'memory_usage': 95.0,
            'disk_usage': 95.0,
            'response_time': 5000.0,
            'error_rate': 10.0,
            'availability': 90.0
        }
        return thresholds.get(metric_name)
    
    def _check_metric_thresholds(self, resource, metric_type, value):
        """Metrik eşik değerlerini kontrol et ve uyarı oluştur"""
        try:
            severity = None
            
            if metric_type.critical_threshold and value >= metric_type.critical_threshold:
                severity = 'critical'
            elif metric_type.warning_threshold and value >= metric_type.warning_threshold:
                severity = 'warning'
            
            if severity:
                # Aynı uyarının zaten açık olup olmadığını kontrol et
                existing_alert = Alert.objects.filter(
                    source_type='threshold',
                    source_id=f"{resource._meta.model_name}_{resource.id}_{metric_type.name}",
                    status='open'
                ).first()
                
                if not existing_alert:
                    Alert.objects.create(
                        title=f"{resource.name} - {metric_type.name} Eşik Aşımı",
                        description=f"{metric_type.name} değeri {value}{metric_type.unit} olarak ölçüldü. Eşik: {metric_type.critical_threshold if severity == 'critical' else metric_type.warning_threshold}{metric_type.unit}",
                        severity=severity,
                        source_type='threshold',
                        source_id=f"{resource._meta.model_name}_{resource.id}_{metric_type.name}",
                        alert_data={
                            'resource_type': resource._meta.model_name,
                            'resource_id': resource.id,
                            'resource_name': resource.name,
                            'metric_name': metric_type.name,
                            'metric_value': value,
                            'threshold_value': metric_type.critical_threshold if severity == 'critical' else metric_type.warning_threshold
                        }
                    )
        
        except Exception as e:
            logger.error(f"Eşik kontrolü yapılamadı: {str(e)}")
    
    def _map_severity(self, external_severity):
        """Harici severity'yi iç severity'ye çevir"""
        mapping = {
            'critical': 'critical',
            'high': 'critical',
            'warning': 'warning',
            'medium': 'warning',
            'info': 'info',
            'low': 'info'
        }
        return mapping.get(external_severity.lower(), 'warning')


class MetricsAnalysisService:
    """Metrik analiz servisi"""
    
    @staticmethod
    def get_server_health_score(server_id):
        """Sunucu sağlık skoru hesapla"""
        try:
            server = Server.objects.get(id=server_id)
            
            # Son 1 saatteki metrikleri al
            one_hour_ago = timezone.now() - timedelta(hours=1)
            recent_metrics = ServerMetric.objects.filter(
                server=server,
                timestamp__gte=one_hour_ago
            ).select_related('metric_type')
            
            if not recent_metrics.exists():
                return None
            
            # Metrik bazında skorlar
            scores = []
            
            for metric in recent_metrics:
                metric_score = 100  # Başlangıç skoru
                
                if metric.metric_type.critical_threshold and metric.value >= metric.metric_type.critical_threshold:
                    metric_score = 0
                elif metric.metric_type.warning_threshold and metric.value >= metric.metric_type.warning_threshold:
                    metric_score = 50
                
                scores.append(metric_score)
            
            # Ortalama skor
            health_score = sum(scores) / len(scores) if scores else 0
            
            return round(health_score, 1)
            
        except Exception as e:
            logger.error(f"Sağlık skoru hesaplanamadı: {str(e)}")
            return None
    
    @staticmethod
    def get_application_performance_summary(app_id, days=7):
        """Uygulama performans özeti"""
        try:
            application = Application.objects.get(id=app_id)
            
            # Son N gündeki metrikleri al
            start_date = timezone.now() - timedelta(days=days)
            metrics = ApplicationMetric.objects.filter(
                application=application,
                timestamp__gte=start_date
            ).select_related('metric_type')
            
            summary = {}
            
            # Metrik türlerine göre grupla
            for metric in metrics:
                metric_name = metric.metric_type.name
                
                if metric_name not in summary:
                    summary[metric_name] = {
                        'values': [],
                        'unit': metric.metric_type.unit
                    }
                
                summary[metric_name]['values'].append(metric.value)
            
            # İstatistikleri hesapla
            for metric_name, data in summary.items():
                values = data['values']
                if values:
                    data['avg'] = sum(values) / len(values)
                    data['min'] = min(values)
                    data['max'] = max(values)
                    data['count'] = len(values)
                else:
                    data['avg'] = data['min'] = data['max'] = data['count'] = 0
            
            return summary
            
        except Exception as e:
            logger.error(f"Performans özeti hesaplanamadı: {str(e)}")
            return {}
