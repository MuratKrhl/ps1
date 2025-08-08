from django.contrib import admin
from .models import (
    Environment, OperatingSystem, Server, ApplicationType, 
    Technology, Application, Database
)


@admin.register(Environment)
class EnvironmentAdmin(admin.ModelAdmin):
    list_display = ['name', 'short_name', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'short_name', 'description']
    list_editable = ['short_name', 'color', 'is_active']


@admin.register(OperatingSystem)
class OperatingSystemAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'family', 'is_active', 'created_at']
    list_filter = ['family', 'is_active', 'created_at']
    search_fields = ['name', 'version']
    list_editable = ['is_active']


@admin.register(Server)
class ServerAdmin(admin.ModelAdmin):
    list_display = ['hostname', 'ip_address', 'environment', 'operating_system', 'status', 'is_active']
    list_filter = ['environment', 'operating_system', 'status', 'is_active', 'created_at']
    search_fields = ['hostname', 'ip_address', 'serial_number', 'purpose']
    list_editable = ['status', 'is_active']
    raw_id_fields = ['owner']
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('hostname', 'ip_address', 'environment', 'operating_system', 'status')
        }),
        ('Donanım Özellikleri', {
            'fields': ('cpu_cores', 'ram_gb', 'disk_gb', 'manufacturer', 'model', 'serial_number')
        }),
        ('Konum ve Fiziksel Bilgiler', {
            'fields': ('location', 'rack_position')
        }),
        ('Monitoring ve Yedekleme', {
            'fields': ('monitoring_enabled', 'backup_enabled', 'last_ping')
        }),
        ('Sorumluluk', {
            'fields': ('owner', 'responsible_team')
        }),
        ('Ek Bilgiler', {
            'fields': ('purpose', 'notes', 'tags')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(ApplicationType)
class ApplicationTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'icon', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['icon', 'is_active']


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ['name', 'version', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'version']
    list_editable = ['version', 'is_active']


@admin.register(Application)
class ApplicationAdmin(admin.ModelAdmin):
    list_display = ['name', 'code_name', 'application_type', 'environment', 'status', 'business_criticality', 'is_active']
    list_filter = ['application_type', 'environment', 'status', 'business_criticality', 'is_active', 'created_at']
    search_fields = ['name', 'code_name', 'description', 'development_team']
    list_editable = ['status', 'is_active']
    raw_id_fields = ['owner']
    filter_horizontal = ['servers', 'technologies', 'tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'code_name', 'description', 'application_type', 'environment')
        }),
        ('Teknoloji ve Sunucular', {
            'fields': ('technologies', 'servers')
        }),
        ('URL\'ler', {
            'fields': ('url', 'admin_url', 'documentation_url', 'repository_url')
        }),
        ('Durum ve Versiyon', {
            'fields': ('status', 'version', 'last_deployment', 'monitoring_enabled')
        }),
        ('Sorumluluk', {
            'fields': ('owner', 'development_team', 'business_owner', 'business_criticality')
        }),
        ('Ek Bilgiler', {
            'fields': ('notes', 'tags')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(Database)
class DatabaseAdmin(admin.ModelAdmin):
    list_display = ['name', 'database_type', 'version', 'server', 'environment', 'status', 'size_gb', 'is_active']
    list_filter = ['database_type', 'environment', 'status', 'backup_enabled', 'is_active', 'created_at']
    search_fields = ['name', 'schema_name', 'purpose']
    list_editable = ['status', 'is_active']
    raw_id_fields = ['server', 'owner']
    filter_horizontal = ['applications', 'tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'database_type', 'version', 'server', 'environment')
        }),
        ('Bağlantı Bilgileri', {
            'fields': ('port', 'schema_name')
        }),
        ('Boyut ve Durum', {
            'fields': ('size_gb', 'status')
        }),
        ('Uygulamalar', {
            'fields': ('applications',)
        }),
        ('Yedekleme', {
            'fields': ('backup_enabled', 'backup_frequency')
        }),
        ('Sorumluluk', {
            'fields': ('owner',)
        }),
        ('Ek Bilgiler', {
            'fields': ('purpose', 'notes', 'tags')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
