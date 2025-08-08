from django.urls import path
from . import views, api_views

app_name = 'otomasyon'

urlpatterns = [
    # Dashboard
    path('', views.otomasyon_dashboard, name='dashboard'),
    
    # Playbooks
    path('playbooks/', views.playbook_list, name='playbook_list'),
    path('playbook/<int:playbook_id>/', views.playbook_detail, name='playbook_detail'),
    path('playbook/<int:playbook_id>/calistir/', views.execute_playbook, name='execute_playbook'),
    
    # Executions
    path('gecmis/', views.execution_history, name='execution_history'),
    path('calistirma/<int:execution_id>/', views.execution_detail, name='execution_detail'),
    
    # Schedules
    path('programlar/', views.schedule_list, name='schedule_list'),
    path('program/<int:schedule_id>/', views.schedule_detail, name='schedule_detail'),
    
    # Templates
    path('sablonlar/', views.template_list, name='template_list'),
    path('sablon/<int:template_id>/', views.template_detail, name='template_detail'),
    
    # Logs
    path('loglar/', views.automation_logs, name='automation_logs'),
    
    # Ansible Tower/AWX
    path('ansible/', views.AnsibleJobTemplateListView.as_view(), name='ansible_job_templates'),
    path('ansible/template/<int:pk>/', views.AnsibleJobTemplateDetailView.as_view(), name='ansible_job_template_detail'),
    path('ansible/template/<int:pk>/launch/', views.launch_job_template, name='launch_job_template'),
    path('ansible/executions/', views.AnsibleJobExecutionListView.as_view(), name='ansible_job_executions'),
    path('ansible/execution/<int:pk>/', views.AnsibleJobExecutionDetailView.as_view(), name='ansible_job_execution_detail'),
    path('ansible/execution/<int:pk>/cancel/', views.cancel_job_execution, name='cancel_job_execution'),
    path('ansible/execution/<int:pk>/refresh/', views.refresh_job_status, name='refresh_job_status'),
    
    # API Endpoints
    path('api/playbook/<int:playbook_id>/execute/', api_views.api_execute_playbook, name='api_execute_playbook'),
    path('api/execution/<int:execution_id>/status/', api_views.api_execution_status, name='api_execution_status'),
    path('api/execution/<int:execution_id>/approve/', api_views.api_approve_execution, name='api_approve_execution'),
    path('api/execution/<int:execution_id>/cancel/', api_views.api_cancel_execution, name='api_cancel_execution'),
    path('api/execution/<int:execution_id>/logs/', api_views.api_execution_logs, name='api_execution_logs'),
    path('api/playbook/<int:playbook_id>/info/', api_views.api_playbook_info, name='api_playbook_info'),
    path('api/schedules/', api_views.api_schedule_list, name='api_schedule_list'),
    path('api/validate-playbook/', api_views.api_validate_playbook, name='api_validate_playbook'),
]
