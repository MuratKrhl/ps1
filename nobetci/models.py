from django.db import models
from core.models import BaseModel
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
from django.urls import reverse


class Team(BaseModel):
    """Teams for duty assignments"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Takım'
        verbose_name_plural = 'Takımlar'
    
    def __str__(self):
        return self.name


class DutyType(BaseModel):
    """Types of duties: On-call, Weekend, Holiday, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#28a745')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    
    # Duration settings
    default_duration_hours = models.PositiveIntegerField(default=24, help_text='Varsayılan nöbet süresi (saat)')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Nöbet Tipi'
        verbose_name_plural = 'Nöbet Tipleri'
    
    def __str__(self):
        return self.name


class DutySchedule(BaseModel):
    """Duty schedule assignments"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='duty_schedules')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='duty_schedules')
    duty_type = models.ForeignKey(DutyType, on_delete=models.CASCADE, related_name='duty_schedules')
    
    # Schedule details
    start_date = models.DateField()
    start_time = models.TimeField(default='09:00')
    end_date = models.DateField()
    end_time = models.TimeField(default='09:00')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Planlandı'),
        ('active', 'Aktif'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
        ('replaced', 'Değiştirildi')
    ], default='scheduled')
    
    # Contact information
    primary_phone = models.CharField(max_length=20, blank=True)
    secondary_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    
    # Replacement information
    replacement_user = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True, 
        related_name='replacement_duties', help_text='Yerine geçen kişi'
    )
    replacement_reason = models.TextField(blank=True, help_text='Değişiklik nedeni')
    
    # Notes
    notes = models.TextField(blank=True, help_text='Nöbet notları')
    
    class Meta:
        ordering = ['start_date', 'start_time']
        verbose_name = 'Nöbet Programı'
        verbose_name_plural = 'Nöbet Programları'
    
    def __str__(self):
        return f"{self.user.get_full_name() or self.user.username} - {self.duty_type.name} ({self.start_date})"
    
    @property
    def is_current(self):
        """Check if duty is currently active"""
        now = timezone.now()
        start_datetime = timezone.make_aware(
            datetime.combine(self.start_date, self.start_time)
        )
        end_datetime = timezone.make_aware(
            datetime.combine(self.end_date, self.end_time)
        )
        return start_datetime <= now <= end_datetime and self.status == 'active'
    
    @property
    def is_upcoming(self):
        """Check if duty is upcoming (within next 7 days)"""
        now = timezone.now().date()
        return self.start_date > now and self.start_date <= now + timedelta(days=7)
    
    @property
    def duration_hours(self):
        """Calculate duty duration in hours"""
        start_datetime = datetime.combine(self.start_date, self.start_time)
        end_datetime = datetime.combine(self.end_date, self.end_time)
        duration = end_datetime - start_datetime
        return duration.total_seconds() / 3600


class DutyLog(BaseModel):
    """Log entries for duty periods"""
    duty_schedule = models.ForeignKey(DutySchedule, on_delete=models.CASCADE, related_name='logs')
    
    # Log details
    log_type = models.CharField(max_length=20, choices=[
        ('start', 'Nöbet Başlangıcı'),
        ('end', 'Nöbet Bitişi'),
        ('incident', 'Olay'),
        ('handover', 'Devir'),
        ('note', 'Not')
    ])
    
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Timing
    logged_at = models.DateTimeField(default=timezone.now)
    
    # Severity for incidents
    severity = models.CharField(max_length=20, choices=[
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik')
    ], blank=True)
    
    # Resolution status for incidents
    is_resolved = models.BooleanField(default=False)
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-logged_at']
        verbose_name = 'Nöbet Logu'
        verbose_name_plural = 'Nöbet Logları'
    
    def __str__(self):
        return f"{self.duty_schedule.user.username} - {self.title} ({self.logged_at.strftime('%Y-%m-%d %H:%M')})"


class EmergencyContact(BaseModel):
    """Emergency contacts for duty periods"""
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=100, help_text='Pozisyon/Görev')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='emergency_contacts')
    
    # Contact information
    primary_phone = models.CharField(max_length=20)
    secondary_phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField()
    
    # Availability
    is_24x7 = models.BooleanField(default=False, help_text='7/24 ulaşılabilir')
    available_hours = models.CharField(
        max_length=100, blank=True, 
        help_text='Ulaşılabilir saatler (örn: 09:00-18:00)'
    )
    
    # Priority
    priority = models.PositiveIntegerField(default=1, help_text='Arama önceliği (1=en yüksek)')
    
    class Meta:
        ordering = ['team', 'priority', 'name']
        verbose_name = 'Acil Durum Kişisi'
        verbose_name_plural = 'Acil Durum Kişileri'
    
    def __str__(self):
        return f"{self.name} ({self.role}) - {self.team.name}"


class DutySwapRequest(BaseModel):
    """Requests for duty swaps between users"""
    requester = models.ForeignKey(User, on_delete=models.CASCADE, related_name='swap_requests')
    original_duty = models.ForeignKey(DutySchedule, on_delete=models.CASCADE, related_name='swap_requests')
    
    # Swap details
    target_user = models.ForeignKey(
        User, on_delete=models.CASCADE, related_name='received_swap_requests',
        null=True, blank=True, help_text='Değişim yapılacak kişi'
    )
    target_duty = models.ForeignKey(
        DutySchedule, on_delete=models.CASCADE, related_name='target_swap_requests',
        null=True, blank=True, help_text='Değişim yapılacak nöbet'
    )
    
    reason = models.TextField(help_text='Değişim nedeni')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('pending', 'Beklemede'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
        ('cancelled', 'İptal Edildi')
    ], default='pending')
    
    # Approval
    approved_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True,
        related_name='approved_swaps', help_text='Onaylayan kişi'
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    rejection_reason = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Nöbet Değişim Talebi'
        verbose_name_plural = 'Nöbet Değişim Talepleri'
    
    def __str__(self):
        return f"{self.requester.get_full_name()} - {self.original_duty}"


class Nobetci(BaseModel):
    """Simple daily duty schedule from external source"""
    tarih = models.DateField(unique=True, help_text='Nöbet tarihi')
    ad_soyad = models.CharField(max_length=100, help_text='Nöbetçinin adı soyadı')
    telefon = models.CharField(max_length=20, blank=True, help_text='Telefon numarası')
    email = models.EmailField(blank=True, help_text='E-posta adresi')
    
    # Ek bilgiler
    notlar = models.TextField(blank=True, help_text='Ek notlar')
    kaynak = models.CharField(max_length=50, default='external', help_text='Veri kaynağı')
    senkron_tarihi = models.DateTimeField(auto_now=True, help_text='Son senkronizasyon tarihi')
    
    class Meta:
        ordering = ['-tarih']
        verbose_name = 'Nöbetçi'
        verbose_name_plural = 'Nöbetçiler'
        indexes = [
            models.Index(fields=['tarih']),
            models.Index(fields=['-tarih']),
        ]
    
    def __str__(self):
        return f"{self.tarih.strftime('%d.%m.%Y')} - {self.ad_soyad}"
    
    def get_absolute_url(self):
        return reverse('nobetci:detail', kwargs={'pk': self.pk})
    
    @property
    def is_today(self):
        """Bugünkü nöbetçi mi?"""
        return self.tarih == timezone.now().date()
    
    @property
    def is_past(self):
        """Geçmiş nöbet mi?"""
        return self.tarih < timezone.now().date()
    
    @property
    def is_future(self):
        """Gelecek nöbet mi?"""
        return self.tarih > timezone.now().date()
    
    @property
    def days_until(self):
        """Nöbete kaç gün kaldı?"""
        if self.is_past:
            return None
        return (self.tarih - timezone.now().date()).days
    
    @classmethod
    def get_current_duty(cls):
        """Bugünkü nöbetçiyi getir"""
        try:
            return cls.objects.get(tarih=timezone.now().date())
        except cls.DoesNotExist:
            return None
    
    @classmethod
    def get_next_duty(cls):
        """Sonraki nöbetçiyi getir"""
        try:
            return cls.objects.filter(
                tarih__gt=timezone.now().date()
            ).order_by('tarih').first()
        except cls.DoesNotExist:
            return None
