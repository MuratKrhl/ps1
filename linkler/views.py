from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, F
from django.http import JsonResponse
from .models import Link, LinkCategory, QuickLink, LinkCollection, PersonalBookmark, BookmarkFolder, LinkClick


@login_required
def link_list(request):
    """List all links with filtering"""
    links = Link.objects.filter(is_active=True).select_related('category').prefetch_related('tags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        links = links.filter(
            Q(title__icontains=search_query) |
            Q(description__icontains=search_query) |
            Q(url__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        links = links.filter(category_id=category_filter)
    
    # Filter by type
    type_filter = request.GET.get('type', '')
    if type_filter == 'internal':
        links = links.filter(is_internal=True)
    elif type_filter == 'external':
        links = links.filter(is_internal=False)
    elif type_filter == 'vpn':
        links = links.filter(requires_vpn=True)
    elif type_filter == 'featured':
        links = links.filter(is_featured=True)
    
    # Ordering
    sort_by = request.GET.get('sort', 'category')
    if sort_by == 'title':
        links = links.order_by('title')
    elif sort_by == 'popular':
        links = links.order_by('-click_count')
    else:  # category
        links = links.order_by('category__order', 'order', 'title')
    
    # Pagination
    paginator = Paginator(links, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = LinkCategory.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Önemli Linkler',
        'links': page_obj,
        'search_query': search_query,
        'categories': categories,
        'current_filters': {
            'category': category_filter,
            'type': type_filter,
            'sort': sort_by,
        }
    }
    
    return render(request, 'linkler/link_list.html', context)


@login_required
def link_redirect(request, link_id):
    """Redirect to link and track click"""
    link = get_object_or_404(Link, id=link_id, is_active=True)
    
    # Track click
    LinkClick.objects.create(
        link=link,
        user=request.user,
        ip_address=request.META.get('REMOTE_ADDR'),
        user_agent=request.META.get('HTTP_USER_AGENT', '')
    )
    
    # Increment click count
    Link.objects.filter(id=link_id).update(click_count=F('click_count') + 1)
    
    return redirect(link.url)


@login_required
def category_links(request, category_id):
    """Links by category"""
    category = get_object_or_404(LinkCategory, id=category_id, is_active=True)
    
    links = Link.objects.filter(
        category=category, is_active=True
    ).prefetch_related('tags').order_by('order', 'title')
    
    # Get subcategories
    subcategories = category.children.filter(is_active=True).order_by('order', 'name')
    
    context = {
        'page_title': f'{category.name} Linkleri',
        'category': category,
        'links': links,
        'subcategories': subcategories,
    }
    
    return render(request, 'linkler/category_links.html', context)


@login_required
def quick_links(request):
    """Quick access links"""
    quick_links = QuickLink.objects.filter(
        is_visible=True, is_active=True
    ).order_by('order', 'title')
    
    context = {
        'page_title': 'Hızlı Linkler',
        'quick_links': quick_links,
    }
    
    return render(request, 'linkler/quick_links.html', context)


@login_required
def collections(request):
    """Link collections"""
    collections = LinkCollection.objects.filter(
        Q(is_public=True) | Q(owner=request.user) | Q(shared_with=request.user),
        is_active=True
    ).distinct().select_related('owner').prefetch_related('links')
    
    # Filter by ownership
    filter_type = request.GET.get('filter', 'all')
    if filter_type == 'my':
        collections = collections.filter(owner=request.user)
    elif filter_type == 'shared':
        collections = collections.filter(shared_with=request.user)
    elif filter_type == 'public':
        collections = collections.filter(is_public=True)
    
    context = {
        'page_title': 'Link Koleksiyonları',
        'collections': collections,
        'current_filter': filter_type,
    }
    
    return render(request, 'linkler/collections.html', context)


@login_required
def collection_detail(request, collection_id):
    """Collection detail view"""
    collection = get_object_or_404(
        LinkCollection.objects.prefetch_related('links', 'linkcollectionitem_set__link'),
        id=collection_id, is_active=True
    )
    
    # Check access permissions
    if not (collection.is_public or collection.owner == request.user or 
            request.user in collection.shared_with.all()):
        return redirect('linkler:collections')
    
    # Get ordered links
    collection_items = collection.linkcollectionitem_set.select_related('link').order_by('order')
    
    context = {
        'page_title': f'Koleksiyon: {collection.name}',
        'collection': collection,
        'collection_items': collection_items,
    }
    
    return render(request, 'linkler/collection_detail.html', context)


@login_required
def my_bookmarks(request):
    """Personal bookmarks"""
    # Get user's bookmark folders
    folders = BookmarkFolder.objects.filter(
        owner=request.user, is_active=True, parent=None
    ).order_by('order', 'name')
    
    # Get bookmarks without folder
    bookmarks_without_folder = PersonalBookmark.objects.filter(
        owner=request.user, folder=None, is_active=True
    ).order_by('order', 'title')
    
    # Get favorite bookmarks
    favorite_bookmarks = PersonalBookmark.objects.filter(
        owner=request.user, is_favorite=True, is_active=True
    ).order_by('title')
    
    context = {
        'page_title': 'Yer İmlerim',
        'folders': folders,
        'bookmarks_without_folder': bookmarks_without_folder,
        'favorite_bookmarks': favorite_bookmarks,
    }
    
    return render(request, 'linkler/my_bookmarks.html', context)


@login_required
def bookmark_folder(request, folder_id):
    """Bookmarks in a specific folder"""
    folder = get_object_or_404(
        BookmarkFolder, id=folder_id, owner=request.user, is_active=True
    )
    
    bookmarks = folder.bookmarks.filter(is_active=True).order_by('order', 'title')
    subfolders = folder.children.filter(is_active=True).order_by('order', 'name')
    
    context = {
        'page_title': f'Klasör: {folder.name}',
        'folder': folder,
        'bookmarks': bookmarks,
        'subfolders': subfolders,
    }
    
    return render(request, 'linkler/bookmark_folder.html', context)


@login_required
def linkler_dashboard(request):
    """Links dashboard"""
    # Featured links
    featured_links = Link.objects.filter(
        is_featured=True, is_active=True
    ).select_related('category').order_by('order', 'title')[:8]
    
    # Popular links
    popular_links = Link.objects.filter(
        is_active=True
    ).select_related('category').order_by('-click_count')[:5]
    
    # Quick links
    quick_links = QuickLink.objects.filter(
        is_visible=True, is_active=True
    ).order_by('order', 'title')[:6]
    
    # Categories with link counts
    categories = LinkCategory.objects.filter(
        is_active=True, parent=None
    ).prefetch_related('links').order_by('order', 'name')[:8]
    
    # User's recent bookmarks
    recent_bookmarks = PersonalBookmark.objects.filter(
        owner=request.user, is_active=True
    ).order_by('-created_at')[:5]
    
    # User's collections
    my_collections = LinkCollection.objects.filter(
        owner=request.user, is_active=True
    ).order_by('-created_at')[:3]
    
    context = {
        'page_title': 'Linkler Dashboard',
        'featured_links': featured_links,
        'popular_links': popular_links,
        'quick_links': quick_links,
        'categories': categories,
        'recent_bookmarks': recent_bookmarks,
        'my_collections': my_collections,
    }
    
    return render(request, 'linkler/dashboard.html', context)


@login_required
def important_links(request):
    """
    Önemli Linkler sayfası - Kategorilere göre gruplanmış linkler
    Kurumsal araçlar ve sık kullanılan web sitelerine hızlı erişim
    """
    # Aktif kategorileri al
    categories = LinkCategory.objects.filter(
        is_active=True
    ).prefetch_related(
        'link_set'
    ).order_by('order', 'name')
    
    # Her kategori için aktif linkleri al
    categories_with_links = []
    for category in categories:
        active_links = category.link_set.filter(
            is_active=True,
            is_public=True
        ).order_by('order', 'title')
        
        if active_links.exists():
            categories_with_links.append({
                'category': category,
                'links': active_links,
                'link_count': active_links.count()
            })
    
    # Öne çıkan linkler (kategorisiz)
    featured_links = Link.objects.filter(
        is_active=True,
        is_public=True,
        is_featured=True
    ).order_by('order', 'title')[:6]
    
    # Hızlı erişim linkleri
    quick_access_links = QuickLink.objects.filter(
        is_active=True,
        is_visible=True
    ).order_by('order', 'title')[:8]
    
    # Son eklenen linkler
    recent_links = Link.objects.filter(
        is_active=True,
        is_public=True
    ).order_by('-created_at')[:5]
    
    # İstatistikler
    stats = {
        'total_categories': len(categories_with_links),
        'total_links': sum(cat['link_count'] for cat in categories_with_links),
        'featured_count': featured_links.count(),
        'quick_access_count': quick_access_links.count()
    }
    
    context = {
        'page_title': 'Önemli Linkler',
        'categories_with_links': categories_with_links,
        'featured_links': featured_links,
        'quick_access_links': quick_access_links,
        'recent_links': recent_links,
        'stats': stats
    }
    
    return render(request, 'linkler/important_links.html', context)
