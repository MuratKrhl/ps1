from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.core.paginator import Paginator
from haystack.query import SearchQuerySet
from haystack.forms import SearchForm
from haystack.generic_views import SearchView
from django.views.generic import TemplateView
import json


@login_required
def global_search(request):
    """Global arama sayfası"""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    page = request.GET.get('page', 1)
    
    results = []
    total_results = 0
    
    if query:
        # Arama sorgusu oluştur
        sqs = SearchQuerySet().auto_query(query)
        
        # Kategori filtresi
        if category != 'all':
            sqs = sqs.models(get_model_by_category(category))
        
        # Sonuçları al
        results = sqs.load_all()
        total_results = len(results)
        
        # Sayfalama
        paginator = Paginator(results, 20)
        results = paginator.get_page(page)
    
    # Kategori istatistikleri
    category_stats = {}
    if query:
        category_stats = get_search_category_stats(query)
    
    context = {
        'query': query,
        'category': category,
        'results': results,
        'total_results': total_results,
        'category_stats': category_stats,
        'categories': [
            {'key': 'all', 'name': 'Tümü', 'icon': 'ri-search-line'},
            {'key': 'servers', 'name': 'Sunucular', 'icon': 'ri-server-line'},
            {'key': 'applications', 'name': 'Uygulamalar', 'icon': 'ri-apps-line'},
            {'key': 'questions', 'name': 'Sorular', 'icon': 'ri-question-line'},
            {'key': 'articles', 'name': 'Makaleler', 'icon': 'ri-article-line'},
            {'key': 'announcements', 'name': 'Duyurular', 'icon': 'ri-notification-line'},
            {'key': 'links', 'name': 'Linkler', 'icon': 'ri-link'},
            {'key': 'playbooks', 'name': 'Playbook\'lar', 'icon': 'ri-play-line'},
        ]
    }
    
    return render(request, 'search/search_results.html', context)


@login_required
def search_api(request):
    """Arama API endpoint'i"""
    query = request.GET.get('q', '').strip()
    category = request.GET.get('category', 'all')
    limit = int(request.GET.get('limit', 10))
    
    if not query:
        return JsonResponse({
            'success': False,
            'error': 'Arama sorgusu gerekli'
        })
    
    try:
        # Arama sorgusu
        sqs = SearchQuerySet().auto_query(query)
        
        # Kategori filtresi
        if category != 'all':
            model = get_model_by_category(category)
            if model:
                sqs = sqs.models(model)
        
        # Sonuçları al
        results = sqs.load_all()[:limit]
        
        # JSON formatına çevir
        search_results = []
        for result in results:
            obj = result.object
            if obj:
                search_results.append({
                    'id': obj.id,
                    'title': get_object_title(obj),
                    'description': get_object_description(obj),
                    'url': get_object_url(obj),
                    'type': obj._meta.verbose_name,
                    'category': get_object_category(obj),
                    'created_at': obj.created_at.isoformat() if hasattr(obj, 'created_at') else None
                })
        
        return JsonResponse({
            'success': True,
            'results': search_results,
            'total': len(search_results),
            'query': query
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        })


@login_required
def search_suggestions(request):
    """Arama önerileri API"""
    query = request.GET.get('q', '').strip()
    
    if len(query) < 2:
        return JsonResponse({'suggestions': []})
    
    try:
        # Kısa arama sorgusu
        sqs = SearchQuerySet().auto_query(query)[:10]
        
        suggestions = []
        for result in sqs:
            obj = result.object
            if obj:
                title = get_object_title(obj)
                if title not in [s['title'] for s in suggestions]:
                    suggestions.append({
                        'title': title,
                        'type': obj._meta.verbose_name,
                        'url': get_object_url(obj)
                    })
        
        return JsonResponse({'suggestions': suggestions})
        
    except Exception as e:
        return JsonResponse({'suggestions': []})


def get_model_by_category(category):
    """Kategoriye göre model döndür"""
    from envanter.models import Server, Application
    from askgt.models import Question, KnowledgeArticle
    from duyurular.models import Announcement
    from linkler.models import Link
    from otomasyon.models import AnsiblePlaybook
    
    category_models = {
        'servers': Server,
        'applications': Application,
        'questions': Question,
        'articles': KnowledgeArticle,
        'announcements': Announcement,
        'links': Link,
        'playbooks': AnsiblePlaybook
    }
    
    return category_models.get(category)


def get_search_category_stats(query):
    """Kategori bazında arama istatistikleri"""
    from envanter.models import Server, Application
    from askgt.models import Question, KnowledgeArticle
    from duyurular.models import Announcement
    from linkler.models import Link
    from otomasyon.models import AnsiblePlaybook
    
    stats = {}
    
    try:
        categories = {
            'servers': Server,
            'applications': Application,
            'questions': Question,
            'articles': KnowledgeArticle,
            'announcements': Announcement,
            'links': Link,
            'playbooks': AnsiblePlaybook
        }
        
        for key, model in categories.items():
            sqs = SearchQuerySet().models(model).auto_query(query)
            stats[key] = len(sqs)
    
    except Exception:
        pass
    
    return stats


def get_object_title(obj):
    """Nesne başlığını al"""
    if hasattr(obj, 'title'):
        return obj.title
    elif hasattr(obj, 'name'):
        return obj.name
    elif hasattr(obj, 'question'):
        return obj.question
    else:
        return str(obj)


def get_object_description(obj):
    """Nesne açıklamasını al"""
    if hasattr(obj, 'description') and obj.description:
        return obj.description[:200]
    elif hasattr(obj, 'content') and obj.content:
        return obj.content[:200]
    elif hasattr(obj, 'answer') and obj.answer:
        return obj.answer[:200]
    else:
        return ''


def get_object_url(obj):
    """Nesne URL'ini al"""
    model_name = obj._meta.model_name
    app_label = obj._meta.app_label
    
    url_patterns = {
        'server': f'/envanter/sunucu/{obj.id}/',
        'application': f'/envanter/uygulama/{obj.id}/',
        'question': f'/askgt/soru/{obj.id}/',
        'knowledgearticle': f'/askgt/makale/{obj.id}/',
        'announcement': f'/duyurular/duyuru/{obj.id}/',
        'link': f'/linkler/git/{obj.id}/',
        'ansibleplaybook': f'/otomasyon/playbook/{obj.id}/',
    }
    
    return url_patterns.get(model_name, '#')


def get_object_category(obj):
    """Nesne kategorisini al"""
    if hasattr(obj, 'category') and obj.category:
        return obj.category.name
    elif hasattr(obj, 'type') and obj.type:
        return obj.type.name
    else:
        return obj._meta.verbose_name


class AdvancedSearchView(TemplateView):
    """Gelişmiş arama sayfası"""
    template_name = 'search/advanced_search.html'
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        
        # Filtre seçenekleri
        from envanter.models import Environment, OperatingSystem
        from askgt.models import KnowledgeCategory, Technology
        from duyurular.models import AnnouncementCategory
        from linkler.models import LinkCategory
        from otomasyon.models import PlaybookCategory
        
        context.update({
            'environments': Environment.objects.filter(is_active=True),
            'operating_systems': OperatingSystem.objects.filter(is_active=True),
            'knowledge_categories': KnowledgeCategory.objects.filter(is_active=True),
            'technologies': Technology.objects.filter(is_active=True),
            'announcement_categories': AnnouncementCategory.objects.filter(is_active=True),
            'link_categories': LinkCategory.objects.filter(is_active=True),
            'playbook_categories': PlaybookCategory.objects.filter(is_active=True),
        })
        
        return context


@login_required
def advanced_search_api(request):
    """Gelişmiş arama API"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'POST gerekli'})
    
    try:
        data = json.loads(request.body)
        query = data.get('query', '').strip()
        filters = data.get('filters', {})
        
        if not query:
            return JsonResponse({'success': False, 'error': 'Arama sorgusu gerekli'})
        
        # Temel arama
        sqs = SearchQuerySet().auto_query(query)
        
        # Filtreler uygula
        if filters.get('content_type'):
            model = get_model_by_category(filters['content_type'])
            if model:
                sqs = sqs.models(model)
        
        if filters.get('date_from'):
            sqs = sqs.filter(created_at__gte=filters['date_from'])
        
        if filters.get('date_to'):
            sqs = sqs.filter(created_at__lte=filters['date_to'])
        
        if filters.get('category'):
            sqs = sqs.filter(category=filters['category'])
        
        # Sonuçları al
        results = sqs.load_all()
        
        # JSON formatına çevir
        search_results = []
        for result in results:
            obj = result.object
            if obj:
                search_results.append({
                    'id': obj.id,
                    'title': get_object_title(obj),
                    'description': get_object_description(obj),
                    'url': get_object_url(obj),
                    'type': obj._meta.verbose_name,
                    'category': get_object_category(obj),
                    'created_at': obj.created_at.isoformat() if hasattr(obj, 'created_at') else None
                })
        
        return JsonResponse({
            'success': True,
            'results': search_results,
            'total': len(search_results),
            'query': query,
            'filters': filters
        })
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
