from django.contrib import admin
from .models import (
    LinkCategory, Link, LinkClick, QuickLink, LinkCollection, 
    LinkCollectionItem, BookmarkFolder, PersonalBookmark
)


@admin.register(LinkCategory)
class LinkCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'color', 'order', 'is_active', 'created_at']
    list_filter = ['parent', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active']


@admin.register(Link)
class LinkAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'is_featured', 'is_internal', 'is_working', 'click_count', 'last_checked']
    list_filter = ['category', 'is_featured', 'is_internal', 'requires_vpn', 'requires_auth', 'is_working', 'is_active']
    search_fields = ['title', 'url', 'description']
    list_editable = ['is_featured', 'is_working']
    filter_horizontal = ['tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'url', 'description', 'category')
        }),
        ('Kategorilendirme', {
            'fields': ('tags',)
        }),
        ('Link Özellikleri', {
            'fields': ('is_internal', 'requires_vpn', 'requires_auth')
        }),
        ('Görüntüleme', {
            'fields': ('is_featured', 'order')
        }),
        ('Erişim Kontrolü', {
            'fields': ('is_public', 'allowed_teams', 'allowed_departments')
        }),
        ('Durum İzleme', {
            'fields': ('is_working', 'last_checked', 'response_time'),
            'classes': ('collapse',)
        }),
        ('İstatistikler', {
            'fields': ('click_count',),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['click_count', 'last_checked', 'response_time']


@admin.register(QuickLink)
class QuickLinkAdmin(admin.ModelAdmin):
    list_display = ['title', 'url', 'order', 'is_visible', 'open_in_new_tab']
    list_filter = ['is_visible', 'open_in_new_tab', 'is_active']
    search_fields = ['title', 'url', 'description']
    list_editable = ['order', 'is_visible', 'open_in_new_tab']


@admin.register(LinkCollection)
class LinkCollectionAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'is_public', 'is_active', 'created_at']
    list_filter = ['is_public', 'is_active', 'created_at']
    search_fields = ['name', 'description', 'owner__username']
    raw_id_fields = ['owner']
    filter_horizontal = ['shared_with']


class LinkCollectionItemInline(admin.TabularInline):
    model = LinkCollectionItem
    extra = 1


@admin.register(BookmarkFolder)
class BookmarkFolderAdmin(admin.ModelAdmin):
    list_display = ['name', 'owner', 'parent', 'order', 'is_active']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'owner__username']
    raw_id_fields = ['owner', 'parent']
    list_editable = ['order']


@admin.register(PersonalBookmark)
class PersonalBookmarkAdmin(admin.ModelAdmin):
    list_display = ['title', 'owner', 'folder', 'is_favorite', 'order']
    list_filter = ['is_favorite', 'is_active', 'created_at']
    search_fields = ['title', 'url', 'owner__username']
    raw_id_fields = ['owner', 'folder']
    filter_horizontal = ['tags']
    list_editable = ['is_favorite', 'order']


@admin.register(LinkClick)
class LinkClickAdmin(admin.ModelAdmin):
    list_display = ['link', 'user', 'clicked_at', 'ip_address']
    list_filter = ['clicked_at']
    search_fields = ['link__title', 'user__username']
    readonly_fields = ['link', 'user', 'clicked_at', 'ip_address', 'user_agent']
