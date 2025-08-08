from django.db import models
from core.models import BaseModel
from django.contrib.auth.models import User
from django.utils import timezone
from .models import PlaybookCategory
import json


class AnsibleJobTemplate(BaseModel):
    """Ansible Tower/AWX Job Template modeli"""
    name = models.CharField(max_length=255, help_text='Job Template adı')
    description = models.TextField(blank=True, help_text='Açıklama')
    
    # Tower/AWX bilgileri
    tower_id = models.IntegerField(unique=True, help_text='Tower/AWX Job Template ID')
    tower_url = models.URLField(help_text='Tower/AWX URL')
    project_name = models.CharField(max_length=255, blank=True, help_text='Proje adı')
    playbook = models.CharField(max_length=500, blank=True, help_text='Playbook dosyası')
    inventory_name = models.CharField(max_length=255, blank=True, help_text='Inventory adı')
    
    # Job Template ayarları
    job_type = models.CharField(max_length=20, choices=[
        ('run', 'Run'),
        ('check', 'Check'),
    ], default='run')
    
    verbosity = models.IntegerField(default=0, choices=[
        (0, '0 (Normal)'),
        (1, '1 (Verbose)'),
        (2, '2 (More Verbose)'),
        (3, '3 (Debug)'),
        (4, '4 (Connection Debug)'),
        (5, '5 (WinRM Debug)'),
    ])
    
    # Erişim kontrolü
    category = models.ForeignKey(PlaybookCategory, on_delete=models.CASCADE, 
                               related_name='job_templates', null=True, blank=True)
    allowed_users = models.ManyToManyField(User, blank=True, 
                                         help_text='İzinli kullanıcılar')
    requires_approval = models.BooleanField(default=False, 
                                          help_text='Onay gerektirir')
    is_enabled = models.BooleanField(default=True, help_text='Aktif')
    
    # Survey/Parametre ayarları
    survey_enabled = models.BooleanField(default=False, 
                                       help_text='Survey aktif')
    ask_variables_on_launch = models.BooleanField(default=False)
    ask_limit_on_launch = models.BooleanField(default=False)
    ask_tags_on_launch = models.BooleanField(default=False)
    ask_skip_tags_on_launch = models.BooleanField(default=False)
    ask_job_type_on_launch = models.BooleanField(default=False)
    ask_verbosity_on_launch = models.BooleanField(default=False)
    ask_inventory_on_launch = models.BooleanField(default=False)
    ask_credential_on_launch = models.BooleanField(default=False)
    
    # İstatistikler
    usage_count = models.PositiveIntegerField(default=0)
    last_used = models.DateTimeField(null=True, blank=True)
    last_sync = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Ansible Job Template'
        verbose_name_plural = 'Ansible Job Templates'
    
    def __str__(self):
        return self.name
    
    def increment_usage(self):
        """Kullanım sayısını artır"""
        self.usage_count += 1
        self.last_used = timezone.now()
        self.save(update_fields=['usage_count', 'last_used'])
    
    def can_user_execute(self, user):
        """Kullanıcının bu job template'i çalıştırma yetkisi var mı?"""
        if not self.is_enabled:
            return False
        
        if self.allowed_users.exists():
            return self.allowed_users.filter(id=user.id).exists()
        
        return True


class SurveyParameter(BaseModel):
    """Job Template survey parametreleri"""
    job_template = models.ForeignKey(AnsibleJobTemplate, on_delete=models.CASCADE,
                                   related_name='survey_parameters')
    
    # Parametre bilgileri
    variable = models.CharField(max_length=255, help_text='Değişken adı')
    question_name = models.CharField(max_length=255, help_text='Soru metni')
    question_description = models.TextField(blank=True, help_text='Soru açıklaması')
    
    # Parametre türü ve ayarları
    type = models.CharField(max_length=20, choices=[
        ('text', 'Text'),
        ('textarea', 'Textarea'),
        ('password', 'Password'),
        ('integer', 'Integer'),
        ('float', 'Float'),
        ('multiplechoice', 'Multiple Choice'),
        ('multiselect', 'Multi Select'),
    ], default='text')
    
    required = models.BooleanField(default=False)
    default_value = models.TextField(blank=True)
    min_value = models.IntegerField(null=True, blank=True)
    max_value = models.IntegerField(null=True, blank=True)
    
    # Seçenekler (multiple choice için)
    choices = models.JSONField(default=list, blank=True, 
                             help_text='Seçenekler listesi')
    
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'variable']
        unique_together = ['job_template', 'variable']
        verbose_name = 'Survey Parametresi'
        verbose_name_plural = 'Survey Parametreleri'
    
    def __str__(self):
        return f"{self.job_template.name} - {self.variable}"


class AnsibleJobExecution(BaseModel):
    """Ansible Job çalıştırma kayıtları"""
    job_template = models.ForeignKey(AnsibleJobTemplate, on_delete=models.CASCADE,
                                   related_name='executions')
    executor = models.ForeignKey(User, on_delete=models.CASCADE,
                               related_name='ansible_job_executions')
    
    # Tower/AWX job bilgileri
    tower_job_id = models.IntegerField(null=True, blank=True, 
                                     help_text='Tower/AWX Job ID')
    execution_id = models.CharField(max_length=100, unique=True,
                                  help_text='Benzersiz çalıştırma ID')
    
    # Çalıştırma parametreleri
    survey_answers = models.JSONField(default=dict, 
                                    help_text='Survey cevapları')
    extra_vars = models.JSONField(default=dict, 
                                help_text='Ek değişkenler')
    limit = models.CharField(max_length=500, blank=True, 
                           help_text='Host limiti')
    tags = models.CharField(max_length=500, blank=True, 
                          help_text='Çalıştırılacak tag\'ler')
    skip_tags = models.CharField(max_length=500, blank=True, 
                               help_text='Atlanacak tag\'ler')
    job_type = models.CharField(max_length=20, choices=[
        ('run', 'Run'),
        ('check', 'Check'),
    ], default='run')
    verbosity = models.IntegerField(default=0)
    
    # Durum bilgileri
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Beklemede'),
        ('waiting', 'Bekleniyor'),
        ('running', 'Çalışıyor'),
        ('successful', 'Başarılı'),
        ('failed', 'Başarısız'),
        ('error', 'Hata'),
        ('canceled', 'İptal Edildi'),
    ], default='pending')
    
    started_at = models.DateTimeField(null=True, blank=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    elapsed = models.FloatField(null=True, blank=True, 
                              help_text='Süre (saniye)')
    
    # Sonuç bilgileri
    result_stdout = models.TextField(blank=True)
    result_stderr = models.TextField(blank=True)
    artifacts = models.JSONField(default=dict, blank=True)
    
    # Onay süreci
    requires_approval = models.BooleanField(default=False)
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, 
                                  null=True, blank=True,
                                  related_name='approved_ansible_jobs')
    approved_at = models.DateTimeField(null=True, blank=True)
    approval_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Ansible Job Çalıştırması'
        verbose_name_plural = 'Ansible Job Çalıştırmaları'
    
    def __str__(self):
        return f"{self.job_template.name} - {self.execution_id}"
    
    @property
    def duration(self):
        """Çalıştırma süresi"""
        if self.elapsed:
            return self.elapsed
        if self.started_at and self.finished_at:
            delta = self.finished_at - self.started_at
            return delta.total_seconds()
        return None
    
    @property
    def is_running(self):
        """Çalışıyor mu?"""
        return self.status in ['pending', 'waiting', 'running']
    
    @property
    def is_successful(self):
        """Başarılı mı?"""
        return self.status == 'successful'
    
    @property
    def is_failed(self):
        """Başarısız mı?"""
        return self.status in ['failed', 'error', 'canceled']
    
    def get_status_display_class(self):
        """Durum için CSS class"""
        status_classes = {
            'pending': 'warning',
            'waiting': 'info',
            'running': 'primary',
            'successful': 'success',
            'failed': 'danger',
            'error': 'danger',
            'canceled': 'secondary',
        }
        return status_classes.get(self.status, 'secondary')


class AnsibleJobLog(BaseModel):
    """Ansible Job log kayıtları"""
    job_execution = models.ForeignKey(AnsibleJobExecution, on_delete=models.CASCADE,
                                    related_name='logs')
    
    level = models.CharField(max_length=20, choices=[
        ('debug', 'Debug'),
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
        ('critical', 'Critical'),
    ], default='info')
    
    message = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Ek veriler
    host = models.CharField(max_length=255, blank=True)
    task = models.CharField(max_length=500, blank=True)
    play = models.CharField(max_length=500, blank=True)
    extra_data = models.JSONField(default=dict, blank=True)
    
    class Meta:
        ordering = ['timestamp']
        verbose_name = 'Ansible Job Log'
        verbose_name_plural = 'Ansible Job Logs'
    
    def __str__(self):
        return f"{self.job_execution.execution_id} - {self.level} - {self.timestamp}"
