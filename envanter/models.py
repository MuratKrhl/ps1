from django.db import models
from core.models import BaseModel, Category, Tag
from django.contrib.auth.models import User


class Environment(BaseModel):
    """Environment types: Production, Staging, Development, etc."""
    name = models.CharField(max_length=50, unique=True)
    short_name = models.CharField(max_length=10)
    color = models.CharField(max_length=7, default='#007bff')
    description = models.TextField(blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Ortam'
        verbose_name_plural = 'Ortamlar'
    
    def __str__(self):
        return self.name


class OperatingSystem(BaseModel):
    """Operating System information"""
    name = models.CharField(max_length=100)
    version = models.CharField(max_length=50, blank=True)
    family = models.CharField(max_length=50, choices=[
        ('linux', 'Linux'),
        ('windows', 'Windows'),
        ('unix', 'Unix'),
        ('other', 'Diğer')
    ])
    
    class Meta:
        ordering = ['family', 'name']
        verbose_name = 'İşletim Sistemi'
        verbose_name_plural = 'İşletim Sistemleri'
    
    def __str__(self):
        return f"{self.name} {self.version}" if self.version else self.name


class Server(BaseModel):
    """Server inventory model"""
    hostname = models.CharField(max_length=255, unique=True)
    ip_address = models.GenericIPAddressField()
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='servers')
    operating_system = models.ForeignKey(OperatingSystem, on_delete=models.SET_NULL, null=True, blank=True)
    
    # Hardware specifications
    cpu_cores = models.PositiveIntegerField(null=True, blank=True)
    ram_gb = models.PositiveIntegerField(null=True, blank=True)
    disk_gb = models.PositiveIntegerField(null=True, blank=True)
    
    # Server details
    location = models.CharField(max_length=100, blank=True, help_text='Fiziksel konum veya veri merkezi')
    rack_position = models.CharField(max_length=50, blank=True)
    serial_number = models.CharField(max_length=100, blank=True)
    manufacturer = models.CharField(max_length=100, blank=True)
    model = models.CharField(max_length=100, blank=True)
    
    # Status and monitoring
    status = models.CharField(max_length=20, choices=[
        ('active', 'Aktif'),
        ('inactive', 'Pasif'),
        ('maintenance', 'Bakımda'),
        ('decommissioned', 'Devre Dışı')
    ], default='active')
    
    last_ping = models.DateTimeField(null=True, blank=True)
    monitoring_enabled = models.BooleanField(default=True)
    backup_enabled = models.BooleanField(default=True)
    
    # Ownership and responsibility
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_servers')
    responsible_team = models.CharField(max_length=100, blank=True)
    
    # Additional information
    purpose = models.TextField(blank=True, help_text='Sunucunun kullanım amacı')
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    class Meta:
        ordering = ['hostname']
        verbose_name = 'Sunucu'
        verbose_name_plural = 'Sunucular'
    
    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"
    
    @property
    def is_online(self):
        """Check if server is considered online based on last ping"""
        if not self.last_ping:
            return False
        from django.utils import timezone
        from datetime import timedelta
        return timezone.now() - self.last_ping < timedelta(minutes=10)


class ApplicationType(BaseModel):
    """Application types: Web, Database, API, etc."""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Uygulama Tipi'
        verbose_name_plural = 'Uygulama Tipleri'
    
    def __str__(self):
        return self.name


class Technology(BaseModel):
    """Technology stack: Java, Python, .NET, etc."""
    name = models.CharField(max_length=100, unique=True)
    version = models.CharField(max_length=50, blank=True)
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Teknoloji'
        verbose_name_plural = 'Teknolojiler'
    
    def __str__(self):
        return f"{self.name} {self.version}" if self.version else self.name


class Application(BaseModel):
    """Application inventory model"""
    name = models.CharField(max_length=255)
    code_name = models.CharField(max_length=100, unique=True, help_text='Uygulama kodu/kısaltması')
    description = models.TextField(blank=True)
    
    # Application details
    application_type = models.ForeignKey(ApplicationType, on_delete=models.SET_NULL, null=True, blank=True)
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='applications')
    servers = models.ManyToManyField(Server, related_name='applications', blank=True)
    technologies = models.ManyToManyField(Technology, blank=True)
    
    # URLs and access
    url = models.URLField(blank=True, help_text='Uygulama URL\'si')
    admin_url = models.URLField(blank=True, help_text='Admin panel URL\'si')
    documentation_url = models.URLField(blank=True, help_text='Dokümantasyon URL\'si')
    repository_url = models.URLField(blank=True, help_text='Kod deposu URL\'si')
    
    # Status and monitoring
    status = models.CharField(max_length=20, choices=[
        ('active', 'Aktif'),
        ('inactive', 'Pasif'),
        ('development', 'Geliştirme'),
        ('testing', 'Test'),
        ('maintenance', 'Bakımda'),
        ('error', 'Hatalı'),
        ('deprecated', 'Kullanımdan Kalktı')
    ], default='active')
    
    # Port and connectivity
    port = models.PositiveIntegerField(null=True, blank=True, help_text='Uygulama portu')
    ssl_enabled = models.BooleanField(default=False, help_text='HTTPS/SSL aktif mi?')
    
    # Version and deployment
    version = models.CharField(max_length=50, blank=True)
    last_deployment = models.DateTimeField(null=True, blank=True)
    monitoring_enabled = models.BooleanField(default=True)
    
    # Sync and health check
    last_health_check = models.DateTimeField(null=True, blank=True, help_text='Son sağlık kontrolü')
    health_check_status = models.CharField(max_length=20, choices=[
        ('healthy', 'Sağlıklı'),
        ('unhealthy', 'Sağlıksız'),
        ('unknown', 'Bilinmiyor')
    ], default='unknown')
    external_id = models.CharField(max_length=100, blank=True, help_text='Harici sistem ID\'si')
    sync_enabled = models.BooleanField(default=True, help_text='Otomatik senkronizasyon aktif mi?')
    
    # Ownership and responsibility
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_applications')
    development_team = models.CharField(max_length=100, blank=True)
    business_owner = models.CharField(max_length=100, blank=True)
    
    # Business information
    business_criticality = models.CharField(max_length=20, choices=[
        ('critical', 'Kritik'),
        ('high', 'Yüksek'),
        ('medium', 'Orta'),
        ('low', 'Düşük')
    ], default='medium')
    
    # Additional information
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Uygulama'
        verbose_name_plural = 'Uygulamalar'
    
    def __str__(self):
        return f"{self.name} ({self.code_name})"
    
    def get_status_badge_class(self):
        """Status için Bootstrap badge class döndürür"""
        status_classes = {
            'active': 'bg-success',
            'inactive': 'bg-secondary', 
            'development': 'bg-info',
            'testing': 'bg-warning',
            'maintenance': 'bg-warning',
            'error': 'bg-danger',
            'deprecated': 'bg-dark'
        }
        return status_classes.get(self.status, 'bg-secondary')
    
    def get_health_status_badge_class(self):
        """Health status için Bootstrap badge class döndürür"""
        health_classes = {
            'healthy': 'bg-success',
            'unhealthy': 'bg-danger',
            'unknown': 'bg-secondary'
        }
        return health_classes.get(self.health_check_status, 'bg-secondary')
    
    def get_primary_server(self):
        """Birincil sunucuyu döndürür"""
        return self.servers.first()
    
    def get_full_url(self):
        """SSL durumuna göre tam URL döndürür"""
        if not self.url:
            return None
        if self.ssl_enabled and not self.url.startswith('https://'):
            return self.url.replace('http://', 'https://')
        return self.url
    
    def is_critical(self):
        """Kritik uygulama mı kontrol eder"""
        return self.business_criticality == 'critical'
    
    def needs_health_check(self):
        """Sağlık kontrolü gerekli mi kontrol eder"""
        if not self.sync_enabled or not self.port:
            return False
        if not self.last_health_check:
            return True
        from django.utils import timezone
        # Son 5 dakikadan eski ise kontrol gerekli
        return (timezone.now() - self.last_health_check).total_seconds() > 300


class Database(BaseModel):
    """Database inventory model"""
    name = models.CharField(max_length=255)
    database_type = models.CharField(max_length=50, choices=[
        ('postgresql', 'PostgreSQL'),
        ('mysql', 'MySQL'),
        ('oracle', 'Oracle'),
        ('mssql', 'MS SQL Server'),
        ('mongodb', 'MongoDB'),
        ('redis', 'Redis'),
        ('elasticsearch', 'Elasticsearch'),
        ('other', 'Diğer')
    ])
    version = models.CharField(max_length=50, blank=True)
    
    # Connection details
    server = models.ForeignKey(Server, on_delete=models.CASCADE, related_name='databases')
    port = models.PositiveIntegerField(default=5432)
    schema_name = models.CharField(max_length=255, blank=True)
    
    # Database details
    environment = models.ForeignKey(Environment, on_delete=models.CASCADE, related_name='databases')
    size_gb = models.FloatField(null=True, blank=True, help_text='Veritabanı boyutu (GB)')
    
    # Applications using this database
    applications = models.ManyToManyField(Application, related_name='databases', blank=True)
    
    # Status and monitoring
    status = models.CharField(max_length=20, choices=[
        ('active', 'Aktif'),
        ('inactive', 'Pasif'),
        ('maintenance', 'Bakımda'),
        ('archived', 'Arşivlendi')
    ], default='active')
    
    backup_enabled = models.BooleanField(default=True)
    backup_frequency = models.CharField(max_length=20, choices=[
        ('daily', 'Günlük'),
        ('weekly', 'Haftalık'),
        ('monthly', 'Aylık'),
        ('custom', 'Özel')
    ], default='daily')
    
    # Ownership
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='owned_databases')
    
    # Additional information
    purpose = models.TextField(blank=True, help_text='Veritabanının kullanım amacı')
    notes = models.TextField(blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Veritabanı'
        verbose_name_plural = 'Veritabanları'
    
    def __str__(self):
        return f"{self.name} ({self.database_type})"
