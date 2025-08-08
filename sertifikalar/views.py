"""
Certificate Management Views
"""
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from django.db.models import Q, Count, Case, When, IntegerField
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.cache import cache_page
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from datetime import datetime, timedelta
from .models import KdbCertificate, JavaCertificate, CertificateAlert, CertificateNotification


@method_decorator(cache_page(60), name='dispatch')
class KdbCertificateListView(LoginRequiredMixin, ListView):
    """KDB Certificate List View"""
    model = KdbCertificate
    template_name = 'sertifikalar/kdb_certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = KdbCertificate.objects.filter(is_active=True).select_related('created_by')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(common_name__icontains=search_query) |
                Q(server_hostname__icontains=search_query) |
                Q(application_name__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(kdb_label__icontains=search_query)
            )
        
        # Environment filter
        environment_filter = self.request.GET.get('environment', '')
        if environment_filter:
            queryset = queryset.filter(environment=environment_filter)
        
        # Expiry status filter
        status_filter = self.request.GET.get('status', '')
        today = timezone.now()
        
        if status_filter == 'expired':
            queryset = queryset.filter(valid_to__lt=today)
        elif status_filter == 'critical':
            queryset = queryset.filter(valid_to__lt=today + timedelta(days=7), valid_to__gte=today)
        elif status_filter == 'warning':
            queryset = queryset.filter(valid_to__lt=today + timedelta(days=30), valid_to__gte=today + timedelta(days=7))
        elif status_filter == 'valid':
            queryset = queryset.filter(valid_to__gte=today + timedelta(days=30))
        
        # Server filter
        server_filter = self.request.GET.get('server', '')
        if server_filter:
            queryset = queryset.filter(server_hostname__icontains=server_filter)
        
        # Application filter
        app_filter = self.request.GET.get('application', '')
        if app_filter:
            queryset = queryset.filter(application_name__icontains=app_filter)
        
        return queryset.order_by('valid_to', 'common_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        environments = KdbCertificate.objects.filter(is_active=True).values_list('environment', flat=True).distinct()
        environments = [env for env in environments if env]
        
        # Get statistics
        today = timezone.now()
        total_certs = KdbCertificate.objects.filter(is_active=True).count()
        expired_certs = KdbCertificate.objects.filter(is_active=True, valid_to__lt=today).count()
        critical_certs = KdbCertificate.objects.filter(
            is_active=True, 
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count()
        warning_certs = KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today + timedelta(days=7)
        ).count()
        
        context.update({
            'page_title': 'KDB Sertifikaları',
            'search_query': self.request.GET.get('search', ''),
            'environment_filter': self.request.GET.get('environment', ''),
            'status_filter': self.request.GET.get('status', ''),
            'server_filter': self.request.GET.get('server', ''),
            'app_filter': self.request.GET.get('application', ''),
            'environments': sorted(environments),
            'stats': {
                'total': total_certs,
                'expired': expired_certs,
                'critical': critical_certs,
                'warning': warning_certs,
                'valid': total_certs - expired_certs - critical_certs - warning_certs,
            }
        })
        return context


@method_decorator(cache_page(60), name='dispatch')
class JavaCertificateListView(LoginRequiredMixin, ListView):
    """Java Certificate List View"""
    model = JavaCertificate
    template_name = 'sertifikalar/java_certificate_list.html'
    context_object_name = 'certificates'
    paginate_by = 25
    
    def get_queryset(self):
        queryset = JavaCertificate.objects.filter(is_active=True).select_related('created_by')
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(common_name__icontains=search_query) |
                Q(server_hostname__icontains=search_query) |
                Q(java_application__icontains=search_query) |
                Q(serial_number__icontains=search_query) |
                Q(alias_name__icontains=search_query)
            )
        
        # Environment filter
        environment_filter = self.request.GET.get('environment', '')
        if environment_filter:
            queryset = queryset.filter(environment=environment_filter)
        
        # Keystore type filter
        keystore_filter = self.request.GET.get('keystore_type', '')
        if keystore_filter:
            queryset = queryset.filter(keystore_type=keystore_filter)
        
        # Application server filter
        app_server_filter = self.request.GET.get('app_server', '')
        if app_server_filter:
            queryset = queryset.filter(application_server=app_server_filter)
        
        # Expiry status filter
        status_filter = self.request.GET.get('status', '')
        today = timezone.now()
        
        if status_filter == 'expired':
            queryset = queryset.filter(valid_to__lt=today)
        elif status_filter == 'critical':
            queryset = queryset.filter(valid_to__lt=today + timedelta(days=7), valid_to__gte=today)
        elif status_filter == 'warning':
            queryset = queryset.filter(valid_to__lt=today + timedelta(days=30), valid_to__gte=today + timedelta(days=7))
        elif status_filter == 'valid':
            queryset = queryset.filter(valid_to__gte=today + timedelta(days=30))
        
        return queryset.order_by('valid_to', 'common_name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Get filter options
        environments = JavaCertificate.objects.filter(is_active=True).values_list('environment', flat=True).distinct()
        environments = [env for env in environments if env]
        
        keystore_types = JavaCertificate.objects.filter(is_active=True).values_list('keystore_type', flat=True).distinct()
        app_servers = JavaCertificate.objects.filter(is_active=True).values_list('application_server', flat=True).distinct()
        app_servers = [server for server in app_servers if server]
        
        # Get statistics
        today = timezone.now()
        total_certs = JavaCertificate.objects.filter(is_active=True).count()
        expired_certs = JavaCertificate.objects.filter(is_active=True, valid_to__lt=today).count()
        critical_certs = JavaCertificate.objects.filter(
            is_active=True, 
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count()
        warning_certs = JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today + timedelta(days=7)
        ).count()
        
        context.update({
            'page_title': 'Java Sertifikaları',
            'search_query': self.request.GET.get('search', ''),
            'environment_filter': self.request.GET.get('environment', ''),
            'keystore_filter': self.request.GET.get('keystore_type', ''),
            'app_server_filter': self.request.GET.get('app_server', ''),
            'status_filter': self.request.GET.get('status', ''),
            'environments': sorted(environments),
            'keystore_types': sorted(keystore_types),
            'app_servers': sorted(app_servers),
            'stats': {
                'total': total_certs,
                'expired': expired_certs,
                'critical': critical_certs,
                'warning': warning_certs,
                'valid': total_certs - expired_certs - critical_certs - warning_certs,
            }
        })
        return context


class KdbCertificateDetailView(LoginRequiredMixin, DetailView):
    """KDB Certificate Detail View"""
    model = KdbCertificate
    template_name = 'sertifikalar/kdb_certificate_detail.html'
    context_object_name = 'certificate'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.get_object()
        
        # Get related certificates (same server or application)
        related_certificates = KdbCertificate.objects.filter(
            Q(server_hostname=certificate.server_hostname) |
            Q(application_name=certificate.application_name)
        ).exclude(pk=certificate.pk).filter(is_active=True)[:5]
        
        # Get notification history
        notifications = CertificateNotification.objects.filter(
            certificate_type='kdb',
            certificate_id=certificate.pk
        ).order_by('-created_at')[:10]
        
        context.update({
            'page_title': f'KDB Sertifika - {certificate.common_name}',
            'related_certificates': related_certificates,
            'notifications': notifications,
        })
        return context


class JavaCertificateDetailView(LoginRequiredMixin, DetailView):
    """Java Certificate Detail View"""
    model = JavaCertificate
    template_name = 'sertifikalar/java_certificate_detail.html'
    context_object_name = 'certificate'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        certificate = self.get_object()
        
        # Get related certificates (same server or application)
        related_certificates = JavaCertificate.objects.filter(
            Q(server_hostname=certificate.server_hostname) |
            Q(java_application=certificate.java_application)
        ).exclude(pk=certificate.pk).filter(is_active=True)[:5]
        
        # Get notification history
        notifications = CertificateNotification.objects.filter(
            certificate_type='java',
            certificate_id=certificate.pk
        ).order_by('-created_at')[:10]
        
        context.update({
            'page_title': f'Java Sertifika - {certificate.common_name}',
            'related_certificates': related_certificates,
            'notifications': notifications,
        })
        return context


@login_required
def certificate_dashboard(request):
    """Certificate management dashboard"""
    today = timezone.now()
    
    # Get expiring certificates from both types
    expiring_kdb = KdbCertificate.objects.filter(
        is_active=True,
        valid_to__lt=today + timedelta(days=30),
        valid_to__gte=today
    ).order_by('valid_to')[:10]
    
    expiring_java = JavaCertificate.objects.filter(
        is_active=True,
        valid_to__lt=today + timedelta(days=30),
        valid_to__gte=today
    ).order_by('valid_to')[:10]
    
    # Get expired certificates
    expired_kdb = KdbCertificate.objects.filter(
        is_active=True,
        valid_to__lt=today
    ).order_by('valid_to')[:5]
    
    expired_java = JavaCertificate.objects.filter(
        is_active=True,
        valid_to__lt=today
    ).order_by('valid_to')[:5]
    
    # Statistics
    kdb_stats = {
        'total': KdbCertificate.objects.filter(is_active=True).count(),
        'expired': KdbCertificate.objects.filter(is_active=True, valid_to__lt=today).count(),
        'critical': KdbCertificate.objects.filter(
            is_active=True, 
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count(),
        'warning': KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today + timedelta(days=7)
        ).count(),
    }
    
    java_stats = {
        'total': JavaCertificate.objects.filter(is_active=True).count(),
        'expired': JavaCertificate.objects.filter(is_active=True, valid_to__lt=today).count(),
        'critical': JavaCertificate.objects.filter(
            is_active=True, 
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count(),
        'warning': JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today + timedelta(days=7)
        ).count(),
    }
    
    # Recent notifications
    recent_notifications = CertificateNotification.objects.filter(
        is_sent=True
    ).order_by('-sent_at')[:10]
    
    context = {
        'page_title': 'Sertifika Yönetimi Dashboard',
        'expiring_kdb': expiring_kdb,
        'expiring_java': expiring_java,
        'expired_kdb': expired_kdb,
        'expired_java': expired_java,
        'kdb_stats': kdb_stats,
        'java_stats': java_stats,
        'recent_notifications': recent_notifications,
    }
    
    return render(request, 'sertifikalar/dashboard.html', context)


# AJAX Views
@login_required
def certificate_stats_api(request):
    """API endpoint for certificate statistics"""
    today = timezone.now()
    
    # KDB Statistics
    kdb_stats = {
        'total': KdbCertificate.objects.filter(is_active=True).count(),
        'expired': KdbCertificate.objects.filter(is_active=True, valid_to__lt=today).count(),
        'expiring_30': KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today
        ).count(),
        'expiring_7': KdbCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count(),
    }
    
    # Java Statistics
    java_stats = {
        'total': JavaCertificate.objects.filter(is_active=True).count(),
        'expired': JavaCertificate.objects.filter(is_active=True, valid_to__lt=today).count(),
        'expiring_30': JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=30),
            valid_to__gte=today
        ).count(),
        'expiring_7': JavaCertificate.objects.filter(
            is_active=True,
            valid_to__lt=today + timedelta(days=7),
            valid_to__gte=today
        ).count(),
    }
    
    return JsonResponse({
        'kdb': kdb_stats,
        'java': java_stats,
        'total': {
            'certificates': kdb_stats['total'] + java_stats['total'],
            'expired': kdb_stats['expired'] + java_stats['expired'],
            'expiring_30': kdb_stats['expiring_30'] + java_stats['expiring_30'],
            'expiring_7': kdb_stats['expiring_7'] + java_stats['expiring_7'],
        }
    })


@login_required
def expiring_certificates_widget(request):
    """AJAX endpoint for expiring certificates widget"""
    days = int(request.GET.get('days', 30))
    limit = int(request.GET.get('limit', 5))
    
    today = timezone.now()
    cutoff_date = today + timedelta(days=days)
    
    # Get expiring certificates from both types
    kdb_certs = list(KdbCertificate.objects.filter(
        is_active=True,
        valid_to__lt=cutoff_date,
        valid_to__gte=today
    ).order_by('valid_to').values(
        'id', 'common_name', 'server_hostname', 'application_name', 
        'valid_to', 'environment'
    )[:limit])
    
    java_certs = list(JavaCertificate.objects.filter(
        is_active=True,
        valid_to__lt=cutoff_date,
        valid_to__gte=today
    ).order_by('valid_to').values(
        'id', 'common_name', 'server_hostname', 'java_application', 
        'valid_to', 'environment'
    )[:limit])
    
    # Add certificate type to each certificate
    for cert in kdb_certs:
        cert['type'] = 'kdb'
        cert['application'] = cert.get('application_name', '')
    
    for cert in java_certs:
        cert['type'] = 'java'
        cert['application'] = cert.get('java_application', '')
    
    # Combine and sort by expiry date
    all_certs = kdb_certs + java_certs
    all_certs.sort(key=lambda x: x['valid_to'])
    
    return JsonResponse({
        'certificates': all_certs[:limit],
        'total_count': len(all_certs)
    })
