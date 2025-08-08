import requests
import json
from datetime import datetime, timedelta
from django.conf import settings
from django.core.cache import cache
from django.utils import timezone
import logging

logger = logging.getLogger(__name__)


class DynatraceAPIService:
    """
    Dynatrace API entegrasyon servisi
    Her teknoloji için özel metrikler çeker ve önbelleğe alır
    """
    
    def __init__(self):
        self.api_base_url = getattr(settings, 'DYNATRACE_API_URL', '')
        self.api_token = getattr(settings, 'DYNATRACE_API_TOKEN', '')
        self.timeout = getattr(settings, 'DYNATRACE_API_TIMEOUT', 30)
        self.cache_timeout = getattr(settings, 'DYNATRACE_CACHE_TIMEOUT', 120)  # 2 dakika
        
        self.headers = {
            'Authorization': f'Api-Token {self.api_token}',
            'Content-Type': 'application/json'
        }
        
        # Teknoloji bazlı metrik tanımları
        self.technology_metrics = {
            'httpd': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'request_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'error_rate': 'builtin:service.errors.rate'
            },
            'nginx': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'request_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'connections': 'builtin:service.webserver.connections'
            },
            'jboss': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'heap_usage': 'builtin:tech.jvm.memory.heap.used',
                'gc_time': 'builtin:tech.jvm.gc.collectionTime',
                'thread_count': 'builtin:tech.jvm.threading.threadCount'
            },
            'websphere': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'heap_usage': 'builtin:tech.jvm.memory.heap.used',
                'session_count': 'builtin:tech.websphere.sessionCount',
                'connection_pool': 'builtin:tech.websphere.connectionPool.usage'
            },
            'ctg': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'transaction_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'error_count': 'builtin:service.errors.count'
            },
            'hazelcast': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'cluster_size': 'builtin:tech.hazelcast.cluster.size',
                'map_size': 'builtin:tech.hazelcast.map.size',
                'cache_hit_ratio': 'builtin:tech.hazelcast.cache.hitRatio'
            },
            'provenir': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'request_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'database_connections': 'builtin:service.dbConnections.usage'
            },
            'glomo': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'request_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'queue_depth': 'builtin:service.queue.depth'
            },
            'octo': {
                'cpu_usage': 'builtin:host.cpu.usage',
                'memory_usage': 'builtin:host.mem.usage',
                'request_rate': 'builtin:service.requestCount.rate',
                'response_time': 'builtin:service.response.time',
                'throughput': 'builtin:service.throughput'
            }
        }
    
    def _make_request(self, method, endpoint, params=None, data=None):
        """API isteği yap"""
        try:
            url = f"{self.api_base_url.rstrip('/')}{endpoint}"
            
            response = requests.request(
                method=method,
                url=url,
                headers=self.headers,
                params=params,
                json=data,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Dynatrace API request failed: {e}")
            return None
        except json.JSONDecodeError as e:
            logger.error(f"Failed to decode Dynatrace API response: {e}")
            return None
    
    def get_technology_metrics(self, technology, time_range='1h', entity_selector=None):
        """
        Belirli teknoloji için metrikleri çek
        
        Args:
            technology (str): Teknoloji adı (httpd, nginx, jboss, vb.)
            time_range (str): Zaman aralığı (1h, 6h, 1d, 7d)
            entity_selector (str): Varlık seçici (opsiyonel)
        
        Returns:
            dict: Metrik verileri
        """
        cache_key = f"dynatrace_metrics_{technology}_{time_range}_{entity_selector or 'all'}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        if technology not in self.technology_metrics:
            logger.warning(f"Unknown technology: {technology}")
            return {}
        
        metrics_config = self.technology_metrics[technology]
        metrics_data = {}
        
        # Zaman aralığını hesapla
        now = timezone.now()
        time_delta = self._parse_time_range(time_range)
        start_time = now - time_delta
        
        for metric_name, metric_id in metrics_config.items():
            try:
                params = {
                    'metricSelector': metric_id,
                    'from': start_time.isoformat(),
                    'to': now.isoformat(),
                    'resolution': 'Inf'  # En yüksek çözünürlük
                }
                
                if entity_selector:
                    params['entitySelector'] = entity_selector
                
                response = self._make_request('GET', '/api/v2/metrics/query', params)
                
                if response and response.get('result'):
                    metric_result = response['result'][0]
                    data_points = metric_result.get('data', [])
                    
                    if data_points:
                        # En son veri noktasını al
                        latest_point = data_points[-1]
                        values = latest_point.get('values', [])
                        
                        if values:
                            metrics_data[metric_name] = {
                                'value': values[-1],
                                'timestamp': latest_point.get('timestamps', [])[-1] if latest_point.get('timestamps') else None,
                                'unit': metric_result.get('unit', ''),
                                'data_points': data_points  # Grafik için tüm veri noktaları
                            }
                
            except Exception as e:
                logger.error(f"Error fetching metric {metric_name} for {technology}: {e}")
                continue
        
        # Önbelleğe al
        cache.set(cache_key, metrics_data, self.cache_timeout)
        return metrics_data
    
    def get_technology_entities(self, technology):
        """
        Belirli teknoloji için varlıkları (host, service) listele
        
        Args:
            technology (str): Teknoloji adı
            
        Returns:
            list: Varlık listesi
        """
        cache_key = f"dynatrace_entities_{technology}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        # Teknoloji bazlı entity selector'lar
        entity_selectors = {
            'httpd': 'type("SERVICE"),softwareTechnologies("APACHE_HTTP_SERVER")',
            'nginx': 'type("SERVICE"),softwareTechnologies("NGINX")',
            'jboss': 'type("SERVICE"),softwareTechnologies("JBOSS")',
            'websphere': 'type("SERVICE"),softwareTechnologies("IBM_WEBSPHERE")',
            'ctg': 'type("SERVICE"),tag("ctg")',
            'hazelcast': 'type("SERVICE"),softwareTechnologies("HAZELCAST")',
            'provenir': 'type("SERVICE"),tag("provenir")',
            'glomo': 'type("SERVICE"),tag("glomo")',
            'octo': 'type("SERVICE"),tag("octo")'
        }
        
        selector = entity_selectors.get(technology)
        if not selector:
            return []
        
        try:
            params = {
                'entitySelector': selector,
                'fields': '+properties,+tags'
            }
            
            response = self._make_request('GET', '/api/v2/entities', params)
            
            if response and response.get('entities'):
                entities = []
                for entity in response['entities']:
                    entities.append({
                        'id': entity.get('entityId'),
                        'name': entity.get('displayName'),
                        'type': entity.get('type'),
                        'properties': entity.get('properties', {}),
                        'tags': entity.get('tags', [])
                    })
                
                # Önbelleğe al (daha uzun süre)
                cache.set(cache_key, entities, self.cache_timeout * 5)
                return entities
                
        except Exception as e:
            logger.error(f"Error fetching entities for {technology}: {e}")
        
        return []
    
    def get_technology_problems(self, technology, severity='AVAILABILITY'):
        """
        Belirli teknoloji için problemleri listele
        
        Args:
            technology (str): Teknoloji adı
            severity (str): Problem şiddeti (AVAILABILITY, ERROR, PERFORMANCE, RESOURCE)
            
        Returns:
            list: Problem listesi
        """
        cache_key = f"dynatrace_problems_{technology}_{severity}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Son 24 saat
            now = timezone.now()
            start_time = now - timedelta(hours=24)
            
            params = {
                'from': start_time.isoformat(),
                'to': now.isoformat(),
                'severityLevel': severity,
                'fields': '+evidenceDetails'
            }
            
            response = self._make_request('GET', '/api/v2/problems', params)
            
            if response and response.get('problems'):
                problems = []
                entities = self.get_technology_entities(technology)
                entity_ids = [e['id'] for e in entities]
                
                for problem in response['problems']:
                    # Problem bu teknoloji ile ilgili mi kontrol et
                    affected_entities = problem.get('affectedEntities', [])
                    if any(entity['entityId'] in entity_ids for entity in affected_entities):
                        problems.append({
                            'id': problem.get('problemId'),
                            'title': problem.get('title'),
                            'status': problem.get('status'),
                            'severity': problem.get('severityLevel'),
                            'start_time': problem.get('startTime'),
                            'end_time': problem.get('endTime'),
                            'affected_entities': affected_entities
                        })
                
                # Önbelleğe al
                cache.set(cache_key, problems, 300)  # 5 dakika
                return problems
                
        except Exception as e:
            logger.error(f"Error fetching problems for {technology}: {e}")
        
        return []
    
    def _parse_time_range(self, time_range):
        """Zaman aralığını timedelta'ya çevir"""
        time_map = {
            '1h': timedelta(hours=1),
            '6h': timedelta(hours=6),
            '1d': timedelta(days=1),
            '7d': timedelta(days=7),
            '30d': timedelta(days=30)
        }
        return time_map.get(time_range, timedelta(hours=1))
    
    def get_dashboard_summary(self, technology):
        """
        Dashboard için teknoloji özeti
        
        Args:
            technology (str): Teknoloji adı
            
        Returns:
            dict: Özet veriler
        """
        cache_key = f"dynatrace_dashboard_{technology}"
        cached_data = cache.get(cache_key)
        
        if cached_data:
            return cached_data
        
        try:
            # Metrikleri al
            metrics = self.get_technology_metrics(technology, '1h')
            entities = self.get_technology_entities(technology)
            problems = self.get_technology_problems(technology)
            
            # Özet hesapla
            summary = {
                'technology': technology,
                'entity_count': len(entities),
                'problem_count': len(problems),
                'health_status': 'healthy',
                'key_metrics': {},
                'last_updated': timezone.now().isoformat()
            }
            
            # Ana metrikleri özetle
            if metrics:
                for metric_name, metric_data in metrics.items():
                    if metric_name in ['cpu_usage', 'memory_usage', 'response_time']:
                        summary['key_metrics'][metric_name] = {
                            'value': metric_data.get('value'),
                            'unit': metric_data.get('unit')
                        }
            
            # Sağlık durumunu belirle
            if problems:
                critical_problems = [p for p in problems if p['severity'] in ['AVAILABILITY', 'ERROR']]
                if critical_problems:
                    summary['health_status'] = 'critical'
                else:
                    summary['health_status'] = 'warning'
            
            # Önbelleğe al
            cache.set(cache_key, summary, 60)  # 1 dakika
            return summary
            
        except Exception as e:
            logger.error(f"Error generating dashboard summary for {technology}: {e}")
            return {
                'technology': technology,
                'entity_count': 0,
                'problem_count': 0,
                'health_status': 'unknown',
                'key_metrics': {},
                'last_updated': timezone.now().isoformat(),
                'error': str(e)
            }


class DynatraceMetricsCollector:
    """
    Dynatrace metriklerini Django modellerine kaydetme servisi
    """
    
    def __init__(self):
        self.dynatrace_api = DynatraceAPIService()
    
    def collect_and_store_metrics(self, technology, time_range='1h'):
        """
        Dynatrace'den metrikleri çekip Django modellerine kaydet
        
        Args:
            technology (str): Teknoloji adı
            time_range (str): Zaman aralığı
        """
        try:
            from .models import MetricType, ServerMetric, ApplicationMetric
            from envanter.models import Server, Application
            
            # Metrikleri çek
            metrics = self.dynatrace_api.get_technology_metrics(technology, time_range)
            entities = self.dynatrace_api.get_technology_entities(technology)
            
            for entity in entities:
                entity_id = entity['id']
                entity_name = entity['name']
                
                # Server veya Application'ı bul/oluştur
                try:
                    if entity['type'] == 'HOST':
                        resource, created = Server.objects.get_or_create(
                            name=entity_name,
                            defaults={'ip_address': '0.0.0.0', 'status': 'active'}
                        )
                        metric_model = ServerMetric
                        resource_field = 'server'
                    else:
                        resource, created = Application.objects.get_or_create(
                            name=entity_name,
                            defaults={'version': '1.0', 'status': 'active'}
                        )
                        metric_model = ApplicationMetric
                        resource_field = 'application'
                    
                    # Metrikleri kaydet
                    for metric_name, metric_data in metrics.items():
                        if not metric_data.get('value'):
                            continue
                        
                        # MetricType'ı bul/oluştur
                        metric_type, created = MetricType.objects.get_or_create(
                            name=f"{technology}_{metric_name}",
                            defaults={
                                'description': f'{technology.upper()} {metric_name}',
                                'unit': metric_data.get('unit', ''),
                                'category': 'application'
                            }
                        )
                        
                        # Metrik kaydını oluştur
                        metric_kwargs = {
                            resource_field: resource,
                            'metric_type': metric_type,
                            'value': metric_data['value'],
                            'timestamp': timezone.now()
                        }
                        
                        metric_model.objects.create(**metric_kwargs)
                        
                except Exception as e:
                    logger.error(f"Error storing metrics for {entity_name}: {e}")
                    continue
                    
        except Exception as e:
            logger.error(f"Error in collect_and_store_metrics for {technology}: {e}")
