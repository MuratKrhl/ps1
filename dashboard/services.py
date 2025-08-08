from django.db.models import Count, Q, Avg
from django.utils import timezone
from datetime import timedelta
from envanter.models import Server, Application, Database
from askgt.models import Question, Answer, AskGTDocument
from nobetci.models import DutySchedule, Nobetci
from duyurular.models import Announcement, MaintenanceNotice, SystemStatus
from linkler.models import Link, LinkClick
from performans.models import ServerMetric, ApplicationMetric, Alert
from otomasyon.models import PlaybookExecution, AutomationSchedule
try:
    from sertifikalar.models import KdbCertificate, JavaCertificate
    CERTIFICATES_AVAILABLE = True
except ImportError:
    CERTIFICATES_AVAILABLE = False
import json


class DashboardDataService:
    """Dashboard için veri toplama servisi"""
    
    @staticmethod
    def get_system_overview():
        """Sistem genel bakış"""
        now = timezone.now()
        
        # Envanter istatistikleri
        total_servers = Server.objects.count()
        active_servers = Server.objects.filter(status='active').count()
        total_applications = Application.objects.count()
        total_databases = Database.objects.count()
        
        # Son 24 saatte eklenen kayıtlar
        yesterday = now - timedelta(days=1)
        new_servers = Server.objects.filter(created_at__gte=yesterday).count()
        new_applications = Application.objects.filter(created_at__gte=yesterday).count()
        
        return {
            'inventory': {
                'total_servers': total_servers,
                'active_servers': active_servers,
                'server_utilization': round((active_servers / total_servers * 100) if total_servers > 0 else 0, 1),
                'total_applications': total_applications,
                'total_databases': total_databases,
                'new_servers_24h': new_servers,
                'new_applications_24h': new_applications
            }
        }
    
    @staticmethod
    def get_knowledge_base_stats():
        """Bilgi bankası istatistikleri"""
        now = timezone.now()
        last_week = now - timedelta(days=7)
        last_month = now - timedelta(days=30)
        
        # Genel istatistikler
        total_questions = Question.objects.count()
        answered_questions = Question.objects.filter(answers__isnull=False).distinct().count()
        total_answers = Answer.objects.count()
        
        # Son aktiviteler
        new_questions_week = Question.objects.filter(created_at__gte=last_week).count()
        new_answers_week = Answer.objects.filter(created_at__gte=last_week).count()
        
        # Popüler sorular (son ay)
        popular_questions = Question.objects.filter(
            created_at__gte=last_month
        ).order_by('-view_count')[:5]
        
        # Cevap oranı
        answer_rate = round((answered_questions / total_questions * 100) if total_questions > 0 else 0, 1)
        
        return {
            'knowledge_base': {
                'total_questions': total_questions,
                'total_answers': total_answers,
                'answer_rate': answer_rate,
                'new_questions_week': new_questions_week,
                'new_answers_week': new_answers_week,
                'popular_questions': [
                    {
                        'id': q.id,
                        'title': q.title,
                        'view_count': q.view_count,
                        'answer_count': q.answers.count()
                    } for q in popular_questions
                ]
            }
        }
    
    @staticmethod
    def get_duty_schedule_info():
        """Nöbet programı bilgileri"""
        now = timezone.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        
        # Bugünkü nöbetçiler
        today_duties = DutySchedule.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).select_related('user', 'duty_type')
        
        # Yarınki nöbetçiler
        tomorrow_duties = DutySchedule.objects.filter(
            start_date__lte=tomorrow,
            end_date__gte=tomorrow
        ).select_related('user', 'duty_type')
        
        # Gelecek hafta başlayacak nöbetler
        upcoming_duties = DutySchedule.objects.filter(
            start_date__range=[today, next_week]
        ).select_related('user', 'duty_type').order_by('start_date')[:5]
        
        return {
            'duty_schedule': {
                'today_duties': [
                    {
                        'user': duty.user.get_full_name() or duty.user.username,
                        'duty_type': duty.duty_type.name,
                        'start_time': duty.start_time,
                        'end_time': duty.end_time
                    } for duty in today_duties
                ],
                'tomorrow_duties': [
                    {
                        'user': duty.user.get_full_name() or duty.user.username,
                        'duty_type': duty.duty_type.name,
                        'start_time': duty.start_time,
                        'end_time': duty.end_time
                    } for duty in tomorrow_duties
                ],
                'upcoming_duties': [
                    {
                        'user': duty.user.get_full_name() or duty.user.username,
                        'duty_type': duty.duty_type.name,
                        'start_date': duty.start_date,
                        'end_date': duty.end_date
                    } for duty in upcoming_duties
                ]
            }
        }
    
    @staticmethod
    def get_announcements_summary():
        """Duyuru özeti"""
        now = timezone.now()
        
        # Aktif duyurular
        active_announcements = Announcement.objects.filter(
            Q(expiry_date__isnull=True) | Q(expiry_date__gt=now),
            is_active=True
        )
        
        # Önemli duyurular
        important_announcements = active_announcements.filter(is_important=True)[:3]
        
        # Sabitlenmiş duyurular
        pinned_announcements = active_announcements.filter(is_pinned=True)[:3]
        
        # Son duyurular
        recent_announcements = active_announcements.order_by('-created_at')[:5]
        
        return {
            'announcements': {
                'total_active': active_announcements.count(),
                'important_count': important_announcements.count(),
                'pinned_count': pinned_announcements.filter(is_pinned=True).count(),
                'important_announcements': [
                    {
                        'id': ann.id,
                        'title': ann.title,
                        'category': ann.category.name,
                        'created_at': ann.created_at,
                        'priority': ann.get_priority_display()
                    } for ann in important_announcements
                ],
                'recent_announcements': [
                    {
                        'id': ann.id,
                        'title': ann.title,
                        'category': ann.category.name,
                        'created_at': ann.created_at,
                        'view_count': ann.view_count
                    } for ann in recent_announcements
                ]
            }
        }
    
    @staticmethod
    def get_system_status():
        """Sistem durumu"""
        # Sistem durumları
        system_statuses = SystemStatus.objects.all()
        
        # Bakım bildirimleri
        now = timezone.now()
        active_maintenances = MaintenanceNotice.objects.filter(
            status__in=['scheduled', 'in_progress'],
            start_time__gte=now - timedelta(hours=24)
        )
        
        # Durum özeti
        operational_count = system_statuses.filter(status='operational').count()
        warning_count = system_statuses.filter(status='warning').count()
        critical_count = system_statuses.filter(status='critical').count()
        
        return {
            'system_status': {
                'operational_count': operational_count,
                'warning_count': warning_count,
                'critical_count': critical_count,
                'total_systems': system_statuses.count(),
                'active_maintenances': [
                    {
                        'id': maint.id,
                        'title': maint.title,
                        'start_time': maint.start_time,
                        'end_time': maint.end_time,
                        'status': maint.get_status_display(),
                        'impact_level': maint.get_impact_level_display()
                    } for maint in active_maintenances
                ],
                'system_list': [
                    {
                        'name': sys.system_name,
                        'status': sys.get_status_display(),
                        'last_check': sys.last_check,
                        'description': sys.description[:100] if sys.description else ''
                    } for sys in system_statuses
                ]
            }
        }
    
    @staticmethod
    def get_automation_stats():
        """Otomasyon istatistikleri"""
        now = timezone.now()
        last_24h = now - timedelta(days=1)
        last_week = now - timedelta(days=7)
        
        # Çalıştırma istatistikleri
        total_executions = PlaybookExecution.objects.count()
        executions_24h = PlaybookExecution.objects.filter(created_at__gte=last_24h).count()
        executions_week = PlaybookExecution.objects.filter(created_at__gte=last_week).count()
        
        # Başarı oranları
        successful_executions = PlaybookExecution.objects.filter(
            status='completed', return_code=0
        ).count()
        success_rate = round((successful_executions / total_executions * 100) if total_executions > 0 else 0, 1)
        
        # Programlı görevler
        active_schedules = AutomationSchedule.objects.filter(is_enabled=True).count()
        
        # Son çalıştırmalar
        recent_executions = PlaybookExecution.objects.select_related(
            'playbook', 'executor'
        ).order_by('-created_at')[:5]
        
        return {
            'automation': {
                'total_executions': total_executions,
                'executions_24h': executions_24h,
                'executions_week': executions_week,
                'success_rate': success_rate,
                'active_schedules': active_schedules,
                'recent_executions': [
                    {
                        'id': exec.id,
                        'playbook_name': exec.playbook.name,
                        'executor': exec.executor.get_full_name() or exec.executor.username,
                        'status': exec.get_status_display(),
                        'created_at': exec.created_at,
                        'duration': str(exec.duration) if exec.duration else None
                    } for exec in recent_executions
                ]
            }
        }
    
    @staticmethod
    def get_performance_alerts():
        """Performans uyarıları"""
        # Aktif uyarılar
        active_alerts = Alert.objects.filter(status='open').order_by('-created_at')
        
        # Kritik uyarılar
        critical_alerts = active_alerts.filter(severity='critical')[:5]
        
        # Uyarı özeti
        alert_summary = {
            'critical': active_alerts.filter(severity='critical').count(),
            'warning': active_alerts.filter(severity='warning').count(),
            'info': active_alerts.filter(severity='info').count()
        }
        
        return {
            'performance': {
                'alert_summary': alert_summary,
                'total_active_alerts': active_alerts.count(),
                'critical_alerts': [
                    {
                        'id': alert.id,
                        'title': alert.title,
                        'severity': alert.get_severity_display(),
                        'source_type': alert.get_source_type_display(),
                        'created_at': alert.created_at
                    } for alert in critical_alerts
                ]
            }
        }
    
    @staticmethod
    def get_quick_links():
        """Hızlı linkler"""
        # En çok kullanılan linkler
        popular_links = Link.objects.annotate(
            click_count=Count('clicks')
        ).filter(is_active=True).order_by('-click_count')[:8]
        
        return {
            'quick_links': [
                {
                    'id': link.id,
                    'title': link.title,
                    'url': link.url,
                    'description': link.description,
                    'click_count': link.click_count,
                    'category': link.category.name if link.category else 'Genel'
                } for link in popular_links
            ]
        }
    
    @classmethod
    def get_complete_dashboard_data(cls):
        """Tüm dashboard verilerini topla"""
        data = {}
        
        try:
            data.update(cls.get_system_overview())
        except Exception as e:
            data['inventory'] = {'error': str(e)}
        
        try:
            data.update(cls.get_knowledge_base_stats())
        except Exception as e:
            data['knowledge_base'] = {'error': str(e)}
        
        try:
            data.update(cls.get_duty_schedule_info())
        except Exception as e:
            data['duty_schedule'] = {'error': str(e)}
        
        try:
            data.update(cls.get_announcements_summary())
        except Exception as e:
            data['announcements'] = {'error': str(e)}
        
        try:
            data.update(cls.get_system_status())
        except Exception as e:
            data['system_status'] = {'error': str(e)}
        
        try:
            data.update(cls.get_automation_stats())
        except Exception as e:
            data['automation'] = {'error': str(e)}
        
        try:
            data.update(cls.get_performance_alerts())
        except Exception as e:
            data['performance'] = {'error': str(e)}
        
        try:
            data.update(cls.get_quick_links())
        except Exception as e:
            data['quick_links'] = {'error': str(e)}
        
        try:
            data.update(cls.get_certificate_stats())
        except Exception as e:
            data['certificates'] = {'error': str(e)}
        
        return data
    
    @staticmethod
    def get_certificate_stats():
        """Sertifika istatistikleri"""
        if not CERTIFICATES_AVAILABLE:
            return {
                'certificates': {
                    'total_kdb': 0,
                    'total_java': 0,
                    'expiring_30': 0,
                    'expiring_7': 0,
                    'expired': 0,
                    'recent_expiring': [],
                    'available': False
                }
            }
        
        try:
            now = timezone.now()
            thirty_days = now + timedelta(days=30)
            seven_days = now + timedelta(days=7)
            
            # KDB Sertifika istatistikleri
            total_kdb = KdbCertificate.objects.count()
            kdb_expiring_30 = KdbCertificate.objects.filter(
                valid_to__lte=thirty_days,
                valid_to__gt=now
            ).count()
            kdb_expiring_7 = KdbCertificate.objects.filter(
                valid_to__lte=seven_days,
                valid_to__gt=now
            ).count()
            kdb_expired = KdbCertificate.objects.filter(
                valid_to__lte=now
            ).count()
            
            # Java Sertifika istatistikleri
            total_java = JavaCertificate.objects.count()
            java_expiring_30 = JavaCertificate.objects.filter(
                valid_to__lte=thirty_days,
                valid_to__gt=now
            ).count()
            java_expiring_7 = JavaCertificate.objects.filter(
                valid_to__lte=seven_days,
                valid_to__gt=now
            ).count()
            java_expired = JavaCertificate.objects.filter(
                valid_to__lte=now
            ).count()
            
            # Yaklaşan sertifikalar (en kritik 5 tanesi)
            recent_expiring = []
            
            # KDB sertifikaları
            kdb_recent = KdbCertificate.objects.filter(
                valid_to__lte=thirty_days,
                valid_to__gt=now
            ).order_by('valid_to')[:3]
            
            for cert in kdb_recent:
                days_left = (cert.valid_to - now).days
                recent_expiring.append({
                    'id': cert.id,
                    'type': 'kdb',
                    'common_name': cert.common_name,
                    'server_hostname': cert.server_hostname,
                    'valid_to': cert.valid_to,
                    'days_left': days_left,
                    'environment': cert.environment,
                    'application_name': cert.application_name
                })
            
            # Java sertifikaları
            java_recent = JavaCertificate.objects.filter(
                valid_to__lte=thirty_days,
                valid_to__gt=now
            ).order_by('valid_to')[:2]
            
            for cert in java_recent:
                days_left = (cert.valid_to - now).days
                recent_expiring.append({
                    'id': cert.id,
                    'type': 'java',
                    'common_name': cert.common_name,
                    'server_hostname': cert.server_hostname,
                    'valid_to': cert.valid_to,
                    'days_left': days_left,
                    'environment': cert.environment,
                    'application_name': cert.java_application
                })
            
            # Tarihe göre sırala
            recent_expiring.sort(key=lambda x: x['valid_to'])
            
            return {
                'certificates': {
                    'total_kdb': total_kdb,
                    'total_java': total_java,
                    'total_certificates': total_kdb + total_java,
                    'expiring_30': kdb_expiring_30 + java_expiring_30,
                    'expiring_7': kdb_expiring_7 + java_expiring_7,
                    'expired': kdb_expired + java_expired,
                    'kdb_stats': {
                        'total': total_kdb,
                        'expiring_30': kdb_expiring_30,
                        'expiring_7': kdb_expiring_7,
                        'expired': kdb_expired
                    },
                    'java_stats': {
                        'total': total_java,
                        'expiring_30': java_expiring_30,
                        'expiring_7': java_expiring_7,
                        'expired': java_expired
                    },
                    'recent_expiring': recent_expiring[:5],
                    'available': True
                }
            }
            
        except Exception as e:
            return {
                'certificates': {
                    'total_kdb': 0,
                    'total_java': 0,
                    'total_certificates': 0,
                    'expiring_30': 0,
                    'expiring_7': 0,
                    'expired': 0,
                    'recent_expiring': [],
                    'available': False,
                    'error': str(e)
                }
            }
    
    @staticmethod
    def get_announcement_stats():
        """Duyuru istatistikleri ve son duyurular"""
        try:
            now = timezone.now()
            
            # Aktif duyurular (yayında ve süresi dolmamış)
            active_announcements = Announcement.objects.filter(
                status='published'
            ).filter(
                Q(yayin_bitis_tarihi__isnull=True) | Q(yayin_bitis_tarihi__gt=now)
            )
            
            # Genel istatistikler
            total_announcements = Announcement.objects.count()
            published_count = active_announcements.count()
            draft_count = Announcement.objects.filter(status='draft').count()
            archived_count = Announcement.objects.filter(status='archived').count()
            
            # Önemli ve sabitlenmiş duyurular
            important_count = active_announcements.filter(is_important=True).count()
            pinned_count = active_announcements.filter(sabitle=True).count()
            
            # Duyuru türü dağılımı
            type_distribution = active_announcements.values('duyuru_tipi').annotate(
                count=Count('id')
            ).order_by('-count')
            
            # Son 5 duyuru (dashboard için)
            recent_announcements = active_announcements.select_related(
                'category', 'created_by'
            ).order_by('-sabitle', '-onem_seviyesi', '-published_at')[:5]
            
            recent_list = []
            for announcement in recent_announcements:
                recent_list.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'summary': announcement.summary or announcement.title,
                    'category': announcement.category.name,
                    'type': announcement.get_duyuru_tipi_display(),
                    'priority': announcement.get_onem_seviyesi_display(),
                    'priority_class': announcement.priority_badge_class,
                    'type_class': announcement.type_badge_class,
                    'published_at': announcement.published_at,
                    'is_important': announcement.is_important,
                    'is_pinned': announcement.sabitle,
                    'url': announcement.get_absolute_url(),
                    'view_count': announcement.view_count,
                    'expires_at': announcement.yayin_bitis_tarihi
                })
            
            # Yakında süresi dolacak duyurular
            thirty_days = now + timedelta(days=30)
            expiring_soon = active_announcements.filter(
                yayin_bitis_tarihi__isnull=False,
                yayin_bitis_tarihi__lte=thirty_days
            ).order_by('yayin_bitis_tarihi')[:3]
            
            expiring_list = []
            for announcement in expiring_soon:
                days_left = (announcement.yayin_bitis_tarihi - now).days
                expiring_list.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'expires_at': announcement.yayin_bitis_tarihi,
                    'days_left': days_left,
                    'url': announcement.get_absolute_url(),
                    'priority': announcement.get_onem_seviyesi_display(),
                    'priority_class': announcement.priority_badge_class
                })
            
            # Haftalık aktivite
            week_ago = now - timedelta(days=7)
            weekly_stats = {
                'new_announcements': Announcement.objects.filter(
                    created_at__gte=week_ago
                ).count(),
                'published_this_week': Announcement.objects.filter(
                    published_at__gte=week_ago
                ).count(),
                'archived_this_week': Announcement.objects.filter(
                    status='archived',
                    updated_at__gte=week_ago
                ).count()
            }
            
            return {
                'announcements': {
                    'total': total_announcements,
                    'published': published_count,
                    'draft': draft_count,
                    'archived': archived_count,
                    'important': important_count,
                    'pinned': pinned_count,
                    'recent': recent_list,
                    'expiring_soon': expiring_list,
                    'type_distribution': list(type_distribution),
                    'weekly_stats': weekly_stats,
                    'available': True
                }
            }
            
        except Exception as e:
            return {
                'announcements': {
                    'total': 0,
                    'published': 0,
                    'draft': 0,
                    'archived': 0,
                    'important': 0,
                    'pinned': 0,
                    'recent': [],
                    'expiring_soon': [],
                    'type_distribution': [],
                    'weekly_stats': {'new_announcements': 0, 'published_this_week': 0, 'archived_this_week': 0},
                    'available': False,
                    'error': str(e)
                }
            }
    
    @staticmethod
    def get_duty_schedule_stats():
        """Nöbet listesi istatistikleri"""
        try:
            now = timezone.now()
            today = now.date()
            
            # Toplam nöbet kayıtları
            total_duties = Nobetci.objects.count()
            
            # Bugünkü nöbetçi
            current_duty = Nobetci.get_current_duty()
            
            # Sonraki nöbetçi
            next_duty = Nobetci.get_next_duty()
            
            # Bu ay nöbet sayısı
            this_month_duties = Nobetci.objects.filter(
                tarih__year=today.year,
                tarih__month=today.month
            ).count()
            
            # Geçen ay nöbet sayısı
            last_month = today.replace(day=1) - timedelta(days=1)
            last_month_duties = Nobetci.objects.filter(
                tarih__year=last_month.year,
                tarih__month=last_month.month
            ).count()
            
            # Gelecek hafta nöbetçileri
            next_week = today + timedelta(days=7)
            upcoming_duties = list(Nobetci.objects.filter(
                tarih__gt=today,
                tarih__lte=next_week
            ).order_by('tarih')[:5].values(
                'id', 'tarih', 'ad_soyad', 'telefon', 'email'
            ))
            
            # Son senkronizasyon tarihi
            last_sync = Nobetci.objects.filter(
                senkron_tarihi__isnull=False
            ).order_by('-senkron_tarihi').first()
            
            return {
                'duty_schedule': {
                    'total_duties': total_duties,
                    'current_duty': {
                        'id': current_duty.id if current_duty else None,
                        'tarih': current_duty.tarih.strftime('%d.%m.%Y') if current_duty else None,
                        'ad_soyad': current_duty.ad_soyad if current_duty else None,
                        'telefon': current_duty.telefon if current_duty else None,
                        'email': current_duty.email if current_duty else None,
                        'exists': bool(current_duty)
                    },
                    'next_duty': {
                        'id': next_duty.id if next_duty else None,
                        'tarih': next_duty.tarih.strftime('%d.%m.%Y') if next_duty else None,
                        'ad_soyad': next_duty.ad_soyad if next_duty else None,
                        'days_until': next_duty.days_until if next_duty else None,
                        'exists': bool(next_duty)
                    },
                    'this_month_count': this_month_duties,
                    'last_month_count': last_month_duties,
                    'upcoming_duties': upcoming_duties,
                    'last_sync': last_sync.senkron_tarihi.strftime('%d.%m.%Y %H:%M') if last_sync and last_sync.senkron_tarihi else None,
                    'available': True
                }
            }
            
        except Exception as e:
            return {
                'duty_schedule': {
                    'total_duties': 0,
                    'current_duty': {'exists': False},
                    'next_duty': {'exists': False},
                    'this_month_count': 0,
                    'last_month_count': 0,
                    'upcoming_duties': [],
                    'last_sync': None,
                    'available': False,
                    'error': str(e)
                }
            }
    
    def get_ansible_stats(self):
        """Ansible istatistiklerini al"""
        try:
            from otomasyon.ansible_models import AnsibleJobTemplate, AnsibleJobExecution
            from django.utils import timezone
            from datetime import timedelta
            
            # Temel istatistikler
            total_templates = AnsibleJobTemplate.objects.filter(is_enabled=True).count()
            total_executions = AnsibleJobExecution.objects.count()
            
            # Son 24 saat
            last_24h = timezone.now() - timedelta(hours=24)
            recent_executions = AnsibleJobExecution.objects.filter(
                created_at__gte=last_24h
            ).count()
            
            # Durum istatistikleri
            running_jobs = AnsibleJobExecution.objects.filter(
                status__in=['pending', 'waiting', 'running']
            ).count()
            
            successful_jobs = AnsibleJobExecution.objects.filter(
                status='successful',
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            failed_jobs = AnsibleJobExecution.objects.filter(
                status__in=['failed', 'error'],
                created_at__gte=timezone.now() - timedelta(days=7)
            ).count()
            
            # Son job'lar
            recent_jobs = AnsibleJobExecution.objects.select_related(
                'job_template', 'executor'
            ).order_by('-created_at')[:5]
            
            recent_jobs_data = []
            for job in recent_jobs:
                recent_jobs_data.append({
                    'id': job.pk,
                    'execution_id': job.execution_id,
                    'template_name': job.job_template.name,
                    'status': job.status,
                    'status_display': job.get_status_display(),
                    'status_class': job.get_status_display_class(),
                    'executor': job.executor.get_full_name() or job.executor.username,
                    'created_at': job.created_at.strftime('%d.%m.%Y %H:%M'),
                    'duration': job.duration,
                    'is_running': job.is_running,
                    'is_successful': job.is_successful,
                    'is_failed': job.is_failed
                })
            
            # En popüler template'ler
            popular_templates = AnsibleJobTemplate.objects.filter(
                is_enabled=True,
                usage_count__gt=0
            ).order_by('-usage_count')[:3]
            
            popular_templates_data = []
            for template in popular_templates:
                popular_templates_data.append({
                    'id': template.pk,
                    'name': template.name,
                    'usage_count': template.usage_count,
                    'last_used': template.last_used.strftime('%d.%m.%Y %H:%M') if template.last_used else None,
                    'category': {
                        'name': template.category.name if template.category else None,
                        'color': template.category.color if template.category else None,
                        'icon': template.category.icon if template.category else None
                    }
                })
            
            return {
                'ansible': {
                    'total_templates': total_templates,
                    'total_executions': total_executions,
                    'recent_executions_24h': recent_executions,
                    'running_jobs': running_jobs,
                    'successful_jobs_7d': successful_jobs,
                    'failed_jobs_7d': failed_jobs,
                    'success_rate': round((successful_jobs / (successful_jobs + failed_jobs) * 100) if (successful_jobs + failed_jobs) > 0 else 0, 1),
                    'recent_jobs': recent_jobs_data,
                    'popular_templates': popular_templates_data,
                    'available': True
                }
            }
            
        except Exception as e:
            return {
                'ansible': {
                    'total_templates': 0,
                    'total_executions': 0,
                    'recent_executions_24h': 0,
                    'running_jobs': 0,
                    'successful_jobs_7d': 0,
                    'failed_jobs_7d': 0,
                    'success_rate': 0,
                    'recent_jobs': [],
                    'popular_templates': [],
                    'available': False,
                    'error': str(e)
                }
            }
    
    def get_dashboard_data(self):
        """Tüm dashboard verilerini topla"""
        data = {}
        
        # Sistem genel bakış
        data.update(self.get_system_overview())
        
        # Performans verileri
        data.update(self.get_performance_overview())
        
        # Sertifika verileri
        data.update(self.get_certificate_stats())
        
        # Nöbet listesi verileri
        data.update(self.get_duty_schedule_stats())
        
        # Ansible verileri
        data.update(self.get_ansible_stats())
        
        # Duyuru verileri
        try:
            from duyurular.models import Announcement
            recent_announcements = Announcement.objects.filter(
                status='published'
            ).order_by('-created_at')[:5]
            
            announcements_data = []
            for announcement in recent_announcements:
                announcements_data.append({
                    'id': announcement.id,
                    'title': announcement.title,
                    'created_at': announcement.created_at.strftime('%d.%m.%Y %H:%M'),
                    'is_pinned': announcement.is_pinned,
                    'priority': announcement.priority
                })
            
            data['announcements'] = {
                'recent_announcements': announcements_data,
                'total_count': Announcement.objects.filter(status='published').count()
            }
        except Exception:
            data['announcements'] = {
                'recent_announcements': [],
                'total_count': 0
            }
        
        # AskGT verileri
        try:
            from askgt.models import AskGTDocument
            recent_documents = AskGTDocument.objects.order_by('-eklenme_tarihi')[:5]
            
            documents_data = []
            for doc in recent_documents:
                documents_data.append({
                    'id': doc.id,
                    'baslik': doc.baslik,
                    'kategori': doc.kategori,
                    'eklenme_tarihi': doc.eklenme_tarihi.strftime('%d.%m.%Y'),
                    'orijinal_url': doc.orijinal_url
                })
            
            data['askgt'] = {
                'recent_documents': documents_data,
                'total_count': AskGTDocument.objects.count()
            }
        except Exception:
            data['askgt'] = {
                'recent_documents': [],
                'total_count': 0
            }
        
        return data


class DashboardCacheService:
    """Dashboard cache yönetimi"""
    
    @staticmethod
    def get_cache_key(user_id=None):
        """Cache anahtarı oluştur"""
        if user_id:
            return f"dashboard_data_user_{user_id}"
        return "dashboard_data_global"
    
    @staticmethod
    def get_cached_data(user_id=None):
        """Cache'den veri al"""
        try:
            from django.core.cache import cache
            cache_key = DashboardCacheService.get_cache_key(user_id)
            return cache.get(cache_key)
        except Exception:
            return None
    
    @staticmethod
    def set_cached_data(data, user_id=None, timeout=300):
        """Veriyi cache'e kaydet (5 dakika)"""
        try:
            from django.core.cache import cache
            cache_key = DashboardCacheService.get_cache_key(user_id)
            cache.set(cache_key, data, timeout)
        except Exception:
            pass
    
    @staticmethod
    def clear_cache(user_id=None):
        """Cache'i temizle"""
        try:
            from django.core.cache import cache
            cache_key = DashboardCacheService.get_cache_key(user_id)
            cache.delete(cache_key)
        except Exception:
            pass
