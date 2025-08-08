# Duyurular Modülü Test Senaryoları

## Test Ortamı Hazırlığı

### 1. Gerekli Veriler
```python
# Django shell'de çalıştırın: python manage.py shell

from django.contrib.auth.models import User, Group, Permission
from duyurular.models import AnnouncementCategory, Announcement

# Test kullanıcıları oluştur
admin_user = User.objects.create_user(
    username='admin_test',
    email='admin@test.com',
    password='test123',
    is_staff=True,
    is_superuser=True
)

regular_user = User.objects.create_user(
    username='user_test',
    email='user@test.com',
    password='test123'
)

# Duyuru yöneticisi grubu ve izinleri
announcement_group, created = Group.objects.get_or_create(name='Duyuru Yöneticileri')
permissions = Permission.objects.filter(
    content_type__app_label='duyurular',
    codename__in=['add_announcement', 'change_announcement', 'delete_announcement']
)
announcement_group.permissions.set(permissions)

# Test kategorileri
categories = [
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

## Fonksiyonel Test Senaryoları

### Test 1: Duyuru Oluşturma (Admin)
**Amaç**: Admin kullanıcısının duyuru oluşturabilmesini test etme

**Adımlar**:
1. Admin kullanıcısı ile giriş yap
2. `/duyurular/` sayfasına git
3. "Yeni Duyuru" butonuna tıkla
4. Modal form açılsın
5. Formu doldur:
   - Başlık: "Test Duyurusu"
   - Tür: "Genel"
   - Öncelik: "Normal"
   - İçerik: "Bu bir test duyurusudur."
6. "Taslak Kaydet" butonuna tıkla

**Beklenen Sonuç**: 
- Duyuru taslak olarak kaydedilsin
- Başarı mesajı gösterilsin
- Sayfa yenilensin ve duyuru listede görünsün

### Test 2: Duyuru Yayınlama
**Amaç**: Taslak duyurunun yayınlanabilmesini test etme

**Adımlar**:
1. Taslak duyuru üzerinde dropdown menüyü aç
2. "Yayınla" seçeneğine tıkla
3. Onay dialogunu kabul et

**Beklenen Sonuç**:
- Duyuru durumu "Yayında" olsun
- Yayın tarihi otomatik atansın
- Dashboard'da görünür olsun

### Test 3: CKEditor Fonksiyonalitesi
**Amaç**: Zengin metin editörünün çalışmasını test etme

**Adımlar**:
1. Yeni duyuru oluştur
2. İçerik alanında CKEditor'ü kullan:
   - Kalın metin ekle
   - Liste oluştur
   - Link ekle
   - Resim yükle (opsiyonel)
3. Önizlemeyi kontrol et
4. Kaydet ve yayınla

**Beklenen Sonuç**:
- Tüm biçimlendirmeler korunsun
- Önizleme doğru gösterilsin
- Yayınlanan duyuruda formatlar görünsün

### Test 4: Otomatik Arşivleme
**Amaç**: Yayın bitiş tarihi geçen duyuruların otomatik arşivlenmesini test etme

**Adımlar**:
1. Yayın bitiş tarihi geçmiş tarih olan duyuru oluştur
2. Management komutunu çalıştır:
   ```bash
   python manage.py archive_expired_announcements --dry-run
   ```
3. Gerçek arşivleme:
   ```bash
   python manage.py archive_expired_announcements
   ```

**Beklenen Sonuç**:
- Dry-run'da arşivlenecek duyurular listelenmeli
- Gerçek komutta duyurular arşivlenmeli
- Arşivlenen duyurular public listede görünmemeli

### Test 5: Dashboard Entegrasyonu
**Amaç**: Dashboard'da duyuru widget'ının çalışmasını test etme

**Adımlar**:
1. Ana dashboard sayfasına git
2. Duyurular bölümünün yüklenmesini bekle
3. Duyuru sayısını kontrol et
4. Son duyuruların listelendiğini kontrol et
5. Duyuru linklerine tıklayarak detay sayfasına git

**Beklenen Sonuç**:
- Widget AJAX ile yüklenmeli
- Doğru sayılar gösterilmeli
- Linkler çalışmalı

### Test 6: Filtreleme ve Arama
**Amaç**: Duyuru listesinde filtreleme ve arama fonksiyonlarını test etme

**Adımlar**:
1. `/duyurular/` sayfasına git
2. Arama kutusuna "test" yaz ve ara
3. Kategori filtresini kullan
4. Tür filtresini kullan
5. Öncelik filtresini kullan
6. Sıralama seçeneklerini dene

**Beklenen Sonuç**:
- Her filtre doğru sonuçlar döndürmeli
- Arama çalışmalı
- Sıralama işlevsel olmalı

### Test 7: Yetkilendirme
**Amaç**: Kullanıcı yetkilerinin doğru çalıştığını test etme

**Adımlar**:
1. Normal kullanıcı ile giriş yap
2. Duyuru listesine git
3. Admin butonlarının görünmediğini kontrol et
4. Duyuru detayına git
5. Admin aksiyonlarının görünmediğini kontrol et

**Beklenen Sonuç**:
- Normal kullanıcı sadece okuma yapabilmeli
- Admin butonları görünmemeli
- CRUD işlemleri engellenmiş olmalı

## API Test Senaryoları

### Test 8: AJAX Duyuru Oluşturma
**Amaç**: API endpoint'lerinin çalışmasını test etme

**Test Komutu**:
```bash
curl -X POST http://localhost:8000/duyurular/api/announcement/create/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{
    "title": "API Test Duyurusu",
    "content": "Bu API ile oluşturulmuş bir duyurudur.",
    "duyuru_tipi": "general",
    "onem_seviyesi": "normal",
    "action": "publish"
  }'
```

### Test 9: Durum Güncelleme API
**Test Komutu**:
```bash
curl -X POST http://localhost:8000/duyurular/api/announcement/1/status/ \
  -H "Content-Type: application/json" \
  -H "X-CSRFToken: YOUR_CSRF_TOKEN" \
  -d '{"status": "archived"}'
```

## Celery Test Senaryoları

### Test 10: E-posta Bildirimleri
**Amaç**: Celery görevlerinin çalışmasını test etme

**Adımlar**:
1. Celery worker'ı başlat:
   ```bash
   celery -A portall worker -l info
   ```
2. Yeni duyuru oluştur ve yayınla
3. E-posta gönderim loglarını kontrol et

### Test 11: Haftalık Rapor
**Adımlar**:
1. Celery beat'i başlat:
   ```bash
   celery -A portall beat -l info
   ```
2. Manuel olarak haftalık rapor görevini tetikle:
   ```python
   from duyurular.tasks import send_weekly_announcement_report
   send_weekly_announcement_report.delay()
   ```

## Performans Test Senaryoları

### Test 12: Çok Sayıda Duyuru ile Test
**Amaç**: Sistemin performansını test etme

**Veri Oluşturma**:
```python
# Django shell'de çalıştır
from duyurular.models import Announcement, AnnouncementCategory
import random
from django.utils import timezone
from datetime import timedelta

category = AnnouncementCategory.objects.first()

# 1000 test duyurusu oluştur
for i in range(1000):
    Announcement.objects.create(
        title=f"Test Duyurusu {i+1}",
        content=f"Bu {i+1}. test duyurusudur. Lorem ipsum dolor sit amet...",
        category=category,
        duyuru_tipi=random.choice(['general', 'maintenance', 'update']),
        onem_seviyesi=random.choice(['low', 'normal', 'high']),
        status='published',
        published_at=timezone.now() - timedelta(days=random.randint(1, 30))
    )
```

**Test Adımları**:
1. Duyuru listesi sayfasını yükle
2. Sayfa yükleme süresini ölç
3. Filtreleme işlemlerinin hızını test et
4. Pagination'ın çalışmasını kontrol et

## Güvenlik Test Senaryoları

### Test 13: XSS Koruması
**Amaç**: Cross-site scripting saldırılarına karşı korunmayı test etme

**Adımlar**:
1. Duyuru içeriğine script etiketi ekle:
   ```html
   <script>alert('XSS Test')</script>
   ```
2. Duyuruyu kaydet ve görüntüle
3. Script'in çalışmadığını kontrol et

### Test 14: CSRF Koruması
**Amaç**: CSRF token kontrolünü test etme

**Test**:
```bash
# CSRF token olmadan istek gönder
curl -X POST http://localhost:8000/duyurular/api/announcement/create/ \
  -H "Content-Type: application/json" \
  -d '{"title": "CSRF Test"}'
```

**Beklenen Sonuç**: 403 Forbidden hatası alınmalı

## Hata Durumu Test Senaryoları

### Test 15: Geçersiz Veri Testi
**Amaç**: Form validasyonlarını test etme

**Adımlar**:
1. Boş başlık ile duyuru oluşturmaya çalış
2. Geçersiz e-posta formatı ile test et
3. Çok uzun başlık ile test et
4. Geçersiz tarih formatı ile test et

### Test 16: Veritabanı Bağlantı Hatası Simülasyonu
**Amaç**: Hata durumlarında sistem davranışını test etme

**Not**: Bu test staging ortamında yapılmalıdır.

## Sonuç Raporu

Her test senaryosu için:
- ✅ Başarılı
- ❌ Başarısız
- ⚠️ Kısmi başarılı

şeklinde işaretleme yapın ve başarısız testler için detaylı hata raporları oluşturun.

## Otomatik Test Komutları

```bash
# Tüm testleri çalıştır
python manage.py test duyurular

# Belirli test sınıfını çalıştır
python manage.py test duyurular.tests.AnnouncementModelTest

# Coverage raporu ile
coverage run --source='.' manage.py test duyurular
coverage report
coverage html
```
