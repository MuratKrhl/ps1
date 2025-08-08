from django.db import models
from core.models import BaseModel
from envanter.models import Server, Application
from django.contrib.auth.models import User
from django.utils import timezone


class MetricType(BaseModel):
    """Types of performance metrics"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    unit = models.CharField(max_length=20, help_text='Ölçü birimi (%, MB, ms, etc.)')
    category = models.CharField(max_length=50, choices=[
        ('cpu', 'CPU'),
        ('memory', 'Bellek'),
        ('disk', 'Disk'),
        ('network', 'Ağ'),
        ('application', 'Uygulama'),
        ('database', 'Veritabanı'),
        ('custom', 'Özel')
    ])
    
    # Thresholds
    warning_threshold = models.FloatField(null=True, blank=True)
    critical_threshold = models.FloatField(null=True, blank=True)
    
    class Meta:
        ordering = ['category', 'name']
        verbose_name = 'Metrik Tipi'
        verbose_name_plural = 'Metrik Tipleri'
    
    def __str__(self):
        return f"{self.name} ({self.unit})"


class ServerMetric(BaseModel):
    """Server performance metrics"""
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    
    # Metric data
    value = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Status based on thresholds
    status = models.CharField(max_length=20, choices=[
        ('ok', 'Normal'),
        ('warning', 'Uyarı'),
        ('critical', 'Kritik')
    ], default='ok')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Sunucu Metriği'
        verbose_name_plural = 'Sunucu Metrikleri'
        indexes = [
            models.Index(fields=['server', 'metric_type', '-timestamp']),
        ]
    
    def __str__(self):
        return f"{self.server.hostname} - {self.metric_type.name}: {self.value}"


class ApplicationMetric(BaseModel):
    """Application performance metrics"""
    application = models.ForeignKey(Application, on_delete=models.CASCADE, related_name='metrics')
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    
    # Metric data
    value = models.FloatField()
    timestamp = models.DateTimeField(default=timezone.now)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('ok', 'Normal'),
        ('warning', 'Uyarı'),
        ('critical', 'Kritik')
    ], default='ok')
    
    class Meta:
        ordering = ['-timestamp']
        verbose_name = 'Uygulama Metriği'
        verbose_name_plural = 'Uygulama Metrikleri'
        indexes = [
            models.Index(fields=['application', 'metric_type', '-timestamp']),
        ]


class PerformanceReport(BaseModel):
    """Performance reports"""
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    
    # Report scope
    servers = models.ManyToManyField(Server, blank=True)
    applications = models.ManyToManyField(Application, blank=True)
    
    # Time range
    start_date = models.DateTimeField()
    end_date = models.DateTimeField()
    
    # Report data
    report_data = models.JSONField(default=dict, help_text='Rapor verileri JSON formatında')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('generating', 'Oluşturuluyor'),
        ('completed', 'Tamamlandı'),
        ('failed', 'Başarısız')
    ], default='generating')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Performans Raporu'
        verbose_name_plural = 'Performans Raporları'


class Alert(BaseModel):
    """Performance alerts"""
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Alert source
    server = models.ForeignKey(Server, on_delete=models.CASCADE, null=True, blank=True)
    application = models.ForeignKey(Application, on_delete=models.CASCADE, null=True, blank=True)
    metric_type = models.ForeignKey(MetricType, on_delete=models.CASCADE)
    
    # Alert details
    severity = models.CharField(max_length=20, choices=[
        ('info', 'Bilgi'),
        ('warning', 'Uyarı'),
        ('critical', 'Kritik')
    ])
    
    threshold_value = models.FloatField()
    actual_value = models.FloatField()
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('open', 'Açık'),
        ('acknowledged', 'Onaylandı'),
        ('resolved', 'Çözüldü'),
        ('closed', 'Kapatıldı')
    ], default='open')
    
    # Resolution
    acknowledged_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='acknowledged_alerts')
    acknowledged_at = models.DateTimeField(null=True, blank=True)
    resolved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='resolved_alerts')
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Performans Uyarısı'
        verbose_name_plural = 'Performans Uyarıları'
