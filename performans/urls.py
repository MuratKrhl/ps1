from django.urls import path
from . import views

app_name = 'performans'

urlpatterns = [
    # Dashboard
    path('', views.performans_dashboard, name='dashboard'),
    
    # Server performance
    path('sunucular/', views.server_performance, name='server_performance'),
    path('sunucu/<int:server_id>/', views.server_detail, name='server_detail'),
    
    # Application performance
    path('uygulamalar/', views.application_performance, name='application_performance'),
    path('uygulama/<int:application_id>/', views.application_detail, name='application_detail'),
    
    # Reports
    path('raporlar/', views.reports, name='reports'),
    path('rapor/<int:report_id>/', views.report_detail, name='report_detail'),
    
    # Alerts
    path('uyarilar/', views.alerts, name='alerts'),
    path('uyari/<int:alert_id>/', views.alert_detail, name='alert_detail'),
    
    # =============================================================================
    # DYNATRACE PERFORMANCE MONITORING
    # =============================================================================
    
    # Performance Overview (All Technologies)
    path('overview/', views.PerformanceOverviewView.as_view(), name='performance_overview'),
    
    # Technology-specific Dashboards
    path('technology/<str:technology>/', views.TechnologyDashboardView.as_view(), name='technology_dashboard'),
    
    # =============================================================================
    # DYNATRACE API ENDPOINTS
    # =============================================================================
    
    # Technology Metrics API
    path('api/technology/<str:technology>/metrics/', views.api_technology_metrics, name='api_technology_metrics'),
    
    # Technology Entities API
    path('api/technology/<str:technology>/entities/', views.api_technology_entities, name='api_technology_entities'),
    
    # Technology Problems API
    path('api/technology/<str:technology>/problems/', views.api_technology_problems, name='api_technology_problems'),
    
    # Performance Overview API
    path('api/overview/', views.api_performance_overview, name='api_performance_overview'),
]
