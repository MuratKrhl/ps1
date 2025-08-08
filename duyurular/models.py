from django.db import models
from core.models import BaseModel, Category, Tag
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone
from ckeditor.fields import RichTextField


class AnnouncementCategory(BaseModel):
    """Categories for announcements"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Duyuru Kategorisi'
        verbose_name_plural = 'Duyuru Kategorileri'
    
    def __str__(self):
        return self.name


class Announcement(BaseModel):
    """Portal announcements with rich content and lifecycle management"""
    title = models.CharField(max_length=255, verbose_name='Başlık')
    slug = models.SlugField(unique=True, blank=True)
    content = RichTextField(config_name='announcement', verbose_name='İçerik')
    summary = models.TextField(blank=True, help_text='Kısa özet', verbose_name='Özet')
    
    # Announcement type and related product
    duyuru_tipi = models.CharField(max_length=50, choices=[
        ('duyuru', 'Genel Duyuru'),
        ('planli_calisma', 'Planlı Çalışma'),
        ('bakim', 'Bakım Bildirimi'),
        ('kesinti', 'Kesinti Bildirimi'),
        ('guncelleme', 'Güncelleme'),
        ('bilgilendirme', 'Bilgilendirme')
    ], default='duyuru', verbose_name='Duyuru Tipi')
    
    category = models.ForeignKey(AnnouncementCategory, on_delete=models.CASCADE, related_name='announcements')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Priority and importance
    onem_seviyesi = models.CharField(max_length=20, choices=[
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik')
    ], default='medium', verbose_name='Önem Seviyesi')
    
    # Related product/system
    ilgili_urun = models.CharField(max_length=200, blank=True, 
                                  help_text='İlgili ürün, sistem veya uygulama',
                                  verbose_name='İlgili Ürün/Sistem')
    
    # Work/maintenance date for planned activities
    calisma_tarihi = models.DateTimeField(null=True, blank=True, 
                                         help_text='Planlı çalışma/bakım tarihi',
                                         verbose_name='Çalışma Tarihi')
    
    is_important = models.BooleanField(default=False, help_text='Önemli duyuru')
    sabitle = models.BooleanField(default=False, help_text='Sabitlenmiş duyuru', verbose_name='Sabitle')
    
    # Publishing settings with lifecycle management
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Taslak'),
        ('published', 'Yayında'),
        ('archived', 'Arşiv'),
        ('scheduled', 'Zamanlanmış')
    ], default='draft', verbose_name='Durum')
    
    published_at = models.DateTimeField(null=True, blank=True, verbose_name='Yayın Tarihi')
    yayin_bitis_tarihi = models.DateTimeField(null=True, blank=True, 
                                             help_text='Duyuru otomatik olarak arşivlenecek tarih',
                                             verbose_name='Yayın Bitiş Tarihi')
    
    # Target audience
    target_all_users = models.BooleanField(default=True, help_text='Tüm kullanıcılara göster')
    target_teams = models.CharField(max_length=500, blank=True, help_text='Hedef takımlar (virgülle ayır)')
    target_departments = models.CharField(max_length=500, blank=True, help_text='Hedef departmanlar (virgülle ayır)')
    
    # Notification settings
    send_email = models.BooleanField(default=False, help_text='E-posta bildirimi gönder')
    show_popup = models.BooleanField(default=False, help_text='Popup olarak göster')
    
    # Statistics
    view_count = models.PositiveIntegerField(default=0)
    
    # Approval workflow
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_announcements')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-sabitle', '-onem_seviyesi', '-published_at', '-created_at']
        verbose_name = 'Duyuru'
        verbose_name_plural = 'Duyurular'
        indexes = [
            models.Index(fields=['status', 'published_at']),
            models.Index(fields=['sabitle', 'onem_seviyesi']),
            models.Index(fields=['yayin_bitis_tarihi']),
        ]
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('duyurular:announcement_detail', kwargs={'slug': self.slug})
    
    @property
    def is_active(self):
        """Check if announcement is currently active and published"""
        now = timezone.now()
        if self.status != 'published':
            return False
        if self.published_at and self.published_at > now:
            return False
        if self.yayin_bitis_tarihi and self.yayin_bitis_tarihi <= now:
            return False
        return True
    
    @property
    def is_expired(self):
        """Check if announcement has expired"""
        if not self.yayin_bitis_tarihi:
            return False
        return timezone.now() >= self.yayin_bitis_tarihi
    
    @property
    def priority_badge_class(self):
        """Get CSS class for priority badge"""
        priority_classes = {
            'low': 'badge-light-info',
            'medium': 'badge-light-primary', 
            'high': 'badge-light-warning',
            'critical': 'badge-light-danger'
        }
        return priority_classes.get(self.onem_seviyesi, 'badge-light-secondary')
    
    @property
    def type_badge_class(self):
        """Get CSS class for announcement type badge"""
        type_classes = {
            'duyuru': 'badge-light-info',
            'planli_calisma': 'badge-light-warning',
            'bakim': 'badge-light-secondary',
            'kesinti': 'badge-light-danger',
            'guncelleme': 'badge-light-success',
            'bilgilendirme': 'badge-light-primary'
        }
        return type_classes.get(self.duyuru_tipi, 'badge-light-secondary')
    
    def save(self, *args, **kwargs):
        # Auto-generate slug from title if not provided
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.title)
        
        # Set published_at when status changes to published
        if self.status == 'published' and not self.published_at:
            self.published_at = timezone.now()
        
        super().save(*args, **kwargs)


class AnnouncementView(models.Model):
    """Track announcement views by users"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='announcement_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        unique_together = ['announcement', 'user']
        verbose_name = 'Duyuru Görüntüleme'
        verbose_name_plural = 'Duyuru Görüntülemeleri'


class AnnouncementComment(BaseModel):
    """Comments on announcements"""
    announcement = models.ForeignKey(Announcement, on_delete=models.CASCADE, related_name='comments')
    content = models.TextField()
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='replies')
    
    # Status
    is_approved = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['created_at']
        verbose_name = 'Duyuru Yorumu'
        verbose_name_plural = 'Duyuru Yorumları'
    
    def __str__(self):
        return f"{self.created_by.username} - {self.announcement.title[:50]}..."


class MaintenanceNotice(BaseModel):
    """System maintenance notices"""
    title = models.CharField(max_length=255)
    description = models.TextField()
    
    # Maintenance schedule
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    
    # Affected systems
    affected_systems = models.TextField(help_text='Etkilenecek sistemler')
    impact_level = models.CharField(max_length=20, choices=[
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik')
    ], default='medium')
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('scheduled', 'Planlandı'),
        ('in_progress', 'Devam Ediyor'),
        ('completed', 'Tamamlandı'),
        ('cancelled', 'İptal Edildi'),
        ('delayed', 'Ertelendi')
    ], default='scheduled')
    
    # Notification settings
    notify_users = models.BooleanField(default=True)
    notification_sent = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['-start_time']
        verbose_name = 'Bakım Bildirimi'
        verbose_name_plural = 'Bakım Bildirimleri'
    
    def __str__(self):
        return f"{self.title} ({self.start_time.strftime('%Y-%m-%d %H:%M')})"
    
    @property
    def is_current(self):
        """Check if maintenance is currently in progress"""
        now = timezone.now()
        return self.start_time <= now <= self.end_time and self.status == 'in_progress'
    
    @property
    def is_upcoming(self):
        """Check if maintenance is upcoming"""
        now = timezone.now()
        return self.start_time > now and self.status == 'scheduled'


class SystemStatus(BaseModel):
    """System status updates"""
    system_name = models.CharField(max_length=100)
    status = models.CharField(max_length=20, choices=[
        ('operational', 'Çalışıyor'),
        ('degraded', 'Yavaş'),
        ('partial_outage', 'Kısmi Kesinti'),
        ('major_outage', 'Büyük Kesinti'),
        ('maintenance', 'Bakımda')
    ])
    
    message = models.TextField(blank=True)
    
    # Timing
    started_at = models.DateTimeField(default=timezone.now)
    resolved_at = models.DateTimeField(null=True, blank=True)
    
    # Impact
    affected_users = models.PositiveIntegerField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = 'Sistem Durumu'
        verbose_name_plural = 'Sistem Durumları'
    
    def __str__(self):
        return f"{self.system_name} - {self.get_status_display()}"
    
    @property
    def is_resolved(self):
        """Check if issue is resolved"""
        return self.resolved_at is not None
    
    @property
    def duration(self):
        """Get issue duration"""
        end_time = self.resolved_at or timezone.now()
        return end_time - self.started_at
