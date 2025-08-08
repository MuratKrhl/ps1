from django import forms
from django.core.exceptions import ValidationError
from .ansible_models import AnsibleJobTemplate, SurveyParameter
import json


class DynamicJobTemplateForm(forms.Form):
    """Job Template için dinamik form"""
    
    def __init__(self, job_template, *args, **kwargs):
        self.job_template = job_template
        super().__init__(*args, **kwargs)
        
        # Survey parametrelerini form field'larına çevir
        if job_template.survey_enabled:
            self._add_survey_fields()
        
        # Launch-time parametrelerini ekle
        self._add_launch_fields()
    
    def _add_survey_fields(self):
        """Survey parametrelerini form field'larına çevir"""
        for param in self.job_template.survey_parameters.all():
            field_name = f"survey_{param.variable}"
            field = self._create_field_from_parameter(param)
            self.fields[field_name] = field
    
    def _add_launch_fields(self):
        """Launch-time parametrelerini ekle"""
        # Extra Variables
        if self.job_template.ask_variables_on_launch:
            self.fields['extra_vars'] = forms.CharField(
                label='Ek Değişkenler (JSON)',
                widget=forms.Textarea(attrs={
                    'rows': 4,
                    'class': 'form-control',
                    'placeholder': '{"key": "value", "another_key": "another_value"}'
                }),
                required=False,
                help_text='JSON formatında ek değişkenler'
            )
        
        # Limit
        if self.job_template.ask_limit_on_launch:
            self.fields['limit'] = forms.CharField(
                label='Host Limiti',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'host1,host2 veya group1'
                }),
                required=False,
                help_text='Çalıştırılacak host veya gruplar'
            )
        
        # Tags
        if self.job_template.ask_tags_on_launch:
            self.fields['tags'] = forms.CharField(
                label='Çalıştırılacak Tag\'ler',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'tag1,tag2,tag3'
                }),
                required=False,
                help_text='Virgülle ayrılmış tag listesi'
            )
        
        # Skip Tags
        if self.job_template.ask_skip_tags_on_launch:
            self.fields['skip_tags'] = forms.CharField(
                label='Atlanacak Tag\'ler',
                widget=forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': 'skip_tag1,skip_tag2'
                }),
                required=False,
                help_text='Virgülle ayrılmış atlanacak tag listesi'
            )
        
        # Job Type
        if self.job_template.ask_job_type_on_launch:
            self.fields['job_type'] = forms.ChoiceField(
                label='Job Türü',
                choices=[
                    ('run', 'Run'),
                    ('check', 'Check'),
                ],
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.job_template.job_type,
                required=False
            )
        
        # Verbosity
        if self.job_template.ask_verbosity_on_launch:
            self.fields['verbosity'] = forms.ChoiceField(
                label='Verbosity',
                choices=[
                    (0, '0 (Normal)'),
                    (1, '1 (Verbose)'),
                    (2, '2 (More Verbose)'),
                    (3, '3 (Debug)'),
                    (4, '4 (Connection Debug)'),
                    (5, '5 (WinRM Debug)'),
                ],
                widget=forms.Select(attrs={'class': 'form-select'}),
                initial=self.job_template.verbosity,
                required=False
            )
    
    def _create_field_from_parameter(self, param):
        """Survey parametresinden form field oluştur"""
        field_kwargs = {
            'label': param.question_name,
            'help_text': param.question_description,
            'required': param.required,
        }
        
        # Default value
        if param.default_value:
            field_kwargs['initial'] = param.default_value
        
        # Field type'a göre uygun field oluştur
        if param.type == 'text':
            field_kwargs['widget'] = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': param.question_name
            })
            field = forms.CharField(**field_kwargs)
            
        elif param.type == 'textarea':
            field_kwargs['widget'] = forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': param.question_name
            })
            field = forms.CharField(**field_kwargs)
            
        elif param.type == 'password':
            field_kwargs['widget'] = forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': param.question_name
            })
            field = forms.CharField(**field_kwargs)
            
        elif param.type == 'integer':
            field_kwargs['widget'] = forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': param.question_name
            })
            if param.min_value is not None:
                field_kwargs['min_value'] = param.min_value
            if param.max_value is not None:
                field_kwargs['max_value'] = param.max_value
            field = forms.IntegerField(**field_kwargs)
            
        elif param.type == 'float':
            field_kwargs['widget'] = forms.NumberInput(attrs={
                'class': 'form-control',
                'step': 'any',
                'placeholder': param.question_name
            })
            if param.min_value is not None:
                field_kwargs['min_value'] = param.min_value
            if param.max_value is not None:
                field_kwargs['max_value'] = param.max_value
            field = forms.FloatField(**field_kwargs)
            
        elif param.type == 'multiplechoice':
            if param.choices:
                choices = [(choice, choice) for choice in param.choices]
                field_kwargs['choices'] = choices
                field_kwargs['widget'] = forms.Select(attrs={'class': 'form-select'})
                field = forms.ChoiceField(**field_kwargs)
            else:
                # Choices yoksa text field olarak kullan
                field_kwargs['widget'] = forms.TextInput(attrs={
                    'class': 'form-control',
                    'placeholder': param.question_name
                })
                field = forms.CharField(**field_kwargs)
                
        elif param.type == 'multiselect':
            if param.choices:
                choices = [(choice, choice) for choice in param.choices]
                field_kwargs['choices'] = choices
                field_kwargs['widget'] = forms.CheckboxSelectMultiple()
                field = forms.MultipleChoiceField(**field_kwargs)
            else:
                # Choices yoksa textarea olarak kullan
                field_kwargs['widget'] = forms.Textarea(attrs={
                    'class': 'form-control',
                    'rows': 3,
                    'placeholder': 'Her satıra bir değer yazın'
                })
                field = forms.CharField(**field_kwargs)
        
        else:
            # Default: text field
            field_kwargs['widget'] = forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': param.question_name
            })
            field = forms.CharField(**field_kwargs)
        
        return field
    
    def clean_extra_vars(self):
        """Extra vars JSON validation"""
        extra_vars = self.cleaned_data.get('extra_vars', '')
        if extra_vars:
            try:
                json.loads(extra_vars)
            except json.JSONDecodeError:
                raise ValidationError('Geçerli bir JSON formatı giriniz')
        return extra_vars
    
    def get_survey_answers(self):
        """Survey cevaplarını al"""
        survey_answers = {}
        for field_name, value in self.cleaned_data.items():
            if field_name.startswith('survey_'):
                variable_name = field_name.replace('survey_', '')
                survey_answers[variable_name] = value
        return survey_answers
    
    def get_launch_parameters(self):
        """Launch parametrelerini al"""
        launch_params = {}
        
        # Extra vars
        if 'extra_vars' in self.cleaned_data and self.cleaned_data['extra_vars']:
            try:
                launch_params['extra_vars'] = json.loads(self.cleaned_data['extra_vars'])
            except json.JSONDecodeError:
                launch_params['extra_vars'] = {}
        
        # Diğer parametreler
        for param in ['limit', 'tags', 'skip_tags', 'job_type', 'verbosity']:
            if param in self.cleaned_data and self.cleaned_data[param]:
                launch_params[param] = self.cleaned_data[param]
        
        return launch_params


class JobTemplateFilterForm(forms.Form):
    """Job Template filtreleme formu"""
    
    search = forms.CharField(
        label='Arama',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job Template adı veya açıklama...'
        }),
        required=False
    )
    
    category = forms.ModelChoiceField(
        label='Kategori',
        queryset=None,  # View'da set edilecek
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False,
        empty_label='Tüm Kategoriler'
    )
    
    status = forms.ChoiceField(
        label='Durum',
        choices=[
            ('', 'Tümü'),
            ('enabled', 'Aktif'),
            ('disabled', 'Pasif'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    survey_enabled = forms.ChoiceField(
        label='Survey',
        choices=[
            ('', 'Tümü'),
            ('yes', 'Survey Var'),
            ('no', 'Survey Yok'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    def __init__(self, *args, **kwargs):
        categories = kwargs.pop('categories', None)
        super().__init__(*args, **kwargs)
        
        if categories:
            self.fields['category'].queryset = categories


class JobExecutionFilterForm(forms.Form):
    """Job Execution filtreleme formu"""
    
    search = forms.CharField(
        label='Arama',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Job Template adı veya Execution ID...'
        }),
        required=False
    )
    
    status = forms.ChoiceField(
        label='Durum',
        choices=[
            ('', 'Tümü'),
            ('pending', 'Beklemede'),
            ('waiting', 'Bekleniyor'),
            ('running', 'Çalışıyor'),
            ('successful', 'Başarılı'),
            ('failed', 'Başarısız'),
            ('error', 'Hata'),
            ('canceled', 'İptal Edildi'),
        ],
        widget=forms.Select(attrs={'class': 'form-select'}),
        required=False
    )
    
    executor = forms.CharField(
        label='Çalıştıran',
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Kullanıcı adı...'
        }),
        required=False
    )
    
    date_from = forms.DateField(
        label='Başlangıç Tarihi',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
    
    date_to = forms.DateField(
        label='Bitiş Tarihi',
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        }),
        required=False
    )
