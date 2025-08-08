from django.contrib import admin
from .models import Category, Tag, UserProfile


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'color', 'order', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']
    list_editable = ['order', 'is_active']


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name']
    list_editable = ['color', 'is_active']


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['user', 'department', 'phone', 'theme_preference', 'language']
    list_filter = ['department', 'theme_preference', 'language', 'is_active']
    search_fields = ['user__username', 'user__first_name', 'user__last_name', 'department']
    raw_id_fields = ['user']
