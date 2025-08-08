"""
Certificate Management Models
"""
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from datetime import datetime, timedelta
import hashlib


class BaseCertificate(models.Model):
    """Abstract base model for all certificate types"""
    
    # Certificate Identity
    common_name = models.CharField(max_length=255, verbose_name='Common Name')
    serial_number = models.CharField(max_length=100, verbose_name='Serial Number', unique=True)
    issuer = models.CharField(max_length=500, verbose_name='Issuer')
    subject = models.CharField(max_length=500, verbose_name='Subject')
    
    # Validity Dates
    valid_from = models.DateTimeField(verbose_name='Valid From')
    valid_to = models.DateTimeField(verbose_name='Valid To', db_index=True)
    
    # Certificate Details
    signature_algorithm = models.CharField(max_length=100, blank=True, verbose_name='Signature Algorithm')
    key_size = models.IntegerField(null=True, blank=True, verbose_name='Key Size')
    fingerprint_sha1 = models.CharField(max_length=59, blank=True, verbose_name='SHA1 Fingerprint')
    fingerprint_sha256 = models.CharField(max_length=95, blank=True, verbose_name='SHA256 Fingerprint')
    
    # Subject Alternative Names
    san_dns = models.TextField(blank=True, verbose_name='DNS Names', help_text='Comma-separated DNS names')
    san_ip = models.TextField(blank=True, verbose_name='IP Addresses', help_text='Comma-separated IP addresses')
    
    # Location and Usage
    server_hostname = models.CharField(max_length=255, blank=True, verbose_name='Server Hostname')
    application_name = models.CharField(max_length=255, blank=True, verbose_name='Application Name')
    environment = models.CharField(max_length=50, blank=True, verbose_name='Environment')
    usage_purpose = models.CharField(max_length=200, blank=True, verbose_name='Usage Purpose')
    
    # Management Fields
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    is_monitored = models.BooleanField(default=True, verbose_name='Monitor Expiry')
    last_sync = models.DateTimeField(auto_now=True, verbose_name='Last Sync')
    sync_source = models.CharField(max_length=100, blank=True, verbose_name='Sync Source')
    external_id = models.CharField(max_length=100, blank=True, verbose_name='External ID')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        abstract = True
        ordering = ['valid_to', 'common_name']
    
    def __str__(self):
        return f"{self.common_name} (expires: {self.valid_to.strftime('%Y-%m-%d')})"
    
    @property
    def days_until_expiry(self):
        """Calculate days until certificate expires"""
        if self.valid_to:
            delta = self.valid_to.date() - timezone.now().date()
            return delta.days
        return None
    
    @property
    def is_expired(self):
        """Check if certificate is expired"""
        return self.valid_to < timezone.now() if self.valid_to else False
    
    @property
    def is_expiring_soon(self):
        """Check if certificate expires within 30 days"""
        days_left = self.days_until_expiry
        return days_left is not None and days_left <= 30
    
    @property
    def is_critical_expiry(self):
        """Check if certificate expires within 7 days"""
        days_left = self.days_until_expiry
        return days_left is not None and days_left <= 7
    
    def get_expiry_status_class(self):
        """Get Bootstrap badge class for expiry status"""
        if self.is_expired:
            return 'bg-danger'
        elif self.is_critical_expiry:
            return 'bg-danger'
        elif self.is_expiring_soon:
            return 'bg-warning'
        else:
            return 'bg-success'
    
    def get_expiry_status_text(self):
        """Get human-readable expiry status"""
        if self.is_expired:
            return 'Expired'
        elif self.is_critical_expiry:
            return 'Critical'
        elif self.is_expiring_soon:
            return 'Expiring Soon'
        else:
            return 'Valid'
    
    def get_san_dns_list(self):
        """Get list of DNS names from SAN"""
        if self.san_dns:
            return [name.strip() for name in self.san_dns.split(',') if name.strip()]
        return []
    
    def get_san_ip_list(self):
        """Get list of IP addresses from SAN"""
        if self.san_ip:
            return [ip.strip() for ip in self.san_ip.split(',') if ip.strip()]
        return []


class KdbCertificate(BaseCertificate):
    """KDB (Key Database) Certificate Model"""
    
    # KDB Specific Fields
    kdb_file_path = models.CharField(max_length=500, blank=True, verbose_name='KDB File Path')
    kdb_label = models.CharField(max_length=255, blank=True, verbose_name='KDB Label')
    password_stash_file = models.CharField(max_length=500, blank=True, verbose_name='Password Stash File')
    
    # IBM HTTP Server / WebSphere specific
    ihs_instance = models.CharField(max_length=100, blank=True, verbose_name='IHS Instance')
    websphere_cell = models.CharField(max_length=100, blank=True, verbose_name='WebSphere Cell')
    websphere_node = models.CharField(max_length=100, blank=True, verbose_name='WebSphere Node')
    
    # Certificate Chain
    has_intermediate_ca = models.BooleanField(default=False, verbose_name='Has Intermediate CA')
    ca_chain_length = models.IntegerField(default=0, verbose_name='CA Chain Length')
    
    # AppViewX Integration
    appviewx_id = models.CharField(max_length=100, blank=True, verbose_name='AppViewX ID')
    appviewx_status = models.CharField(max_length=50, blank=True, verbose_name='AppViewX Status')
    
    class Meta:
        verbose_name = 'KDB Certificate'
        verbose_name_plural = 'KDB Certificates'
        db_table = 'sertifikalar_kdb_certificate'
        indexes = [
            models.Index(fields=['valid_to', 'is_active']),
            models.Index(fields=['server_hostname', 'application_name']),
            models.Index(fields=['kdb_label']),
        ]
    
    def get_certificate_type(self):
        return 'KDB'


class JavaCertificate(BaseCertificate):
    """Java KeyStore Certificate Model"""
    
    # Java Specific Fields
    keystore_path = models.CharField(max_length=500, blank=True, verbose_name='KeyStore Path')
    keystore_type = models.CharField(
        max_length=20, 
        choices=[
            ('JKS', 'Java KeyStore (JKS)'),
            ('PKCS12', 'PKCS#12'),
            ('JCEKS', 'Java Cryptography Extension KeyStore'),
        ],
        default='JKS',
        verbose_name='KeyStore Type'
    )
    alias_name = models.CharField(max_length=255, blank=True, verbose_name='Alias Name')
    
    # Java Application Details
    java_application = models.CharField(max_length=255, blank=True, verbose_name='Java Application')
    jvm_instance = models.CharField(max_length=100, blank=True, verbose_name='JVM Instance')
    application_server = models.CharField(
        max_length=50,
        choices=[
            ('tomcat', 'Apache Tomcat'),
            ('jetty', 'Eclipse Jetty'),
            ('wildfly', 'WildFly'),
            ('websphere', 'IBM WebSphere'),
            ('weblogic', 'Oracle WebLogic'),
            ('other', 'Other'),
        ],
        blank=True,
        verbose_name='Application Server'
    )
    
    # Certificate Usage in Java
    is_client_auth = models.BooleanField(default=False, verbose_name='Client Authentication')
    is_server_auth = models.BooleanField(default=True, verbose_name='Server Authentication')
    is_code_signing = models.BooleanField(default=False, verbose_name='Code Signing')
    
    # Trust Store Information
    truststore_path = models.CharField(max_length=500, blank=True, verbose_name='TrustStore Path')
    is_in_truststore = models.BooleanField(default=False, verbose_name='In TrustStore')
    
    class Meta:
        verbose_name = 'Java Certificate'
        verbose_name_plural = 'Java Certificates'
        db_table = 'sertifikalar_java_certificate'
        indexes = [
            models.Index(fields=['valid_to', 'is_active']),
            models.Index(fields=['server_hostname', 'java_application']),
            models.Index(fields=['alias_name']),
            models.Index(fields=['keystore_type']),
        ]
    
    def get_certificate_type(self):
        return 'Java'


class CertificateAlert(models.Model):
    """Certificate expiry alerts and notifications"""
    
    ALERT_TYPES = [
        ('90_days', '90 Days Before Expiry'),
        ('60_days', '60 Days Before Expiry'),
        ('30_days', '30 Days Before Expiry'),
        ('15_days', '15 Days Before Expiry'),
        ('7_days', '7 Days Before Expiry'),
        ('1_day', '1 Day Before Expiry'),
        ('expired', 'Certificate Expired'),
    ]
    
    # Alert Configuration
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, verbose_name='Alert Type')
    is_active = models.BooleanField(default=True, verbose_name='Is Active')
    
    # Recipients
    email_recipients = models.TextField(
        verbose_name='Email Recipients',
        help_text='Comma-separated email addresses'
    )
    
    # Email Template
    email_subject_template = models.CharField(
        max_length=255,
        default='Certificate Expiry Alert: {common_name}',
        verbose_name='Email Subject Template'
    )
    email_body_template = models.TextField(
        default='''
Certificate expiry notification:

Certificate: {common_name}
Serial Number: {serial_number}
Server: {server_hostname}
Application: {application_name}
Expires: {valid_to}
Days Remaining: {days_until_expiry}

Please take necessary action to renew this certificate.
        ''',
        verbose_name='Email Body Template'
    )
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    
    class Meta:
        verbose_name = 'Certificate Alert'
        verbose_name_plural = 'Certificate Alerts'
        unique_together = ['alert_type']
    
    def __str__(self):
        return f"Alert: {self.get_alert_type_display()}"
    
    def get_recipient_list(self):
        """Get list of email recipients"""
        if self.email_recipients:
            return [email.strip() for email in self.email_recipients.split(',') if email.strip()]
        return []


class CertificateNotification(models.Model):
    """Log of sent certificate notifications"""
    
    # Certificate Reference (using generic foreign key for both types)
    certificate_type = models.CharField(
        max_length=20,
        choices=[('kdb', 'KDB Certificate'), ('java', 'Java Certificate')],
        verbose_name='Certificate Type'
    )
    certificate_id = models.PositiveIntegerField(verbose_name='Certificate ID')
    certificate_common_name = models.CharField(max_length=255, verbose_name='Certificate CN')
    
    # Notification Details
    alert_type = models.CharField(max_length=20, choices=CertificateAlert.ALERT_TYPES)
    sent_to = models.TextField(verbose_name='Sent To', help_text='Comma-separated email addresses')
    email_subject = models.CharField(max_length=255, verbose_name='Email Subject')
    
    # Status
    is_sent = models.BooleanField(default=False, verbose_name='Is Sent')
    sent_at = models.DateTimeField(null=True, blank=True, verbose_name='Sent At')
    error_message = models.TextField(blank=True, verbose_name='Error Message')
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        verbose_name = 'Certificate Notification'
        verbose_name_plural = 'Certificate Notifications'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['certificate_type', 'certificate_id']),
            models.Index(fields=['alert_type', 'is_sent']),
            models.Index(fields=['sent_at']),
        ]
    
    def __str__(self):
        return f"Notification: {self.certificate_common_name} - {self.get_alert_type_display()}"
