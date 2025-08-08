from django.urls import path
from django.contrib.auth import views as auth_views
from . import views

app_name = 'authentication'

urlpatterns = [
    # Login/Logout
    path('login/', views.CustomLoginView.as_view(), name='login'),
    path('logout/', views.CustomLogoutView.as_view(), name='logout'),
    
    # Profile
    path('profile/', views.profile_view, name='profile'),
    
    # Account locked (django-axes)
    path('locked/', views.AccountLockedView.as_view(), name='account_locked'),
    
    # Password reset (disabled for LDAP)
    path('password_reset/', views.password_reset_disabled, name='password_reset'),
    path('password_reset/done/', views.password_reset_disabled, name='password_reset_done'),
    path('reset/<uidb64>/<token>/', views.password_reset_disabled, name='password_reset_confirm'),
    path('reset/done/', views.password_reset_disabled, name='password_reset_complete'),
    
    # Password change (disabled for LDAP)
    path('password_change/', views.password_reset_disabled, name='password_change'),
    path('password_change/done/', views.password_reset_disabled, name='password_change_done'),
    
    # Health check
    path('health/', views.HealthCheckView.as_view(), name='health_check'),
]
