from django.contrib import admin
from .models import (
    AnnouncementCategory, Announcement, AnnouncementView, 
    AnnouncementComment, MaintenanceNotice, SystemStatus
)


@admin.register(AnnouncementCategory)
class AnnouncementCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['color', 'order', 'is_active']


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'priority', 'status', 'is_important', 'is_pinned', 'published_at', 'view_count']
    list_filter = ['category', 'priority', 'status', 'is_important', 'is_pinned', 'published_at', 'created_at']
    search_fields = ['title', 'content', 'summary']
    list_editable = ['priority', 'status', 'is_important', 'is_pinned']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['tags']
    raw_id_fields = ['approved_by']
    date_hierarchy = 'published_at'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'slug', 'summary', 'content', 'category')
        }),
        ('Kategorilendirme', {
            'fields': ('tags',)
        }),
        ('Öncelik ve Önem', {
            'fields': ('priority', 'is_important', 'is_pinned')
        }),
        ('Yayınlama', {
            'fields': ('status', 'published_at', 'expires_at')
        }),
        ('Hedef Kitle', {
            'fields': ('target_all_users', 'target_teams', 'target_departments')
        }),
        ('Bildirim Ayarları', {
            'fields': ('send_email', 'show_popup')
        }),
        ('Onay ve İstatistikler', {
            'fields': ('approved_by', 'approved_at', 'view_count'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['view_count']


@admin.register(AnnouncementComment)
class AnnouncementCommentAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'created_by', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'created_at']
    search_fields = ['content', 'announcement__title', 'created_by__username']
    list_editable = ['is_approved']
    raw_id_fields = ['announcement', 'parent']


@admin.register(MaintenanceNotice)
class MaintenanceNoticeAdmin(admin.ModelAdmin):
    list_display = ['title', 'start_time', 'end_time', 'impact_level', 'status', 'notify_users']
    list_filter = ['impact_level', 'status', 'notify_users', 'start_time']
    search_fields = ['title', 'description', 'affected_systems']
    list_editable = ['status', 'notify_users']
    date_hierarchy = 'start_time'
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'description')
        }),
        ('Zamanlama', {
            'fields': ('start_time', 'end_time')
        }),
        ('Etki', {
            'fields': ('affected_systems', 'impact_level')
        }),
        ('Durum', {
            'fields': ('status',)
        }),
        ('Bildirim', {
            'fields': ('notify_users', 'notification_sent')
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['notification_sent']


@admin.register(SystemStatus)
class SystemStatusAdmin(admin.ModelAdmin):
    list_display = ['system_name', 'status', 'started_at', 'resolved_at', 'affected_users']
    list_filter = ['status', 'started_at', 'resolved_at']
    search_fields = ['system_name', 'message']
    date_hierarchy = 'started_at'
    
    fieldsets = (
        ('Sistem Bilgileri', {
            'fields': ('system_name', 'status', 'message')
        }),
        ('Zamanlama', {
            'fields': ('started_at', 'resolved_at')
        }),
        ('Etki', {
            'fields': ('affected_users',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )


@admin.register(AnnouncementView)
class AnnouncementViewAdmin(admin.ModelAdmin):
    list_display = ['announcement', 'user', 'viewed_at', 'ip_address']
    list_filter = ['viewed_at']
    search_fields = ['announcement__title', 'user__username']
    readonly_fields = ['announcement', 'user', 'viewed_at', 'ip_address']
