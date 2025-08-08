import requests
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from otomasyon.ansible_models import AnsibleJobTemplate, SurveyParameter
from otomasyon.models import PlaybookCategory
import json

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync Ansible Tower/AWX Job Templates and Survey parameters'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--tower-url',
            type=str,
            default=getattr(settings, 'ANSIBLE_TOWER_URL', 'https://tower.example.com'),
            help='Ansible Tower/AWX URL'
        )
        parser.add_argument(
            '--username',
            type=str,
            default=getattr(settings, 'ANSIBLE_TOWER_USERNAME', ''),
            help='Tower/AWX username'
        )
        parser.add_argument(
            '--password',
            type=str,
            default=getattr(settings, 'ANSIBLE_TOWER_PASSWORD', ''),
            help='Tower/AWX password'
        )
        parser.add_argument(
            '--token',
            type=str,
            default=getattr(settings, 'ANSIBLE_TOWER_TOKEN', ''),
            help='Tower/AWX API token'
        )
        parser.add_argument(
            '--timeout',
            type=int,
            default=30,
            help='Request timeout in seconds'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Perform a dry run without saving data'
        )
        parser.add_argument(
            '--category',
            type=str,
            help='Default category name for job templates'
        )
    
    def handle(self, *args, **options):
        tower_url = options['tower_url'].rstrip('/')
        username = options['username']
        password = options['password']
        token = options['token']
        timeout = options['timeout']
        dry_run = options['dry_run']
        default_category = options['category']
        
        self.stdout.write(f"🔄 Ansible Tower/AWX Job Template Senkronizasyonu Başlatılıyor...")
        self.stdout.write(f"Tower URL: {tower_url}")
        
        try:
            # API session oluştur
            session = self.create_api_session(tower_url, username, password, token, timeout)
            
            # Job Template'leri çek
            job_templates = self.fetch_job_templates(session, tower_url)
            
            if not job_templates:
                self.stdout.write(self.style.ERROR("❌ Job Template bulunamadı"))
                return
            
            # Default kategori oluştur
            category = None
            if default_category:
                category, created = PlaybookCategory.objects.get_or_create(
                    name=default_category,
                    defaults={
                        'description': 'Ansible Tower/AWX Job Templates',
                        'color': '#28a745',
                        'icon': 'ri-settings-3-line'
                    }
                )
                if created:
                    self.stdout.write(f"📁 Kategori oluşturuldu: {category.name}")
            
            # Job Template'leri işle
            created_count, updated_count, error_count = self.process_job_templates(
                session, tower_url, job_templates, category, dry_run
            )
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"🔍 DRY RUN: {created_count} yeni, {updated_count} güncellenecek, {error_count} hata")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Senkronizasyon tamamlandı: {created_count} yeni, {updated_count} güncellendi, {error_count} hata")
                )
                
        except Exception as e:
            logger.error(f"Ansible Tower sync error: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Hata: {e}"))
    
    def create_api_session(self, tower_url, username, password, token, timeout):
        """API session oluştur"""
        session = requests.Session()
        session.timeout = timeout
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        # Authentication
        if token:
            session.headers['Authorization'] = f'Bearer {token}'
        elif username and password:
            session.auth = (username, password)
        else:
            raise ValueError("Token veya username/password gerekli")
        
        # SSL verification ayarı
        session.verify = getattr(settings, 'ANSIBLE_TOWER_VERIFY_SSL', True)
        
        return session
    
    def fetch_job_templates(self, session, tower_url):
        """Job Template'leri çek"""
        try:
            url = f"{tower_url}/api/v2/job_templates/"
            response = session.get(url)
            response.raise_for_status()
            
            data = response.json()
            job_templates = data.get('results', [])
            
            # Pagination handling
            while data.get('next'):
                response = session.get(data['next'])
                response.raise_for_status()
                data = response.json()
                job_templates.extend(data.get('results', []))
            
            self.stdout.write(f"📋 {len(job_templates)} Job Template bulundu")
            return job_templates
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to fetch job templates: {e}")
            return []
    
    def process_job_templates(self, session, tower_url, job_templates, category, dry_run=False):
        """Job Template'leri işle ve kaydet"""
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for template_data in job_templates:
            try:
                tower_id = template_data.get('id')
                name = template_data.get('name')
                
                if not tower_id or not name:
                    error_count += 1
                    continue
                
                # Job Template verilerini hazırla
                template_fields = {
                    'name': name,
                    'description': template_data.get('description', ''),
                    'tower_url': tower_url,
                    'project_name': template_data.get('summary_fields', {}).get('project', {}).get('name', ''),
                    'playbook': template_data.get('playbook', ''),
                    'inventory_name': template_data.get('summary_fields', {}).get('inventory', {}).get('name', ''),
                    'job_type': template_data.get('job_type', 'run'),
                    'verbosity': template_data.get('verbosity', 0),
                    'survey_enabled': template_data.get('survey_enabled', False),
                    'ask_variables_on_launch': template_data.get('ask_variables_on_launch', False),
                    'ask_limit_on_launch': template_data.get('ask_limit_on_launch', False),
                    'ask_tags_on_launch': template_data.get('ask_tags_on_launch', False),
                    'ask_skip_tags_on_launch': template_data.get('ask_skip_tags_on_launch', False),
                    'ask_job_type_on_launch': template_data.get('ask_job_type_on_launch', False),
                    'ask_verbosity_on_launch': template_data.get('ask_verbosity_on_launch', False),
                    'ask_inventory_on_launch': template_data.get('ask_inventory_on_launch', False),
                    'ask_credential_on_launch': template_data.get('ask_credential_on_launch', False),
                    'category': category,
                }
                
                if not dry_run:
                    # Job Template'i oluştur veya güncelle
                    job_template, created = AnsibleJobTemplate.objects.get_or_create(
                        tower_id=tower_id,
                        defaults=template_fields
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f"➕ Yeni: {name}")
                    else:
                        # Mevcut template'i güncelle
                        updated = False
                        for field, value in template_fields.items():
                            if field != 'category' and getattr(job_template, field) != value:
                                setattr(job_template, field, value)
                                updated = True
                        
                        if category and job_template.category != category:
                            job_template.category = category
                            updated = True
                        
                        if updated:
                            job_template.save()
                            updated_count += 1
                            self.stdout.write(f"🔄 Güncellendi: {name}")
                    
                    # Survey parametrelerini senkronize et
                    if template_data.get('survey_enabled'):
                        self.sync_survey_parameters(session, tower_url, job_template, tower_id)
                else:
                    # Dry run - sadece say
                    try:
                        existing = AnsibleJobTemplate.objects.get(tower_id=tower_id)
                        updated_count += 1
                    except AnsibleJobTemplate.DoesNotExist:
                        created_count += 1
                        
            except Exception as e:
                logger.error(f"Job template processing error: {e}")
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Template işleme hatası: {template_data.get('name', 'Unknown')} - {e}")
                )
        
        return created_count, updated_count, error_count
    
    def sync_survey_parameters(self, session, tower_url, job_template, tower_id):
        """Survey parametrelerini senkronize et"""
        try:
            url = f"{tower_url}/api/v2/job_templates/{tower_id}/survey_spec/"
            response = session.get(url)
            
            if response.status_code == 404:
                # Survey yok
                return
            
            response.raise_for_status()
            survey_data = response.json()
            
            # Mevcut parametreleri temizle
            job_template.survey_parameters.all().delete()
            
            # Yeni parametreleri ekle
            for i, spec in enumerate(survey_data.get('spec', [])):
                SurveyParameter.objects.create(
                    job_template=job_template,
                    variable=spec.get('variable', ''),
                    question_name=spec.get('question_name', ''),
                    question_description=spec.get('question_description', ''),
                    type=self.map_survey_type(spec.get('type', 'text')),
                    required=spec.get('required', False),
                    default_value=str(spec.get('default', '')),
                    min_value=spec.get('min'),
                    max_value=spec.get('max'),
                    choices=spec.get('choices', []) if spec.get('choices') else [],
                    order=i
                )
            
            self.stdout.write(f"  📝 Survey parametreleri güncellendi: {len(survey_data.get('spec', []))} parametre")
            
        except Exception as e:
            logger.error(f"Survey sync error for template {tower_id}: {e}")
    
    def map_survey_type(self, tower_type):
        """Tower survey type'ını model type'ına çevir"""
        type_mapping = {
            'text': 'text',
            'textarea': 'textarea',
            'password': 'password',
            'integer': 'integer',
            'float': 'float',
            'multiplechoice': 'multiplechoice',
            'multiselect': 'multiselect',
        }
        return type_mapping.get(tower_type, 'text')
