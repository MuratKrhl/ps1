from django.db import models
from core.models import BaseModel, Category, Tag
from django.contrib.auth.models import User
from django.core.validators import URLValidator


class LinkCategory(BaseModel):
    """Categories for organizing links"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['order', 'name']
        verbose_name = 'Link Kategorisi'
        verbose_name_plural = 'Link Kategorileri'
    
    def __str__(self):
        return self.name


class Link(BaseModel):
    """Important links and bookmarks"""
    title = models.CharField(max_length=255)
    url = models.URLField(validators=[URLValidator()])
    description = models.TextField(blank=True)
    
    category = models.ForeignKey(LinkCategory, on_delete=models.CASCADE, related_name='links')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Link properties
    is_internal = models.BooleanField(default=False, help_text='Dahili link mi?')
    requires_vpn = models.BooleanField(default=False, help_text='VPN gerektirir mi?')
    requires_auth = models.BooleanField(default=False, help_text='Kimlik doğrulama gerektirir mi?')
    
    # Display settings
    is_featured = models.BooleanField(default=False, help_text='Öne çıkarılmış link')
    order = models.PositiveIntegerField(default=0)
    
    # Access control
    is_public = models.BooleanField(default=True, help_text='Herkese açık')
    allowed_teams = models.CharField(max_length=500, blank=True, help_text='İzinli takımlar (virgülle ayır)')
    allowed_departments = models.CharField(max_length=500, blank=True, help_text='İzinli departmanlar (virgülle ayır)')
    
    # Statistics
    click_count = models.PositiveIntegerField(default=0)
    
    # Status monitoring
    last_checked = models.DateTimeField(null=True, blank=True)
    is_working = models.BooleanField(default=True, help_text='Link çalışıyor mu?')
    response_time = models.FloatField(null=True, blank=True, help_text='Yanıt süresi (ms)')
    
    class Meta:
        ordering = ['category', 'order', 'title']
        verbose_name = 'Link'
        verbose_name_plural = 'Linkler'
    
    def __str__(self):
        return self.title


class LinkClick(models.Model):
    """Track link clicks by users"""
    link = models.ForeignKey(Link, on_delete=models.CASCADE, related_name='clicks')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    clicked_at = models.DateTimeField(auto_now_add=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-clicked_at']
        verbose_name = 'Link Tıklama'
        verbose_name_plural = 'Link Tıklamalar'
    
    def __str__(self):
        return f"{self.user.username} - {self.link.title}"


class QuickLink(BaseModel):
    """Quick access links for dashboard"""
    title = models.CharField(max_length=100)
    url = models.URLField()
    description = models.CharField(max_length=200, blank=True)
    icon = models.CharField(max_length=50, blank=True, help_text='CSS icon class')
    color = models.CharField(max_length=7, default='#007bff')
    
    # Display settings
    order = models.PositiveIntegerField(default=0)
    is_visible = models.BooleanField(default=True)
    
    # Target settings
    open_in_new_tab = models.BooleanField(default=True)
    
    class Meta:
        ordering = ['order', 'title']
        verbose_name = 'Hızlı Link'
        verbose_name_plural = 'Hızlı Linkler'
    
    def __str__(self):
        return self.title


class LinkCollection(BaseModel):
    """Collections of related links"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#007bff')
    icon = models.CharField(max_length=50, blank=True)
    
    links = models.ManyToManyField(Link, through='LinkCollectionItem', related_name='collections')
    
    # Access control
    is_public = models.BooleanField(default=True)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='link_collections')
    shared_with = models.ManyToManyField(User, blank=True, related_name='shared_collections')
    
    class Meta:
        ordering = ['name']
        verbose_name = 'Link Koleksiyonu'
        verbose_name_plural = 'Link Koleksiyonları'
    
    def __str__(self):
        return self.name


class LinkCollectionItem(models.Model):
    """Links within collections with ordering"""
    collection = models.ForeignKey(LinkCollection, on_delete=models.CASCADE)
    link = models.ForeignKey(Link, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)
    notes = models.TextField(blank=True)
    
    class Meta:
        ordering = ['order']
        unique_together = ['collection', 'link']
        verbose_name = 'Koleksiyon Linki'
        verbose_name_plural = 'Koleksiyon Linkleri'


class BookmarkFolder(BaseModel):
    """Personal bookmark folders for users"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    color = models.CharField(max_length=7, default='#6c757d')
    icon = models.CharField(max_length=50, blank=True)
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='bookmark_folders')
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children')
    order = models.PositiveIntegerField(default=0)
    
    class Meta:
        ordering = ['owner', 'order', 'name']
        verbose_name = 'Yer İmi Klasörü'
        verbose_name_plural = 'Yer İmi Klasörleri'
    
    def __str__(self):
        return f"{self.owner.username} - {self.name}"


class PersonalBookmark(BaseModel):
    """Personal bookmarks for users"""
    title = models.CharField(max_length=255)
    url = models.URLField()
    description = models.TextField(blank=True)
    
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name='personal_bookmarks')
    folder = models.ForeignKey(BookmarkFolder, on_delete=models.CASCADE, null=True, blank=True, related_name='bookmarks')
    tags = models.ManyToManyField(Tag, blank=True)
    
    # Display settings
    order = models.PositiveIntegerField(default=0)
    is_favorite = models.BooleanField(default=False)
    
    class Meta:
        ordering = ['owner', 'folder', 'order', 'title']
        verbose_name = 'Kişisel Yer İmi'
        verbose_name_plural = 'Kişisel Yer İmleri'
    
    def __str__(self):
        return f"{self.owner.username} - {self.title}"
