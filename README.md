# Portall - Middleware Operations Portal

Portall, middleware ekibinin operasyonel yükünü azaltmak ve son kullanıcılara self-servis imkânları sunan modern bir web portalıdır.

## 🎯 Proje Vizyonu
- Tekrarlayan görevleri otomatize etmek
- Geliştiricilere ve iş birimlerine self-servis bilgi ve aksiyon imkânları sunmak
- Güvenli, merkezi ve ölçeklenebilir portal çözümü

## 🛠 Teknoloji Stack
- **Backend**: Django 4.2 + Soft UI Dashboard
- **Frontend**: Velzon Modern Demo (Light/Dark Mode)
- **Veritabanı**: PostgreSQL
- **Arama**: django-haystack + Whoosh
- **Deployment**: Gunicorn + Nginx
- **Task Queue**: Celery + Redis

## 📁 Modüller
- **Envanter**: Sunucu ve uygulama yönetimi
- **AskGT**: Bilgi bankası ve soru/cevap sistemi
- **Nöbetçi**: Nöbet listesi yönetimi
- **Duyurular & Planlı Çalışmalar**: Kapsamlı duyuru yönetim sistemi
- **Sertifika Yönetimi**: KDB ve Java sertifika takibi
- **Önemli Linkler**: Kategorizeli link yönetimi
- **Performans**: Monitoring entegrasyonu
- **Otomasyon**: Ansible playbook tetikleme

## 🚀 Kurulum

### Gereksinimler
- Python 3.11+
- PostgreSQL 13+
- Redis (Celery için)

### Adımlar
```bash
# Virtual environment oluştur
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # Linux/Mac

# Bağımlılıkları yükle
pip install -r requirements.txt

# Veritabanı ayarları
python manage.py makemigrations
python manage.py migrate

# Superuser oluştur
python manage.py createsuperuser

# Static dosyaları topla
python manage.py collectstatic

# Celery worker başlat (ayrı terminal)
celery -A portall worker -l info

# Celery beat scheduler başlat (ayrı terminal)
celery -A portall beat -l info

# Geliştirme sunucusunu başlat
python manage.py runserver
```

## 📋 Geliştirme Fazları

### Faz 0: Kurulum ve Arayüz Entegrasyonu ✅
- [x] Temel Django projesi kurulumu
- [x] Soft UI Dashboard entegrasyonu
- [x] Velzon teması entegrasyonu
- [x] Light/Dark mode desteği
- [x] Dikey menü yapısı (ikon modu)

### Faz 1: Bilgi ve Görünürlük (MVP)
- [ ] Envanter modülü
- [ ] AskGT bilgi bankası
- [ ] Nöbetçi listesi
- [ ] Duyurular sistemi
- [ ] Önemli linkler

### Faz 2: Kontrollü Otomasyon
- [ ] Ansible playbook entegrasyonu
- [ ] Duyuru yönetim paneli
- [ ] Dashboard canlı veri entegrasyonu

### Faz 3: Entegrasyonlar ve İyileştirmeler
- [ ] Performans monitoring
- [ ] Global arama sistemi
- [ ] API entegrasyonları

## 🔐 Sertifika Yönetimi Modülü

Sertifika Yönetimi modülü, KDB ve Java sertifikalarının merkezi yönetimini sağlar.

### Özellikler
- **KDB Sertifikaları**: IBM HTTP Server KDB sertifikalarının yönetimi
- **Java Sertifikaları**: Java keystore sertifikalarının yönetimi
- **Otomatik Senkronizasyon**: SQL DB, AppViewX API ve SSH üzerinden veri senkronizasyonu
- **Süre Takibi**: Sertifika sürelerinin otomatik takibi ve uyarı sistemi
- **E-posta Bildirimleri**: Süre dolumu uyarıları ve haftalık raporlar
- **Dashboard Entegrasyonu**: Ana dashboard'da sertifika durumu widget'ı

### Veri Kaynakları
1. **SQL Database**: Mevcut sertifika envanteri
2. **AppViewX API**: Sertifika yönetim sistemi entegrasyonu
3. **Ansible**: Otomasyon scriptleri çıktıları
4. **SSH Keystore**: Sunuculardaki Java keystore dosyaları

### Otomatik Görevler (Celery Beat)
- **Günlük Senkronizasyon**: Her gün 02:00'da tüm kaynaklar
- **Günlük Uyarılar**: Her gün 08:00'da süre dolumu uyarıları
- **Haftalık Rapor**: Her Pazartesi 09:00'da yöneticilere rapor
- **Hızlı KDB Sync**: Her 6 saatte bir SQL'den
- **Java Sync**: Her Çarşamba 03:30'da SSH üzerinden

### Konfigürasyon
```bash
# SQL Database
CERTIFICATE_SQL_CONNECTION="DRIVER={ODBC Driver 17 for SQL Server};SERVER=server;DATABASE=db;UID=user;PWD=pass"

# AppViewX API
APPVIEWX_API_URL="https://appviewx.company.com/api"
APPVIEWX_API_KEY="your-api-key"

# SSH Access
CERTIFICATE_SSH_KEY_PATH="/path/to/ssh/key"

# Email Alerts
CERTIFICATE_ADMIN_EMAILS="admin1@company.com,admin2@company.com"
```

### Management Commands
```bash
# KDB sertifikalarını senkronize et
python manage.py sync_kdb_certificates --source sql

# Java sertifikalarını senkronize et
python manage.py sync_java_certificates --server web01

# Süre uyarıları gönder
python manage.py send_certificate_alerts --alert-type expired
```

## 🔧 Konfigürasyon
Proje `.env` dosyası ile yapılandırılır. `.env.example` dosyasını kopyalayarak başlayın.

## 📝 Lisans
Bu proje dahili kullanım için geliştirilmiştir.
