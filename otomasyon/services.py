import subprocess
import json
import os
import tempfile
import uuid
from datetime import datetime
from django.conf import settings
from django.utils import timezone
from .models import PlaybookExecution, AutomationLog
from .ansible_models import AnsibleJobTemplate, AnsibleJobExecution, AnsibleJobLog
import logging
import requests

logger = logging.getLogger(__name__)


class AnsibleService:
    """Ansible playbook çalıştırma servisi"""
    
    def __init__(self):
        self.ansible_path = getattr(settings, 'ANSIBLE_PATH', 'ansible-playbook')
        self.working_dir = getattr(settings, 'ANSIBLE_WORKING_DIR', '/tmp/ansible')
        self.timeout = getattr(settings, 'ANSIBLE_TIMEOUT', 1800)  # 30 dakika
    
    def execute_playbook(self, execution_id):
        """Playbook çalıştır"""
        try:
            execution = PlaybookExecution.objects.get(id=execution_id)
            playbook = execution.playbook
            
            # Log başlangıç
            self._log_info(f"Playbook çalıştırma başlatıldı: {playbook.name}", execution)
            
            # Çalıştırma durumunu güncelle
            execution.status = 'running'
            execution.started_at = timezone.now()
            execution.save()
            
            # Geçici dosyalar oluştur
            temp_dir = self._create_temp_directory()
            inventory_file = self._create_inventory_file(temp_dir, execution)
            vars_file = self._create_vars_file(temp_dir, execution)
            
            # Ansible komutunu oluştur
            cmd = self._build_ansible_command(
                playbook.playbook_path,
                inventory_file,
                vars_file,
                execution
            )
            
            self._log_info(f"Ansible komutu: {' '.join(cmd)}", execution)
            
            # Komutu çalıştır
            result = subprocess.run(
                cmd,
                cwd=temp_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )
            
            # Sonuçları kaydet
            execution.return_code = result.returncode
            execution.stdout = result.stdout
            execution.stderr = result.stderr
            execution.completed_at = timezone.now()
            
            if result.returncode == 0:
                execution.status = 'completed'
                playbook.success_count += 1
                self._log_info("Playbook başarıyla tamamlandı", execution)
            else:
                execution.status = 'failed'
                self._log_error(f"Playbook başarısız: {result.stderr}", execution)
            
            # İstatistikleri güncelle
            playbook.execution_count += 1
            playbook.last_execution = timezone.now()
            playbook.save()
            
            execution.save()
            
            # Geçici dosyaları temizle
            self._cleanup_temp_files(temp_dir)
            
            return execution
            
        except subprocess.TimeoutExpired:
            execution.status = 'timeout'
            execution.completed_at = timezone.now()
            execution.save()
            self._log_error("Playbook zaman aşımına uğradı", execution)
            return execution
            
        except Exception as e:
            execution.status = 'failed'
            execution.stderr = str(e)
            execution.completed_at = timezone.now()
            execution.save()
            self._log_error(f"Playbook çalıştırma hatası: {str(e)}", execution)
            return execution
    
    def _create_temp_directory(self):
        """Geçici çalışma dizini oluştur"""
        temp_dir = tempfile.mkdtemp(prefix='ansible_')
        return temp_dir
    
    def _create_inventory_file(self, temp_dir, execution):
        """Inventory dosyası oluştur"""
        inventory_path = os.path.join(temp_dir, 'inventory.ini')
        
        # Hedef hostları al
        hosts = execution.target_hosts or []
        
        # Playbook'tan hedef sunucuları al
        if not hosts and execution.playbook.target_servers.exists():
            hosts = [server.hostname for server in execution.playbook.target_servers.all()]
        
        # Varsayılan inventory
        if not hosts:
            hosts = ['localhost']
        
        # Inventory içeriği
        inventory_content = "[targets]\n"
        for host in hosts:
            inventory_content += f"{host}\n"
        
        with open(inventory_path, 'w') as f:
            f.write(inventory_content)
        
        return inventory_path
    
    def _create_vars_file(self, temp_dir, execution):
        """Değişkenler dosyası oluştur"""
        vars_path = os.path.join(temp_dir, 'vars.json')
        
        # Playbook varsayılan değişkenleri
        variables = execution.playbook.default_variables.copy()
        
        # Çalıştırma değişkenleri
        if execution.variables:
            if isinstance(execution.variables, str):
                try:
                    execution_vars = json.loads(execution.variables)
                    variables.update(execution_vars)
                except json.JSONDecodeError:
                    pass
            elif isinstance(execution.variables, dict):
                variables.update(execution.variables)
        
        with open(vars_path, 'w') as f:
            json.dump(variables, f, indent=2)
        
        return vars_path
    
    def _build_ansible_command(self, playbook_path, inventory_file, vars_file, execution):
        """Ansible komutunu oluştur"""
        cmd = [
            self.ansible_path,
            playbook_path,
            '-i', inventory_file,
            '--extra-vars', f'@{vars_file}',
            '-v'  # Verbose output
        ]
        
        # Timeout ekle
        if execution.playbook.timeout_minutes:
            cmd.extend(['--timeout', str(execution.playbook.timeout_minutes * 60)])
        
        return cmd
    
    def _cleanup_temp_files(self, temp_dir):
        """Geçici dosyaları temizle"""
        try:
            import shutil
            shutil.rmtree(temp_dir)
        except Exception as e:
            logger.warning(f"Geçici dosyalar temizlenemedi: {e}")
    
    def _log_info(self, message, execution=None):
        """Info log"""
        AutomationLog.objects.create(
            level='info',
            message=message,
            playbook_execution=execution
        )
        logger.info(message)
    
    def _log_error(self, message, execution=None):
        """Error log"""
        AutomationLog.objects.create(
            level='error',
            message=message,
            playbook_execution=execution
        )
        logger.error(message)


class PlaybookValidator:
    """Playbook doğrulama servisi"""
    
    @staticmethod
    def validate_playbook_file(playbook_path):
        """Playbook dosyasını doğrula"""
        if not os.path.exists(playbook_path):
            return False, "Playbook dosyası bulunamadı"
        
        if not playbook_path.endswith(('.yml', '.yaml')):
            return False, "Playbook dosyası YAML formatında olmalı"
        
        try:
            import yaml
            with open(playbook_path, 'r') as f:
                yaml.safe_load(f)
            return True, "Playbook dosyası geçerli"
        except yaml.YAMLError as e:
            return False, f"YAML formatı hatalı: {e}"
        except Exception as e:
            return False, f"Dosya okuma hatası: {e}"
    
    @staticmethod
    def validate_variables(variables, required_vars):
        """Değişkenleri doğrula"""
        if not required_vars:
            return True, "Zorunlu değişken yok"
        
        if isinstance(variables, str):
            try:
                variables = json.loads(variables)
            except json.JSONDecodeError:
                return False, "Değişkenler JSON formatında olmalı"
        
        if not isinstance(variables, dict):
            return False, "Değişkenler dict formatında olmalı"
        
        missing_vars = []
        for var in required_vars:
            if var not in variables:
                missing_vars.append(var)
        
        if missing_vars:
            return False, f"Eksik zorunlu değişkenler: {', '.join(missing_vars)}"
        
        return True, "Tüm zorunlu değişkenler mevcut"


class ScheduleManager:
    """Programlı görev yöneticisi"""
    
    @staticmethod
    def calculate_next_run(schedule):
        """Sonraki çalıştırma zamanını hesapla"""
        from datetime import datetime, timedelta
        import calendar
        
        now = timezone.now()
        
        if schedule.schedule_type == 'once':
            if schedule.scheduled_date and schedule.scheduled_time:
                next_run = timezone.make_aware(
                    datetime.combine(schedule.scheduled_date, schedule.scheduled_time)
                )
                if next_run > now:
                    return next_run
            return None
        
        elif schedule.schedule_type == 'daily':
            next_run = now.replace(
                hour=schedule.scheduled_time.hour,
                minute=schedule.scheduled_time.minute,
                second=0,
                microsecond=0
            )
            if next_run <= now:
                next_run += timedelta(days=1)
            return next_run
        
        elif schedule.schedule_type == 'weekly':
            # Haftalık çalıştırma (Pazartesi = 0)
            days_ahead = 0 - now.weekday()  # Pazartesi için
            if days_ahead <= 0:
                days_ahead += 7
            
            next_run = now + timedelta(days=days_ahead)
            next_run = next_run.replace(
                hour=schedule.scheduled_time.hour,
                minute=schedule.scheduled_time.minute,
                second=0,
                microsecond=0
            )
            return next_run
        
        elif schedule.schedule_type == 'monthly':
            # Aylık çalıştırma (ayın ilk günü)
            if now.day == 1 and now.time() < schedule.scheduled_time:
                next_run = now.replace(
                    hour=schedule.scheduled_time.hour,
                    minute=schedule.scheduled_time.minute,
                    second=0,
                    microsecond=0
                )
            else:
                # Sonraki ayın ilk günü
                if now.month == 12:
                    next_month = now.replace(year=now.year + 1, month=1, day=1)
                else:
                    next_month = now.replace(month=now.month + 1, day=1)
                
                next_run = next_month.replace(
                    hour=schedule.scheduled_time.hour,
                    minute=schedule.scheduled_time.minute,
                    second=0,
                    microsecond=0
                )
            return next_run
        
        elif schedule.schedule_type == 'cron':
            # Cron ifadesi için croniter kullanılabilir
            # Şimdilik basit implementasyon
            return now + timedelta(hours=1)
        
        return None


class AnsibleTowerService:
    """Ansible Tower/AWX API servisi"""
    
    def __init__(self):
        self.tower_url = getattr(settings, 'ANSIBLE_TOWER_URL', '').rstrip('/')
        self.username = getattr(settings, 'ANSIBLE_TOWER_USERNAME', '')
        self.password = getattr(settings, 'ANSIBLE_TOWER_PASSWORD', '')
        self.token = getattr(settings, 'ANSIBLE_TOWER_TOKEN', '')
        self.verify_ssl = getattr(settings, 'ANSIBLE_TOWER_VERIFY_SSL', True)
        self.timeout = getattr(settings, 'ANSIBLE_TOWER_TIMEOUT', 30)
        
        if not self.tower_url:
            raise ValueError("ANSIBLE_TOWER_URL ayarı gerekli")
    
    def _get_session(self):
        """API session oluştur"""
        session = requests.Session()
        session.timeout = self.timeout
        session.verify = self.verify_ssl
        session.headers.update({
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        })
        
        # Authentication
        if self.token:
            session.headers['Authorization'] = f'Bearer {self.token}'
        elif self.username and self.password:
            session.auth = (self.username, self.password)
        else:
            raise ValueError("Token veya username/password gerekli")
        
        return session
    
    def launch_job_template(self, job_template, user, survey_answers=None, extra_vars=None, **kwargs):
        """Job Template'i çalıştır"""
        try:
            session = self._get_session()
            
            # Execution ID oluştur
            execution_id = str(uuid.uuid4())
            
            # Job execution kaydı oluştur
            job_execution = AnsibleJobExecution.objects.create(
                job_template=job_template,
                executor=user,
                execution_id=execution_id,
                survey_answers=survey_answers or {},
                extra_vars=extra_vars or {},
                limit=kwargs.get('limit', ''),
                tags=kwargs.get('tags', ''),
                skip_tags=kwargs.get('skip_tags', ''),
                job_type=kwargs.get('job_type', job_template.job_type),
                verbosity=kwargs.get('verbosity', job_template.verbosity),
                status='pending'
            )
            
            # Launch payload hazırla
            launch_data = {
                'extra_vars': {**survey_answers or {}, **extra_vars or {}}
            }
            
            # Opsiyonel parametreler
            if kwargs.get('limit'):
                launch_data['limit'] = kwargs['limit']
            if kwargs.get('tags'):
                launch_data['job_tags'] = kwargs['tags']
            if kwargs.get('skip_tags'):
                launch_data['skip_tags'] = kwargs['skip_tags']
            if kwargs.get('job_type'):
                launch_data['job_type'] = kwargs['job_type']
            if kwargs.get('verbosity') is not None:
                launch_data['verbosity'] = kwargs['verbosity']
            
            # Job'u başlat
            url = f"{self.tower_url}/api/v2/job_templates/{job_template.tower_id}/launch/"
            response = session.post(url, json=launch_data)
            response.raise_for_status()
            
            job_data = response.json()
            tower_job_id = job_data.get('id')
            
            # Job execution'ı güncelle
            job_execution.tower_job_id = tower_job_id
            job_execution.status = 'waiting'
            job_execution.save()
            
            # Usage count artır
            job_template.increment_usage()
            
            # Log kaydet
            self._log_job_event(job_execution, 'info', f'Job başlatıldı: Tower Job ID {tower_job_id}')
            
            logger.info(f"Job launched successfully: {job_template.name} (Tower ID: {tower_job_id})")
            return job_execution
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to launch job template {job_template.name}: {e}")
            if 'job_execution' in locals():
                job_execution.status = 'error'
                job_execution.result_stderr = str(e)
                job_execution.save()
                self._log_job_event(job_execution, 'error', f'Job başlatma hatası: {e}')
            raise
        except Exception as e:
            logger.error(f"Unexpected error launching job: {e}")
            if 'job_execution' in locals():
                job_execution.status = 'error'
                job_execution.result_stderr = str(e)
                job_execution.save()
                self._log_job_event(job_execution, 'error', f'Beklenmeyen hata: {e}')
            raise
    
    def get_job_status(self, job_execution):
        """Job durumunu kontrol et"""
        if not job_execution.tower_job_id:
            return None
        
        try:
            session = self._get_session()
            url = f"{self.tower_url}/api/v2/jobs/{job_execution.tower_job_id}/"
            response = session.get(url)
            response.raise_for_status()
            
            job_data = response.json()
            return job_data
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to get job status for {job_execution.execution_id}: {e}")
            return None
    
    def update_job_status(self, job_execution):
        """Job durumunu güncelle"""
        job_data = self.get_job_status(job_execution)
        if not job_data:
            return False
        
        try:
            # Durum mapping
            status_mapping = {
                'pending': 'pending',
                'waiting': 'waiting', 
                'running': 'running',
                'successful': 'successful',
                'failed': 'failed',
                'error': 'error',
                'canceled': 'canceled'
            }
            
            old_status = job_execution.status
            new_status = status_mapping.get(job_data.get('status'), 'error')
            
            # Job execution güncelle
            job_execution.status = new_status
            
            if job_data.get('started'):
                job_execution.started_at = timezone.datetime.fromisoformat(
                    job_data['started'].replace('Z', '+00:00')
                )
            
            if job_data.get('finished'):
                job_execution.finished_at = timezone.datetime.fromisoformat(
                    job_data['finished'].replace('Z', '+00:00')
                )
            
            if job_data.get('elapsed'):
                job_execution.elapsed = job_data['elapsed']
            
            job_execution.save()
            
            # Durum değişikliği logla
            if old_status != new_status:
                self._log_job_event(
                    job_execution, 'info', 
                    f'Durum değişti: {old_status} -> {new_status}'
                )
            
            # Job tamamlandıysa stdout/stderr al
            if new_status in ['successful', 'failed', 'error'] and not job_execution.result_stdout:
                self._fetch_job_output(job_execution)
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to update job status for {job_execution.execution_id}: {e}")
            return False
    
    def _fetch_job_output(self, job_execution):
        """Job çıktısını al"""
        if not job_execution.tower_job_id:
            return
        
        try:
            session = self._get_session()
            
            # Stdout al
            stdout_url = f"{self.tower_url}/api/v2/jobs/{job_execution.tower_job_id}/stdout/?format=txt"
            stdout_response = session.get(stdout_url)
            if stdout_response.status_code == 200:
                job_execution.result_stdout = stdout_response.text
            
            # Job events al (stderr için)
            events_url = f"{self.tower_url}/api/v2/jobs/{job_execution.tower_job_id}/job_events/"
            events_response = session.get(events_url)
            if events_response.status_code == 200:
                events_data = events_response.json()
                stderr_lines = []
                
                for event in events_data.get('results', []):
                    if event.get('event') == 'error' or event.get('failed', False):
                        if event.get('stdout'):
                            stderr_lines.append(event['stdout'])
                
                if stderr_lines:
                    job_execution.result_stderr = '\n'.join(stderr_lines)
            
            job_execution.save()
            
        except Exception as e:
            logger.error(f"Failed to fetch job output for {job_execution.execution_id}: {e}")
    
    def cancel_job(self, job_execution):
        """Job'u iptal et"""
        if not job_execution.tower_job_id or not job_execution.is_running:
            return False
        
        try:
            session = self._get_session()
            url = f"{self.tower_url}/api/v2/jobs/{job_execution.tower_job_id}/cancel/"
            response = session.post(url)
            response.raise_for_status()
            
            # Durumu güncelle
            job_execution.status = 'canceled'
            job_execution.finished_at = timezone.now()
            job_execution.save()
            
            self._log_job_event(job_execution, 'warning', 'Job iptal edildi')
            
            logger.info(f"Job canceled: {job_execution.execution_id}")
            return True
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to cancel job {job_execution.execution_id}: {e}")
            return False
    
    def _log_job_event(self, job_execution, level, message, **kwargs):
        """Job event logla"""
        AnsibleJobLog.objects.create(
            job_execution=job_execution,
            level=level,
            message=message,
            host=kwargs.get('host', ''),
            task=kwargs.get('task', ''),
            play=kwargs.get('play', ''),
            extra_data=kwargs.get('extra_data', {})
        )
