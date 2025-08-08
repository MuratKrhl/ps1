"""
Certificate Management Admin
"""
from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import KdbCertificate, JavaCertificate, CertificateAlert, CertificateNotification


@admin.register(KdbCertificate)
class KdbCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'common_name', 'server_hostname', 'application_name', 
        'environment', 'valid_to_colored', 'days_until_expiry_display',
        'is_active', 'last_sync'
    ]
    list_filter = [
        'environment', 'is_active', 'is_monitored', 
        'has_intermediate_ca', 'appviewx_status', 'valid_to'
    ]
    search_fields = [
        'common_name', 'server_hostname', 'application_name',
        'serial_number', 'kdb_label', 'issuer'
    ]
    readonly_fields = [
        'serial_number', 'fingerprint_sha1', 'fingerprint_sha256',
        'created_at', 'updated_at', 'last_sync'
    ]
    fieldsets = (
        ('Certificate Identity', {
            'fields': ('common_name', 'serial_number', 'issuer', 'subject')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('KDB Specific', {
            'fields': ('kdb_file_path', 'kdb_label', 'password_stash_file',
                      'ihs_instance', 'websphere_cell', 'websphere_node')
        }),
        ('Location & Usage', {
            'fields': ('server_hostname', 'application_name', 'environment', 'usage_purpose')
        }),
        ('Certificate Details', {
            'fields': ('signature_algorithm', 'key_size', 'fingerprint_sha1', 'fingerprint_sha256')
        }),
        ('Subject Alternative Names', {
            'fields': ('san_dns', 'san_ip')
        }),
        ('AppViewX Integration', {
            'fields': ('appviewx_id', 'appviewx_status')
        }),
        ('Management', {
            'fields': ('is_active', 'is_monitored', 'sync_source', 'external_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_sync', 'created_by')
        }),
    )
    ordering = ['valid_to', 'common_name']
    date_hierarchy = 'valid_to'
    
    def valid_to_colored(self, obj):
        """Display valid_to with color coding"""
        if obj.is_expired:
            color = 'red'
            icon = '❌'
        elif obj.is_critical_expiry:
            color = 'red'
            icon = '⚠️'
        elif obj.is_expiring_soon:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'green'
            icon = '✅'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.valid_to.strftime('%Y-%m-%d')
        )
    valid_to_colored.short_description = 'Valid To'
    valid_to_colored.admin_order_field = 'valid_to'
    
    def days_until_expiry_display(self, obj):
        """Display days until expiry with color coding"""
        days = obj.days_until_expiry
        if days is None:
            return '-'
        
        if days < 0:
            return format_html('<span style="color: red;">Expired {} days ago</span>', abs(days))
        elif days <= 7:
            return format_html('<span style="color: red;">{} days</span>', days)
        elif days <= 30:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    
    days_until_expiry_display.short_description = 'Days Until Expiry'


@admin.register(JavaCertificate)
class JavaCertificateAdmin(admin.ModelAdmin):
    list_display = [
        'common_name', 'server_hostname', 'java_application',
        'keystore_type', 'valid_to_colored', 'days_until_expiry_display',
        'is_active', 'last_sync'
    ]
    list_filter = [
        'environment', 'keystore_type', 'application_server',
        'is_active', 'is_monitored', 'is_client_auth', 'is_server_auth',
        'is_code_signing', 'valid_to'
    ]
    search_fields = [
        'common_name', 'server_hostname', 'java_application',
        'serial_number', 'alias_name', 'issuer'
    ]
    readonly_fields = [
        'serial_number', 'fingerprint_sha1', 'fingerprint_sha256',
        'created_at', 'updated_at', 'last_sync'
    ]
    fieldsets = (
        ('Certificate Identity', {
            'fields': ('common_name', 'serial_number', 'issuer', 'subject')
        }),
        ('Validity', {
            'fields': ('valid_from', 'valid_to')
        }),
        ('Java Specific', {
            'fields': ('keystore_path', 'keystore_type', 'alias_name',
                      'java_application', 'jvm_instance', 'application_server')
        }),
        ('Certificate Usage', {
            'fields': ('is_client_auth', 'is_server_auth', 'is_code_signing')
        }),
        ('Trust Store', {
            'fields': ('truststore_path', 'is_in_truststore')
        }),
        ('Location & Usage', {
            'fields': ('server_hostname', 'application_name', 'environment', 'usage_purpose')
        }),
        ('Certificate Details', {
            'fields': ('signature_algorithm', 'key_size', 'fingerprint_sha1', 'fingerprint_sha256')
        }),
        ('Subject Alternative Names', {
            'fields': ('san_dns', 'san_ip')
        }),
        ('Management', {
            'fields': ('is_active', 'is_monitored', 'sync_source', 'external_id')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'last_sync', 'created_by')
        }),
    )
    ordering = ['valid_to', 'common_name']
    date_hierarchy = 'valid_to'
    
    def valid_to_colored(self, obj):
        """Display valid_to with color coding"""
        if obj.is_expired:
            color = 'red'
            icon = '❌'
        elif obj.is_critical_expiry:
            color = 'red'
            icon = '⚠️'
        elif obj.is_expiring_soon:
            color = 'orange'
            icon = '⚠️'
        else:
            color = 'green'
            icon = '✅'
        
        return format_html(
            '<span style="color: {};">{} {}</span>',
            color, icon, obj.valid_to.strftime('%Y-%m-%d')
        )
    valid_to_colored.short_description = 'Valid To'
    valid_to_colored.admin_order_field = 'valid_to'
    
    def days_until_expiry_display(self, obj):
        """Display days until expiry with color coding"""
        days = obj.days_until_expiry
        if days is None:
            return '-'
        
        if days < 0:
            return format_html('<span style="color: red;">Expired {} days ago</span>', abs(days))
        elif days <= 7:
            return format_html('<span style="color: red;">{} days</span>', days)
        elif days <= 30:
            return format_html('<span style="color: orange;">{} days</span>', days)
        else:
            return format_html('<span style="color: green;">{} days</span>', days)
    
    days_until_expiry_display.short_description = 'Days Until Expiry'


@admin.register(CertificateAlert)
class CertificateAlertAdmin(admin.ModelAdmin):
    list_display = ['alert_type', 'is_active', 'recipient_count', 'created_at']
    list_filter = ['alert_type', 'is_active']
    search_fields = ['email_recipients']
    fieldsets = (
        ('Alert Configuration', {
            'fields': ('alert_type', 'is_active')
        }),
        ('Recipients', {
            'fields': ('email_recipients',)
        }),
        ('Email Template', {
            'fields': ('email_subject_template', 'email_body_template')
        }),
        ('Metadata', {
            'fields': ('created_at', 'updated_at', 'created_by')
        }),
    )
    readonly_fields = ['created_at', 'updated_at']
    
    def recipient_count(self, obj):
        """Display number of email recipients"""
        return len(obj.get_recipient_list())
    recipient_count.short_description = 'Recipients'


@admin.register(CertificateNotification)
class CertificateNotificationAdmin(admin.ModelAdmin):
    list_display = [
        'certificate_common_name', 'certificate_type', 'alert_type',
        'is_sent', 'sent_at', 'created_at'
    ]
    list_filter = [
        'certificate_type', 'alert_type', 'is_sent', 'sent_at'
    ]
    search_fields = [
        'certificate_common_name', 'sent_to', 'email_subject'
    ]
    readonly_fields = [
        'certificate_type', 'certificate_id', 'certificate_common_name',
        'alert_type', 'sent_to', 'email_subject', 'is_sent', 'sent_at',
        'error_message', 'created_at'
    ]
    date_hierarchy = 'created_at'
    ordering = ['-created_at']
    
    def has_add_permission(self, request):
        """Disable manual addition of notifications"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Disable editing of notifications"""
        return False
