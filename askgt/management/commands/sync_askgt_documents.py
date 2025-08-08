import requests
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from askgt.models import AskGTDocument

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync AskGT documents from external API'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--api-url',
            type=str,
            default=getattr(settings, 'ASKGT_API_URL', 'https://api.example.com/documents'),
            help='API endpoint URL'
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
    
    def handle(self, *args, **options):
        api_url = options['api_url']
        timeout = options['timeout']
        dry_run = options['dry_run']
        
        self.stdout.write(f"🔄 AskGT Doküman Senkronizasyonu Başlatılıyor...")
        self.stdout.write(f"API URL: {api_url}")
        
        try:
            # API'den veri çek
            response = self.fetch_documents(api_url, timeout)
            
            if not response:
                self.stdout.write(self.style.ERROR("❌ API'den veri alınamadı"))
                return
            
            # Verileri işle
            created_count, updated_count = self.process_documents(response, dry_run)
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"🔍 DRY RUN: {created_count} yeni, {updated_count} güncellenecek doküman")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Senkronizasyon tamamlandı: {created_count} yeni, {updated_count} güncellendi")
                )
                
        except Exception as e:
            logger.error(f"AskGT sync error: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Hata: {e}"))
    
    def fetch_documents(self, api_url, timeout):
        """API'den dokümanları çek"""
        try:
            headers = {
                'User-Agent': 'Portall-AskGT-Sync/1.0',
                'Accept': 'application/json',
            }
            
            # API key varsa ekle
            api_key = getattr(settings, 'ASKGT_API_KEY', None)
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.get(api_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            self.stdout.write(f"📥 {len(data.get('documents', []))} doküman alındı")
            
            return data.get('documents', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"API request failed: {e}")
            return None
        except ValueError as e:
            logger.error(f"JSON parse error: {e}")
            return None
    
    def process_documents(self, documents, dry_run=False):
        """Dokümanları işle ve kaydet"""
        created_count = 0
        updated_count = 0
        
        for doc_data in documents:
            try:
                # Gerekli alanları kontrol et
                required_fields = ['id', 'title', 'url', 'category']
                if not all(field in doc_data for field in required_fields):
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Eksik alan: {doc_data.get('id', 'unknown')}")
                    )
                    continue
                
                kaynak_id = str(doc_data['id'])
                
                # Mevcut dokümanı kontrol et
                document, created = AskGTDocument.objects.get_or_create(
                    kaynak_id=kaynak_id,
                    defaults={
                        'baslik': doc_data['title'][:255],
                        'orijinal_url': doc_data['url'],
                        'kategori': doc_data['category'][:100],
                        'ozet': doc_data.get('summary', '')[:1000],
                        'is_active': doc_data.get('active', True),
                    }
                )
                
                if not dry_run:
                    if created:
                        created_count += 1
                        self.stdout.write(f"➕ Yeni: {document.baslik}")
                    else:
                        # Mevcut dokümanı güncelle
                        updated = False
                        if document.baslik != doc_data['title'][:255]:
                            document.baslik = doc_data['title'][:255]
                            updated = True
                        if document.orijinal_url != doc_data['url']:
                            document.orijinal_url = doc_data['url']
                            updated = True
                        if document.kategori != doc_data['category'][:100]:
                            document.kategori = doc_data['category'][:100]
                            updated = True
                        if document.ozet != doc_data.get('summary', '')[:1000]:
                            document.ozet = doc_data.get('summary', '')[:1000]
                            updated = True
                        
                        if updated:
                            document.guncelleme_tarihi = timezone.now()
                            document.save()
                            updated_count += 1
                            self.stdout.write(f"🔄 Güncellendi: {document.baslik}")
                else:
                    if created:
                        created_count += 1
                    else:
                        updated_count += 1
                        
            except Exception as e:
                logger.error(f"Document processing error: {e}")
                self.stdout.write(
                    self.style.ERROR(f"❌ İşleme hatası: {doc_data.get('id', 'unknown')} - {e}")
                )
        
        return created_count, updated_count
