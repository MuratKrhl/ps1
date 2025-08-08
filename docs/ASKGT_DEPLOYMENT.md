# AskGT Modülü Deployment Rehberi

## 📋 Genel Bakış

AskGT (Bilgi Bankası) modülü harici API'den doküman senkronizasyonu, dinamik kategori menüleri ve otomatik raporlama özelliklerine sahiptir.

## 🔧 Ön Gereksinimler

### Sistem Gereksinimleri
- Python 3.8+
- PostgreSQL 12+
- Redis 6+ (Celery için)
- Nginx (production)

### Python Paketleri
```bash
pip install -r requirements.txt
```

Yeni eklenen paketler:
- `celery>=5.2.0`
- `redis>=4.0.0`
- `requests>=2.28.0`

## 🚀 Deployment Adımları

### 1. Veritabanı Migration

```bash
# AskGT modülü için migration oluştur
python manage.py makemigrations askgt

# Migration'ları uygula
python manage.py migrate askgt

# Tüm migration'ları kontrol et
python manage.py migrate
```

**Beklenen Çıktı:**
```
Migrations for 'askgt':
  askgt/migrations/0002_askgtdocument.py
    - Create model AskGTDocument
    - Add indexes for kategori and kaynak_id
```

### 2. Static Files

```bash
# Static dosyaları topla
python manage.py collectstatic --noinput

# Template dosyalarını kontrol et
python manage.py check --deploy
```

### 3. Environment Variables

`.env` dosyasına eklenecek değişkenler:

```env
# AskGT API Configuration
ASKGT_API_URL=https://api.example.com/documents
ASKGT_API_KEY=your_api_key_here
ASKGT_ADMIN_EMAIL=admin@company.com
ASKGT_FROM_EMAIL=askgt@company.com

# Celery Configuration
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### 4. Celery Worker ve Beat Scheduler

#### Terminal 1: Celery Worker
```bash
celery -A portall worker --loglevel=info --concurrency=4
```

#### Terminal 2: Celery Beat Scheduler
```bash
celery -A portall beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

#### Terminal 3: Celery Flower (Monitoring - Opsiyonel)
```bash
celery -A portall flower --port=5555
```

### 5. İlk Veri Yükleme

```bash
# API'den ilk doküman senkronizasyonu
python manage.py sync_askgt_documents --dry-run

# Gerçek senkronizasyon
python manage.py sync_askgt_documents

# Cache'i temizle
python manage.py shell -c "from django.core.cache import cache; cache.clear()"
```

## 🧪 Test Senaryoları

### 1. API Senkronizasyon Testi

```bash
# Dry run ile test
python manage.py sync_askgt_documents --dry-run --api-url=https://api.example.com/documents

# Gerçek API testi
python manage.py sync_askgt_documents --timeout=60
```

**Beklenen Çıktı:**
```
🔄 AskGT Doküman Senkronizasyonu Başlatılıyor...
API URL: https://api.example.com/documents
📥 25 doküman alındı
➕ Yeni: JBoss Konfigürasyon Rehberi
➕ Yeni: WebSphere Deployment Guide
✅ Senkronizasyon tamamlandı: 25 yeni, 0 güncellendi
```

### 2. Dinamik Menü Testi

Django shell'de test:
```python
python manage.py shell

# Context processor testi
from askgt.context_processors import askgt_categories
from django.http import HttpRequest
request = HttpRequest()
categories = askgt_categories(request)
print(categories['askgt_categories'])
```

### 3. Celery Task Testi

```python
# Django shell'de
from askgt.tasks import sync_documents_from_api, send_weekly_stats_report

# Senkronizasyon task'ını test et
result = sync_documents_from_api.delay()
print(f"Task ID: {result.id}")
print(f"Status: {result.status}")

# Haftalık rapor task'ını test et
report_result = send_weekly_stats_report.delay()
print(f"Report Task ID: {report_result.id}")
```

### 4. E-posta Testi

```bash
# Django shell'de e-posta testi
python manage.py shell

from askgt.tasks import send_weekly_stats_report
send_weekly_stats_report()
```

### 5. Web Interface Testi

1. **Ana Sayfa**: `http://localhost:8000/askgt/`
2. **Dokümanlar Dashboard**: `http://localhost:8000/askgt/dokumanlar/`
3. **Kategori Listesi**: `http://localhost:8000/askgt/dokumanlar/JBoss/`
4. **Sidebar Menü**: Dinamik kategorilerin görünürlüğü

## 🔍 Troubleshooting

### Yaygın Sorunlar

#### 1. Migration Hatası
```bash
# Hata: "No such table: askgt_askgtdocument"
python manage.py migrate askgt --fake-initial
python manage.py migrate askgt
```

#### 2. Context Processor Hatası
```bash
# Hata: "askgt_categories not found in template"
# settings.py'de context processor'ın eklendiğini kontrol et
python manage.py check
```

#### 3. Celery Bağlantı Hatası
```bash
# Redis bağlantısını test et
redis-cli ping

# Celery broker'ı test et
celery -A portall inspect ping
```

#### 4. API Senkronizasyon Hatası
```bash
# API endpoint'ini test et
curl -H "Authorization: Bearer YOUR_API_KEY" https://api.example.com/documents

# Timeout artır
python manage.py sync_askgt_documents --timeout=120
```

## 📊 Monitoring ve Bakım

### Log Dosyaları
```bash
# Django logs
tail -f logs/django.log

# Celery logs
tail -f logs/celery.log

# Nginx logs (production)
tail -f /var/log/nginx/portall_access.log
```

### Performans Metrikleri
- API response time: < 5 saniye
- Doküman senkronizasyon süresi: < 2 dakika
- Cache hit ratio: > %80
- Memory usage: < 512MB per worker

### Düzenli Bakım
```bash
# Haftalık cache temizliği
python manage.py shell -c "from django.core.cache import cache; cache.clear()"

# Aylık eski doküman temizliği
python manage.py shell -c "from askgt.tasks import cleanup_old_documents; cleanup_old_documents()"

# Celery worker restart (haftalık)
sudo systemctl restart celery-worker
sudo systemctl restart celery-beat
```

## 🔐 Güvenlik Ayarları

### API Key Güvenliği
```python
# settings.py
ASKGT_API_KEY = os.getenv('ASKGT_API_KEY')
if not ASKGT_API_KEY:
    raise ValueError("ASKGT_API_KEY environment variable is required")
```

### Rate Limiting
```python
# API istekleri için rate limiting
ASKGT_API_RATE_LIMIT = 100  # requests per hour
```

## 📈 Production Deployment

### Nginx Konfigürasyonu
```nginx
# /etc/nginx/sites-available/portall
location /askgt/ {
    proxy_pass http://127.0.0.1:8000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_cache askgt_cache;
    proxy_cache_valid 200 15m;
}
```

### Systemd Services
```ini
# /etc/systemd/system/celery-askgt.service
[Unit]
Description=Celery Worker for AskGT
After=network.target

[Service]
Type=forking
User=portall
Group=portall
WorkingDirectory=/opt/portall
ExecStart=/opt/portall/venv/bin/celery -A portall worker --loglevel=info --concurrency=2
Restart=always

[Install]
WantedBy=multi-user.target
```

## ✅ Deployment Checklist

- [ ] Python environment kurulumu
- [ ] Requirements.txt paketleri yüklendi
- [ ] PostgreSQL veritabanı hazırlandı
- [ ] Redis server çalışıyor
- [ ] Environment variables ayarlandı
- [ ] Migration'lar çalıştırıldı
- [ ] Static files toplandı
- [ ] Celery worker başlatıldı
- [ ] Celery beat scheduler başlatıldı
- [ ] API senkronizasyon testi yapıldı
- [ ] E-posta testi yapıldı
- [ ] Web interface testi yapıldı
- [ ] Sidebar dinamik menü testi yapıldı
- [ ] Log monitoring kuruldu
- [ ] Backup stratejisi belirlendi

## 📞 Destek

Sorun yaşandığında:
1. Log dosyalarını kontrol edin
2. Celery worker durumunu kontrol edin
3. Redis bağlantısını test edin
4. API endpoint'ini test edin
5. Cache'i temizleyin

---
**AskGT Modülü v1.0** - Production Ready ✅
