from django.contrib import admin
from .models import Team, DutyType, DutySchedule, DutyLog, EmergencyContact, DutySwapRequest


@admin.register(Team)
class TeamAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['color', 'is_active']


@admin.register(DutyType)
class DutyTypeAdmin(admin.ModelAdmin):
    list_display = ['name', 'default_duration_hours', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['default_duration_hours', 'color', 'is_active']


@admin.register(DutySchedule)
class DutyScheduleAdmin(admin.ModelAdmin):
    list_display = ['user', 'team', 'duty_type', 'start_date', 'end_date', 'status', 'is_active']
    list_filter = ['team', 'duty_type', 'status', 'is_active', 'start_date']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'notes']
    list_editable = ['status', 'is_active']
    raw_id_fields = ['user', 'replacement_user']
    date_hierarchy = 'start_date'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('user', 'team', 'duty_type')
        }),
        ('Tarih ve Saat', {
            'fields': ('start_date', 'start_time', 'end_date', 'end_time')
        }),
        ('Durum', {
            'fields': ('status',)
        }),
        ('İletişim Bilgileri', {
            'fields': ('primary_phone', 'secondary_phone', 'email')
        }),
        ('Değişiklik Bilgileri', {
            'fields': ('replacement_user', 'replacement_reason'),
            'classes': ('collapse',)
        }),
        ('Notlar', {
            'fields': ('notes',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(DutyLog)
class DutyLogAdmin(admin.ModelAdmin):
    list_display = ['duty_schedule', 'log_type', 'title', 'severity', 'is_resolved', 'logged_at']
    list_filter = ['log_type', 'severity', 'is_resolved', 'logged_at']
    search_fields = ['title', 'description', 'duty_schedule__user__username']
    raw_id_fields = ['duty_schedule']
    date_hierarchy = 'logged_at'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('duty_schedule', 'log_type', 'title', 'description')
        }),
        ('Zaman', {
            'fields': ('logged_at',)
        }),
        ('Olay Detayları', {
            'fields': ('severity', 'is_resolved', 'resolved_at', 'resolution_notes'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ['name', 'role', 'team', 'primary_phone', 'priority', 'is_24x7', 'is_active']
    list_filter = ['team', 'is_24x7', 'is_active', 'created_at']
    search_fields = ['name', 'role', 'primary_phone', 'email']
    list_editable = ['priority', 'is_24x7', 'is_active']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('name', 'role', 'team')
        }),
        ('İletişim Bilgileri', {
            'fields': ('primary_phone', 'secondary_phone', 'email')
        }),
        ('Ulaşılabilirlik', {
            'fields': ('is_24x7', 'available_hours', 'priority')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(DutySwapRequest)
class DutySwapRequestAdmin(admin.ModelAdmin):
    list_display = ['requester', 'original_duty', 'target_user', 'status', 'created_at']
    list_filter = ['status', 'created_at']
    search_fields = ['requester__username', 'target_user__username', 'reason']
    raw_id_fields = ['requester', 'original_duty', 'target_user', 'target_duty', 'approved_by']
    
    fieldsets = (
        ('Talep Bilgileri', {
            'fields': ('requester', 'original_duty', 'reason')
        }),
        ('Hedef Bilgileri', {
            'fields': ('target_user', 'target_duty')
        }),
        ('Durum', {
            'fields': ('status',)
        }),
        ('Onay Bilgileri', {
            'fields': ('approved_by', 'approved_at', 'rejection_reason'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
