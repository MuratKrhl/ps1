from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import Announcement, AnnouncementCategory, AnnouncementComment, MaintenanceNotice, SystemStatus
from .forms import (
    AnnouncementForm, AnnouncementCategoryForm, AnnouncementCommentForm,
    MaintenanceNoticeForm, SystemStatusForm, AnnouncementFilterForm,
    BulkAnnouncementActionForm
)
import json


def is_staff_or_editor(user):
    """Staff veya editor kontrolü"""
    return user.is_staff or user.groups.filter(name='Duyuru Editörleri').exists()


@login_required
@user_passes_test(is_staff_or_editor)
def announcement_management(request):
    """Duyuru yönetim ana sayfası"""
    # İstatistikler
    stats = {
        'total_announcements': Announcement.objects.count(),
        'active_announcements': Announcement.objects.filter(is_active=True).count(),
        'important_announcements': Announcement.objects.filter(is_important=True, is_active=True).count(),
        'pinned_announcements': Announcement.objects.filter(is_pinned=True, is_active=True).count(),
        'expired_announcements': Announcement.objects.filter(
            expiry_date__lt=timezone.now(), is_active=True
        ).count(),
        'total_views': sum(Announcement.objects.values_list('view_count', flat=True)),
        'total_comments': AnnouncementComment.objects.count(),
        'categories': AnnouncementCategory.objects.filter(is_active=True).count()
    }
    
    # Son duyurular
    recent_announcements = Announcement.objects.select_related(
        'author', 'category'
    ).order_by('-created_at')[:10]
    
    # En çok görüntülenen duyurular
    popular_announcements = Announcement.objects.select_related(
        'author', 'category'
    ).filter(is_active=True).order_by('-view_count')[:5]
    
    # Son yorumlar
    recent_comments = AnnouncementComment.objects.select_related(
        'author', 'announcement'
    ).order_by('-created_at')[:10]
    
    context = {
        'stats': stats,
        'recent_announcements': recent_announcements,
        'popular_announcements': popular_announcements,
        'recent_comments': recent_comments,
    }
    
    return render(request, 'duyurular/management/dashboard.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def announcement_list_management(request):
    """Duyuru listesi yönetimi"""
    announcements = Announcement.objects.select_related('author', 'category').prefetch_related('tags')
    
    # Filtreleme formu
    filter_form = AnnouncementFilterForm(request.GET)
    if filter_form.is_valid():
        if filter_form.cleaned_data['category']:
            announcements = announcements.filter(category=filter_form.cleaned_data['category'])
        
        if filter_form.cleaned_data['priority']:
            announcements = announcements.filter(priority=filter_form.cleaned_data['priority'])
        
        if filter_form.cleaned_data['target_audience']:
            announcements = announcements.filter(target_audience=filter_form.cleaned_data['target_audience'])
        
        if filter_form.cleaned_data['is_important']:
            announcements = announcements.filter(is_important=True)
        
        if filter_form.cleaned_data['date_from']:
            announcements = announcements.filter(created_at__gte=filter_form.cleaned_data['date_from'])
        
        if filter_form.cleaned_data['date_to']:
            announcements = announcements.filter(created_at__lte=filter_form.cleaned_data['date_to'])
        
        if filter_form.cleaned_data['search']:
            search = filter_form.cleaned_data['search']
            announcements = announcements.filter(
                Q(title__icontains=search) | Q(content__icontains=search)
            )
    
    # Sıralama
    sort_by = request.GET.get('sort', '-created_at')
    announcements = announcements.order_by(sort_by)
    
    # Sayfalama
    paginator = Paginator(announcements, 25)
    page = request.GET.get('page')
    announcements = paginator.get_page(page)
    
    # Toplu işlem formu
    bulk_form = BulkAnnouncementActionForm()
    
    context = {
        'announcements': announcements,
        'filter_form': filter_form,
        'bulk_form': bulk_form,
        'sort_by': sort_by,
    }
    
    return render(request, 'duyurular/management/announcement_list.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def announcement_create(request):
    """Yeni duyuru oluştur"""
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, user=request.user)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, f'Duyuru "{announcement.title}" başarıyla oluşturuldu.')
            return redirect('duyurular:management_announcement_detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Yeni Duyuru Oluştur'
    }
    
    return render(request, 'duyurular/management/announcement_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def announcement_edit(request, announcement_id):
    """Duyuru düzenle"""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Sadece kendi duyurusunu veya admin düzenleyebilir
    if announcement.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Bu duyuruyu düzenleme izniniz yok.")
    
    if request.method == 'POST':
        form = AnnouncementForm(request.POST, instance=announcement, user=request.user)
        if form.is_valid():
            announcement = form.save()
            messages.success(request, f'Duyuru "{announcement.title}" başarıyla güncellendi.')
            return redirect('duyurular:management_announcement_detail', announcement_id=announcement.id)
    else:
        form = AnnouncementForm(instance=announcement, user=request.user)
    
    context = {
        'form': form,
        'announcement': announcement,
        'title': f'Duyuru Düzenle: {announcement.title}'
    }
    
    return render(request, 'duyurular/management/announcement_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def announcement_detail_management(request, announcement_id):
    """Duyuru detay yönetimi"""
    announcement = get_object_or_404(
        Announcement.objects.select_related('author', 'category').prefetch_related('tags'),
        id=announcement_id
    )
    
    # Yorumlar
    comments = announcement.comments.select_related('author').filter(
        is_approved=True
    ).order_by('-created_at')
    
    # İstatistikler
    stats = {
        'view_count': announcement.view_count,
        'comment_count': comments.count(),
        'days_since_published': (timezone.now() - announcement.created_at).days,
        'is_expired': announcement.is_expired,
    }
    
    context = {
        'announcement': announcement,
        'comments': comments,
        'stats': stats,
    }
    
    return render(request, 'duyurular/management/announcement_detail.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
@require_http_methods(["POST"])
def announcement_delete(request, announcement_id):
    """Duyuru sil"""
    announcement = get_object_or_404(Announcement, id=announcement_id)
    
    # Sadece kendi duyurusunu veya admin silebilir
    if announcement.author != request.user and not request.user.is_staff:
        return HttpResponseForbidden("Bu duyuruyu silme izniniz yok.")
    
    title = announcement.title
    announcement.delete()
    messages.success(request, f'Duyuru "{title}" başarıyla silindi.')
    
    return redirect('duyurular:management_announcement_list')


@login_required
@user_passes_test(is_staff_or_editor)
@csrf_exempt
@require_http_methods(["POST"])
def bulk_announcement_action(request):
    """Toplu duyuru işlemleri"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        announcement_ids = data.get('announcement_ids', [])
        
        if not action or not announcement_ids:
            return JsonResponse({'success': False, 'error': 'Geçersiz parametreler'})
        
        announcements = Announcement.objects.filter(id__in=announcement_ids)
        
        # İzin kontrolü (admin değilse sadece kendi duyurularını işleyebilir)
        if not request.user.is_staff:
            announcements = announcements.filter(author=request.user)
        
        count = announcements.count()
        
        if action == 'delete':
            announcements.delete()
            message = f'{count} duyuru silindi'
        
        elif action == 'pin':
            announcements.update(is_pinned=True)
            message = f'{count} duyuru sabitlendi'
        
        elif action == 'unpin':
            announcements.update(is_pinned=False)
            message = f'{count} duyuru sabitlemeden çıkarıldı'
        
        elif action == 'mark_important':
            announcements.update(is_important=True)
            message = f'{count} duyuru önemli olarak işaretlendi'
        
        elif action == 'unmark_important':
            announcements.update(is_important=False)
            message = f'{count} duyuru önemli işaretinden çıkarıldı'
        
        elif action == 'change_category':
            category_id = data.get('category_id')
            if category_id:
                category = get_object_or_404(AnnouncementCategory, id=category_id)
                announcements.update(category=category)
                message = f'{count} duyuru kategorisi "{category.name}" olarak değiştirildi'
            else:
                return JsonResponse({'success': False, 'error': 'Kategori seçilmedi'})
        
        elif action == 'set_expiry':
            expiry_date = data.get('expiry_date')
            if expiry_date:
                announcements.update(expiry_date=expiry_date)
                message = f'{count} duyuru için son kullanma tarihi belirlendi'
            else:
                return JsonResponse({'success': False, 'error': 'Son kullanma tarihi seçilmedi'})
        
        else:
            return JsonResponse({'success': False, 'error': 'Geçersiz işlem'})
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})


@login_required
@user_passes_test(is_staff_or_editor)
def maintenance_notice_management(request):
    """Bakım bildirimi yönetimi"""
    notices = MaintenanceNotice.objects.select_related('created_by').order_by('-created_at')
    
    # Filtreleme
    status = request.GET.get('status')
    if status:
        notices = notices.filter(status=status)
    
    maintenance_type = request.GET.get('type')
    if maintenance_type:
        notices = notices.filter(maintenance_type=maintenance_type)
    
    # Sayfalama
    paginator = Paginator(notices, 20)
    page = request.GET.get('page')
    notices = paginator.get_page(page)
    
    context = {
        'notices': notices,
        'status_choices': MaintenanceNotice._meta.get_field('status').choices,
        'type_choices': MaintenanceNotice._meta.get_field('maintenance_type').choices,
        'current_status': status,
        'current_type': maintenance_type,
    }
    
    return render(request, 'duyurular/management/maintenance_list.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def maintenance_notice_create(request):
    """Yeni bakım bildirimi oluştur"""
    if request.method == 'POST':
        form = MaintenanceNoticeForm(request.POST, user=request.user)
        if form.is_valid():
            notice = form.save()
            messages.success(request, f'Bakım bildirimi "{notice.title}" başarıyla oluşturuldu.')
            return redirect('duyurular:management_maintenance_list')
    else:
        form = MaintenanceNoticeForm(user=request.user)
    
    context = {
        'form': form,
        'title': 'Yeni Bakım Bildirimi'
    }
    
    return render(request, 'duyurular/management/maintenance_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def maintenance_notice_edit(request, notice_id):
    """Bakım bildirimi düzenle"""
    notice = get_object_or_404(MaintenanceNotice, id=notice_id)
    
    if request.method == 'POST':
        form = MaintenanceNoticeForm(request.POST, instance=notice, user=request.user)
        if form.is_valid():
            notice = form.save()
            messages.success(request, f'Bakım bildirimi "{notice.title}" başarıyla güncellendi.')
            return redirect('duyurular:management_maintenance_list')
    else:
        form = MaintenanceNoticeForm(instance=notice, user=request.user)
    
    context = {
        'form': form,
        'notice': notice,
        'title': f'Bakım Bildirimi Düzenle: {notice.title}'
    }
    
    return render(request, 'duyurular/management/maintenance_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def system_status_management(request):
    """Sistem durumu yönetimi"""
    systems = SystemStatus.objects.order_by('system_name')
    
    # Durum filtreleme
    status = request.GET.get('status')
    if status:
        systems = systems.filter(status=status)
    
    context = {
        'systems': systems,
        'status_choices': SystemStatus._meta.get_field('status').choices,
        'current_status': status,
    }
    
    return render(request, 'duyurular/management/system_status_list.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def system_status_create(request):
    """Yeni sistem durumu oluştur"""
    if request.method == 'POST':
        form = SystemStatusForm(request.POST)
        if form.is_valid():
            system = form.save()
            messages.success(request, f'Sistem durumu "{system.system_name}" başarıyla oluşturuldu.')
            return redirect('duyurular:management_system_status_list')
    else:
        form = SystemStatusForm()
    
    context = {
        'form': form,
        'title': 'Yeni Sistem Durumu'
    }
    
    return render(request, 'duyurular/management/system_status_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def system_status_edit(request, system_id):
    """Sistem durumu düzenle"""
    system = get_object_or_404(SystemStatus, id=system_id)
    
    if request.method == 'POST':
        form = SystemStatusForm(request.POST, instance=system)
        if form.is_valid():
            system = form.save()
            messages.success(request, f'Sistem durumu "{system.system_name}" başarıyla güncellendi.')
            return redirect('duyurular:management_system_status_list')
    else:
        form = SystemStatusForm(instance=system)
    
    context = {
        'form': form,
        'system': system,
        'title': f'Sistem Durumu Düzenle: {system.system_name}'
    }
    
    return render(request, 'duyurular/management/system_status_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def category_management(request):
    """Kategori yönetimi"""
    categories = AnnouncementCategory.objects.annotate(
        announcement_count=Count('announcements')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'duyurular/management/category_list.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def category_create(request):
    """Yeni kategori oluştur"""
    if request.method == 'POST':
        form = AnnouncementCategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Kategori "{category.name}" başarıyla oluşturuldu.')
            return redirect('duyurular:management_category_list')
    else:
        form = AnnouncementCategoryForm()
    
    context = {
        'form': form,
        'title': 'Yeni Kategori'
    }
    
    return render(request, 'duyurular/management/category_form.html', context)


@login_required
@user_passes_test(is_staff_or_editor)
def category_edit(request, category_id):
    """Kategori düzenle"""
    category = get_object_or_404(AnnouncementCategory, id=category_id)
    
    if request.method == 'POST':
        form = AnnouncementCategoryForm(request.POST, instance=category)
        if form.is_valid():
            category = form.save()
            messages.success(request, f'Kategori "{category.name}" başarıyla güncellendi.')
            return redirect('duyurular:management_category_list')
    else:
        form = AnnouncementCategoryForm(instance=category)
    
    context = {
        'form': form,
        'category': category,
        'title': f'Kategori Düzenle: {category.name}'
    }
    
    return render(request, 'duyurular/management/category_form.html', context)
