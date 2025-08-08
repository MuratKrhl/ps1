from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.core.paginator import Paginator
from django.db.models import Q, Count
from django.utils import timezone
from .models import (
    AnsiblePlaybook, PlaybookExecution, AutomationSchedule, 
    AutomationLog, AutomationTemplate, PlaybookCategory
)
from .ansible_models import AnsibleJobTemplate, AnsibleJobExecution, AnsibleJobLog
from .forms import DynamicJobTemplateForm, JobTemplateFilterForm, JobExecutionFilterForm
from .services import AnsibleTowerService
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.views.generic import ListView, DetailView
from django.contrib.auth.decorators import permission_required
import uuid


@login_required
def otomasyon_dashboard(request):
    """Otomasyon ana sayfası"""
    # İstatistikler
    total_playbooks = AnsiblePlaybook.objects.count()
    active_schedules = AutomationSchedule.objects.filter(is_enabled=True).count()
    recent_executions = PlaybookExecution.objects.filter(
        created_at__gte=timezone.now() - timezone.timedelta(days=7)
    ).count()
    
    # Son çalıştırmalar
    latest_executions = PlaybookExecution.objects.select_related(
        'playbook', 'executor'
    ).order_by('-created_at')[:10]
    
    # Popüler playbook'lar
    popular_playbooks = AnsiblePlaybook.objects.filter(
        execution_count__gt=0
    ).order_by('-execution_count')[:5]
    
    # Yaklaşan programlı görevler
    upcoming_schedules = AutomationSchedule.objects.filter(
        is_enabled=True,
        next_run__isnull=False,
        next_run__gte=timezone.now()
    ).order_by('next_run')[:5]
    
    # Son loglar
    recent_logs = AutomationLog.objects.select_related(
        'user', 'playbook_execution'
    ).order_by('-created_at')[:10]
    
    context = {
        'total_playbooks': total_playbooks,
        'active_schedules': active_schedules,
        'recent_executions': recent_executions,
        'latest_executions': latest_executions,
        'popular_playbooks': popular_playbooks,
        'upcoming_schedules': upcoming_schedules,
        'recent_logs': recent_logs,
    }
    
    return render(request, 'otomasyon/dashboard.html', context)


@login_required
def playbook_list(request):
    """Playbook listesi"""
    playbooks = AnsiblePlaybook.objects.select_related('category').prefetch_related(
        'target_servers', 'target_applications'
    )
    
    # Filtreleme
    category_id = request.GET.get('category')
    if category_id:
        playbooks = playbooks.filter(category_id=category_id)
    
    search = request.GET.get('search')
    if search:
        playbooks = playbooks.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    dangerous = request.GET.get('dangerous')
    if dangerous:
        playbooks = playbooks.filter(is_dangerous=True)
    
    # Sıralama
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'popularity':
        playbooks = playbooks.order_by('-execution_count')
    elif sort_by == 'recent':
        playbooks = playbooks.order_by('-last_execution')
    else:
        playbooks = playbooks.order_by('name')
    
    # Sayfalama
    paginator = Paginator(playbooks, 20)
    page = request.GET.get('page')
    playbooks = paginator.get_page(page)
    
    # Kategoriler
    categories = PlaybookCategory.objects.all()
    
    context = {
        'playbooks': playbooks,
        'categories': categories,
        'current_category': category_id,
        'search_query': search,
        'sort_by': sort_by,
    }
    
    return render(request, 'otomasyon/playbook_list.html', context)


@login_required
def playbook_detail(request, playbook_id):
    """Playbook detayı"""
    playbook = get_object_or_404(AnsiblePlaybook, id=playbook_id)
    
    # Son çalıştırmalar
    recent_executions = playbook.executions.select_related(
        'executor', 'approved_by'
    ).order_by('-created_at')[:10]
    
    # İstatistikler
    stats = {
        'total_executions': playbook.execution_count,
        'success_rate': playbook.success_rate,
        'last_execution': playbook.last_execution,
    }
    
    context = {
        'playbook': playbook,
        'recent_executions': recent_executions,
        'stats': stats,
    }
    
    return render(request, 'otomasyon/playbook_detail.html', context)


@login_required
def execute_playbook(request, playbook_id):
    """Playbook çalıştırma"""
    playbook = get_object_or_404(AnsiblePlaybook, id=playbook_id)
    
    if request.method == 'POST':
        # Çalıştırma kaydı oluştur
        execution = PlaybookExecution.objects.create(
            playbook=playbook,
            executor=request.user,
            execution_id=str(uuid.uuid4())[:8],
            variables=request.POST.get('variables', '{}'),
            target_hosts=request.POST.getlist('target_hosts', []),
            status='pending' if playbook.requires_approval else 'approved'
        )
        
        if playbook.requires_approval:
            messages.success(request, 'Playbook çalıştırma talebi onaya gönderildi.')
        else:
            messages.success(request, 'Playbook çalıştırılmaya başlandı.')
        
        return redirect('otomasyon:execution_detail', execution_id=execution.id)
    
    context = {
        'playbook': playbook,
    }
    
    return render(request, 'otomasyon/execute_playbook.html', context)


@login_required
def execution_history(request):
    """Çalıştırma geçmişi"""
    executions = PlaybookExecution.objects.select_related(
        'playbook', 'executor', 'approved_by'
    )
    
    # Filtreleme
    status = request.GET.get('status')
    if status:
        executions = executions.filter(status=status)
    
    playbook_id = request.GET.get('playbook')
    if playbook_id:
        executions = executions.filter(playbook_id=playbook_id)
    
    executor_id = request.GET.get('executor')
    if executor_id:
        executions = executions.filter(executor_id=executor_id)
    
    # Tarih aralığı
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        executions = executions.filter(created_at__gte=date_from)
    if date_to:
        executions = executions.filter(created_at__lte=date_to)
    
    executions = executions.order_by('-created_at')
    
    # Sayfalama
    paginator = Paginator(executions, 25)
    page = request.GET.get('page')
    executions = paginator.get_page(page)
    
    # Filtre seçenekleri
    playbooks = AnsiblePlaybook.objects.all()
    
    context = {
        'executions': executions,
        'playbooks': playbooks,
        'status_choices': PlaybookExecution._meta.get_field('status').choices,
        'filters': {
            'status': status,
            'playbook': playbook_id,
            'executor': executor_id,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'otomasyon/execution_history.html', context)


@login_required
def execution_detail(request, execution_id):
    """Çalıştırma detayı"""
    execution = get_object_or_404(
        PlaybookExecution.objects.select_related(
            'playbook', 'executor', 'approved_by'
        ),
        id=execution_id
    )
    
    # Loglar
    logs = execution.logs.order_by('created_at')
    
    context = {
        'execution': execution,
        'logs': logs,
    }
    
    return render(request, 'otomasyon/execution_detail.html', context)


@login_required
def schedule_list(request):
    """Programlı görevler listesi"""
    schedules = AutomationSchedule.objects.select_related('playbook')
    
    # Filtreleme
    enabled = request.GET.get('enabled')
    if enabled == '1':
        schedules = schedules.filter(is_enabled=True)
    elif enabled == '0':
        schedules = schedules.filter(is_enabled=False)
    
    schedule_type = request.GET.get('type')
    if schedule_type:
        schedules = schedules.filter(schedule_type=schedule_type)
    
    schedules = schedules.order_by('name')
    
    # Sayfalama
    paginator = Paginator(schedules, 20)
    page = request.GET.get('page')
    schedules = paginator.get_page(page)
    
    context = {
        'schedules': schedules,
        'schedule_types': AutomationSchedule._meta.get_field('schedule_type').choices,
        'filters': {
            'enabled': enabled,
            'type': schedule_type,
        }
    }
    
    return render(request, 'otomasyon/schedule_list.html', context)


@login_required
def schedule_detail(request, schedule_id):
    """Program detayı"""
    schedule = get_object_or_404(AutomationSchedule, id=schedule_id)
    
    # Son çalıştırmalar
    recent_executions = PlaybookExecution.objects.filter(
        playbook=schedule.playbook
    ).select_related('executor').order_by('-created_at')[:10]
    
    context = {
        'schedule': schedule,
        'recent_executions': recent_executions,
    }
    
    return render(request, 'otomasyon/schedule_detail.html', context)


@login_required
def template_list(request):
    """Şablon listesi"""
    templates = AutomationTemplate.objects.select_related('category')
    
    # Filtreleme
    category_id = request.GET.get('category')
    if category_id:
        templates = templates.filter(category_id=category_id)
    
    search = request.GET.get('search')
    if search:
        templates = templates.filter(
            Q(name__icontains=search) |
            Q(description__icontains=search)
        )
    
    # Sıralama
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'popularity':
        templates = templates.order_by('-usage_count')
    else:
        templates = templates.order_by('name')
    
    # Sayfalama
    paginator = Paginator(templates, 20)
    page = request.GET.get('page')
    templates = paginator.get_page(page)
    
    # Kategoriler
    categories = PlaybookCategory.objects.all()
    
    context = {
        'templates': templates,
        'categories': categories,
        'current_category': category_id,
        'search_query': search,
        'sort_by': sort_by,
    }
    
    return render(request, 'otomasyon/template_list.html', context)


@login_required
def template_detail(request, template_id):
    """Şablon detayı"""
    template = get_object_or_404(AutomationTemplate, id=template_id)
    
    context = {
        'template': template,
    }
    
    return render(request, 'otomasyon/template_detail.html', context)


@login_required
def automation_logs(request):
    """Otomasyon logları"""
    logs = AutomationLog.objects.select_related(
        'user', 'playbook_execution__playbook'
    )
    
    # Filtreleme
    level = request.GET.get('level')
    if level:
        logs = logs.filter(level=level)
    
    search = request.GET.get('search')
    if search:
        logs = logs.filter(message__icontains=search)
    
    # Tarih aralığı
    date_from = request.GET.get('date_from')
    date_to = request.GET.get('date_to')
    if date_from:
        logs = logs.filter(created_at__gte=date_from)
    if date_to:
        logs = logs.filter(created_at__lte=date_to)
    
    logs = logs.order_by('-created_at')
    
    # Sayfalama
    paginator = Paginator(logs, 50)
    page = request.GET.get('page')
    logs = paginator.get_page(page)
    
    context = {
        'logs': logs,
        'log_levels': AutomationLog._meta.get_field('level').choices,
        'filters': {
            'level': level,
            'search': search,
            'date_from': date_from,
            'date_to': date_to,
        }
    }
    
    return render(request, 'otomasyon/automation_logs.html', context)


# ===============================
# ANSIBLE TOWER/AWX VIEWS
# ===============================

class AnsibleJobTemplateListView(LoginRequiredMixin, ListView):
    """Ansible Job Template listesi"""
    model = AnsibleJobTemplate
    template_name = 'otomasyon/ansible_job_templates.html'
    context_object_name = 'job_templates'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AnsibleJobTemplate.objects.select_related('category').filter(
            is_enabled=True
        )
        
        # Kullanıcı yetkisi kontrolü
        user = self.request.user
        if not user.is_superuser:
            # Sadece izinli job template'leri göster
            queryset = queryset.filter(
                Q(allowed_users__isnull=True) | Q(allowed_users=user)
            ).distinct()
        
        # Filtreleme
        form = JobTemplateFilterForm(self.request.GET, categories=PlaybookCategory.objects.all())
        if form.is_valid():
            if form.cleaned_data.get('search'):
                search = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(name__icontains=search) | Q(description__icontains=search)
                )
            
            if form.cleaned_data.get('category'):
                queryset = queryset.filter(category=form.cleaned_data['category'])
            
            if form.cleaned_data.get('status') == 'enabled':
                queryset = queryset.filter(is_enabled=True)
            elif form.cleaned_data.get('status') == 'disabled':
                queryset = queryset.filter(is_enabled=False)
            
            if form.cleaned_data.get('survey_enabled') == 'yes':
                queryset = queryset.filter(survey_enabled=True)
            elif form.cleaned_data.get('survey_enabled') == 'no':
                queryset = queryset.filter(survey_enabled=False)
        
        return queryset.order_by('name')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = JobTemplateFilterForm(
            self.request.GET, 
            categories=PlaybookCategory.objects.all()
        )
        
        # İstatistikler
        context['stats'] = {
            'total_templates': AnsibleJobTemplate.objects.filter(is_enabled=True).count(),
            'survey_enabled': AnsibleJobTemplate.objects.filter(survey_enabled=True, is_enabled=True).count(),
            'recent_executions': AnsibleJobExecution.objects.filter(
                created_at__gte=timezone.now() - timezone.timedelta(days=7)
            ).count(),
        }
        
        return context


class AnsibleJobTemplateDetailView(LoginRequiredMixin, DetailView):
    """Ansible Job Template detayı"""
    model = AnsibleJobTemplate
    template_name = 'otomasyon/ansible_job_template_detail.html'
    context_object_name = 'job_template'
    
    def get_object(self):
        obj = super().get_object()
        
        # Yetki kontrolü
        if not obj.can_user_execute(self.request.user):
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Bu Job Template'i çalıştırma yetkiniz yok")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Son çalıştırmalar
        context['recent_executions'] = self.object.executions.select_related(
            'executor'
        ).order_by('-created_at')[:10]
        
        # Survey parametreleri
        context['survey_parameters'] = self.object.survey_parameters.order_by('order')
        
        # Dinamik form
        context['launch_form'] = DynamicJobTemplateForm(self.object)
        
        return context


@login_required
def launch_job_template(request, pk):
    """Job Template'i çalıştır"""
    job_template = get_object_or_404(AnsibleJobTemplate, pk=pk)
    
    # Yetki kontrolü
    if not job_template.can_user_execute(request.user):
        messages.error(request, "Bu Job Template'i çalıştırma yetkiniz yok")
        return redirect('otomasyon:ansible_job_template_detail', pk=pk)
    
    if request.method == 'POST':
        form = DynamicJobTemplateForm(job_template, request.POST)
        if form.is_valid():
            try:
                # Ansible Tower servisini başlat
                tower_service = AnsibleTowerService()
                
                # Survey cevapları ve launch parametrelerini al
                survey_answers = form.get_survey_answers()
                launch_params = form.get_launch_parameters()
                
                # Job'u başlat
                job_execution = tower_service.launch_job_template(
                    job_template=job_template,
                    user=request.user,
                    survey_answers=survey_answers,
                    **launch_params
                )
                
                messages.success(
                    request, 
                    f'Job başarıyla başlatıldı! Execution ID: {job_execution.execution_id}'
                )
                return redirect('otomasyon:ansible_job_execution_detail', pk=job_execution.pk)
                
            except Exception as e:
                messages.error(request, f'Job başlatma hatası: {str(e)}')
        else:
            messages.error(request, 'Form verilerinde hata var. Lütfen kontrol edin.')
    
    return redirect('otomasyon:ansible_job_template_detail', pk=pk)


class AnsibleJobExecutionListView(LoginRequiredMixin, ListView):
    """Ansible Job Execution listesi"""
    model = AnsibleJobExecution
    template_name = 'otomasyon/ansible_job_executions.html'
    context_object_name = 'job_executions'
    paginate_by = 20
    
    def get_queryset(self):
        queryset = AnsibleJobExecution.objects.select_related(
            'job_template', 'executor'
        )
        
        # Kullanıcı sadece kendi çalıştırdıklarını görebilir (admin hariç)
        if not self.request.user.is_superuser:
            queryset = queryset.filter(executor=self.request.user)
        
        # Filtreleme
        form = JobExecutionFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data.get('search'):
                search = form.cleaned_data['search']
                queryset = queryset.filter(
                    Q(job_template__name__icontains=search) | 
                    Q(execution_id__icontains=search)
                )
            
            if form.cleaned_data.get('status'):
                queryset = queryset.filter(status=form.cleaned_data['status'])
            
            if form.cleaned_data.get('executor'):
                executor_search = form.cleaned_data['executor']
                queryset = queryset.filter(
                    Q(executor__username__icontains=executor_search) |
                    Q(executor__first_name__icontains=executor_search) |
                    Q(executor__last_name__icontains=executor_search)
                )
            
            if form.cleaned_data.get('date_from'):
                queryset = queryset.filter(created_at__gte=form.cleaned_data['date_from'])
            
            if form.cleaned_data.get('date_to'):
                queryset = queryset.filter(created_at__lte=form.cleaned_data['date_to'])
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = JobExecutionFilterForm(self.request.GET)
        
        # İstatistikler
        user_filter = {} if self.request.user.is_superuser else {'executor': self.request.user}
        
        context['stats'] = {
            'total_executions': AnsibleJobExecution.objects.filter(**user_filter).count(),
            'running_jobs': AnsibleJobExecution.objects.filter(
                status__in=['pending', 'waiting', 'running'], **user_filter
            ).count(),
            'successful_jobs': AnsibleJobExecution.objects.filter(
                status='successful', **user_filter
            ).count(),
            'failed_jobs': AnsibleJobExecution.objects.filter(
                status__in=['failed', 'error'], **user_filter
            ).count(),
        }
        
        return context


class AnsibleJobExecutionDetailView(LoginRequiredMixin, DetailView):
    """Ansible Job Execution detayı"""
    model = AnsibleJobExecution
    template_name = 'otomasyon/ansible_job_execution_detail.html'
    context_object_name = 'job_execution'
    
    def get_object(self):
        obj = super().get_object()
        
        # Yetki kontrolü - kullanıcı sadece kendi job'larını görebilir
        if not self.request.user.is_superuser and obj.executor != self.request.user:
            from django.core.exceptions import PermissionDenied
            raise PermissionDenied("Bu job execution'ı görme yetkiniz yok")
        
        return obj
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Job logları
        context['job_logs'] = self.object.logs.order_by('timestamp')
        
        # Survey cevapları (güzel formatta)
        survey_answers = []
        if self.object.survey_answers:
            for param in self.object.job_template.survey_parameters.order_by('order'):
                if param.variable in self.object.survey_answers:
                    survey_answers.append({
                        'question': param.question_name,
                        'variable': param.variable,
                        'answer': self.object.survey_answers[param.variable]
                    })
        context['survey_answers'] = survey_answers
        
        return context


@login_required
def cancel_job_execution(request, pk):
    """Job execution'ı iptal et"""
    job_execution = get_object_or_404(AnsibleJobExecution, pk=pk)
    
    # Yetki kontrolü
    if not request.user.is_superuser and job_execution.executor != request.user:
        messages.error(request, "Bu job'u iptal etme yetkiniz yok")
        return redirect('otomasyon:ansible_job_execution_detail', pk=pk)
    
    if not job_execution.is_running:
        messages.warning(request, "Bu job zaten tamamlanmış veya iptal edilmiş")
        return redirect('otomasyon:ansible_job_execution_detail', pk=pk)
    
    try:
        tower_service = AnsibleTowerService()
        if tower_service.cancel_job(job_execution):
            messages.success(request, "Job başarıyla iptal edildi")
        else:
            messages.error(request, "Job iptal edilemedi")
    except Exception as e:
        messages.error(request, f"Job iptal etme hatası: {str(e)}")
    
    return redirect('otomasyon:ansible_job_execution_detail', pk=pk)


@login_required
def refresh_job_status(request, pk):
    """Job durumunu yenile"""
    job_execution = get_object_or_404(AnsibleJobExecution, pk=pk)
    
    # Yetki kontrolü
    if not request.user.is_superuser and job_execution.executor != request.user:
        return JsonResponse({'error': 'Yetkiniz yok'}, status=403)
    
    try:
        tower_service = AnsibleTowerService()
        updated = tower_service.update_job_status(job_execution)
        
        if updated:
            job_execution.refresh_from_db()
            return JsonResponse({
                'status': job_execution.status,
                'status_display': job_execution.get_status_display(),
                'status_class': job_execution.get_status_display_class(),
                'started_at': job_execution.started_at.isoformat() if job_execution.started_at else None,
                'finished_at': job_execution.finished_at.isoformat() if job_execution.finished_at else None,
                'duration': job_execution.duration,
                'is_running': job_execution.is_running,
            })
        else:
            return JsonResponse({'error': 'Durum güncellenemedi'}, status=500)
            
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)
