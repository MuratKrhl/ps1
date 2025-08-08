from django import forms
from django.contrib.auth.models import User
from .models import Announcement, AnnouncementCategory, AnnouncementComment, MaintenanceNotice, SystemStatus
from ckeditor.widgets import CKEditorWidget


class AnnouncementForm(forms.ModelForm):
    """Duyuru oluşturma/düzenleme formu - Modal destekli"""
    
    # Custom field for action buttons
    action = forms.CharField(widget=forms.HiddenInput(), required=False)
    
    class Meta:
        model = Announcement
        fields = [
            'title', 'content', 'summary', 'duyuru_tipi', 'category', 
            'onem_seviyesi', 'ilgili_urun', 'calisma_tarihi', 'sabitle', 
            'yayin_bitis_tarihi', 'is_important', 'target_all_users', 
            'send_email', 'tags'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Duyuru başlığı',
                'required': True
            }),
            'content': CKEditorWidget(config_name='announcement'),
            'summary': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Kısa özet (opsiyonel)...'
            }),
            'duyuru_tipi': forms.Select(attrs={
                'class': 'form-select'
            }),
            'category': forms.Select(attrs={
                'class': 'form-select'
            }),
            'onem_seviyesi': forms.Select(attrs={
                'class': 'form-select'
            }),
            'ilgili_urun': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'İlgili ürün, sistem veya uygulama'
            }),
            'calisma_tarihi': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'yayin_bitis_tarihi': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'tags': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'multiple': True,
                'size': '4'
            }),
            'sabitle': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'is_important': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'target_all_users': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'send_email': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
        
        # Kategori seçeneklerini filtrele
        self.fields['category'].queryset = AnnouncementCategory.objects.filter(is_active=True)
        
        # Field labels in Turkish
        self.fields['title'].label = 'Başlık'
        self.fields['content'].label = 'İçerik'
        self.fields['summary'].label = 'Özet'
        self.fields['duyuru_tipi'].label = 'Duyuru Tipi'
        self.fields['onem_seviyesi'].label = 'Önem Seviyesi'
        self.fields['ilgili_urun'].label = 'İlgili Ürün/Sistem'
        self.fields['calisma_tarihi'].label = 'Çalışma Tarihi'
        self.fields['yayin_bitis_tarihi'].label = 'Yayın Bitiş Tarihi'
        self.fields['sabitle'].label = 'Sabitle'
        self.fields['is_important'].label = 'Önemli Duyuru'
        self.fields['target_all_users'].label = 'Tüm Kullanıcılara Göster'
        self.fields['send_email'].label = 'E-posta Bildirimi Gönder'
        
        # Make optional fields
        self.fields['summary'].required = False
        self.fields['ilgili_urun'].required = False
        self.fields['calisma_tarihi'].required = False
        self.fields['yayin_bitis_tarihi'].required = False
        self.fields['tags'].required = False
        
        # Eğer kullanıcı admin değilse bazı alanları gizle
        if self.user and not self.user.is_staff:
            self.fields['sabitle'].widget = forms.HiddenInput()
            self.fields['send_email'].widget = forms.HiddenInput()
    
    def save(self, commit=True):
        announcement = super().save(commit=False)
        
        # Set author if creating new announcement
        if not announcement.pk and self.user:
            announcement.created_by = self.user
        
        # Handle action-based status setting
        action = self.cleaned_data.get('action')
        if action == 'draft':
            announcement.status = 'draft'
        elif action == 'publish':
            announcement.status = 'published'
            if not announcement.published_at:
                from django.utils import timezone
                announcement.published_at = timezone.now()
        
        if commit:
            announcement.save()
            self.save_m2m()
        
        return announcement


class AnnouncementCategoryForm(forms.ModelForm):
    """Duyuru kategorisi formu"""
    
    class Meta:
        model = AnnouncementCategory
        fields = ['name', 'description', 'color', 'icon', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kategori adı'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Kategori açıklaması'
            }),
            'color': forms.TextInput(attrs={
                'class': 'form-control',
                'type': 'color'
            }),
            'icon': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'ri-notification-line'
            }),
            'is_active': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            })
        }


class AnnouncementCommentForm(forms.ModelForm):
    """Duyuru yorumu formu"""
    
    class Meta:
        model = AnnouncementComment
        fields = ['content']
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Yorumunuzu yazın...'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        self.announcement = kwargs.pop('announcement', None)
        super().__init__(*args, **kwargs)
    
    def save(self, commit=True):
        comment = super().save(commit=False)
        if self.user:
            comment.author = self.user
        if self.announcement:
            comment.announcement = self.announcement
        if commit:
            comment.save()
        return comment


class MaintenanceNoticeForm(forms.ModelForm):
    """Bakım bildirimi formu"""
    
    class Meta:
        model = MaintenanceNotice
        fields = [
            'title', 'description', 'maintenance_type', 'affected_systems',
            'start_time', 'end_time', 'impact_level', 'status'
        ]
        widgets = {
            'title': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Bakım başlığı'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 5,
                'placeholder': 'Bakım detayları...'
            }),
            'maintenance_type': forms.Select(attrs={
                'class': 'form-select'
            }),
            'affected_systems': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Etkilenen sistemler...'
            }),
            'start_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'end_time': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            }),
            'impact_level': forms.Select(attrs={
                'class': 'form-select'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            })
        }
    
    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super().__init__(*args, **kwargs)
    
    def clean(self):
        cleaned_data = super().clean()
        start_time = cleaned_data.get('start_time')
        end_time = cleaned_data.get('end_time')
        
        if start_time and end_time and start_time >= end_time:
            raise forms.ValidationError('Bitiş zamanı başlangıç zamanından sonra olmalıdır.')
        
        return cleaned_data
    
    def save(self, commit=True):
        notice = super().save(commit=False)
        if self.user:
            notice.created_by = self.user
        if commit:
            notice.save()
        return notice


class SystemStatusForm(forms.ModelForm):
    """Sistem durumu formu"""
    
    class Meta:
        model = SystemStatus
        fields = ['system_name', 'status', 'description', 'last_check']
        widgets = {
            'system_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sistem adı'
            }),
            'status': forms.Select(attrs={
                'class': 'form-select'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Durum açıklaması...'
            }),
            'last_check': forms.DateTimeInput(attrs={
                'class': 'form-control',
                'type': 'datetime-local'
            })
        }


class AnnouncementFilterForm(forms.Form):
    """Duyuru filtreleme formu"""
    
    PRIORITY_CHOICES = [('', 'Tüm Öncelikler')] + Announcement.PRIORITY_CHOICES
    TARGET_CHOICES = [('', 'Tüm Hedef Kitleler')] + Announcement.TARGET_AUDIENCE_CHOICES
    
    category = forms.ModelChoiceField(
        queryset=AnnouncementCategory.objects.filter(is_active=True),
        empty_label='Tüm Kategoriler',
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    priority = forms.ChoiceField(
        choices=PRIORITY_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    target_audience = forms.ChoiceField(
        choices=TARGET_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_important = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Başlık veya içerik ara...'
        })
    )


class BulkAnnouncementActionForm(forms.Form):
    """Toplu duyuru işlemleri formu"""
    
    ACTION_CHOICES = [
        ('', 'İşlem Seçin'),
        ('delete', 'Sil'),
        ('pin', 'Sabitle'),
        ('unpin', 'Sabitlemeden Çıkar'),
        ('mark_important', 'Önemli Olarak İşaretle'),
        ('unmark_important', 'Önemli İşaretini Kaldır'),
        ('change_category', 'Kategori Değiştir'),
        ('set_expiry', 'Son Kullanma Tarihi Belirle')
    ]
    
    action = forms.ChoiceField(
        choices=ACTION_CHOICES,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    category = forms.ModelChoiceField(
        queryset=AnnouncementCategory.objects.filter(is_active=True),
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    expiry_date = forms.DateTimeField(
        required=False,
        widget=forms.DateTimeInput(attrs={
            'class': 'form-control',
            'type': 'datetime-local'
        })
    )
    
    selected_announcements = forms.CharField(
        widget=forms.HiddenInput()
    )
    
    def clean(self):
        cleaned_data = super().clean()
        action = cleaned_data.get('action')
        
        if action == 'change_category' and not cleaned_data.get('category'):
            raise forms.ValidationError('Kategori değiştirme için yeni kategori seçmelisiniz.')
        
        if action == 'set_expiry' and not cleaned_data.get('expiry_date'):
            raise forms.ValidationError('Son kullanma tarihi belirleme için tarih seçmelisiniz.')
        
        return cleaned_data
