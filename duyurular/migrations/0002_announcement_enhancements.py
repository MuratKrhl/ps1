# Generated migration file for Announcement model enhancements
# This file should be created by running: python manage.py makemigrations duyurular

from django.db import migrations, models
import django.db.models.deletion
import ckeditor.fields
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('duyurular', '0001_initial'),
    ]

    operations = [
        # Update Announcement model with new fields
        migrations.AddField(
            model_name='announcement',
            name='duyuru_tipi',
            field=models.CharField(
                choices=[
                    ('general', 'Genel'),
                    ('planned_work', 'Planlı Çalışma'),
                    ('maintenance', 'Bakım'),
                    ('outage', 'Kesinti'),
                    ('update', 'Güncelleme'),
                    ('info', 'Bilgilendirme')
                ],
                default='general',
                max_length=20,
                verbose_name='Duyuru Türü'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='onem_seviyesi',
            field=models.CharField(
                choices=[
                    ('low', 'Düşük'),
                    ('normal', 'Normal'),
                    ('high', 'Yüksek'),
                    ('critical', 'Kritik')
                ],
                default='normal',
                max_length=10,
                verbose_name='Önem Seviyesi'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='ilgili_urun',
            field=models.CharField(
                blank=True,
                max_length=100,
                null=True,
                verbose_name='İlgili Ürün/Sistem'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='calisma_tarihi',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Planlı Çalışma Tarihi'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='sabitle',
            field=models.BooleanField(
                default=False,
                verbose_name='Sabitlenmiş'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='yayin_bitis_tarihi',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Yayın Bitiş Tarihi'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='status',
            field=models.CharField(
                choices=[
                    ('draft', 'Taslak'),
                    ('published', 'Yayında'),
                    ('archived', 'Arşivlenmiş'),
                    ('scheduled', 'Zamanlanmış')
                ],
                default='draft',
                max_length=20,
                verbose_name='Durum'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='published_at',
            field=models.DateTimeField(
                blank=True,
                null=True,
                verbose_name='Yayın Tarihi'
            ),
        ),
        migrations.AddField(
            model_name='announcement',
            name='view_count',
            field=models.PositiveIntegerField(
                default=0,
                verbose_name='Görüntülenme Sayısı'
            ),
        ),
        
        # Update content field to use CKEditor
        migrations.AlterField(
            model_name='announcement',
            name='content',
            field=ckeditor.fields.RichTextField(
                verbose_name='İçerik'
            ),
        ),
        
        # Add indexes for performance
        migrations.AddIndex(
            model_name='announcement',
            index=models.Index(
                fields=['status', 'published_at'],
                name='duyurular_ann_status_pub_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='announcement',
            index=models.Index(
                fields=['sabitle', 'onem_seviyesi'],
                name='duyurular_ann_pin_priority_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='announcement',
            index=models.Index(
                fields=['duyuru_tipi', 'created_at'],
                name='duyurular_ann_type_created_idx'
            ),
        ),
    ]
