"""
Certificate Management URLs
"""
from django.urls import path
from . import views

app_name = 'sertifikalar'

urlpatterns = [
    # Dashboard
    path('', views.certificate_dashboard, name='dashboard'),
    
    # KDB Certificates
    path('kdb/', views.KdbCertificateListView.as_view(), name='kdb_list'),
    path('kdb/<int:pk>/', views.KdbCertificateDetailView.as_view(), name='kdb_detail'),
    
    # Java Certificates
    path('java/', views.JavaCertificateListView.as_view(), name='java_list'),
    path('java/<int:pk>/', views.JavaCertificateDetailView.as_view(), name='java_detail'),
    
    # AJAX APIs
    path('api/stats/', views.certificate_stats_api, name='stats_api'),
    path('api/expiring-widget/', views.expiring_certificates_widget, name='expiring_widget'),
]
