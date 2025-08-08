"""
Django settings for Portall project.
"""

import os
from pathlib import Path
from decouple import config, Csv

# LDAP imports (conditional to avoid errors if not installed)
try:
    import ldap
    from django_auth_ldap.config import LDAPSearch, GroupOfNamesType
    LDAP_AVAILABLE = True
except ImportError:
    LDAP_AVAILABLE = False

# Build paths inside the project like this: BASE_DIR / 'subdir'.
BASE_DIR = Path(__file__).resolve().parent.parent

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = config('SECRET_KEY', default='django-insecure-change-me-in-production')

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = config('DEBUG', default=True, cast=bool)

ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='localhost,127.0.0.1').split(',')

# Application definition
DJANGO_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
]

THIRD_PARTY_APPS = [
    'crispy_forms',
    'crispy_bootstrap5',
    'haystack',
    'rest_framework',
    'django_filters',
    'axes',  # Brute-force protection
    'ckeditor',  # Rich text editor
    'ckeditor_uploader',  # File upload support
]

LOCAL_APPS = [
    'core',
    'dashboard',
    'authentication',
    'envanter',
    'askgt',
    'nobetci',
    'duyurular',
    'linkler',
    'performans',
    'otomasyon',
    'search',
    'sertifikalar',
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'portall.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
                'askgt.context_processors.askgt_categories',
                'askgt.context_processors.askgt_stats',
            ],
        },
    },
]

WSGI_APPLICATION = 'portall.wsgi.application'

# Database
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': config('DB_NAME', default='portall_db'),
        'USER': config('DB_USER', default='portall_user'),
        'PASSWORD': config('DB_PASSWORD', default='password'),
        'HOST': config('DB_HOST', default='localhost'),
        'PORT': config('DB_PORT', default='5432'),
    }
}

# LDAP Authentication Settings (only if LDAP is available and enabled)
if LDAP_AVAILABLE and config('USE_LDAP_AUTH', default=True, cast=bool):
    AUTH_LDAP_SERVER_URI = config('LDAP_SERVER_URI', default='ldap://localhost:389')
    AUTH_LDAP_BIND_DN = config('LDAP_BIND_DN', default='')
    AUTH_LDAP_BIND_PASSWORD = config('LDAP_BIND_PASSWORD', default='')
    
    # LDAP User Search
    AUTH_LDAP_USER_SEARCH = LDAPSearch(
        config('LDAP_USER_SEARCH_BASE', default='ou=users,dc=company,dc=com'),
        ldap.SCOPE_SUBTREE,
        config('LDAP_USER_SEARCH_FILTER', default='(uid=%(user)s)')
    )
    
    # LDAP User Attribute Mapping
    AUTH_LDAP_USER_ATTR_MAP = {
        'first_name': 'givenName',
        'last_name': 'sn',
        'email': 'mail',
    }
    
    # LDAP Group Search and Mapping
    AUTH_LDAP_GROUP_SEARCH = LDAPSearch(
        config('LDAP_GROUP_SEARCH_BASE', default='ou=groups,dc=company,dc=com'),
        ldap.SCOPE_SUBTREE,
        '(objectClass=groupOfNames)'
    )
    AUTH_LDAP_GROUP_TYPE = GroupOfNamesType()
    
    # Mirror LDAP groups to Django groups
    AUTH_LDAP_MIRROR_GROUPS = True
    
    # Map LDAP groups to Django groups and permissions
    AUTH_LDAP_USER_FLAGS_BY_GROUP = {
        'is_active': config('LDAP_ACTIVE_GROUP', default='cn=active,ou=groups,dc=company,dc=com'),
        'is_staff': config('LDAP_STAFF_GROUP', default='cn=staff,ou=groups,dc=company,dc=com'),
        'is_superuser': config('LDAP_ADMIN_GROUP', default='cn=admins,ou=groups,dc=company,dc=com'),
    }
    
    # LDAP Connection Options
    AUTH_LDAP_CONNECTION_OPTIONS = {
        ldap.OPT_DEBUG_LEVEL: 1,
        ldap.OPT_REFERRALS: 0,
    }
    
    # Always update user from LDAP
    AUTH_LDAP_ALWAYS_UPDATE_USER = True
    
    # Create users automatically
    AUTH_LDAP_AUTHORIZE_ALL_USERS = True
    
    # Authentication Backends with LDAP
    AUTHENTICATION_BACKENDS = [
        'django_auth_ldap.backend.LDAPBackend',
        'django.contrib.auth.backends.ModelBackend',  # Fallback for superuser
    ]
else:
    # Standard Django authentication
    AUTHENTICATION_BACKENDS = [
        'django.contrib.auth.backends.ModelBackend',
    ]

# Password validation
if config('USE_LDAP_AUTH', default=True, cast=bool):
    AUTH_PASSWORD_VALIDATORS = []  # Disable for LDAP users
else:
    AUTH_PASSWORD_VALIDATORS = [
        {
            'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
        },
        {
            'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
        },
    ]
AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]

# Internationalization
LANGUAGE_CODE = 'tr-tr'
TIME_ZONE = 'Europe/Istanbul'
USE_I18N = True
USE_TZ = True

# Static files (CSS, JavaScript, Images)
STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_DIRS = [
    BASE_DIR / 'static',
]

# Media files
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Default primary key field type
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# Crispy Forms
CRISPY_ALLOWED_TEMPLATE_PACKS = "bootstrap5"
CRISPY_TEMPLATE_PACK = "bootstrap5"

# Haystack Search Configuration
HAYSTACK_CONNECTIONS = {
    'default': {
        'ENGINE': 'haystack.backends.whoosh_backend.WhooshEngine',
        'PATH': BASE_DIR / 'whoosh_index',
    },
}

# Celery Configuration
CELERY_BROKER_URL = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_RESULT_BACKEND = config('REDIS_URL', default='redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE

# Cache Configuration
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.redis.RedisCache',
        'LOCATION': config('REDIS_URL', default='redis://localhost:6379/1'),
        'OPTIONS': {
            'CLIENT_CLASS': 'django_redis.client.DefaultClient',
        },
        'KEY_PREFIX': 'portall_cache',
        'TIMEOUT': 300,  # 5 dakika default
    }
}

# Performance & Dynatrace Settings
DYNATRACE_API_URL = config('DYNATRACE_API_URL', default='')
DYNATRACE_API_TOKEN = config('DYNATRACE_API_TOKEN', default='')
DYNATRACE_API_TIMEOUT = config('DYNATRACE_API_TIMEOUT', default=30, cast=int)
DYNATRACE_CACHE_TIMEOUT = config('DYNATRACE_CACHE_TIMEOUT', default=120, cast=int)  # 2 dakika

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Günlük sertifika senkronizasyonu (her gün 02:00)
    'daily-certificate-sync': {
        'task': 'sertifikalar.tasks.daily_certificate_sync',
        'schedule': crontab(hour=2, minute=0),
        'options': {'expires': 3600}  # 1 saat içinde çalışmazsa iptal et
    },
    
    # Günlük sertifika süre uyarıları (her gün 08:00)
    'daily-certificate-alerts': {
        'task': 'sertifikalar.tasks.daily_certificate_alerts',
        'schedule': crontab(hour=8, minute=0),
        'options': {'expires': 1800}  # 30 dakika içinde çalışmazsa iptal et
    },
    
    # Haftalık sertifika raporu (her Pazartesi 09:00)
    'weekly-certificate-report': {
        'task': 'sertifikalar.tasks.weekly_certificate_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
        'options': {'expires': 3600}
    },
    
    # Eski bildirimleri temizle (her ay 1. gün 03:00)
    'cleanup-old-notifications': {
        'task': 'sertifikalar.tasks.cleanup_old_notifications',
        'schedule': crontab(hour=3, minute=0, day_of_month=1),
        'options': {'expires': 1800}
    },
    
    # KDB sertifikaları hızlı senkronizasyon (her 6 saatte bir)
    'quick-kdb-sync': {
        'task': 'sertifikalar.tasks.sync_kdb_certificates',
        'schedule': crontab(minute=0, hour='*/6'),
        'kwargs': {'source': 'sql'},  # Sadece SQL kaynağından
        'options': {'expires': 1800}
    },
    
    # Java sertifikaları haftalık senkronizasyon (her Çarşamba 03:30)
    'weekly-java-sync': {
        'task': 'sertifikalar.tasks.sync_java_certificates',
        'schedule': crontab(hour=3, minute=30, day_of_week=3),
        'options': {'expires': 3600}
    },
    
    # Duyurular modülü görevleri
    # Süresi dolmuş duyuruları arşivle (her gün 01:00)
    'archive-expired-announcements': {
        'task': 'duyurular.tasks.archive_expired_announcements',
        'schedule': crontab(hour=1, minute=0),
        'options': {'expires': 1800}
    },
    
    # Günlük duyuru bakımı (her gün 02:30)
    'daily-announcement-maintenance': {
        'task': 'duyurular.tasks.daily_announcement_maintenance',
        'schedule': crontab(hour=2, minute=30),
        'options': {'expires': 3600}
    },
    
    # Haftalık duyuru raporu (her Pazartesi 10:00)
    'weekly-announcement-report': {
        'task': 'duyurular.tasks.weekly_announcement_report',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),
        'options': {'expires': 1800}
    },
}

# Email Configuration
EMAIL_BACKEND = config('EMAIL_BACKEND', default='django.core.mail.backends.console.EmailBackend')
EMAIL_HOST = config('EMAIL_HOST', default='')
EMAIL_PORT = config('EMAIL_PORT', default=587, cast=int)
EMAIL_USE_TLS = config('EMAIL_USE_TLS', default=True, cast=bool)
EMAIL_HOST_USER = config('EMAIL_HOST_USER', default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')

# Session Configuration
SESSION_COOKIE_AGE = 1800  # 30 minutes
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = False
SESSION_COOKIE_SECURE = config('SESSION_COOKIE_SECURE', default=False, cast=bool)
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = 'Lax'

# Django Axes (Brute-force protection) Settings
AXES_ENABLED = True
AXES_FAILURE_LIMIT = 5
AXES_COOLOFF_TIME = 1  # 1 hour
AXES_LOCKOUT_TEMPLATE = 'registration/account_locked.html'
AXES_RESET_ON_SUCCESS = True
AXES_LOCK_OUT_BY_COMBINATION_USER_AND_IP = True
AXES_USE_USER_AGENT = True

# Login/Logout URLs
LOGIN_URL = '/auth/login/'
LOGIN_REDIRECT_URL = '/'
LOGOUT_REDIRECT_URL = '/auth/login/'

# Custom Settings
ANSIBLE_PLAYBOOK_PATH = config('ANSIBLE_PLAYBOOK_PATH', default='/opt/ansible/playbooks')
ANSIBLE_INVENTORY_PATH = config('ANSIBLE_INVENTORY_PATH', default='/opt/ansible/inventory')
MONITORING_API_KEY = config('MONITORING_API_KEY', default='')
MONITORING_API_URL = config('MONITORING_API_URL', default='')

# CKEditor Configuration
CKEDITOR_UPLOAD_PATH = "uploads/"
CKEDITOR_IMAGE_BACKEND = "pillow"
CKEDITOR_JQUERY_URL = '//ajax.googleapis.com/ajax/libs/jquery/2.2.4/jquery.min.js'

CKEDITOR_CONFIGS = {
    'default': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent', '-', 'JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink'],
            ['RemoveFormat', 'Source']
        ],
        'height': 200,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'extraAllowedContent': 'div(*);p(*);span(*);ul(*);ol(*);li(*);a[href,target];strong;em;u;br',
    },
    'announcement': {
        'toolbar': 'Custom',
        'toolbar_Custom': [
            ['Bold', 'Italic', 'Underline', 'Strike'],
            ['NumberedList', 'BulletedList', '-', 'Outdent', 'Indent'],
            ['JustifyLeft', 'JustifyCenter', 'JustifyRight', 'JustifyBlock'],
            ['Link', 'Unlink', 'Anchor'],
            ['Image', 'Table', 'HorizontalRule'],
            ['TextColor', 'BGColor'],
            ['Styles', 'Format', 'Font', 'FontSize'],
            ['RemoveFormat', 'Source', 'Maximize']
        ],
        'height': 300,
        'width': '100%',
        'removePlugins': 'stylesheetparser',
        'allowedContent': True,
        'extraAllowedContent': 'div(*);p(*);span(*);ul(*);ol(*);li(*);a[href,target];strong;em;u;br;img[src,alt,width,height];table(*);tr(*);td(*);th(*);hr',
        'format_tags': 'p;h1;h2;h3;h4;h5;h6;pre;address;div',
    }
}

# Celery Configuration
CELERY_BROKER_URL = os.getenv('CELERY_BROKER_URL', 'redis://localhost:6379/0')
CELERY_RESULT_BACKEND = os.getenv('CELERY_RESULT_BACKEND', 'redis://localhost:6379/0')
CELERY_ACCEPT_CONTENT = ['json']
CELERY_TASK_SERIALIZER = 'json'
CELERY_RESULT_SERIALIZER = 'json'
CELERY_TIMEZONE = TIME_ZONE
CELERY_ENABLE_UTC = True

# Celery Beat Schedule
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    # Duyuru otomatik arşivleme (günlük 01:00)
    'archive-expired-announcements': {
        'task': 'duyurular.tasks.archive_expired_announcements',
        'schedule': crontab(hour=1, minute=0),
    },
    # Duyuru haftalık raporu (Pazartesi 09:00)
    'weekly-announcement-report': {
        'task': 'duyurular.tasks.send_weekly_report',
        'schedule': crontab(hour=9, minute=0, day_of_week=1),
    },
    # Sertifika senkronizasyonu (günlük 02:00)
    'sync-certificates': {
        'task': 'sertifikalar.tasks.sync_all_certificates',
        'schedule': crontab(hour=2, minute=0),
    },
    # Sertifika süre kontrolü (günlük 08:00)
    'check-certificate-expiry': {
        'task': 'sertifikalar.tasks.check_expiring_certificates',
        'schedule': crontab(hour=8, minute=0),
    },
    # Sertifika haftalık raporu (Cuma 17:00)
    'weekly-certificate-report': {
        'task': 'sertifikalar.tasks.send_weekly_report',
        'schedule': crontab(hour=17, minute=0, day_of_week=5),
    },
    # AskGT doküman senkronizasyonu (günlük 03:00)
    'sync-askgt-documents': {
        'task': 'askgt.tasks.sync_documents_from_api',
        'schedule': crontab(hour=3, minute=0),
    },
    # AskGT haftalık istatistik raporu (Pazartesi 10:00)
    'askgt-weekly-stats': {
        'task': 'askgt.tasks.send_weekly_stats_report',
        'schedule': crontab(hour=10, minute=0, day_of_week=1),
    },
}

# Security Settings
if not DEBUG:
    SECURE_BROWSER_XSS_FILTER = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_SECONDS = 31536000
    SECURE_REDIRECT_EXEMPT = []
    SECURE_SSL_REDIRECT = True
    CSRF_COOKIE_SECURE = True
