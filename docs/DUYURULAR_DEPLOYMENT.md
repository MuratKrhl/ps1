# Duyurular Modülü Deployment Rehberi

## Genel Bakış
Bu rehber, Duyurular & Planlı Çalışmalar modülünün production ortamında çalıştırılması için gerekli adımları içerir.

## 1. Sistem Gereksinimleri

### Python Paketleri
```bash
pip install django-ckeditor
pip install celery
pip install redis  # Celery broker için
```

### Sistem Bağımlılıkları
- Redis Server (Celery broker)
- PostgreSQL (veritabanı)
- Nginx (web server)
- Gunicorn (WSGI server)

## 2. Environment Variables

`.env` dosyasına aşağıdaki değişkenleri ekleyin:

```bash
# Duyuru Ayarları
ANNOUNCEMENT_ADMIN_EMAIL=admin@company.com
ANNOUNCEMENT_FROM_EMAIL=noreply@company.com
SITE_URL=https://portall.company.com

# CKEditor Ayarları
CKEDITOR_UPLOAD_PATH=uploads/
CKEDITOR_IMAGE_BACKEND=pillow

# Celery Ayarları
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## 3. Database Migration

```bash
# Migration dosyalarını oluştur
python manage.py makemigrations duyurular

# Migration'ları uygula
python manage.py migrate

# Süper kullanıcı oluştur (eğer yoksa)
python manage.py createsuperuser
```

## 4. Static Files

```bash
# Static dosyaları topla
python manage.py collectstatic --noinput

# Media klasörü izinlerini ayarla
chmod 755 media/
chmod 755 media/uploads/
```

## 5. Celery Setup

### Celery Worker Başlatma
```bash
# Development
celery -A portall worker -l info

# Production (systemd service olarak)
sudo systemctl start celery-worker
sudo systemctl enable celery-worker
```

### Celery Beat Scheduler Başlatma
```bash
# Development
celery -A portall beat -l info

# Production (systemd service olarak)
sudo systemctl start celery-beat
sudo systemctl enable celery-beat
```

### Systemd Service Dosyaları

#### `/etc/systemd/system/celery-worker.service`
```ini
[Unit]
Description=Celery Worker Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
EnvironmentFile=/path/to/portall/.env
WorkingDirectory=/path/to/portall
ExecStart=/path/to/venv/bin/celery -A portall worker --detach
ExecStop=/path/to/venv/bin/celery -A portall control shutdown
ExecReload=/path/to/venv/bin/celery -A portall control reload
KillMode=mixed
Restart=always

[Install]
WantedBy=multi-user.target
```

#### `/etc/systemd/system/celery-beat.service`
```ini
[Unit]
Description=Celery Beat Service
After=network.target

[Service]
Type=forking
User=www-data
Group=www-data
EnvironmentFile=/path/to/portall/.env
WorkingDirectory=/path/to/portall
ExecStart=/path/to/venv/bin/celery -A portall beat --detach
KillMode=mixed
Restart=always

[Install]
WantedBy=multi-user.target
```

## 6. Nginx Konfigürasyonu

CKEditor dosya upload'ları için nginx ayarları:

```nginx
server {
    listen 80;
    server_name portall.company.com;
    
    location /media/ {
        alias /path/to/portall/media/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    location /static/ {
        alias /path/to/portall/staticfiles/;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }
    
    # CKEditor upload size limit
    client_max_body_size 10M;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 7. İlk Kurulum Adımları

### 1. Kategoriler Oluşturma
```python
python manage.py shell

from duyurular.models import AnnouncementCategory

# Temel kategoriler
categories = [
    {'name': 'Genel', 'description': 'Genel duyurular', 'color': '#6366f1'},
    {'name': 'Sistem', 'description': 'Sistem duyuruları', 'color': '#ef4444'},
    {'name': 'Bakım', 'description': 'Bakım çalışmaları', 'color': '#f59e0b'},
    {'name': 'Güncelleme', 'description': 'Sistem güncellemeleri', 'color': '#10b981'},
]

for cat_data in categories:
    AnnouncementCategory.objects.get_or_create(
        name=cat_data['name'],
        defaults=cat_data
    )
```

### 2. İlk Duyuru Oluşturma
Admin panelinden `/admin/duyurular/announcement/` adresine giderek ilk duyuruyu oluşturun.

## 8. Test Senaryoları

### Temel Fonksiyonalite Testleri
1. **Duyuru Oluşturma**: Admin panelinden yeni duyuru oluşturun
2. **Modal Form**: Ana sayfadan modal ile duyuru oluşturun
3. **Draft/Publish**: Taslak kaydetme ve yayınlama işlemlerini test edin
4. **Otomatik Arşivleme**: Yayın bitiş tarihi geçmiş duyuru oluşturup arşivleme komutunu çalıştırın
5. **E-posta Bildirimleri**: Yeni duyuru oluşturduğunuzda e-posta gönderimini kontrol edin

### Celery Görevleri Testi
```bash
# Manuel olarak arşivleme komutunu çalıştır
python manage.py archive_expired_announcements --dry-run

# Celery görevlerini kontrol et
celery -A portall inspect active
celery -A portall inspect scheduled
```

### Dashboard Testi
1. Ana dashboard'a gidin
2. Duyurular widget'ının yüklendiğini kontrol edin
3. Duyuru sayısının doğru gösterildiğini kontrol edin
4. Son duyuruların listelendiğini kontrol edin

## 9. Monitoring ve Logs

### Celery Logs
```bash
# Worker logs
tail -f /var/log/celery/worker.log

# Beat logs
tail -f /var/log/celery/beat.log
```

### Django Logs
```python
# settings.py'de logging konfigürasyonu
LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'handlers': {
        'file': {
            'level': 'INFO',
            'class': 'logging.FileHandler',
            'filename': '/var/log/portall/announcements.log',
        },
    },
    'loggers': {
        'duyurular': {
            'handlers': ['file'],
            'level': 'INFO',
            'propagate': True,
        },
    },
}
```

## 10. Bakım ve Güncelleme

### Periyodik Görevler
- **Günlük**: Arşivleme ve temizlik görevleri otomatik çalışır
- **Haftalık**: Aktivite raporları otomatik gönderilir
- **Aylık**: Eski görüntüleme kayıtlarını temizleyin

### Backup
```bash
# Duyuru verilerini yedekle
python manage.py dumpdata duyurular > announcements_backup.json

# Restore
python manage.py loaddata announcements_backup.json
```

## 11. Sorun Giderme

### Yaygın Sorunlar
1. **CKEditor yüklenmiyorsa**: Static files'ı kontrol edin
2. **E-posta gönderilmiyorsa**: SMTP ayarlarını ve Celery worker'ı kontrol edin
3. **Dashboard yüklenmiyorsa**: Redis bağlantısını ve cache ayarlarını kontrol edin
4. **Modal açılmiyorsa**: JavaScript hataları için browser console'u kontrol edin

### Debug Komutları
```bash
# Celery durumunu kontrol et
celery -A portall status

# Redis bağlantısını test et
redis-cli ping

# Django ayarlarını kontrol et
python manage.py check

# Template syntax'ını kontrol et
python manage.py check --deploy
```

## 12. Güvenlik

### Öneriler
1. CKEditor upload klasörüne script dosyası yüklemesini engelleyin
2. CSRF korumasının aktif olduğunu kontrol edin
3. Admin paneline erişimi IP kısıtlaması ile sınırlayın
4. E-posta şablonlarında XSS koruması kullanın

### Nginx Güvenlik
```nginx
# Sadece belirli dosya tiplerinin upload edilmesine izin ver
location /media/uploads/ {
    location ~* \.(php|pl|py|jsp|asp|sh|cgi)$ {
        deny all;
    }
}
```

Bu rehberi takip ederek Duyurular modülünü başarıyla production ortamında çalıştırabilirsiniz.
