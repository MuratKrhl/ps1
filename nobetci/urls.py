from django.urls import path
from . import views

app_name = 'nobetci'

urlpatterns = [
    # Dashboard
    path('', views.duty_dashboard, name='dashboard'),
    
    # Duty schedules
    path('liste/', views.duty_list, name='duty_list'),
    path('takvim/', views.duty_calendar, name='duty_calendar'),
    path('nobet/<int:duty_id>/', views.duty_detail, name='duty_detail'),
    
    # Personal duties
    path('nobetlerim/', views.my_duties, name='my_duties'),
    
    # Emergency contacts
    path('acil-durum/', views.emergency_contacts, name='emergency_contacts'),
    
    # Simple duty schedule (external sync)
    path('nobetci-listesi/', views.nobetci_list, name='nobetci_list'),
    path('nobetci/<int:pk>/', views.nobetci_detail, name='nobetci_detail'),
    path('api/current-duty/', views.current_duty_api, name='current_duty_api'),
]
