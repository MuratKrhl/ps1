from django.db.models import Count
from django.core.cache import cache
from .models import AskGTDocument


def askgt_categories(request):
    """
    Context processor to provide AskGT categories for dynamic menu generation
    """
    # Cache key for categories
    cache_key = 'askgt_categories_menu'
    categories = cache.get(cache_key)
    
    if categories is None:
        # Aktif dokümanların kategorilerini say
        categories = (
            AskGTDocument.objects
            .filter(is_active=True)
            .values('kategori')
            .annotate(count=Count('id'))
            .order_by('kategori')
        )
        
        # Cache'e 15 dakika boyunca sakla
        cache.set(cache_key, list(categories), 60 * 15)
    
    return {
        'askgt_categories': categories
    }


def askgt_stats(request):
    """
    Context processor to provide AskGT statistics
    """
    cache_key = 'askgt_stats'
    stats = cache.get(cache_key)
    
    if stats is None:
        total_documents = AskGTDocument.objects.filter(is_active=True).count()
        total_categories = (
            AskGTDocument.objects
            .filter(is_active=True)
            .values('kategori')
            .distinct()
            .count()
        )
        
        stats = {
            'total_documents': total_documents,
            'total_categories': total_categories,
        }
        
        # Cache'e 30 dakika boyunca sakla
        cache.set(cache_key, stats, 60 * 30)
    
    return {
        'askgt_stats': stats
    }
