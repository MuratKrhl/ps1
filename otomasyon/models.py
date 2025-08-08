from django.db import models
from core.models import BaseModel
from envanter.models import Server, Application
from django.contrib.auth.models import User
from django.utils import timezone
import json

# Ansible Tower/AWX modelleri
from .ansible_models import (
    AnsibleJobTemplate,
    SurveyParameter, 
    AnsibleJobExecution,
    AnsibleJobLog
)


class PlaybookCategory(BaseModel):
    """Categories for organizing playbooks"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Playbook Kategorisi'
        verbose_name_plural = 'Playbook Kategorileri'
    
    def __str__(self):
        return self.name


class AnsiblePlaybook(BaseModel):
    """Ansible playbooks for automation"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(PlaybookCategory, on_delete=models.CASCADE, related_name='playbooks')
    
    # Playbook file information
    playbook_path = models.CharField(max_length=500, help_text='Playbook dosya yolu')
    inventory_path = models.CharField(max_length=500, blank=True, help_text='Inventory dosya yolu')
    
    # Execution settings
    requires_approval = models.BooleanField(default=True, help_text='Onay gerektirir')
    is_dangerous = models.BooleanField(default=False, help_text='Tehlikeli işlem')
    timeout_minutes = models.PositiveIntegerField(default=30, help_text='Zaman aşımı (dakika)')
    
    # Target settings
    target_servers = models.ManyToManyField(Server, blank=True, help_text='Hedef sunucular')
    target_applications = models.ManyToManyField(Application, blank=True, help_text='Hedef uygulamalar')
    
    # Variables and parameters
    default_variables = models.JSONField(default=dict, help_text='Varsayılan değişkenler')
    required_variables = models.JSONField(default=list, help_text='Zorunlu değişkenler')
    
    # Access control
    allowed_users = models.ManyToManyField(User, blank=True, help_text='İzinli kullanıcılar')
    allowed_groups = models.CharField(max_length=500, blank=True, help_text='İzinli gruplar (virgülle ayır)')
    
    # Statistics
    execution_count = models.PositiveIntegerField(default=0)
    success_count = models.PositiveIntegerField(default=0)
    last_execution = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Ansible Playbook'
        verbose_name_plural = 'Ansible Playbook\'lar'
    
    def __str__(self):
        return self.name
    
    @property
    def success_rate(self):
        if self.execution_count == 0:
            return 0
        return round((self.success_count / self.execution_count) * 100, 1)


class PlaybookExecution(BaseModel):
    """Playbook execution records"""
    playbook = models.ForeignKey(AnsiblePlaybook, on_delete=models.CASCADE, related_name='executions')
    executor = models.ForeignKey(User, on_delete=models.CASCADE, related_name='playbook_executions')
    
    # Execution details
    execution_id = models.CharField(max_length=100, unique=True, help_text='Benzersiz çalıştırma ID')
    variables = models.JSONField(default=dict, help_text='Çalıştırma değişkenleri')
    inventory = models.TextField(blank=True, help_text='Kullanılan inventory')
    
    # Target information
    target_hosts = models.JSONField(default=list, help_text='Hedef hostlar')
    
    # Status and timing
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Beklemede'),
        ('approved', 'Onaylandı'),
        ('running', 'Çalışıyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız'),
        ('cancelled', 'İptal Edildi'),
        ('timeout', 'Zaman Aşımı')
    ], default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    # Results
    return_code = models.IntegerField(null=True, blank=True)
    stdout = models.TextField(blank=True)
    stderr = models.TextField(blank=True)
    
    # Approval workflow
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_executions')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Playbook Çalıştırma'
        verbose_name_plural = 'Playbook Çalıştırmalar'
    
    def __str__(self):
        return f"{self.playbook.name} - {self.execution_id}"
    
    @property
    def duration(self):
        if self.started_at and self.completed_at:
            return self.completed_at - self.started_at
        return None
    
    @property
    def is_successful(self):
        return self.status == 'completed' and self.return_code == 0


class AutomationSchedule(BaseModel):
    """Scheduled automation tasks"""
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    playbook = models.ForeignKey(AnsiblePlaybook, on_delete=models.CASCADE, related_name='schedules')
    
    # Schedule settings
    is_enabled = models.BooleanField(default=True)
    schedule_type = models.CharField(max_length=20, choices=[
        ('once', 'Bir Kez'),
        ('daily', 'Günlük'),
        ('weekly', 'Haftalık'),
        ('monthly', 'Aylık'),
        ('cron', 'Cron İfadesi')
    ])
    
    # Timing
    scheduled_time = models.TimeField(help_text='Çalıştırma saati')
    scheduled_date = models.DateField(null=True, blank=True, help_text='Tek seferlik çalıştırma tarihi')
    cron_expression = models.CharField(max_length=100, blank=True, help_text='Cron ifadesi')
    
    # Execution settings
    variables = models.JSONField(default=dict, help_text='Çalıştırma değişkenleri')
    
    # Status
    last_run = models.DateTimeField(null=True, blank=True)
    next_run = models.DateTimeField(null=True, blank=True)
    run_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Otomasyon Programı'
        verbose_name_plural = 'Otomasyon Programları'
    
    def __str__(self):
        return self.name


class AutomationLog(BaseModel):
    """Automation system logs"""
    level = models.CharField(max_length=20, choices=[
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical')
    ])
    
    message = models.TextField()
    
    # Context
    playbook_execution = models.ForeignKey(PlaybookExecution, on_delete=models.CASCADE, null=True, blank=True, related_name='logs')
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Additional data
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Otomasyon Logu'
        verbose_name_plural = 'Otomasyon Logları'
    
    def __str__(self):
        return f"[{self.level.upper()}] {self.message[:100]}"


class AutomationTemplate(BaseModel):
    """Templates for common automation tasks"""
    name = models.CharField(max_length=255)
    description = models.TextField()
    category = models.ForeignKey(PlaybookCategory, on_delete=models.CASCADE, related_name='templates')
    
    # Template content
    playbook_content = models.TextField(help_text='Playbook YAML içeriği')
    default_variables = models.JSONField(default=dict)
    
    # Usage
    usage_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Otomasyon Şablonu'
        verbose_name_plural = 'Otomasyon Şablonları'
    
    def __str__(self):
        return self.name
