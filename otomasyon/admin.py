from django.contrib import admin
from .models import (
    PlaybookCategory, AnsiblePlaybook, PlaybookExecution,
    AutomationSchedule, AutomationLog, AutomationTemplate
)


@admin.register(PlaybookCategory)
class PlaybookCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'order', 'created_at']
    list_editable = ['order']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'color', 'icon', 'order')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(AnsiblePlaybook)
class AnsiblePlaybookAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'category', 'requires_approval', 'is_dangerous',
        'execution_count', 'success_rate', 'last_execution'
    ]
    list_filter = [
        'category', 'requires_approval', 'is_dangerous',
        'created_at', 'last_execution'
    ]
    search_fields = ['name', 'description', 'playbook_path']
    filter_horizontal = ['target_servers', 'target_applications', 'allowed_users']
    readonly_fields = [
        'execution_count', 'success_count', 'last_execution',
        'success_rate', 'created_at', 'updated_at'
    ]
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category')
        }),
        ('Dosya Bilgileri', {
            'fields': ('playbook_path', 'inventory_path')
        }),
        ('Çalıştırma Ayarları', {
            'fields': ('requires_approval', 'is_dangerous', 'timeout_minutes')
        }),
        ('Hedef Ayarları', {
            'fields': ('target_servers', 'target_applications')
        }),
        ('Değişkenler', {
            'fields': ('default_variables', 'required_variables'),
            'classes': ('collapse',)
        }),
        ('Erişim Kontrolü', {
            'fields': ('allowed_users', 'allowed_groups'),
            'classes': ('collapse',)
        }),
        ('İstatistikler', {
            'fields': ('execution_count', 'success_count', 'success_rate', 'last_execution'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PlaybookExecution)
class PlaybookExecutionAdmin(admin.ModelAdmin):
    list_display = [
        'execution_id', 'playbook', 'executor', 'status',
        'started_at', 'completed_at', 'return_code'
    ]
    list_filter = [
        'status', 'playbook__category', 'created_at',
        'started_at', 'completed_at'
    ]
    search_fields = [
        'execution_id', 'playbook__name', 'executor__username',
        'approved_by__username'
    ]
    readonly_fields = [
        'execution_id', 'duration', 'is_successful',
        'created_at', 'updated_at'
    ]
    raw_id_fields = ['playbook', 'executor', 'approved_by']
    
    fieldsets = (
        (None, {
            'fields': ('playbook', 'executor', 'execution_id', 'status')
        }),
        ('Çalıştırma Detayları', {
            'fields': ('variables', 'inventory', 'target_hosts')
        }),
        ('Zamanlama', {
            'fields': ('started_at', 'completed_at', 'duration')
        }),
        ('Sonuçlar', {
            'fields': ('return_code', 'is_successful', 'stdout', 'stderr'),
            'classes': ('collapse',)
        }),
        ('Onay Süreci', {
            'fields': ('approved_by', 'approved_at', 'approval_notes'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AutomationSchedule)
class AutomationScheduleAdmin(admin.ModelAdmin):
    list_display = [
        'name', 'playbook', 'schedule_type', 'is_enabled',
        'last_run', 'next_run', 'run_count'
    ]
    list_filter = [
        'is_enabled', 'schedule_type', 'playbook__category',
        'created_at', 'last_run'
    ]
    search_fields = ['name', 'description', 'playbook__name']
    readonly_fields = ['last_run', 'next_run', 'run_count', 'created_at', 'updated_at']
    raw_id_fields = ['playbook']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'playbook', 'is_enabled')
        }),
        ('Program Ayarları', {
            'fields': ('schedule_type', 'scheduled_time', 'scheduled_date', 'cron_expression')
        }),
        ('Çalıştırma Ayarları', {
            'fields': ('variables',),
            'classes': ('collapse',)
        }),
        ('Durum', {
            'fields': ('last_run', 'next_run', 'run_count'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AutomationLog)
class AutomationLogAdmin(admin.ModelAdmin):
    list_display = ['level', 'message_short', 'user', 'playbook_execution', 'created_at']
    list_filter = ['level', 'created_at']
    search_fields = ['message', 'user__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['playbook_execution', 'user']
    
    def message_short(self, obj):
        return obj.message[:100] + '...' if len(obj.message) > 100 else obj.message
    message_short.short_description = 'Mesaj'
    
    fieldsets = (
        (None, {
            'fields': ('level', 'message', 'user', 'playbook_execution')
        }),
        ('Ek Veri', {
            'fields': ('extra_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(AutomationTemplate)
class AutomationTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'category', 'usage_count', 'created_at']
    list_filter = ['category', 'created_at']
    search_fields = ['name', 'description']
    readonly_fields = ['usage_count', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'category')
        }),
        ('Şablon İçeriği', {
            'fields': ('playbook_content', 'default_variables')
        }),
        ('İstatistikler', {
            'fields': ('usage_count',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
