from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'dashboard'

urlpatterns = [
    # Main dashboard
    path('', views.DashboardHomeView.as_view(), name='home'),
    
    # API endpoints for asynchronous data loading
    path('api/data/', views.dashboard_api_data, name='api_data'),
    path('api/performance-chart/', views.performance_chart_data, name='performance_chart_data'),
    path('api/inventory-health/', views.inventory_health_data, name='inventory_health_data'),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    path('password_change/', auth_views.PasswordChangeView.as_view(template_name='registration/password_change.html'), name='password_change'),
    path('password_change/done/', auth_views.PasswordChangeDoneView.as_view(template_name='registration/password_change_done.html'), name='password_change_done'),
]
