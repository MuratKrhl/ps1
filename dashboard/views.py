from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import TemplateView
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.db.models import Count, Q
from django.utils import timezone
from datetime import timedelta
import json

from .services import DashboardDataService


@method_decorator(cache_page(60), name='dispatch')
class DashboardHomeView(LoginRequiredMixin, TemplateView):
    """
    Main dashboard view with comprehensive data overview
    """
    template_name = 'dashboard/home.html'
    
    @method_decorator(cache_page(60))  # Cache for 60 seconds
    def dispatch(self, *args, **kwargs):
        return super().dispatch(*args, **kwargs)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get dashboard data from service
        dashboard_service = DashboardDataService()
        dashboard_data = dashboard_service.get_dashboard_data()
        
        context.update(dashboard_data)
        return context


@login_required
def dashboard_api_data(request):
    """
    API endpoint for asynchronous dashboard data loading
    """
    dashboard_service = DashboardDataService()
    data = dashboard_service.get_dashboard_data()
    
    # Add announcement data
    announcement_data = dashboard_service.get_announcement_stats()
    data.update(announcement_data)
    
    # Add duty schedule data
    duty_data = dashboard_service.get_duty_schedule_stats()
    data.update(duty_data)
    
    return JsonResponse(data, safe=False)


@login_required
def performance_chart_data(request):
    """
    API endpoint for performance chart data (last 24 hours)
    """
    try:
        from performans.models import ServerMetric, ApplicationMetric
        
        # Get last 24 hours data
        since = timezone.now() - timedelta(hours=24)
        
        # Server response times
        server_metrics = ServerMetric.objects.filter(
            timestamp__gte=since,
            metric_name='response_time'
        ).order_by('timestamp').values('timestamp', 'value', 'server__name')
        
        # Application response times
        app_metrics = ApplicationMetric.objects.filter(
            timestamp__gte=since,
            metric_name='response_time'
        ).order_by('timestamp').values('timestamp', 'value', 'application__name')
        
        # Format data for Chart.js
        chart_data = {
            'labels': [],
            'datasets': []
        }
        
        # Process server metrics
        server_data = {}
        for metric in server_metrics:
            server_name = metric['server__name']
            if server_name not in server_data:
                server_data[server_name] = []
            server_data[server_name].append({
                'x': metric['timestamp'].isoformat(),
                'y': float(metric['value'])
            })
        
        # Add server datasets
        colors = ['#667eea', '#764ba2', '#f093fb', '#f5576c', '#4facfe']
        for i, (server_name, data) in enumerate(server_data.items()):
            chart_data['datasets'].append({
                'label': f'Server: {server_name}',
                'data': data,
                'borderColor': colors[i % len(colors)],
                'backgroundColor': colors[i % len(colors)] + '20',
                'tension': 0.4
            })
        
        return JsonResponse(chart_data)
        
    except ImportError:
        # Fallback data if performans app not available
        return JsonResponse({
            'labels': [],
            'datasets': [{
                'label': 'Sample Data',
                'data': [{'x': timezone.now().isoformat(), 'y': 100}],
                'borderColor': '#667eea',
                'backgroundColor': '#667eea20'
            }]
        })


@login_required
def inventory_health_data(request):
    """
    API endpoint for inventory health donut chart
    """
    try:
        from envanter.models import Application
        
        # Count applications by status
        status_counts = Application.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Prepare data for donut chart
        labels = []
        data = []
        colors = []
        
        status_colors = {
            'active': '#28a745',
            'inactive': '#6c757d', 
            'maintenance': '#ffc107',
            'error': '#dc3545'
        }
        
        for item in status_counts:
            status = item['status'] or 'unknown'
            labels.append(status.title())
            data.append(item['count'])
            colors.append(status_colors.get(status, '#6c757d'))
        
        chart_data = {
            'labels': labels,
            'datasets': [{
                'data': data,
                'backgroundColor': colors,
                'borderWidth': 2,
                'borderColor': '#ffffff'
            }]
        }
        
        return JsonResponse(chart_data)
        
    except ImportError:
        # Fallback data
        return JsonResponse({
            'labels': ['Active', 'Inactive', 'Maintenance'],
            'datasets': [{
                'data': [65, 25, 10],
                'backgroundColor': ['#28a745', '#6c757d', '#ffc107'],
                'borderWidth': 2,
                'borderColor': '#ffffff'
            }]
        })
