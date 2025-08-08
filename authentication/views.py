from django.contrib.auth import views as auth_views
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import render, redirect
from django.urls import reverse_lazy
from django.views.generic import TemplateView
from django.contrib.auth import logout
from django.http import HttpResponseRedirect
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class CustomLoginView(auth_views.LoginView):
    """
    Custom login view with Soft UI theme integration
    """
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def get_success_url(self):
        """Redirect to dashboard after successful login"""
        return reverse_lazy('dashboard:home')
    
    def form_valid(self, form):
        """Log successful login attempts"""
        logger.info(f"Successful login for user: {form.get_user().username}")
        messages.success(self.request, f'Hoş geldiniz, {form.get_user().get_full_name() or form.get_user().username}!')
        return super().form_valid(form)
    
    def form_invalid(self, form):
        """Log failed login attempts"""
        username = form.cleaned_data.get('username', 'Unknown')
        logger.warning(f"Failed login attempt for username: {username} from IP: {self.get_client_ip()}")
        messages.error(self.request, 'Kullanıcı adı veya şifre hatalı.')
        return super().form_invalid(form)
    
    def get_client_ip(self):
        """Get client IP address"""
        x_forwarded_for = self.request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = self.request.META.get('REMOTE_ADDR')
        return ip


class CustomLogoutView(auth_views.LogoutView):
    """
    Custom logout view
    """
    next_page = reverse_lazy('authentication:login')
    
    def dispatch(self, request, *args, **kwargs):
        """Log logout attempts"""
        if request.user.is_authenticated:
            logger.info(f"User logout: {request.user.username}")
            messages.info(request, 'Başarıyla çıkış yaptınız.')
        return super().dispatch(request, *args, **kwargs)


class AccountLockedView(TemplateView):
    """
    Account locked view for django-axes
    """
    template_name = 'registration/account_locked.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update({
            'cooloff_time': getattr(settings, 'AXES_COOLOFF_TIME', 1),
            'failure_limit': getattr(settings, 'AXES_FAILURE_LIMIT', 5),
        })
        return context


@login_required
def profile_view(request):
    """
    User profile view
    """
    context = {
        'user': request.user,
        'ldap_enabled': getattr(settings, 'PORTALL_SETTINGS', {}).get('LDAP_ENABLED', False),
    }
    return render(request, 'registration/profile.html', context)


def password_reset_disabled(request):
    """
    Password reset disabled view for LDAP users
    """
    messages.warning(request, 'Şifre sıfırlama işlemi LDAP kullanıcıları için devre dışıdır. IT departmanı ile iletişime geçin.')
    return redirect('authentication:login')


class HealthCheckView(TemplateView):
    """
    Health check view for authentication system
    """
    template_name = 'registration/health_check.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Check LDAP availability
        ldap_status = 'disabled'
        if hasattr(settings, 'AUTH_LDAP_SERVER_URI'):
            try:
                import ldap
                ldap_status = 'enabled'
            except ImportError:
                ldap_status = 'error'
        
        # Check Axes status
        axes_status = 'enabled' if getattr(settings, 'AXES_ENABLED', False) else 'disabled'
        
        context.update({
            'ldap_status': ldap_status,
            'axes_status': axes_status,
            'session_timeout': getattr(settings, 'SESSION_COOKIE_AGE', 1800) // 60,  # minutes
            'authentication_backends': getattr(settings, 'AUTHENTICATION_BACKENDS', []),
        })
        return context
