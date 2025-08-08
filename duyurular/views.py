from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, permission_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.utils import timezone
from django.views.generic import ListView, DetailView, CreateView, UpdateView
from django.contrib import messages
from django.http import JsonResponse
from django.urls import reverse_lazy
from django.views.decorators.http import require_http_methods
import json
from .models import Announcement, AnnouncementCategory, MaintenanceNotice, SystemStatus, AnnouncementView
from .forms import AnnouncementForm


class AnnouncementListView(LoginRequiredMixin, ListView):
    """List all active announcements with filtering and search"""
    model = Announcement
    template_name = 'duyurular/announcement_list.html'
    context_object_name = 'announcements'
    paginate_by = 10
    
    def get_queryset(self):
        """Filter announcements based on status and expiry"""
        queryset = Announcement.objects.filter(
            status='published'
        ).select_related('category', 'created_by').prefetch_related('tags')
        
        # Filter expired announcements
        now = timezone.now()
        queryset = queryset.filter(
            Q(yayin_bitis_tarihi__isnull=True) | Q(yayin_bitis_tarihi__gt=now)
        )
        
        # Search functionality
        search_query = self.request.GET.get('search', '')
        if search_query:
            queryset = queryset.filter(
                Q(title__icontains=search_query) |
                Q(content__icontains=search_query) |
                Q(summary__icontains=search_query)
            )
        
        # Filter by category
        category_filter = self.request.GET.get('category', '')
        if category_filter:
            queryset = queryset.filter(category_id=category_filter)
        
        # Filter by announcement type
        type_filter = self.request.GET.get('type', '')
        if type_filter:
            queryset = queryset.filter(duyuru_tipi=type_filter)
        
        # Filter by priority
        priority_filter = self.request.GET.get('priority', '')
        if priority_filter:
            queryset = queryset.filter(onem_seviyesi=priority_filter)
        
        # Filter by importance
        important_only = self.request.GET.get('important', '') == 'true'
        if important_only:
            queryset = queryset.filter(is_important=True)
        
        # Ordering: pinned first, then by priority and date
        return queryset.order_by('-sabitle', '-onem_seviyesi', '-published_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['categories'] = AnnouncementCategory.objects.filter(is_active=True)
        context['announcement_types'] = Announcement._meta.get_field('duyuru_tipi').choices
        context['priority_levels'] = Announcement._meta.get_field('onem_seviyesi').choices
        context['search_query'] = self.request.GET.get('search', '')
        context['selected_category'] = self.request.GET.get('category', '')
        context['selected_type'] = self.request.GET.get('type', '')
        context['selected_priority'] = self.request.GET.get('priority', '')
        context['show_important'] = self.request.GET.get('important', '') == 'true'
        return context


class AnnouncementCreateView(PermissionRequiredMixin, CreateView):
    """Create new announcement - Admin only"""
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'duyurular/announcement_form.html'
    permission_required = 'duyurular.add_announcement'
    success_url = reverse_lazy('duyurular:announcement_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Handle different submit actions
        action = self.request.POST.get('action', 'draft')
        form.instance.status = 'published' if action == 'publish' else 'draft'
        
        if form.instance.status == 'published' and not form.instance.published_at:
            form.instance.published_at = timezone.now()
        
        response = super().form_valid(form)
        
        if action == 'publish':
            messages.success(self.request, f'Duyuru "{self.object.title}" başarıyla yayınlandı.')
        else:
            messages.success(self.request, f'Duyuru "{self.object.title}" taslak olarak kaydedildi.')
        
        return response


class AnnouncementUpdateView(PermissionRequiredMixin, UpdateView):
    """Update existing announcement - Admin only"""
    model = Announcement
    form_class = AnnouncementForm
    template_name = 'duyurular/announcement_form.html'
    permission_required = 'duyurular.change_announcement'
    success_url = reverse_lazy('duyurular:announcement_list')
    
    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs['user'] = self.request.user
        return kwargs
    
    def form_valid(self, form):
        # Handle different submit actions
        action = self.request.POST.get('action', 'save')
        
        if action == 'publish':
            form.instance.status = 'published'
            if not form.instance.published_at:
                form.instance.published_at = timezone.now()
        elif action == 'draft':
            form.instance.status = 'draft'
        elif action == 'archive':
            form.instance.status = 'archived'
        
        response = super().form_valid(form)
        
        action_messages = {
            'publish': f'Duyuru "{self.object.title}" yayınlandı.',
            'draft': f'Duyuru "{self.object.title}" taslak olarak kaydedildi.',
            'archive': f'Duyuru "{self.object.title}" arşivlendi.',
            'save': f'Duyuru "{self.object.title}" güncellendi.'
        }
        
        messages.success(self.request, action_messages.get(action, 'Duyuru güncellendi.'))
        return response


class AnnouncementDetailView(LoginRequiredMixin, DetailView):
    """Announcement detail view"""
    model = Announcement
    template_name = 'duyurular/announcement_detail.html'
    context_object_name = 'announcement'
    
    def get_queryset(self):
        """Only show published announcements to regular users"""
        if self.request.user.has_perm('duyurular.view_announcement'):
            # Admin can see all announcements
            return Announcement.objects.all()
        else:
            # Regular users only see published, non-expired announcements
            now = timezone.now()
            return Announcement.objects.filter(
                status='published'
            ).filter(
                Q(yayin_bitis_tarihi__isnull=True) | Q(yayin_bitis_tarihi__gt=now)
            )
    
    def get_object(self, queryset=None):
        obj = super().get_object(queryset)
        
        # Track view if user is authenticated
        if self.request.user.is_authenticated:
            view_obj, created = AnnouncementView.objects.get_or_create(
                announcement=obj,
                user=self.request.user,
                defaults={'ip_address': self.get_client_ip()}
            )
            
            # Increment view count
            obj.view_count = F('view_count') + 1
            obj.save(update_fields=['view_count'])
        
        return obj
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


@login_required
def announcement_list_legacy(request):
    """Legacy function-based view for compatibility"""
    announcements = Announcement.objects.filter(
        status='published'
    ).select_related('category', 'created_by').prefetch_related('tags')
    
    # Filter expired announcements
    now = timezone.now()
    announcements = announcements.filter(
        Q(yayin_bitis_tarihi__isnull=True) | Q(yayin_bitis_tarihi__gt=now)
    )
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        announcements = announcements.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(summary__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        announcements = announcements.filter(category_id=category_filter)
    
    # Filter by priority
    priority_filter = request.GET.get('priority', '')
    if priority_filter:
        announcements = announcements.filter(priority=priority_filter)
    
    # Filter by importance
    important_only = request.GET.get('important', '') == 'true'
    if important_only:
        announcements = announcements.filter(is_important=True)
    
    # Ordering
    announcements = announcements.order_by('-is_pinned', '-priority', '-published_at')
    
    # Pagination
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = AnnouncementCategory.objects.filter(is_active=True)
    priority_choices = Announcement._meta.get_field('priority').choices
    
    context = {
        'page_title': 'Duyurular',
        'announcements': page_obj,
        'search_query': search_query,
        'categories': categories,
        'priority_choices': priority_choices,
        'current_filters': {
            'category': category_filter,
            'priority': priority_filter,
            'important': important_only,
        }
    }
    
    return render(request, 'duyurular/announcement_list.html', context)


# API Views for AJAX operations
@require_http_methods(["POST"])
@permission_required('duyurular.add_announcement', raise_exception=True)
def announcement_create_api(request):
    """API endpoint for creating announcements via AJAX"""
    try:
        form = AnnouncementForm(request.POST)
        if form.is_valid():
            announcement = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Duyuru başarıyla oluşturuldu!',
                'announcement_id': announcement.id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Form hatası!',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Hata oluştu: {str(e)}'
        }, status=500)


@require_http_methods(["GET"])
def announcement_detail_api(request, pk):
    """API endpoint for getting announcement details"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        return JsonResponse({
            'id': announcement.id,
            'title': announcement.title,
            'content': announcement.content,
            'category': announcement.category.id if announcement.category else None,
            'duyuru_tipi': announcement.duyuru_tipi,
            'onem_seviyesi': announcement.onem_seviyesi,
            'ilgili_urun': announcement.ilgili_urun,
            'sabitle': announcement.sabitle,
            'calisma_tarihi': announcement.calisma_tarihi.isoformat() if announcement.calisma_tarihi else None,
            'yayin_bitis_tarihi': announcement.yayin_bitis_tarihi.isoformat() if announcement.yayin_bitis_tarihi else None,
            'status': announcement.status
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Hata oluştu: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@permission_required('duyurular.change_announcement', raise_exception=True)
def announcement_update_api(request, pk):
    """API endpoint for updating announcements via AJAX"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        form = AnnouncementForm(request.POST, instance=announcement)
        if form.is_valid():
            announcement = form.save()
            return JsonResponse({
                'success': True,
                'message': 'Duyuru başarıyla güncellendi!',
                'announcement_id': announcement.id
            })
        else:
            return JsonResponse({
                'success': False,
                'message': 'Form hatası!',
                'errors': form.errors
            }, status=400)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Hata oluştu: {str(e)}'
        }, status=500)


@require_http_methods(["DELETE"])
@permission_required('duyurular.delete_announcement', raise_exception=True)
def announcement_delete_api(request, pk):
    """API endpoint for deleting announcements via AJAX"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        announcement.delete()
        return JsonResponse({
            'success': True,
            'message': 'Duyuru başarıyla silindi!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Hata oluştu: {str(e)}'
        }, status=500)


@require_http_methods(["POST"])
@permission_required('duyurular.change_announcement', raise_exception=True)
def announcement_status_api(request, pk):
    """API endpoint for updating announcement status via AJAX"""
    try:
        announcement = get_object_or_404(Announcement, pk=pk)
        data = json.loads(request.body)
        new_status = data.get('status')
        
        if new_status not in ['draft', 'published', 'archived']:
            return JsonResponse({
                'success': False,
                'message': 'Geçersiz durum!'
            }, status=400)
        
        announcement.status = new_status
        if new_status == 'published' and not announcement.published_at:
            announcement.published_at = timezone.now()
        
        announcement.save()
        
        return JsonResponse({
            'success': True,
            'message': f'Duyuru durumu {announcement.get_status_display()} olarak güncellendi!'
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': f'Hata oluştu: {str(e)}'
        }, status=500)


@login_required
def announcement_detail(request, slug):
    """Announcement detail view"""
    announcement = get_object_or_404(
        Announcement.objects.select_related('category', 'created_by', 'approved_by')
                           .prefetch_related('tags'),
        slug=slug, status='published', is_active=True
    )
    
    # Check if announcement is expired
    if announcement.is_expired:
        # You might want to show a different template or redirect
        pass
    
    # Track view
    view, created = AnnouncementView.objects.get_or_create(
        announcement=announcement,
        user=request.user,
        defaults={'ip_address': request.META.get('REMOTE_ADDR')}
    )
    
    if created:
        # Increment view count
        Announcement.objects.filter(id=announcement.id).update(view_count=F('view_count') + 1)
    
    # Get comments
    comments = announcement.comments.filter(
        is_approved=True, is_active=True, parent=None
    ).select_related('created_by').prefetch_related('replies').order_by('created_at')
    
    # Related announcements
    related_announcements = Announcement.objects.filter(
        category=announcement.category, status='published', is_active=True
    ).exclude(id=announcement.id)[:5]
    
    context = {
        'page_title': announcement.title,
        'announcement': announcement,
        'comments': comments,
        'related_announcements': related_announcements,
    }
    
    return render(request, 'duyurular/announcement_detail.html', context)


@login_required
def important_announcements(request):
    """List only important announcements"""
    announcements = Announcement.objects.filter(
        status='published', is_active=True, is_important=True
    ).select_related('category', 'created_by').prefetch_related('tags')
    
    # Filter expired announcements
    now = timezone.now()
    announcements = announcements.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).order_by('-is_pinned', '-priority', '-published_at')
    
    context = {
        'page_title': 'Önemli Duyurular',
        'announcements': announcements,
    }
    
    return render(request, 'duyurular/important_announcements.html', context)


@login_required
def maintenance_notices(request):
    """List maintenance notices"""
    notices = MaintenanceNotice.objects.filter(is_active=True).order_by('-start_time')
    
    # Separate current, upcoming, and completed
    now = timezone.now()
    current_notices = notices.filter(
        start_time__lte=now, end_time__gte=now, status='in_progress'
    )
    upcoming_notices = notices.filter(
        start_time__gt=now, status='scheduled'
    )[:5]
    recent_notices = notices.filter(
        status='completed'
    )[:10]
    
    context = {
        'page_title': 'Bakım Bildirimleri',
        'current_notices': current_notices,
        'upcoming_notices': upcoming_notices,
        'recent_notices': recent_notices,
    }
    
    return render(request, 'duyurular/maintenance_notices.html', context)


@login_required
def system_status(request):
    """System status page"""
    statuses = SystemStatus.objects.filter(is_active=True).order_by('system_name', '-started_at')
    
    # Get latest status for each system
    latest_statuses = {}
    for status in statuses:
        if status.system_name not in latest_statuses:
            latest_statuses[status.system_name] = status
    
    # Separate by status
    operational_systems = []
    issues = []
    
    for system_name, status in latest_statuses.items():
        if status.status == 'operational':
            operational_systems.append(status)
        else:
            issues.append(status)
    
    # Get recent incidents
    recent_incidents = SystemStatus.objects.filter(
        is_active=True, resolved_at__isnull=False
    ).order_by('-resolved_at')[:10]
    
    context = {
        'page_title': 'Sistem Durumu',
        'operational_systems': operational_systems,
        'issues': issues,
        'recent_incidents': recent_incidents,
    }
    
    return render(request, 'duyurular/system_status.html', context)


@login_required
def category_announcements(request, category_id):
    """Announcements by category"""
    category = get_object_or_404(AnnouncementCategory, id=category_id, is_active=True)
    
    announcements = Announcement.objects.filter(
        category=category, status='published', is_active=True
    ).select_related('created_by').prefetch_related('tags')
    
    # Filter expired announcements
    now = timezone.now()
    announcements = announcements.filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).order_by('-is_pinned', '-priority', '-published_at')
    
    # Pagination
    paginator = Paginator(announcements, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': f'{category.name} Duyuruları',
        'category': category,
        'announcements': page_obj,
    }
    
    return render(request, 'duyurular/category_announcements.html', context)


@login_required
def duyurular_dashboard(request):
    """Announcements dashboard"""
    now = timezone.now()
    
    # Recent announcements
    recent_announcements = Announcement.objects.filter(
        status='published', is_active=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).select_related('category').order_by('-published_at')[:5]
    
    # Pinned announcements
    pinned_announcements = Announcement.objects.filter(
        status='published', is_active=True, is_pinned=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).select_related('category').order_by('-priority', '-published_at')[:3]
    
    # Important announcements
    important_announcements = Announcement.objects.filter(
        status='published', is_active=True, is_important=True
    ).filter(
        Q(expires_at__isnull=True) | Q(expires_at__gt=now)
    ).select_related('category').order_by('-published_at')[:3]
    
    # Current maintenance
    current_maintenance = MaintenanceNotice.objects.filter(
        start_time__lte=now, end_time__gte=now, status='in_progress', is_active=True
    )
    
    # System issues
    system_issues = SystemStatus.objects.filter(
        is_active=True, resolved_at__isnull=True
    ).exclude(status='operational')
    
    # Statistics
    total_announcements = Announcement.objects.filter(
        status='published', is_active=True
    ).count()
    
    context = {
        'page_title': 'Duyurular Dashboard',
        'recent_announcements': recent_announcements,
        'pinned_announcements': pinned_announcements,
        'important_announcements': important_announcements,
        'current_maintenance': current_maintenance,
        'system_issues': system_issues,
        'stats': {
            'total_announcements': total_announcements,
            'current_maintenance_count': current_maintenance.count(),
            'system_issues_count': system_issues.count(),
        }
    }
    
    return render(request, 'duyurular/dashboard.html', context)
