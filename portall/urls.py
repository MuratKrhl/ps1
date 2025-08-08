"""
URL configuration for Portall project.
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('auth/', include('authentication.urls')),
    path('', include('dashboard.urls')),
    path('envanter/', include('envanter.urls')),
    path('askgt/', include('askgt.urls')),
    path('nobetci/', include('nobetci.urls')),
    path('duyurular/', include('duyurular.urls')),
    path('linkler/', include('linkler.urls')),
    path('performans/', include('performans.urls')),
    path('otomasyon/', include('otomasyon.urls')),
    path('sertifikalar/', include('sertifikalar.urls')),
    path('search/', include('haystack.urls')),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
