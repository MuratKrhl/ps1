import requests
import pandas as pd
import logging
from django.core.management.base import BaseCommand
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_date
from nobetci.models import Nobetci
from datetime import datetime
import json
import csv
from io import StringIO

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Sync duty schedule from external source (CSV, Excel, JSON)'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--source-url',
            type=str,
            default=getattr(settings, 'DUTY_SCHEDULE_URL', 'https://example.com/duty-schedule.csv'),
            help='External data source URL'
        )
        parser.add_argument(
            '--source-type',
            type=str,
            choices=['csv', 'excel', 'json'],
            default='csv',
            help='Data source format'
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
            '--clear-existing',
            action='store_true',
            help='Clear existing duty records before sync'
        )
    
    def handle(self, *args, **options):
        source_url = options['source_url']
        source_type = options['source_type']
        timeout = options['timeout']
        dry_run = options['dry_run']
        clear_existing = options['clear_existing']
        
        self.stdout.write(f"🔄 Nöbet Listesi Senkronizasyonu Başlatılıyor...")
        self.stdout.write(f"Kaynak: {source_url}")
        self.stdout.write(f"Format: {source_type}")
        
        try:
            # Veriyi çek
            data = self.fetch_data(source_url, source_type, timeout)
            
            if not data:
                self.stdout.write(self.style.ERROR("❌ Veri alınamadı"))
                return
            
            # Mevcut kayıtları temizle (isteğe bağlı)
            if clear_existing and not dry_run:
                deleted_count = Nobetci.objects.all().delete()[0]
                self.stdout.write(f"🗑️ {deleted_count} mevcut kayıt silindi")
            
            # Verileri işle
            created_count, updated_count, error_count = self.process_data(data, dry_run)
            
            if dry_run:
                self.stdout.write(
                    self.style.WARNING(f"🔍 DRY RUN: {created_count} yeni, {updated_count} güncellenecek, {error_count} hata")
                )
            else:
                self.stdout.write(
                    self.style.SUCCESS(f"✅ Senkronizasyon tamamlandı: {created_count} yeni, {updated_count} güncellendi, {error_count} hata")
                )
                
        except Exception as e:
            logger.error(f"Duty schedule sync error: {e}")
            self.stdout.write(self.style.ERROR(f"❌ Hata: {e}"))
    
    def fetch_data(self, source_url, source_type, timeout):
        """Harici kaynaktan veri çek"""
        try:
            headers = {
                'User-Agent': 'Portall-DutySchedule-Sync/1.0',
                'Accept': 'application/json, text/csv, application/vnd.ms-excel',
            }
            
            # API key varsa ekle
            api_key = getattr(settings, 'DUTY_SCHEDULE_API_KEY', None)
            if api_key:
                headers['Authorization'] = f'Bearer {api_key}'
            
            response = requests.get(source_url, headers=headers, timeout=timeout)
            response.raise_for_status()
            
            # Format'a göre parse et
            if source_type == 'json':
                return response.json()
            elif source_type == 'csv':
                return self.parse_csv(response.text)
            elif source_type == 'excel':
                return self.parse_excel(response.content)
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            return None
        except Exception as e:
            logger.error(f"Data parsing error: {e}")
            return None
    
    def parse_csv(self, csv_content):
        """CSV içeriğini parse et"""
        try:
            # CSV'yi pandas ile oku
            df = pd.read_csv(StringIO(csv_content))
            
            # Sütun isimlerini normalize et
            df.columns = df.columns.str.lower().str.strip()
            
            # Gerekli sütunları kontrol et
            required_columns = ['tarih', 'ad_soyad']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Eksik sütunlar: {missing_columns}")
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"CSV parsing error: {e}")
            return None
    
    def parse_excel(self, excel_content):
        """Excel içeriğini parse et"""
        try:
            # Excel'i pandas ile oku
            df = pd.read_excel(excel_content)
            
            # Sütun isimlerini normalize et
            df.columns = df.columns.str.lower().str.strip()
            
            # Gerekli sütunları kontrol et
            required_columns = ['tarih', 'ad_soyad']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Eksik sütunlar: {missing_columns}")
            
            return df.to_dict('records')
            
        except Exception as e:
            logger.error(f"Excel parsing error: {e}")
            return None
    
    def process_data(self, data, dry_run=False):
        """Veriyi işle ve kaydet"""
        created_count = 0
        updated_count = 0
        error_count = 0
        
        for record in data:
            try:
                # Tarihi parse et
                tarih_str = str(record.get('tarih', '')).strip()
                if not tarih_str:
                    error_count += 1
                    continue
                
                # Farklı tarih formatlarını dene
                tarih = self.parse_date_flexible(tarih_str)
                if not tarih:
                    self.stdout.write(
                        self.style.WARNING(f"⚠️ Geçersiz tarih formatı: {tarih_str}")
                    )
                    error_count += 1
                    continue
                
                # Diğer alanları al
                ad_soyad = str(record.get('ad_soyad', '')).strip()
                if not ad_soyad:
                    error_count += 1
                    continue
                
                telefon = str(record.get('telefon', '')).strip()
                email = str(record.get('email', '')).strip()
                notlar = str(record.get('notlar', '')).strip()
                
                if not dry_run:
                    # Mevcut kaydı kontrol et
                    nobetci, created = Nobetci.objects.get_or_create(
                        tarih=tarih,
                        defaults={
                            'ad_soyad': ad_soyad,
                            'telefon': telefon,
                            'email': email,
                            'notlar': notlar,
                            'kaynak': 'external_sync',
                        }
                    )
                    
                    if created:
                        created_count += 1
                        self.stdout.write(f"➕ Yeni: {tarih.strftime('%d.%m.%Y')} - {ad_soyad}")
                    else:
                        # Mevcut kaydı güncelle
                        updated = False
                        if nobetci.ad_soyad != ad_soyad:
                            nobetci.ad_soyad = ad_soyad
                            updated = True
                        if nobetci.telefon != telefon:
                            nobetci.telefon = telefon
                            updated = True
                        if nobetci.email != email:
                            nobetci.email = email
                            updated = True
                        if nobetci.notlar != notlar:
                            nobetci.notlar = notlar
                            updated = True
                        
                        if updated:
                            nobetci.save()
                            updated_count += 1
                            self.stdout.write(f"🔄 Güncellendi: {tarih.strftime('%d.%m.%Y')} - {ad_soyad}")
                else:
                    # Dry run - sadece say
                    try:
                        existing = Nobetci.objects.get(tarih=tarih)
                        updated_count += 1
                    except Nobetci.DoesNotExist:
                        created_count += 1
                        
            except Exception as e:
                logger.error(f"Record processing error: {e}")
                error_count += 1
                self.stdout.write(
                    self.style.ERROR(f"❌ Kayıt işleme hatası: {record} - {e}")
                )
        
        return created_count, updated_count, error_count
    
    def parse_date_flexible(self, date_str):
        """Esnek tarih parsing"""
        # Yaygın tarih formatları
        date_formats = [
            '%Y-%m-%d',      # 2024-01-15
            '%d.%m.%Y',      # 15.01.2024
            '%d/%m/%Y',      # 15/01/2024
            '%d-%m-%Y',      # 15-01-2024
            '%Y/%m/%d',      # 2024/01/15
            '%m/%d/%Y',      # 01/15/2024
            '%d.%m.%y',      # 15.01.24
            '%d/%m/%y',      # 15/01/24
        ]
        
        for fmt in date_formats:
            try:
                return datetime.strptime(date_str, fmt).date()
            except ValueError:
                continue
        
        # Django'nun parse_date fonksiyonunu dene
        try:
            return parse_date(date_str)
        except:
            return None
