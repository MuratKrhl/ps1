from django.contrib import admin
from .models import (
    KnowledgeCategory, Technology, Question, Answer, 
    QuestionView, QuestionVote, AnswerVote, FAQ, KnowledgeArticle
)


@admin.register(KnowledgeCategory)
class KnowledgeCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'parent', 'color', 'order', 'is_active', 'created_at']
    list_filter = ['parent', 'is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['order', 'is_active']
    prepopulated_fields = {'color': ('name',)}


@admin.register(Technology)
class TechnologyAdmin(admin.ModelAdmin):
    list_display = ['name', 'color', 'is_active', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    list_editable = ['color', 'is_active']


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'priority', 'status', 'view_count', 'helpful_count', 'created_at']
    list_filter = ['category', 'difficulty', 'priority', 'status', 'technologies', 'is_active', 'created_at']
    search_fields = ['title', 'content']
    list_editable = ['status', 'priority']
    raw_id_fields = ['created_by', 'approved_by']
    filter_horizontal = ['technologies', 'tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'content', 'category')
        }),
        ('Kategorilendirme', {
            'fields': ('technologies', 'tags', 'difficulty', 'priority')
        }),
        ('Durum ve Onay', {
            'fields': ('status', 'approved_by', 'approved_at')
        }),
        ('İstatistikler', {
            'fields': ('view_count', 'helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['view_count', 'helpful_count', 'not_helpful_count']


@admin.register(Answer)
class AnswerAdmin(admin.ModelAdmin):
    list_display = ['question', 'is_accepted', 'is_official', 'status', 'helpful_count', 'created_at']
    list_filter = ['is_accepted', 'is_official', 'status', 'code_language', 'is_active', 'created_at']
    search_fields = ['content', 'question__title']
    list_editable = ['is_accepted', 'is_official', 'status']
    raw_id_fields = ['question', 'created_by']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('question', 'content')
        }),
        ('Kod Örneği', {
            'fields': ('code_example', 'code_language'),
            'classes': ('collapse',)
        }),
        ('Durum ve Özellikler', {
            'fields': ('status', 'is_accepted', 'is_official')
        }),
        ('İstatistikler', {
            'fields': ('helpful_count', 'not_helpful_count'),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['helpful_count', 'not_helpful_count']


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question', 'category', 'order', 'is_featured', 'view_count', 'is_active']
    list_filter = ['category', 'is_featured', 'technologies', 'is_active', 'created_at']
    search_fields = ['question', 'answer']
    list_editable = ['order', 'is_featured', 'is_active']
    filter_horizontal = ['technologies']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('question', 'answer', 'category')
        }),
        ('Kategorilendirme', {
            'fields': ('technologies',)
        }),
        ('Görüntüleme Ayarları', {
            'fields': ('order', 'is_featured')
        }),
        ('İstatistikler', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['view_count']


@admin.register(KnowledgeArticle)
class KnowledgeArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'difficulty', 'status', 'view_count', 'published_at']
    list_filter = ['category', 'difficulty', 'status', 'technologies', 'is_active', 'created_at']
    search_fields = ['title', 'content', 'summary']
    list_editable = ['status']
    prepopulated_fields = {'slug': ('title',)}
    filter_horizontal = ['technologies', 'tags']
    
    fieldsets = (
        ('Temel Bilgiler', {
            'fields': ('title', 'slug', 'summary', 'content')
        }),
        ('Kategorilendirme', {
            'fields': ('category', 'technologies', 'tags', 'difficulty')
        }),
        ('Yayınlama', {
            'fields': ('status', 'published_at', 'estimated_read_time')
        }),
        ('İstatistikler', {
            'fields': ('view_count',),
            'classes': ('collapse',)
        }),
        ('Sistem Bilgileri', {
            'fields': ('is_active', 'created_by', 'updated_by'),
            'classes': ('collapse',)
        })
    )
    
    readonly_fields = ['view_count']


# Inline admins for votes and views
class QuestionVoteInline(admin.TabularInline):
    model = QuestionVote
    extra = 0
    readonly_fields = ['user', 'is_helpful', 'created_at']


class AnswerVoteInline(admin.TabularInline):
    model = AnswerVote
    extra = 0
    readonly_fields = ['user', 'is_helpful', 'created_at']


@admin.register(QuestionView)
class QuestionViewAdmin(admin.ModelAdmin):
    list_display = ['question', 'user', 'viewed_at', 'ip_address']
    list_filter = ['viewed_at']
    search_fields = ['question__title', 'user__username']
    readonly_fields = ['question', 'user', 'viewed_at', 'ip_address']


@admin.register(QuestionVote)
class QuestionVoteAdmin(admin.ModelAdmin):
    list_display = ['question', 'user', 'is_helpful', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    search_fields = ['question__title', 'user__username']


@admin.register(AnswerVote)
class AnswerVoteAdmin(admin.ModelAdmin):
    list_display = ['answer', 'user', 'is_helpful', 'created_at']
    list_filter = ['is_helpful', 'created_at']
    search_fields = ['answer__question__title', 'user__username']
