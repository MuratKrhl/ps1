from django.db import models
from core.models import BaseModel, Category, Tag
from django.contrib.auth.models import User
from django.urls import reverse


class KnowledgeCategory(BaseModel):
    """Categories for knowledge base articles"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Bilgi Kategorisi'
        verbose_name_plural = 'Bilgi Kategorileri'
    
    def __str__(self):
        return self.name
    
    def get_absolute_url(self):
        return reverse('askgt:category_detail', kwargs={'category_id': self.id})


class Technology(BaseModel):
    """Technologies for filtering questions/answers"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6c757d')
    icon = models.CharField(max_length=50, blank=True)
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Teknoloji'
        verbose_name_plural = 'Teknolojiler'
    
    def __str__(self):
        return self.name


class Question(BaseModel):
    """Knowledge base questions"""
    title = models.CharField(max_length=255, help_text='Soru başlığı')
    content = models.TextField(help_text='Soru detayı')
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='questions')
    technologies = models.ManyToManyField(Technology, blank=True, help_text='İlgili teknolojiler')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Question metadata
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Başlangıç'),
        ('intermediate', 'Orta'),
        ('advanced', 'İleri'),
        ('expert', 'Uzman')
    ], default='intermediate')
    
    priority = models.CharField(max_length=20, choices=[
        ('low', 'Düşük'),
        ('medium', 'Orta'),
        ('high', 'Yüksek'),
        ('critical', 'Kritik')
    ], default='medium')
    
    # Status and approval
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Taslak'),
        ('pending', 'Onay Bekliyor'),
        ('approved', 'Onaylandı'),
        ('rejected', 'Reddedildi'),
        ('archived', 'Arşivlendi')
    ], default='draft')
    
    # User interactions
    view_count = models.PositiveIntegerField(default=0)
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Approval workflow
    approved_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name='approved_questions')
    approved_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = 'Soru'
        verbose_name_plural = 'Sorular'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('askgt:question_detail', kwargs={'question_id': self.id})
    
    @property
    def helpful_percentage(self):
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return round((self.helpful_count / total_votes) * 100, 1)


class Answer(BaseModel):
    """Answers to knowledge base questions"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='answers')
    content = models.TextField(help_text='Cevap içeriği')
    
    # Answer metadata
    is_accepted = models.BooleanField(default=False, help_text='Kabul edilen cevap')
    is_official = models.BooleanField(default=False, help_text='Resmi cevap')
    
    # Code examples and attachments
    code_example = models.TextField(blank=True, help_text='Kod örneği')
    code_language = models.CharField(max_length=50, blank=True, help_text='Kod dili (python, java, etc.)')
    
    # User interactions
    helpful_count = models.PositiveIntegerField(default=0)
    not_helpful_count = models.PositiveIntegerField(default=0)
    
    # Status
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Taslak'),
        ('published', 'Yayınlandı'),
        ('archived', 'Arşivlendi')
    ], default='draft')
    
    class Meta:
        ordering = ['-is_accepted', '-is_official', '-helpful_count', '-created_at']
        verbose_name = 'Cevap'
        verbose_name_plural = 'Cevaplar'
    
    def __str__(self):
        return f"Cevap: {self.question.title[:50]}..."
    
    @property
    def helpful_percentage(self):
        total_votes = self.helpful_count + self.not_helpful_count
        if total_votes == 0:
            return 0
        return round((self.helpful_count / total_votes) * 100, 1)


class QuestionView(models.Model):
    """Track question views by users"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='question_views')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    viewed_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    
    class Meta:
        unique_together = ['question', 'user']
        verbose_name = 'Soru Görüntüleme'
        verbose_name_plural = 'Soru Görüntülemeleri'


class QuestionVote(models.Model):
    """User votes for questions (helpful/not helpful)"""
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['question', 'user']
        verbose_name = 'Soru Oyu'
        verbose_name_plural = 'Soru Oyları'


class AnswerVote(models.Model):
    """User votes for answers (helpful/not helpful)"""
    answer = models.ForeignKey(Answer, on_delete=models.CASCADE, related_name='votes')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    is_helpful = models.BooleanField()
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        unique_together = ['answer', 'user']
        verbose_name = 'Cevap Oyu'
        verbose_name_plural = 'Cevap Oyları'


class FAQ(BaseModel):
    """Frequently Asked Questions"""
    question = models.CharField(max_length=255)
    answer = models.TextField()
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='faqs')
    technologies = models.ManyToManyField(Technology, blank=True)
    
    # Display settings
    order = models.PositiveIntegerField(default=0)
    is_featured = models.BooleanField(default=False, help_text='Ana sayfada göster')
    
    # Statistics
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', '-created_at']
        verbose_name = 'Sık Sorulan Soru'
        verbose_name_plural = 'Sık Sorulan Sorular'
    
    def __str__(self):
        return self.question


class AskGTDocument(BaseModel):
    """External documentation links from API sync"""
    baslik = models.CharField(max_length=255, help_text='Doküman başlığı')
    orijinal_url = models.URLField(help_text='Orijinal doküman URL\'si')
    kategori = models.CharField(max_length=100, help_text='Doküman kategorisi', db_index=True)
    ozet = models.TextField(blank=True, help_text='Doküman özeti')
    kaynak_id = models.CharField(max_length=100, unique=True, help_text='Harici API\'den gelen benzersiz ID')
    eklenme_tarihi = models.DateTimeField(auto_now_add=True)
    guncelleme_tarihi = models.DateTimeField(auto_now=True)
    view_count = models.PositiveIntegerField(default=0)
    is_active = models.BooleanField(default=True, help_text='Aktif doküman')
    
    class Meta:
        ordering = ['-eklenme_tarihi']
        verbose_name = 'AskGT Dokümanı'
        verbose_name_plural = 'AskGT Dokümanları'
        indexes = [
            models.Index(fields=['kategori', '-eklenme_tarihi']),
            models.Index(fields=['kaynak_id']),
        ]
    
    def __str__(self):
        return f"{self.baslik} ({self.kategori})"
    
    def get_absolute_url(self):
        return reverse('askgt:document_redirect', kwargs={'document_id': self.id})
    
    def increment_view_count(self):
        """Görüntülenme sayısını artır"""
        self.view_count += 1
        self.save(update_fields=['view_count'])


class KnowledgeArticle(BaseModel):
    """Knowledge base articles/documentation"""
    title = models.CharField(max_length=255)
    slug = models.SlugField(unique=True)
    content = models.TextField()
    summary = models.TextField(blank=True, help_text='Kısa özet')
    category = models.ForeignKey(KnowledgeCategory, on_delete=models.CASCADE, related_name='articles')
    technologies = models.ManyToManyField(Technology, blank=True)
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Article metadata
    difficulty = models.CharField(max_length=20, choices=[
        ('beginner', 'Başlangıç'),
        ('intermediate', 'Orta'),
        ('advanced', 'İleri'),
        ('expert', 'Uzman')
    ], default='intermediate')
    
    estimated_read_time = models.PositiveIntegerField(default=5, help_text='Tahmini okuma süresi (dakika)')
    
    # Status and publishing
    status = models.CharField(max_length=20, choices=[
        ('draft', 'Taslak'),
        ('published', 'Yayınlandı'),
        ('archived', 'Arşivlendi')
    ], default='draft')
    
    published_at = models.DateTimeField(null=True, blank=True)
    
    # Statistics
    view_count = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['-published_at', '-created_at']
        verbose_name = 'Bilgi Makalesi'
        verbose_name_plural = 'Bilgi Makaleleri'
    
    def __str__(self):
        return self.title
    
    def get_absolute_url(self):
        return reverse('askgt:article_detail', kwargs={'slug': self.slug})
