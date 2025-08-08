from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404
from django.utils import timezone
from .models import AnsiblePlaybook, PlaybookExecution, AutomationSchedule
from .services import PlaybookValidator
from .tasks import execute_ansible_playbook, send_execution_notification
import json
import uuid


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_execute_playbook(request, playbook_id):
    """API: Playbook çalıştır"""
    try:
        playbook = get_object_or_404(AnsiblePlaybook, id=playbook_id)
        
        # İzin kontrolü
        if playbook.allowed_users.exists() and request.user not in playbook.allowed_users.all():
            return JsonResponse({
                'success': False,
                'error': 'Bu playbook\'u çalıştırma izniniz yok'
            }, status=403)
        
        # POST verilerini al
        data = json.loads(request.body) if request.body else {}
        variables = data.get('variables', {})
        target_hosts = data.get('target_hosts', [])
        
        # Değişkenleri doğrula
        is_valid, message = PlaybookValidator.validate_variables(
            variables, playbook.required_variables
        )
        if not is_valid:
            return JsonResponse({
                'success': False,
                'error': message
            }, status=400)
        
        # Çalıştırma kaydı oluştur
        execution = PlaybookExecution.objects.create(
            playbook=playbook,
            executor=request.user,
            execution_id=str(uuid.uuid4())[:8],
            variables=variables,
            target_hosts=target_hosts,
            status='pending' if playbook.requires_approval else 'approved'
        )
        
        # Onay gerektirmiyorsa hemen çalıştır
        if not playbook.requires_approval:
            execute_ansible_playbook.delay(execution.id)
            message = 'Playbook çalıştırılmaya başlandı'
        else:
            message = 'Playbook çalıştırma talebi onaya gönderildi'
        
        return JsonResponse({
            'success': True,
            'message': message,
            'execution_id': execution.id,
            'execution_uuid': execution.execution_id,
            'status': execution.status
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_execution_status(request, execution_id):
    """API: Çalıştırma durumu sorgula"""
    try:
        execution = get_object_or_404(
            PlaybookExecution.objects.select_related('playbook'),
            id=execution_id
        )
        
        # Sadece kendi çalıştırmalarını veya admin görebilir
        if execution.executor != request.user and not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Bu çalıştırmayı görme izniniz yok'
            }, status=403)
        
        return JsonResponse({
            'success': True,
            'execution': {
                'id': execution.id,
                'execution_id': execution.execution_id,
                'playbook_name': execution.playbook.name,
                'status': execution.status,
                'started_at': execution.started_at.isoformat() if execution.started_at else None,
                'completed_at': execution.completed_at.isoformat() if execution.completed_at else None,
                'duration': str(execution.duration) if execution.duration else None,
                'return_code': execution.return_code,
                'is_successful': execution.is_successful
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_approve_execution(request, execution_id):
    """API: Çalıştırma onaylama"""
    try:
        execution = get_object_or_404(PlaybookExecution, id=execution_id)
        
        # Sadece admin onaylayabilir
        if not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Onaylama izniniz yok'
            }, status=403)
        
        if execution.status != 'pending':
            return JsonResponse({
                'success': False,
                'error': 'Bu çalıştırma zaten işleme alınmış'
            }, status=400)
        
        # POST verilerini al
        data = json.loads(request.body) if request.body else {}
        approval_notes = data.get('notes', '')
        
        # Onaylama işlemi
        execution.status = 'approved'
        execution.approved_by = request.user
        execution.approved_at = timezone.now()
        execution.approval_notes = approval_notes
        execution.save()
        
        # Playbook'ı çalıştır
        execute_ansible_playbook.delay(execution.id)
        
        return JsonResponse({
            'success': True,
            'message': 'Çalıştırma onaylandı ve başlatıldı',
            'execution_id': execution.id
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_cancel_execution(request, execution_id):
    """API: Çalıştırma iptal etme"""
    try:
        execution = get_object_or_404(PlaybookExecution, id=execution_id)
        
        # Sadece çalıştıran kişi veya admin iptal edebilir
        if execution.executor != request.user and not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Bu çalıştırmayı iptal etme izniniz yok'
            }, status=403)
        
        if execution.status not in ['pending', 'approved']:
            return JsonResponse({
                'success': False,
                'error': 'Bu çalıştırma iptal edilemez'
            }, status=400)
        
        # İptal işlemi
        execution.status = 'cancelled'
        execution.completed_at = timezone.now()
        execution.save()
        
        return JsonResponse({
            'success': True,
            'message': 'Çalıştırma iptal edildi'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_playbook_info(request, playbook_id):
    """API: Playbook bilgilerini getir"""
    try:
        playbook = get_object_or_404(AnsiblePlaybook, id=playbook_id)
        
        return JsonResponse({
            'success': True,
            'playbook': {
                'id': playbook.id,
                'name': playbook.name,
                'description': playbook.description,
                'category': playbook.category.name,
                'requires_approval': playbook.requires_approval,
                'is_dangerous': playbook.is_dangerous,
                'timeout_minutes': playbook.timeout_minutes,
                'default_variables': playbook.default_variables,
                'required_variables': playbook.required_variables,
                'target_servers': [
                    {'id': server.id, 'name': server.name, 'hostname': server.hostname}
                    for server in playbook.target_servers.all()
                ],
                'execution_count': playbook.execution_count,
                'success_rate': playbook.success_rate,
                'last_execution': playbook.last_execution.isoformat() if playbook.last_execution else None
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_schedule_list(request):
    """API: Programlı görevler listesi"""
    try:
        schedules = AutomationSchedule.objects.select_related('playbook').filter(
            is_enabled=True
        )
        
        schedule_list = []
        for schedule in schedules:
            schedule_list.append({
                'id': schedule.id,
                'name': schedule.name,
                'playbook_name': schedule.playbook.name,
                'schedule_type': schedule.schedule_type,
                'next_run': schedule.next_run.isoformat() if schedule.next_run else None,
                'last_run': schedule.last_run.isoformat() if schedule.last_run else None,
                'run_count': schedule.run_count
            })
        
        return JsonResponse({
            'success': True,
            'schedules': schedule_list
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@csrf_exempt
@require_http_methods(["POST"])
def api_validate_playbook(request):
    """API: Playbook dosyasını doğrula"""
    try:
        data = json.loads(request.body)
        playbook_path = data.get('playbook_path')
        
        if not playbook_path:
            return JsonResponse({
                'success': False,
                'error': 'Playbook yolu gerekli'
            }, status=400)
        
        is_valid, message = PlaybookValidator.validate_playbook_file(playbook_path)
        
        return JsonResponse({
            'success': True,
            'is_valid': is_valid,
            'message': message
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@login_required
@require_http_methods(["GET"])
def api_execution_logs(request, execution_id):
    """API: Çalıştırma loglarını getir"""
    try:
        execution = get_object_or_404(PlaybookExecution, id=execution_id)
        
        # İzin kontrolü
        if execution.executor != request.user and not request.user.is_staff:
            return JsonResponse({
                'success': False,
                'error': 'Bu logları görme izniniz yok'
            }, status=403)
        
        logs = execution.logs.order_by('created_at').values(
            'level', 'message', 'created_at'
        )
        
        return JsonResponse({
            'success': True,
            'logs': list(logs),
            'stdout': execution.stdout,
            'stderr': execution.stderr
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)
