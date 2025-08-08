from haystack import indexes
from envanter.models import Server, Application, Database
from askgt.models import Question, Answer, KnowledgeArticle, FAQ
from duyurular.models import Announcement
from linkler.models import Link
from otomasyon.models import AnsiblePlaybook


class ServerIndex(indexes.SearchIndex, indexes.Indexable):
    """Sunucu arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    hostname = indexes.CharField(model_attr='hostname')
    environment = indexes.CharField(model_attr='environment__name', null=True)
    status = indexes.CharField(model_attr='status')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Server
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class ApplicationIndex(indexes.SearchIndex, indexes.Indexable):
    """Uygulama arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description', null=True)
    type = indexes.CharField(model_attr='type__name', null=True)
    status = indexes.CharField(model_attr='status')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Application
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class QuestionIndex(indexes.SearchIndex, indexes.Indexable):
    """Soru arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    content = indexes.CharField(model_attr='content')
    category = indexes.CharField(model_attr='category__name', null=True)
    technologies = indexes.MultiValueField()
    status = indexes.CharField(model_attr='status')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Question
    
    def prepare_technologies(self, obj):
        return [tech.name for tech in obj.technologies.all()]
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class AnswerIndex(indexes.SearchIndex, indexes.Indexable):
    """Cevap arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    content = indexes.CharField(model_attr='content')
    question_title = indexes.CharField(model_attr='question__title')
    is_accepted = indexes.BooleanField(model_attr='is_accepted')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Answer
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class KnowledgeArticleIndex(indexes.SearchIndex, indexes.Indexable):
    """Bilgi makalesi arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    content = indexes.CharField(model_attr='content')
    category = indexes.CharField(model_attr='category__name', null=True)
    technologies = indexes.MultiValueField()
    status = indexes.CharField(model_attr='status')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return KnowledgeArticle
    
    def prepare_technologies(self, obj):
        return [tech.name for tech in obj.technologies.all()]
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(status='published')


class FAQIndex(indexes.SearchIndex, indexes.Indexable):
    """SSS arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    question = indexes.CharField(model_attr='question')
    answer = indexes.CharField(model_attr='answer')
    category = indexes.CharField(model_attr='category__name', null=True)
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return FAQ
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class AnnouncementIndex(indexes.SearchIndex, indexes.Indexable):
    """Duyuru arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    content = indexes.CharField(model_attr='content')
    category = indexes.CharField(model_attr='category__name', null=True)
    priority = indexes.CharField(model_attr='priority')
    is_important = indexes.BooleanField(model_attr='is_important')
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Announcement
    
    def index_queryset(self, using=None):
        from django.utils import timezone
        return self.get_model().objects.filter(
            is_active=True
        ).exclude(
            expiry_date__lt=timezone.now()
        )


class LinkIndex(indexes.SearchIndex, indexes.Indexable):
    """Link arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    title = indexes.CharField(model_attr='title')
    description = indexes.CharField(model_attr='description', null=True)
    category = indexes.CharField(model_attr='category__name', null=True)
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return Link
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)


class PlaybookIndex(indexes.SearchIndex, indexes.Indexable):
    """Playbook arama indeksi"""
    text = indexes.CharField(document=True, use_template=True)
    name = indexes.CharField(model_attr='name')
    description = indexes.CharField(model_attr='description')
    category = indexes.CharField(model_attr='category__name', null=True)
    created_at = indexes.DateTimeField(model_attr='created_at')
    
    def get_model(self):
        return AnsiblePlaybook
    
    def index_queryset(self, using=None):
        return self.get_model().objects.filter(is_active=True)
