from django.contrib import admin
from .models import MetricType, ServerMetric, ApplicationMetric, PerformanceReport, Alert


@admin.register(MetricType)
class MetricTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'unit', 'category', 'is_active', 'created_at']
    list_filter = ['category', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['category', 'name']
    
    fieldsets = (
        (None, {
            'fields': ('name', 'description', 'unit', 'category', 'is_active')
        }),
        ('Eşik Değerleri', {
            'fields': ('warning_threshold', 'critical_threshold')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ServerMetric)
class ServerMetricAdmin(admin.ModelAdmin):
    list_display = ['server', 'metric_type', 'value', 'status', 'timestamp']
    list_filter = ['metric_type', 'status', 'timestamp', 'server__environment']
    search_fields = ['server__name', 'server__hostname', 'metric_type__name']
    raw_id_fields = ['server']
    readonly_fields = ['status', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('server', 'metric_type', 'value', 'timestamp')
        }),
        ('Durum', {
            'fields': ('status',)
        }),
        ('Ek Bilgiler', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(ApplicationMetric)
class ApplicationMetricAdmin(admin.ModelAdmin):
    list_display = ['application', 'metric_type', 'value', 'status', 'timestamp']
    list_filter = ['metric_type', 'status', 'timestamp', 'application__type']
    search_fields = ['application__name', 'metric_type__name']
    raw_id_fields = ['application']
    readonly_fields = ['status', 'created_at', 'updated_at']
    
    fieldsets = (
        (None, {
            'fields': ('application', 'metric_type', 'value', 'timestamp')
        }),
        ('Durum', {
            'fields': ('status',)
        }),
        ('Ek Bilgiler', {
            'fields': ('additional_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PerformanceReport)
class PerformanceReportAdmin(admin.ModelAdmin):
    list_display = ['title', 'report_type', 'period_start', 'period_end', 'created_by', 'created_at']
    list_filter = ['report_type', 'created_at', 'period_start']
    search_fields = ['title', 'description', 'created_by__username']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['created_by']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'report_type', 'created_by')
        }),
        ('Dönem', {
            'fields': ('period_start', 'period_end')
        }),
        ('Rapor İçeriği', {
            'fields': ('report_data', 'summary'),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ['title', 'severity', 'status', 'source_type', 'created_at', 'resolved_at']
    list_filter = ['severity', 'status', 'source_type', 'created_at', 'resolved_at']
    search_fields = ['title', 'description']
    readonly_fields = ['created_at', 'updated_at']
    raw_id_fields = ['resolved_by']
    
    fieldsets = (
        (None, {
            'fields': ('title', 'description', 'severity', 'status')
        }),
        ('Kaynak', {
            'fields': ('source_type', 'source_id')
        }),
        ('Çözüm', {
            'fields': ('resolved_by', 'resolved_at', 'resolution_notes'),
            'classes': ('collapse',)
        }),
        ('Ek Bilgiler', {
            'fields': ('alert_data',),
            'classes': ('collapse',)
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
