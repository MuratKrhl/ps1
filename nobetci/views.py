from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q
from django.utils import timezone
from datetime import datetime, timedelta
from .models import DutySchedule, Team, DutyType, EmergencyContact, DutyLog, Nobetci


@login_required
def duty_list(request):
    """Current and upcoming duty schedules"""
    now = timezone.now()
    today = now.date()
    
    # Get current duties
    current_duties = DutySchedule.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        status='active',
        is_active=True
    ).select_related('user', 'team', 'duty_type').order_by('start_time')
    
    # Get upcoming duties (next 30 days)
    upcoming_duties = DutySchedule.objects.filter(
        start_date__gt=today,
        start_date__lte=today + timedelta(days=30),
        status='scheduled',
        is_active=True
    ).select_related('user', 'team', 'duty_type').order_by('start_date', 'start_time')
    
    # Filter by team
    team_filter = request.GET.get('team', '')
    if team_filter:
        current_duties = current_duties.filter(team_id=team_filter)
        upcoming_duties = upcoming_duties.filter(team_id=team_filter)
    
    # Filter by duty type
    type_filter = request.GET.get('type', '')
    if type_filter:
        current_duties = current_duties.filter(duty_type_id=type_filter)
        upcoming_duties = upcoming_duties.filter(duty_type_id=type_filter)
    
    # Get filter options
    teams = Team.objects.filter(is_active=True)
    duty_types = DutyType.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Nöbet Listesi',
        'current_duties': current_duties,
        'upcoming_duties': upcoming_duties[:10],  # Limit upcoming duties
        'teams': teams,
        'duty_types': duty_types,
        'current_filters': {
            'team': team_filter,
            'type': type_filter,
        }
    }
    
    return render(request, 'nobetci/duty_list.html', context)


@login_required
def duty_calendar(request):
    """Calendar view of duty schedules"""
    # Get month and year from request
    month = int(request.GET.get('month', timezone.now().month))
    year = int(request.GET.get('year', timezone.now().year))
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1).date()
    if month == 12:
        end_date = datetime(year + 1, 1, 1).date() - timedelta(days=1)
    else:
        end_date = datetime(year, month + 1, 1).date() - timedelta(days=1)
    
    # Get duties for the month
    duties = DutySchedule.objects.filter(
        start_date__lte=end_date,
        end_date__gte=start_date,
        is_active=True
    ).select_related('user', 'team', 'duty_type').order_by('start_date', 'start_time')
    
    # Filter by team
    team_filter = request.GET.get('team', '')
    if team_filter:
        duties = duties.filter(team_id=team_filter)
    
    # Get filter options
    teams = Team.objects.filter(is_active=True)
    
    # Calculate navigation dates
    prev_month = month - 1 if month > 1 else 12
    prev_year = year if month > 1 else year - 1
    next_month = month + 1 if month < 12 else 1
    next_year = year if month < 12 else year + 1
    
    context = {
        'page_title': 'Nöbet Takvimi',
        'duties': duties,
        'teams': teams,
        'current_month': month,
        'current_year': year,
        'prev_month': prev_month,
        'prev_year': prev_year,
        'next_month': next_month,
        'next_year': next_year,
        'current_filters': {
            'team': team_filter,
        }
    }
    
    return render(request, 'nobetci/duty_calendar.html', context)


@login_required
def duty_detail(request, duty_id):
    """Duty schedule detail view"""
    duty = get_object_or_404(
        DutySchedule.objects.select_related('user', 'team', 'duty_type', 'replacement_user'),
        id=duty_id, is_active=True
    )
    
    # Get duty logs
    logs = duty.logs.filter(is_active=True).order_by('-logged_at')
    
    context = {
        'page_title': f'Nöbet Detayı - {duty.user.get_full_name() or duty.user.username}',
        'duty': duty,
        'logs': logs,
    }
    
    return render(request, 'nobetci/duty_detail.html', context)


@login_required
def emergency_contacts(request):
    """Emergency contacts list"""
    contacts = EmergencyContact.objects.filter(is_active=True).select_related('team').order_by('team', 'priority', 'name')
    
    # Filter by team
    team_filter = request.GET.get('team', '')
    if team_filter:
        contacts = contacts.filter(team_id=team_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        contacts = contacts.filter(
            Q(name__icontains=search_query) |
            Q(role__icontains=search_query) |
            Q(primary_phone__icontains=search_query)
        )
    
    # Get filter options
    teams = Team.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Acil Durum Kişileri',
        'contacts': contacts,
        'teams': teams,
        'search_query': search_query,
        'current_filters': {
            'team': team_filter,
        }
    }
    
    return render(request, 'nobetci/emergency_contacts.html', context)


@login_required
def my_duties(request):
    """Current user's duty schedules"""
    now = timezone.now()
    today = now.date()
    
    # Get user's current duties
    current_duties = DutySchedule.objects.filter(
        user=request.user,
        start_date__lte=today,
        end_date__gte=today,
        status='active',
        is_active=True
    ).select_related('team', 'duty_type')
    
    # Get user's upcoming duties
    upcoming_duties = DutySchedule.objects.filter(
        user=request.user,
        start_date__gt=today,
        status='scheduled',
        is_active=True
    ).select_related('team', 'duty_type').order_by('start_date', 'start_time')[:10]
    
    # Get user's recent duties
    recent_duties = DutySchedule.objects.filter(
        user=request.user,
        end_date__lt=today,
        is_active=True
    ).select_related('team', 'duty_type').order_by('-end_date')[:5]
    
    context = {
        'page_title': 'Nöbetlerim',
        'current_duties': current_duties,
        'upcoming_duties': upcoming_duties,
        'recent_duties': recent_duties,
    }
    
    return render(request, 'nobetci/my_duties.html', context)


@login_required
def duty_dashboard(request):
    """Duty dashboard with statistics"""
    now = timezone.now()
    today = now.date()
    
    # Current statistics
    current_on_duty = DutySchedule.objects.filter(
        start_date__lte=today,
        end_date__gte=today,
        status='active',
        is_active=True
    ).count()
    
    upcoming_this_week = DutySchedule.objects.filter(
        start_date__gt=today,
        start_date__lte=today + timedelta(days=7),
        status='scheduled',
        is_active=True
    ).count()
    
    # Team statistics
    team_stats = Team.objects.filter(is_active=True).annotate(
        current_duties=models.Count(
            'duty_schedules',
            filter=Q(
                duty_schedules__start_date__lte=today,
                duty_schedules__end_date__gte=today,
                duty_schedules__status='active',
                duty_schedules__is_active=True
            )
        )
    )
    
    # Recent logs
    recent_logs = DutyLog.objects.filter(
        is_active=True
    ).select_related('duty_schedule__user', 'duty_schedule__team').order_by('-logged_at')[:10]
    
    context = {
        'page_title': 'Nöbet Dashboard',
        'stats': {
            'current_on_duty': current_on_duty,
            'upcoming_this_week': upcoming_this_week,
        },
        'team_stats': team_stats,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'nobetci/duty_dashboard.html', context)


@login_required
def nobetci_list(request):
    """Simple duty schedule list with DataTables"""
    # Tüm nöbetçileri getir
    nobetciler = Nobetci.objects.all().order_by('-tarih')
    
    # Arama
    search_query = request.GET.get('search', '')
    if search_query:
        nobetciler = nobetciler.filter(
            Q(ad_soyad__icontains=search_query) |
            Q(telefon__icontains=search_query) |
            Q(email__icontains=search_query)
        )
    
    # Tarih filtreleme
    date_filter = request.GET.get('date_filter', '')
    if date_filter == 'current':
        nobetciler = nobetciler.filter(tarih=timezone.now().date())
    elif date_filter == 'future':
        nobetciler = nobetciler.filter(tarih__gte=timezone.now().date())
    elif date_filter == 'past':
        nobetciler = nobetciler.filter(tarih__lt=timezone.now().date())
    
    # Bu ay filtreleme
    month_filter = request.GET.get('month', '')
    if month_filter:
        try:
            year, month = month_filter.split('-')
            nobetciler = nobetciler.filter(tarih__year=year, tarih__month=month)
        except ValueError:
            pass
    
    context = {
        'page_title': 'Nöbet Listesi',
        'nobetciler': nobetciler,
        'search_query': search_query,
        'date_filter': date_filter,
        'month_filter': month_filter,
        'total_count': nobetciler.count(),
        'current_duty': Nobetci.get_current_duty(),
        'next_duty': Nobetci.get_next_duty(),
    }
    
    return render(request, 'nobetci/nobetci_list.html', context)


@login_required
def nobetci_detail(request, pk):
    """Duty schedule detail view"""
    nobetci = get_object_or_404(Nobetci, pk=pk)
    
    context = {
        'page_title': f'Nöbetçi Detayı - {nobetci.tarih.strftime("%d.%m.%Y")}',
        'nobetci': nobetci,
    }
    
    return render(request, 'nobetci/nobetci_detail.html', context)


@login_required
def current_duty_api(request):
    """API endpoint for current duty (for dashboard widget)"""
    from django.http import JsonResponse
    
    current_duty = Nobetci.get_current_duty()
    next_duty = Nobetci.get_next_duty()
    
    data = {
        'current_duty': None,
        'next_duty': None,
        'has_current': False,
        'has_next': False,
    }
    
    if current_duty:
        data['current_duty'] = {
            'id': current_duty.id,
            'tarih': current_duty.tarih.strftime('%d.%m.%Y'),
            'ad_soyad': current_duty.ad_soyad,
            'telefon': current_duty.telefon,
            'email': current_duty.email,
            'notlar': current_duty.notlar,
        }
        data['has_current'] = True
    
    if next_duty:
        data['next_duty'] = {
            'id': next_duty.id,
            'tarih': next_duty.tarih.strftime('%d.%m.%Y'),
            'ad_soyad': next_duty.ad_soyad,
            'telefon': next_duty.telefon,
            'email': next_duty.email,
            'days_until': next_duty.days_until,
        }
        data['has_next'] = True
    
    return JsonResponse(data)
