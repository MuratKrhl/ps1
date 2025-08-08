from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Q, Count, F
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from .models import (
    Question, Answer, KnowledgeCategory, Technology, FAQ, 
    KnowledgeArticle, QuestionView, QuestionVote, AnswerVote, AskGTDocument
)


@login_required
def askgt_home(request):
    """AskGT home page with featured content"""
    # Featured FAQs
    featured_faqs = FAQ.objects.filter(is_featured=True, is_active=True)[:6]
    
    # Recent questions
    recent_questions = Question.objects.filter(
        status='approved', is_active=True
    ).select_related('category', 'created_by').prefetch_related('technologies')[:8]
    
    # Popular questions (by view count)
    popular_questions = Question.objects.filter(
        status='approved', is_active=True
    ).order_by('-view_count')[:5]
    
    # Categories with question counts
    categories = KnowledgeCategory.objects.annotate(
        question_count=Count('questions', filter=Q(questions__status='approved', questions__is_active=True))
    ).filter(is_active=True, parent=None)[:8]
    
    # Technologies with question counts
    technologies = Technology.objects.annotate(
        question_count=Count('question', filter=Q(question__status='approved', question__is_active=True))
    ).filter(is_active=True)[:10]
    
    context = {
        'page_title': 'Bilgi Bankası',
        'featured_faqs': featured_faqs,
        'recent_questions': recent_questions,
        'popular_questions': popular_questions,
        'categories': categories,
        'technologies': technologies,
    }
    
    return render(request, 'askgt/home.html', context)


@login_required
def question_list(request):
    """Question list with filtering and search"""
    questions = Question.objects.filter(status='approved', is_active=True).select_related(
        'category', 'created_by'
    ).prefetch_related('technologies', 'answers')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        questions = questions.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(answers__content__icontains=search_query)
        ).distinct()
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        questions = questions.filter(category_id=category_filter)
    
    # Filter by technology
    technology_filter = request.GET.get('technology', '')
    if technology_filter:
        questions = questions.filter(technologies__id=technology_filter)
    
    # Filter by difficulty
    difficulty_filter = request.GET.get('difficulty', '')
    if difficulty_filter:
        questions = questions.filter(difficulty=difficulty_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', 'recent')
    if sort_by == 'popular':
        questions = questions.order_by('-view_count')
    elif sort_by == 'helpful':
        questions = questions.order_by('-helpful_count')
    else:  # recent
        questions = questions.order_by('-created_at')
    
    # Pagination
    paginator = Paginator(questions, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = KnowledgeCategory.objects.filter(is_active=True)
    technologies = Technology.objects.filter(is_active=True)
    difficulty_choices = Question._meta.get_field('difficulty').choices
    
    context = {
        'page_title': 'Sorular',
        'questions': page_obj,
        'search_query': search_query,
        'categories': categories,
        'technologies': technologies,
        'difficulty_choices': difficulty_choices,
        'current_filters': {
            'category': category_filter,
            'technology': technology_filter,
            'difficulty': difficulty_filter,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/question_list.html', context)


@login_required
def question_detail(request, question_id):
    """Question detail view with answers"""
    question = get_object_or_404(
        Question.objects.select_related('category', 'created_by', 'approved_by')
                       .prefetch_related('technologies', 'tags'),
        id=question_id, status='approved', is_active=True
    )
    
    # Track view
    view, created = QuestionView.objects.get_or_create(
        question=question,
        user=request.user,
        defaults={'ip_address': request.META.get('REMOTE_ADDR')}
    )
    
    if created:
        # Increment view count
        Question.objects.filter(id=question_id).update(view_count=F('view_count') + 1)
    
    # Get answers
    answers = question.answers.filter(
        status='published', is_active=True
    ).select_related('created_by').order_by('-is_accepted', '-is_official', '-helpful_count')
    
    # Check if user has voted
    user_question_vote = None
    if request.user.is_authenticated:
        try:
            user_question_vote = QuestionVote.objects.get(question=question, user=request.user)
        except QuestionVote.DoesNotExist:
            pass
    
    # Get user votes for answers
    user_answer_votes = {}
    if request.user.is_authenticated:
        votes = AnswerVote.objects.filter(answer__in=answers, user=request.user)
        user_answer_votes = {vote.answer_id: vote.is_helpful for vote in votes}
    
    # Related questions
    related_questions = Question.objects.filter(
        category=question.category, status='approved', is_active=True
    ).exclude(id=question.id)[:5]
    
    context = {
        'page_title': question.title,
        'question': question,
        'answers': answers,
        'user_question_vote': user_question_vote,
        'user_answer_votes': user_answer_votes,
        'related_questions': related_questions,
    }
    
    return render(request, 'askgt/question_detail.html', context)


@login_required
@require_POST
def vote_question(request, question_id):
    """Vote for a question (helpful/not helpful)"""
    question = get_object_or_404(Question, id=question_id, status='approved', is_active=True)
    is_helpful = request.POST.get('is_helpful') == 'true'
    
    vote, created = QuestionVote.objects.get_or_create(
        question=question,
        user=request.user,
        defaults={'is_helpful': is_helpful}
    )
    
    if not created:
        # Update existing vote
        if vote.is_helpful != is_helpful:
            vote.is_helpful = is_helpful
            vote.save()
    
    # Update question vote counts
    helpful_count = question.votes.filter(is_helpful=True).count()
    not_helpful_count = question.votes.filter(is_helpful=False).count()
    
    Question.objects.filter(id=question_id).update(
        helpful_count=helpful_count,
        not_helpful_count=not_helpful_count
    )
    
    return JsonResponse({
        'success': True,
        'helpful_count': helpful_count,
        'not_helpful_count': not_helpful_count,
        'user_vote': is_helpful
    })


@login_required
@require_POST
def vote_answer(request, answer_id):
    """Vote for an answer (helpful/not helpful)"""
    answer = get_object_or_404(Answer, id=answer_id, status='published', is_active=True)
    is_helpful = request.POST.get('is_helpful') == 'true'
    
    vote, created = AnswerVote.objects.get_or_create(
        answer=answer,
        user=request.user,
        defaults={'is_helpful': is_helpful}
    )
    
    if not created:
        # Update existing vote
        if vote.is_helpful != is_helpful:
            vote.is_helpful = is_helpful
            vote.save()
    
    # Update answer vote counts
    helpful_count = answer.votes.filter(is_helpful=True).count()
    not_helpful_count = answer.votes.filter(is_helpful=False).count()
    
    Answer.objects.filter(id=answer_id).update(
        helpful_count=helpful_count,
        not_helpful_count=not_helpful_count
    )
    
    return JsonResponse({
        'success': True,
        'helpful_count': helpful_count,
        'not_helpful_count': not_helpful_count,
        'user_vote': is_helpful
    })


@login_required
def category_list(request):
    """Knowledge categories list"""
    categories = KnowledgeCategory.objects.annotate(
        question_count=Count('questions', filter=Q(questions__status='approved', questions__is_active=True)),
        article_count=Count('articles', filter=Q(articles__status='published', articles__is_active=True))
    ).filter(is_active=True, parent=None).order_by('order', 'name')
    
    context = {
        'page_title': 'Kategoriler',
        'categories': categories,
    }
    
    return render(request, 'askgt/category_list.html', context)


@login_required
def category_detail(request, category_id):
    """Category detail with questions and articles"""
    category = get_object_or_404(KnowledgeCategory, id=category_id, is_active=True)
    
    # Get questions in this category
    questions = Question.objects.filter(
        category=category, status='approved', is_active=True
    ).select_related('created_by').prefetch_related('technologies')[:10]
    
    # Get articles in this category
    articles = KnowledgeArticle.objects.filter(
        category=category, status='published', is_active=True
    ).select_related('created_by')[:10]
    
    # Get subcategories
    subcategories = category.children.filter(is_active=True).annotate(
        question_count=Count('questions', filter=Q(questions__status='approved', questions__is_active=True))
    )
    
    context = {
        'page_title': f'Kategori: {category.name}',
        'category': category,
        'questions': questions,
        'articles': articles,
        'subcategories': subcategories,
    }
    
    return render(request, 'askgt/category_detail.html', context)


@login_required
def faq_list(request):
    """FAQ list"""
    faqs = FAQ.objects.filter(is_active=True).select_related('category').prefetch_related('technologies')
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        faqs = faqs.filter(category_id=category_filter)
    
    # Filter by technology
    technology_filter = request.GET.get('technology', '')
    if technology_filter:
        faqs = faqs.filter(technologies__id=technology_filter)
    
    # Search
    search_query = request.GET.get('search', '')
    if search_query:
        faqs = faqs.filter(
            Q(question__icontains=search_query) |
            Q(answer__icontains=search_query)
        )
    
    faqs = faqs.order_by('order', '-created_at')
    
    # Get filter options
    categories = KnowledgeCategory.objects.filter(is_active=True)
    technologies = Technology.objects.filter(is_active=True)
    
    context = {
        'page_title': 'Sık Sorulan Sorular',
        'faqs': faqs,
        'search_query': search_query,
        'categories': categories,
        'technologies': technologies,
        'current_filters': {
            'category': category_filter,
            'technology': technology_filter,
        }
    }
    
    return render(request, 'askgt/faq_list.html', context)


@login_required
def article_list(request):
    """Knowledge articles list"""
    articles = KnowledgeArticle.objects.filter(
        status='published', is_active=True
    ).select_related('category', 'created_by').prefetch_related('technologies', 'tags')
    
    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        articles = articles.filter(
            Q(title__icontains=search_query) |
            Q(content__icontains=search_query) |
            Q(summary__icontains=search_query)
        )
    
    # Filter by category
    category_filter = request.GET.get('category', '')
    if category_filter:
        articles = articles.filter(category_id=category_filter)
    
    # Filter by technology
    technology_filter = request.GET.get('technology', '')
    if technology_filter:
        articles = articles.filter(technologies__id=technology_filter)
    
    # Filter by difficulty
    difficulty_filter = request.GET.get('difficulty', '')
    if difficulty_filter:
        articles = articles.filter(difficulty=difficulty_filter)
    
    # Sorting
    sort_by = request.GET.get('sort', 'recent')
    if sort_by == 'popular':
        articles = articles.order_by('-view_count')
    elif sort_by == 'title':
        articles = articles.order_by('title')
    else:  # recent
        articles = articles.order_by('-published_at')
    
    # Pagination
    paginator = Paginator(articles, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Get filter options
    categories = KnowledgeCategory.objects.filter(is_active=True)
    technologies = Technology.objects.filter(is_active=True)
    difficulty_choices = KnowledgeArticle._meta.get_field('difficulty').choices
    
    context = {
        'page_title': 'Bilgi Makaleleri',
        'articles': page_obj,
        'search_query': search_query,
        'categories': categories,
        'technologies': technologies,
        'difficulty_choices': difficulty_choices,
        'current_filters': {
            'category': category_filter,
            'technology': technology_filter,
            'difficulty': difficulty_filter,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/article_list.html', context)


@login_required
def article_detail(request, slug):
    """Knowledge article detail"""
    article = get_object_or_404(
        KnowledgeArticle.objects.select_related('category', 'created_by')
                               .prefetch_related('technologies', 'tags'),
        slug=slug, status='published', is_active=True
    )
    
    # Increment view count
    KnowledgeArticle.objects.filter(id=article.id).update(view_count=F('view_count') + 1)
    
    # Related articles
    related_articles = KnowledgeArticle.objects.filter(
        category=article.category, status='published', is_active=True
    ).exclude(id=article.id)[:5]
    
    context = {
        'page_title': article.title,
        'article': article,
        'related_articles': related_articles,
    }
    
    return render(request, 'askgt/article_detail.html', context)


@login_required
def document_list_by_category(request, kategori):
    """List AskGT documents by category"""
    # Kategoriyi URL decode et
    kategori = kategori.replace('-', ' ').replace('_', ' ')
    
    # Dokümanları filtrele
    documents = AskGTDocument.objects.filter(
        kategori__iexact=kategori,
        is_active=True
    ).order_by('-eklenme_tarihi')
    
    # Sayfalama
    paginator = Paginator(documents, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    # Arama
    search_query = request.GET.get('search', '')
    if search_query:
        documents = documents.filter(
            Q(baslik__icontains=search_query) |
            Q(ozet__icontains=search_query)
        )
        paginator = Paginator(documents, 20)
        page_obj = paginator.get_page(page_number)
    
    context = {
        'page_title': f'{kategori} Dokümanları',
        'kategori': kategori,
        'documents': page_obj,
        'search_query': search_query,
        'total_count': documents.count(),
    }
    
    return render(request, 'askgt/document_list.html', context)


@login_required
def document_redirect(request, document_id):
    """Redirect to original document URL and increment view count"""
    document = get_object_or_404(AskGTDocument, id=document_id, is_active=True)
    
    # Görüntülenme sayısını artır
    document.increment_view_count()
    
    # Orijinal URL'ye yönlendir
    return redirect(document.orijinal_url)


@login_required
def documents_dashboard(request):
    """AskGT documents dashboard view"""
    # Son eklenen dokümanlar
    recent_documents = AskGTDocument.objects.filter(
        is_active=True
    ).order_by('-eklenme_tarihi')[:10]
    
    # Kategorilere göre istatistikler
    category_stats = (
        AskGTDocument.objects
        .filter(is_active=True)
        .values('kategori')
        .annotate(count=Count('id'))
        .order_by('-count')[:10]
    )
    
    # En çok görüntülenen dokümanlar
    popular_documents = AskGTDocument.objects.filter(
        is_active=True
    ).order_by('-view_count')[:5]
    
    context = {
        'page_title': 'AskGT Dokümanları',
        'recent_documents': recent_documents,
        'category_stats': category_stats,
        'popular_documents': popular_documents,
        'total_documents': AskGTDocument.objects.filter(is_active=True).count(),
        'total_categories': AskGTDocument.objects.filter(is_active=True).values('kategori').distinct().count(),
    }
    
    return render(request, 'askgt/documents_dashboard.html', context)
