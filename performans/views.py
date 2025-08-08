from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.core.paginator import Paginator
from django.db.models import Q, Avg, Max, Min
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import cache_page
from datetime import timedelta
from .models import ServerMetric, ApplicationMetric, MetricType, PerformanceReport, Alert
from envanter.models import Server, Application
from .services.dynatrace import DynatraceAPIService
import logging

logger = logging.getLogger(__name__)


@login_required
def performans_dashboard(request):
    """Performance monitoring dashboard"""
    # Get recent alerts
    recent_alerts = Alert.objects.filter(
        status__in=['open', 'acknowledged'], is_active=True
    ).select_related('server', 'application', 'metric_type').order_by('-created_at')[:10]
    
    # Critical alerts count
    critical_alerts = Alert.objects.filter(
        severity='critical', status='open', is_active=True
    ).count()
    
    # Warning alerts count
    warning_alerts = Alert.objects.filter(
        severity='warning', status='open', is_active=True
    ).count()
    
    # Server status summary
    total_servers = Server.objects.filter(is_active=True).count()
    
    # Recent performance data
    now = timezone.now()
    last_hour = now - timedelta(hours=1)
    
    # Get latest metrics for key performance indicators
    cpu_metrics = ServerMetric.objects.filter(
        metric_type__category='cpu',
        timestamp__gte=last_hour,
        is_active=True
    ).aggregate(
        avg_value=Avg('value'),
        max_value=Max('value')
    )
    
    memory_metrics = ServerMetric.objects.filter(
        metric_type__category='memory',
        timestamp__gte=last_hour,
        is_active=True
    ).aggregate(
        avg_value=Avg('value'),
        max_value=Max('value')
    )
    
    context = {
        'page_title': 'Performans Dashboard',
        'recent_alerts': recent_alerts,
        'stats': {
            'critical_alerts': critical_alerts,
            'warning_alerts': warning_alerts,
            'total_servers': total_servers,
            'avg_cpu': cpu_metrics.get('avg_value', 0) or 0,
            'max_cpu': cpu_metrics.get('max_value', 0) or 0,
            'avg_memory': memory_metrics.get('avg_value', 0) or 0,
            'max_memory': memory_metrics.get('max_value', 0) or 0,
        }
    }
    
    return render(request, 'performans/dashboard.html', context)


@login_required
def server_performance(request):
    """Server performance overview"""
    servers = Server.objects.filter(is_active=True).select_related('environment')
    
    # Filter by environment
    env_filter = request.GET.get('environment', '')
    if env_filter:
        servers = servers.filter(environment_id=env_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        servers = servers.filter(
            Q(hostname__icontains=search_query) |
            Q(ip_address__icontains=search_query)
        )
    
    # Get latest metrics for each server
    server_data = []
    for server in servers:
        latest_cpu = ServerMetric.objects.filter(
            server=server, metric_type__category='cpu', is_active=True
        ).order_by('-timestamp').first()
        
        latest_memory = ServerMetric.objects.filter(
            server=server, metric_type__category='memory', is_active=True
        ).order_by('-timestamp').first()
        
        server_data.append({
            'server': server,
            'cpu_usage': latest_cpu.value if latest_cpu else None,
            'cpu_status': latest_cpu.status if latest_cpu else 'unknown',
            'memory_usage': latest_memory.value if latest_memory else None,
            'memory_status': latest_memory.status if latest_memory else 'unknown',
        })
    
    context = {
        'page_title': 'Sunucu Performansı',
        'server_data': server_data,
        'search_query': search_query,
    }
    
    return render(request, 'performans/server_performance.html', context)


@login_required
def server_detail(request, server_id):
    """Detailed server performance view"""
    server = get_object_or_404(Server, id=server_id, is_active=True)
    
    # Get time range
    hours = int(request.GET.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Get metrics for the time range
    metrics = ServerMetric.objects.filter(
        server=server,
        timestamp__gte=start_time,
        is_active=True
    ).select_related('metric_type').order_by('-timestamp')
    
    # Group metrics by type
    metrics_by_type = {}
    for metric in metrics:
        metric_name = metric.metric_type.name
        if metric_name not in metrics_by_type:
            metrics_by_type[metric_name] = []
        metrics_by_type[metric_name].append(metric)
    
    # Get recent alerts for this server
    recent_alerts = Alert.objects.filter(
        server=server, is_active=True
    ).select_related('metric_type').order_by('-created_at')[:10]
    
    context = {
        'page_title': f'Sunucu Performansı - {server.hostname}',
        'server': server,
        'metrics_by_type': metrics_by_type,
        'recent_alerts': recent_alerts,
        'selected_hours': hours,
    }
    
    return render(request, 'performans/server_detail.html', context)


@login_required
def application_performance(request):
    """Application performance overview"""
    applications = Application.objects.filter(is_active=True).select_related('environment')
    
    # Filter by environment
    env_filter = request.GET.get('environment', '')
    if env_filter:
        applications = applications.filter(environment_id=env_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(name__icontains=search_query) |
            Q(code_name__icontains=search_query)
        )
    
    context = {
        'page_title': 'Uygulama Performansı',
        'applications': applications,
        'search_query': search_query,
    }
    
    return render(request, 'performans/application_performance.html', context)


@login_required
def application_detail(request, application_id):
    """Detailed application performance view"""
    application = get_object_or_404(Application, id=application_id, is_active=True)
    
    # Get time range
    hours = int(request.GET.get('hours', 24))
    start_time = timezone.now() - timedelta(hours=hours)
    
    # Get metrics for the time range
    metrics = ApplicationMetric.objects.filter(
        application=application,
        timestamp__gte=start_time,
        is_active=True
    ).select_related('metric_type').order_by('-timestamp')
    
    context = {
        'page_title': f'Uygulama Performansı - {application.name}',
        'application': application,
        'metrics': metrics,
        'selected_hours': hours,
    }
    
    return render(request, 'performans/application_detail.html', context)


@login_required
def reports(request):
    """Performance reports list"""
    reports = PerformanceReport.objects.filter(is_active=True).order_by('-created_at')
    
    # Pagination
    paginator = Paginator(reports, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': 'Performans Raporları',
        'reports': page_obj,
    }
    
    return render(request, 'performans/reports.html', context)


@login_required
def report_detail(request, report_id):
    """Performance report detail"""
    report = get_object_or_404(PerformanceReport, id=report_id, is_active=True)
    
    context = {
        'page_title': f'Rapor - {report.title}',
        'report': report,
    }
    
    return render(request, 'performans/report_detail.html', context)


@login_required
def alerts(request):
    """Performance alerts list"""
    alerts = Alert.objects.filter(is_active=True).select_related(
        'server', 'application', 'metric_type'
    ).order_by('-created_at')
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        alerts = alerts.filter(status=status_filter)
    
    # Filter by severity
    severity_filter = request.GET.get('severity', '')
    if severity_filter:
        alerts = alerts.filter(severity=severity_filter)
    
    # Pagination
    paginator = Paginator(alerts, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    status_choices = Alert._meta.get_field('status').choices
    severity_choices = Alert._meta.get_field('severity').choices
    
    context = {
        'page_title': 'Performans Uyarıları',
        'alerts': page_obj,
        'status_choices': status_choices,
        'severity_choices': severity_choices,
        'current_filters': {
            'status': status_filter,
            'severity': severity_filter,
        }
    }
    
    return render(request, 'performans/alerts.html', context)


@login_required
def alert_detail(request, alert_id):
    """Performance alert detail"""
    alert = get_object_or_404(
        Alert.objects.select_related('server', 'application', 'metric_type'),
        id=alert_id, is_active=True
    )
    
    context = {
        'page_title': f'Uyarı - {alert.title}',
        'alert': alert,
    }
    
    return render(request, 'performans/alert_detail.html', context)


# =============================================================================
# DYNATRACE PERFORMANCE DASHBOARD VIEWS
# =============================================================================

class TechnologyDashboardView(LoginRequiredMixin, TemplateView):
    """
    Teknoloji bazlı performans dashboard'u
    Her teknoloji için özel metrikler ve grafikler
    """
    template_name = 'performans/technology_dashboard.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        technology = kwargs.get('technology', 'httpd')
        
        # Desteklenen teknolojiler
        supported_technologies = [
            'httpd', 'nginx', 'jboss', 'websphere', 
            'ctg', 'hazelcast', 'provenir', 'glomo', 'octo'
        ]
        
        if technology not in supported_technologies:
            technology = 'httpd'  # Default
        
        context.update({
            'technology': technology,
            'technology_name': technology.upper(),
            'supported_technologies': supported_technologies,
            'page_title': f'{technology.upper()} Performance Dashboard'
        })
        
        return context


class PerformanceOverviewView(LoginRequiredMixin, TemplateView):
    """
    Tüm teknolojiler için genel performans özeti
    """
    template_name = 'performans/performance_overview.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Desteklenen teknolojiler
        technologies = [
            {'id': 'httpd', 'name': 'Apache HTTPD', 'icon': 'ri-global-line'},
            {'id': 'nginx', 'name': 'Nginx', 'icon': 'ri-server-line'},
            {'id': 'jboss', 'name': 'JBoss', 'icon': 'ri-java-line'},
            {'id': 'websphere', 'name': 'WebSphere', 'icon': 'ri-cloud-line'},
            {'id': 'ctg', 'name': 'CTG', 'icon': 'ri-database-2-line'},
            {'id': 'hazelcast', 'name': 'Hazelcast', 'icon': 'ri-stack-line'},
            {'id': 'provenir', 'name': 'Provenir', 'icon': 'ri-shield-check-line'},
            {'id': 'glomo', 'name': 'GLOMO', 'icon': 'ri-money-dollar-circle-line'},
            {'id': 'octo', 'name': 'OCTO', 'icon': 'ri-git-branch-line'}
        ]
        
        context.update({
            'technologies': technologies,
            'page_title': 'Performance Overview'
        })
        
        return context


# =============================================================================
# DYNATRACE API ENDPOINTS
# =============================================================================

@login_required
@require_http_methods(["GET"])
@cache_page(60)  # 1 dakika cache
def api_technology_metrics(request, technology):
    """
    Belirli teknoloji için Dynatrace metriklerini döndür
    
    Args:
        technology (str): Teknoloji adı (httpd, nginx, jboss, vb.)
    
    Query Parameters:
        time_range (str): Zaman aralığı (1h, 6h, 1d, 7d) - default: 1h
        entity_selector (str): Varlık seçici (opsiyonel)
    
    Returns:
        JsonResponse: Metrik verileri
    """
    try:
        dynatrace_service = DynatraceAPIService()
        
        # Query parametreleri
        time_range = request.GET.get('time_range', '1h')
        entity_selector = request.GET.get('entity_selector')
        
        # Metrikleri çek
        metrics = dynatrace_service.get_technology_metrics(
            technology=technology,
            time_range=time_range,
            entity_selector=entity_selector
        )
        
        # Dashboard özeti
        summary = dynatrace_service.get_dashboard_summary(technology)
        
        return JsonResponse({
            'success': True,
            'technology': technology,
            'time_range': time_range,
            'metrics': metrics,
            'summary': summary,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error fetching metrics for {technology}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'technology': technology
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_technology_entities(request, technology):
    """
    Belirli teknoloji için varlıkları (entities) listele
    
    Args:
        technology (str): Teknoloji adı
    
    Returns:
        JsonResponse: Varlık listesi
    """
    try:
        dynatrace_service = DynatraceAPIService()
        entities = dynatrace_service.get_technology_entities(technology)
        
        return JsonResponse({
            'success': True,
            'technology': technology,
            'entities': entities,
            'count': len(entities)
        })
        
    except Exception as e:
        logger.error(f"Error fetching entities for {technology}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'technology': technology
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_technology_problems(request, technology):
    """
    Belirli teknoloji için problemleri listele
    
    Args:
        technology (str): Teknoloji adı
    
    Query Parameters:
        severity (str): Problem şiddeti (AVAILABILITY, ERROR, PERFORMANCE, RESOURCE)
    
    Returns:
        JsonResponse: Problem listesi
    """
    try:
        dynatrace_service = DynatraceAPIService()
        severity = request.GET.get('severity', 'AVAILABILITY')
        
        problems = dynatrace_service.get_technology_problems(
            technology=technology,
            severity=severity
        )
        
        return JsonResponse({
            'success': True,
            'technology': technology,
            'severity': severity,
            'problems': problems,
            'count': len(problems)
        })
        
    except Exception as e:
        logger.error(f"Error fetching problems for {technology}: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e),
            'technology': technology
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_performance_overview(request):
    """
    Tüm teknolojiler için genel performans özeti
    
    Returns:
        JsonResponse: Tüm teknolojiler için özet veriler
    """
    try:
        dynatrace_service = DynatraceAPIService()
        
        technologies = [
            'httpd', 'nginx', 'jboss', 'websphere',
            'ctg', 'hazelcast', 'provenir', 'glomo', 'octo'
        ]
        
        overview_data = {}
        
        for tech in technologies:
            try:
                summary = dynatrace_service.get_dashboard_summary(tech)
                overview_data[tech] = summary
            except Exception as e:
                logger.warning(f"Failed to get summary for {tech}: {e}")
                overview_data[tech] = {
                    'technology': tech,
                    'entity_count': 0,
                    'problem_count': 0,
                    'health_status': 'unknown',
                    'key_metrics': {},
                    'error': str(e)
                }
        
        return JsonResponse({
            'success': True,
            'overview': overview_data,
            'timestamp': timezone.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"Error generating performance overview: {e}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
