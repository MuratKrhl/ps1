from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from .models import Server, Application, Database, Environment, OperatingSystem, ApplicationType, Technology
from .services import InventoryStatsService, HealthCheckService
from .forms import ApplicationForm, ServerForm


@login_required
def server_list(request):
    """Server list view with filtering and search"""
    servers = Server.objects.select_related('environment', 'operating_system', 'owner').prefetch_related('tags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        servers = servers.filter(
            Q(hostname__icontains=search_query) |
            Q(ip_address__icontains=search_query) |
            Q(purpose__icontains=search_query) |
            Q(responsible_team__icontains=search_query)
        )
    
    # Filter by environment
    environment_filter = request.GET.get('environment', '')
    if environment_filter:
        servers = servers.filter(environment_id=environment_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        servers = servers.filter(status=status_filter)
    
    # Filter by OS
    os_filter = request.GET.get('os', '')
    if os_filter:
        servers = servers.filter(operating_system_id=os_filter)
    
    # Pagination
    paginator = Paginator(servers, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    environments = Environment.objects.filter(is_active=True)
    operating_systems = OperatingSystem.objects.filter(is_active=True)
    status_choices = Server._meta.get_field('status').choices
    
    context = {
        'page_title': 'Sunucu Listesi',
        'servers': page_obj,
        'search_query': search_query,
        'environments': environments,
        'operating_systems': operating_systems,
        'status_choices': status_choices,
        'current_filters': {
            'environment': environment_filter,
            'status': status_filter,
            'os': os_filter,
        }
    }
    
    return render(request, 'envanter/server_list.html', context)


@login_required
def server_detail(request, server_id):
    """Server detail view"""
    server = get_object_or_404(
        Server.objects.select_related('environment', 'operating_system', 'owner')
                     .prefetch_related('applications', 'databases', 'tags'),
        id=server_id
    )
    
    context = {
        'page_title': f'Sunucu Detayı - {server.hostname}',
        'server': server,
    }
    
    return render(request, 'envanter/server_detail.html', context)


@login_required
def application_list(request):
    """Application list view with filtering and search"""
    applications = Application.objects.select_related('environment', 'application_type', 'owner').prefetch_related('technologies', 'servers', 'tags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        applications = applications.filter(
            Q(name__icontains=search_query) |
            Q(code_name__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(development_team__icontains=search_query)
        )
    
    # Filter by environment
    environment_filter = request.GET.get('environment', '')
    if environment_filter:
        applications = applications.filter(environment_id=environment_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        applications = applications.filter(status=status_filter)
    
    # Filter by application type
    type_filter = request.GET.get('type', '')
    if type_filter:
        applications = applications.filter(application_type_id=type_filter)
    
    # Filter by criticality
    criticality_filter = request.GET.get('criticality', '')
    if criticality_filter:
        applications = applications.filter(business_criticality=criticality_filter)
    
    # Pagination
    paginator = Paginator(applications, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    environments = Environment.objects.filter(is_active=True)
    application_types = ApplicationType.objects.filter(is_active=True)
    status_choices = Application._meta.get_field('status').choices
    criticality_choices = Application._meta.get_field('business_criticality').choices
    
    context = {
        'page_title': 'Uygulama Listesi',
        'applications': page_obj,
        'search_query': search_query,
        'environments': environments,
        'application_types': application_types,
        'status_choices': status_choices,
        'criticality_choices': criticality_choices,
        'current_filters': {
            'environment': environment_filter,
            'status': status_filter,
            'type': type_filter,
            'criticality': criticality_filter,
        }
    }
    
    return render(request, 'envanter/application_list.html', context)


@login_required
def application_detail(request, application_id):
    """Application detail view"""
    application = get_object_or_404(
        Application.objects.select_related('environment', 'application_type', 'owner')
                          .prefetch_related('technologies', 'servers', 'databases', 'tags'),
        id=application_id
    )
    
    context = {
        'page_title': f'Uygulama Detayı - {application.name}',
        'application': application,
    }
    
    return render(request, 'envanter/application_detail.html', context)


@login_required
def database_list(request):
    """Database list view with filtering and search"""
    databases = Database.objects.select_related('server', 'environment', 'owner').prefetch_related('applications', 'tags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        databases = databases.filter(
            Q(name__icontains=search_query) |
            Q(schema_name__icontains=search_query) |
            Q(purpose__icontains=search_query)
        )
    
    # Filter by environment
    environment_filter = request.GET.get('environment', '')
    if environment_filter:
        databases = databases.filter(environment_id=environment_filter)
    
    # Filter by database type
    type_filter = request.GET.get('type', '')
    if type_filter:
        databases = databases.filter(database_type=type_filter)
    
    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        databases = databases.filter(status=status_filter)
    
    # Pagination
    paginator = Paginator(databases, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    environments = Environment.objects.filter(is_active=True)
    type_choices = Database._meta.get_field('database_type').choices
    status_choices = Database._meta.get_field('status').choices
    
    context = {
        'page_title': 'Veritabanı Listesi',
        'databases': page_obj,
        'search_query': search_query,
        'environments': environments,
        'type_choices': type_choices,
        'status_choices': status_choices,
        'current_filters': {
            'environment': environment_filter,
            'type': type_filter,
            'status': status_filter,
        }
    }
    
    return render(request, 'envanter/database_list.html', context)


@login_required
def database_detail(request, database_id):
    """Database detail view"""
    database = get_object_or_404(
        Database.objects.select_related('server', 'environment', 'owner')
                       .prefetch_related('applications', 'tags'),
        id=database_id
    )
    
    context = {
        'page_title': f'Veritabanı Detayı - {database.name}',
        'database': database,
    }
    
    return render(request, 'envanter/database_detail.html', context)


@login_required
def envanter_dashboard(request):
    """Envanter dashboard with statistics"""
    stats = InventoryStatsService.get_dashboard_stats()
    env_stats = InventoryStatsService.get_environment_stats()
    tech_stats = InventoryStatsService.get_technology_stats()
    
    # Recent additions
    recent_servers = Server.objects.select_related('environment').order_by('-created_at')[:5]
    recent_applications = Application.objects.select_related('environment').order_by('-created_at')[:5]
    
    context = {
        'page_title': 'Envanter Dashboard',
        'stats': stats,
        'env_stats': env_stats,
        'tech_stats': tech_stats,
        'recent_servers': recent_servers,
        'recent_applications': recent_applications,
    }
    
    return render(request, 'envanter/dashboard.html', context)


# =============================================================================
# CLASS-BASED VIEWS (Modern Implementation)
# =============================================================================

@method_decorator(cache_page(60), name='dispatch')
class EnvanterListView(LoginRequiredMixin, ListView):
    """Ana envanter listesi - tüm sunucu ve uygulamaları gösteren birleşik tablo"""
    template_name = 'envanter/inventory_list.html'
    context_object_name = 'items'
    paginate_by = 25
    
    def get_queryset(self):
        """Sunucu ve uygulamaları birleştiren queryset"""
        search_query = self.request.GET.get('search', '')
        item_type = self.request.GET.get('type', 'all')  # all, servers, applications
        environment_filter = self.request.GET.get('environment', '')
        status_filter = self.request.GET.get('status', '')
        
        items = []
        
        # Sunucuları ekle
        if item_type in ['all', 'servers']:
            servers = Server.objects.select_related('environment', 'operating_system')
            
            if search_query:
                servers = servers.filter(
                    Q(hostname__icontains=search_query) |
                    Q(ip_address__icontains=search_query) |
                    Q(purpose__icontains=search_query)
                )
            
            if environment_filter:
                servers = servers.filter(environment_id=environment_filter)
            
            if status_filter:
                servers = servers.filter(status=status_filter)
            
            for server in servers:
                items.append({
                    'type': 'server',
                    'id': server.id,
                    'name': server.hostname,
                    'description': server.purpose or 'Sunucu',
                    'environment': server.environment,
                    'status': server.status,
                    'ip_address': server.ip_address,
                    'object': server
                })
        
        # Uygulamaları ekle
        if item_type in ['all', 'applications']:
            applications = Application.objects.select_related('environment').prefetch_related('servers')
            
            if search_query:
                applications = applications.filter(
                    Q(name__icontains=search_query) |
                    Q(code_name__icontains=search_query) |
                    Q(description__icontains=search_query)
                )
            
            if environment_filter:
                applications = applications.filter(environment_id=environment_filter)
            
            if status_filter:
                applications = applications.filter(status=status_filter)
            
            for app in applications:
                server = app.get_primary_server()
                items.append({
                    'type': 'application',
                    'id': app.id,
                    'name': app.name,
                    'description': app.description or app.code_name,
                    'environment': app.environment,
                    'status': app.status,
                    'ip_address': server.ip_address if server else None,
                    'port': app.port,
                    'object': app
                })
        
        # Sıralama
        items.sort(key=lambda x: (x['environment'].name, x['name']))
        return items
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'page_title': 'Envanter Listesi',
            'search_query': self.request.GET.get('search', ''),
            'type_filter': self.request.GET.get('type', 'all'),
            'environment_filter': self.request.GET.get('environment', ''),
            'status_filter': self.request.GET.get('status', ''),
            'environments': Environment.objects.filter(is_active=True),
            'stats': InventoryStatsService.get_dashboard_stats(),
        })
        return context


class ApplicationDetailView(LoginRequiredMixin, DetailView):
    """Uygulama detay view'ı - sekmeli görünüm"""
    model = Application
    template_name = 'envanter/application_detail.html'
    context_object_name = 'application'
    
    def get_object(self):
        return get_object_or_404(
            Application.objects.select_related(
                'environment', 'application_type', 'owner'
            ).prefetch_related(
                'servers', 'technologies', 'databases', 'tags'
            ),
            pk=self.kwargs['pk']
        )
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        application = self.get_object()
        
        # İlgili AskGT makaleleri (varsa)
        related_articles = []
        try:
            from askgt.models import Article
            related_articles = Article.objects.filter(
                Q(title__icontains=application.name) |
                Q(content__icontains=application.code_name) |
                Q(technologies__in=application.technologies.all())
            ).distinct()[:5]
        except ImportError:
            pass
        
        # Operasyon geçmişi (placeholder)
        operation_history = []
        
        context.update({
            'page_title': f'{application.name} - Detay',
            'related_articles': related_articles,
            'operation_history': operation_history,
            'can_edit': self.request.user.has_perm('envanter.change_application'),
            'can_delete': self.request.user.has_perm('envanter.delete_application'),
        })
        return context


# =============================================================================
# AJAX VIEWS
# =============================================================================

def application_health_check(request, pk):
    """AJAX ile uygulama sağlık kontrolü"""
    if not request.user.is_authenticated:
        return JsonResponse({'error': 'Authentication required'}, status=401)
    
    try:
        application = get_object_or_404(Application, pk=pk)
        health_service = HealthCheckService()
        status = health_service.check_application_health(application)
        
        return JsonResponse({
            'success': True,
            'status': status,
            'status_display': application.get_health_check_status_display(),
            'last_check': application.last_health_check.isoformat() if application.last_health_check else None,
            'badge_class': application.get_health_status_badge_class()
        })
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
