"""
Forms for Envanter (Inventory) module
"""
from django import forms
from django.core.exceptions import ValidationError
from .models import Server, Application, Database, Environment, OperatingSystem, ApplicationType, Technology


class ApplicationForm(forms.ModelForm):
    """Form for creating and updating applications"""
    
    class Meta:
        model = Application
        fields = [
            'name', 'code_name', 'description', 'version',
            'environment', 'application_type', 'status',
            'business_criticality', 'monitoring_enabled',
            'owner', 'responsible_team', 'servers',
            'technologies', 'databases', 'tags',
            'port', 'ssl_enabled', 'sync_enabled',
            'documentation_url', 'repository_url'
        ]
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Uygulama adı'
            }),
            'code_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Kod adı (örn: myapp-prod)'
            }),
            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Uygulama açıklaması'
            }),
            'version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'v1.0.0'
            }),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'application_type': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'business_criticality': forms.Select(attrs={'class': 'form-select'}),
            'monitoring_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'responsible_team': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sorumlu takım'
            }),
            'servers': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'multiple': True,
                'size': 5
            }),
            'technologies': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'multiple': True,
                'size': 5
            }),
            'databases': forms.SelectMultiple(attrs={
                'class': 'form-select',
                'multiple': True,
                'size': 3
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tag1, Tag2, Tag3'
            }),
            'port': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': '8080',
                'min': 1,
                'max': 65535
            }),
            'ssl_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'sync_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'documentation_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://docs.example.com'
            }),
            'repository_url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://github.com/company/repo'
            }),
        }
        labels = {
            'name': 'Uygulama Adı',
            'code_name': 'Kod Adı',
            'description': 'Açıklama',
            'version': 'Versiyon',
            'environment': 'Ortam',
            'application_type': 'Uygulama Tipi',
            'status': 'Durum',
            'business_criticality': 'İş Kritikliği',
            'monitoring_enabled': 'Monitoring Aktif',
            'owner': 'Sahip',
            'responsible_team': 'Sorumlu Takım',
            'servers': 'Sunucular',
            'technologies': 'Teknolojiler',
            'databases': 'Veritabanları',
            'tags': 'Etiketler',
            'port': 'Port',
            'ssl_enabled': 'SSL Aktif',
            'sync_enabled': 'Senkronizasyon Aktif',
            'documentation_url': 'Dokümantasyon URL',
            'repository_url': 'Repository URL',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aktif ortamları filtrele
        self.fields['environment'].queryset = Environment.objects.filter(is_active=True)
        
        # Aktif sunucuları filtrele
        self.fields['servers'].queryset = Server.objects.filter(is_active=True).select_related('environment')
        
        # Aktif teknolojileri filtrele
        self.fields['technologies'].queryset = Technology.objects.filter(is_active=True)
        
        # Aktif veritabanlarını filtrele
        self.fields['databases'].queryset = Database.objects.filter(is_active=True)

    def clean_code_name(self):
        """Code name validation"""
        code_name = self.cleaned_data.get('code_name')
        if code_name:
            # Alfanumerik ve tire karakterleri kontrol et
            if not code_name.replace('-', '').replace('_', '').isalnum():
                raise ValidationError('Kod adı sadece harf, rakam, tire ve alt çizgi içerebilir.')
            
            # Benzersizlik kontrolü
            if self.instance.pk:
                # Güncelleme durumu
                if Application.objects.filter(code_name=code_name).exclude(pk=self.instance.pk).exists():
                    raise ValidationError('Bu kod adı zaten kullanılıyor.')
            else:
                # Yeni kayıt durumu
                if Application.objects.filter(code_name=code_name).exists():
                    raise ValidationError('Bu kod adı zaten kullanılıyor.')
        
        return code_name

    def clean_port(self):
        """Port validation"""
        port = self.cleaned_data.get('port')
        if port:
            if port < 1 or port > 65535:
                raise ValidationError('Port numarası 1-65535 arasında olmalıdır.')
        return port

    def clean(self):
        """Form-wide validation"""
        cleaned_data = super().clean()
        
        # SSL ve port kontrolü
        ssl_enabled = cleaned_data.get('ssl_enabled')
        port = cleaned_data.get('port')
        
        if ssl_enabled and port:
            # SSL için yaygın portları kontrol et
            if port in [80, 8080, 3000, 5000] and ssl_enabled:
                self.add_error('port', 'SSL aktifken HTTP portları kullanmayın.')
        
        return cleaned_data


class ServerForm(forms.ModelForm):
    """Form for creating and updating servers"""
    
    class Meta:
        model = Server
        fields = [
            'hostname', 'ip_address', 'purpose', 'environment',
            'operating_system', 'status', 'cpu_cores', 'ram_gb',
            'disk_gb', 'owner', 'responsible_team', 'tags',
            'monitoring_enabled', 'backup_enabled'
        ]
        widgets = {
            'hostname': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'server01.example.com'
            }),
            'ip_address': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': '192.168.1.100'
            }),
            'purpose': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Sunucu amacı ve açıklaması'
            }),
            'environment': forms.Select(attrs={'class': 'form-select'}),
            'operating_system': forms.Select(attrs={'class': 'form-select'}),
            'status': forms.Select(attrs={'class': 'form-select'}),
            'cpu_cores': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 128
            }),
            'ram_gb': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 1024
            }),
            'disk_gb': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': 1,
                'max': 10000
            }),
            'owner': forms.Select(attrs={'class': 'form-select'}),
            'responsible_team': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Sorumlu takım'
            }),
            'tags': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Tag1, Tag2, Tag3'
            }),
            'monitoring_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'backup_enabled': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'hostname': 'Sunucu Adı',
            'ip_address': 'IP Adresi',
            'purpose': 'Amaç',
            'environment': 'Ortam',
            'operating_system': 'İşletim Sistemi',
            'status': 'Durum',
            'cpu_cores': 'CPU Çekirdek Sayısı',
            'ram_gb': 'RAM (GB)',
            'disk_gb': 'Disk (GB)',
            'owner': 'Sahip',
            'responsible_team': 'Sorumlu Takım',
            'tags': 'Etiketler',
            'monitoring_enabled': 'Monitoring Aktif',
            'backup_enabled': 'Backup Aktif',
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        
        # Aktif ortamları filtrele
        self.fields['environment'].queryset = Environment.objects.filter(is_active=True)
        
        # Aktif işletim sistemlerini filtrele
        self.fields['operating_system'].queryset = OperatingSystem.objects.filter(is_active=True)

    def clean_hostname(self):
        """Hostname validation"""
        hostname = self.cleaned_data.get('hostname')
        if hostname:
            # Benzersizlik kontrolü
            if self.instance.pk:
                # Güncelleme durumu
                if Server.objects.filter(hostname=hostname).exclude(pk=self.instance.pk).exists():
                    raise ValidationError('Bu sunucu adı zaten kullanılıyor.')
            else:
                # Yeni kayıt durumu
                if Server.objects.filter(hostname=hostname).exists():
                    raise ValidationError('Bu sunucu adı zaten kullanılıyor.')
        
        return hostname

    def clean_ip_address(self):
        """IP address validation"""
        ip_address = self.cleaned_data.get('ip_address')
        if ip_address:
            # Basit IP format kontrolü
            parts = ip_address.split('.')
            if len(parts) != 4:
                raise ValidationError('Geçerli bir IP adresi girin.')
            
            try:
                for part in parts:
                    num = int(part)
                    if num < 0 or num > 255:
                        raise ValidationError('Geçerli bir IP adresi girin.')
            except ValueError:
                raise ValidationError('Geçerli bir IP adresi girin.')
            
            # Benzersizlik kontrolü
            if self.instance.pk:
                # Güncelleme durumu
                if Server.objects.filter(ip_address=ip_address).exclude(pk=self.instance.pk).exists():
                    raise ValidationError('Bu IP adresi zaten kullanılıyor.')
            else:
                # Yeni kayıt durumu
                if Server.objects.filter(ip_address=ip_address).exists():
                    raise ValidationError('Bu IP adresi zaten kullanılıyor.')
        
        return ip_address


class InventorySearchForm(forms.Form):
    """Advanced search form for inventory items"""
    
    ITEM_TYPE_CHOICES = [
        ('all', 'Tümü'),
        ('servers', 'Sunucular'),
        ('applications', 'Uygulamalar'),
    ]
    
    search = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Arama...',
            'autocomplete': 'off'
        }),
        label='Arama'
    )
    
    type = forms.ChoiceField(
        choices=ITEM_TYPE_CHOICES,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Tip'
    )
    
    environment = forms.ModelChoiceField(
        queryset=Environment.objects.filter(is_active=True),
        required=False,
        empty_label='Tüm Ortamlar',
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Ortam'
    )
    
    status = forms.ChoiceField(
        choices=[('', 'Tüm Durumlar')] + Application._meta.get_field('status').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='Durum'
    )
    
    criticality = forms.ChoiceField(
        choices=[('', 'Tüm Kritiklik Seviyeleri')] + Application._meta.get_field('business_criticality').choices,
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'}),
        label='İş Kritikliği'
    )
