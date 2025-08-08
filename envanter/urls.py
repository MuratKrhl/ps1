from django.urls import path
from . import views

app_name = 'envanter'

urlpatterns = [
    # Dashboard
    path('', views.envanter_dashboard, name='dashboard'),
    
    # Modern Inventory Views (Class-Based)
    path('liste/', views.EnvanterListView.as_view(), name='inventory_list'),
    
    # Server URLs (Function-Based - Legacy)
    path('sunucular/', views.server_list, name='server_list'),
    path('sunucular/<int:server_id>/', views.server_detail, name='server_detail'),
    
    # Application URLs (Mixed - Function + Class-Based)
    path('uygulamalar/', views.application_list, name='application_list'),
    path('uygulamalar/<int:pk>/', views.ApplicationDetailView.as_view(), name='application_detail'),
    path('uygulamalar/yeni/', views.ApplicationCreateView.as_view(), name='application_create'),
    path('uygulamalar/<int:pk>/duzenle/', views.ApplicationUpdateView.as_view(), name='application_update'),
    path('uygulamalar/<int:pk>/sil/', views.ApplicationDeleteView.as_view(), name='application_delete'),
    
    # Database URLs (Function-Based - Legacy)
    path('veritabanlari/', views.database_list, name='database_list'),
    path('veritabanlari/<int:database_id>/', views.database_detail, name='database_detail'),
    
    # AJAX Endpoints
    path('ajax/uygulama/<int:pk>/saglik-kontrol/', views.application_health_check, name='application_health_check'),
]
