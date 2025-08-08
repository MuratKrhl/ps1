from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.http import JsonResponse, HttpResponseForbidden
from django.core.paginator import Paginator
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.views.decorators.http import require_http_methods
from django.views.decorators.csrf import csrf_exempt
from .models import (
    Question, Answer, KnowledgeCategory, Technology, FAQ, 
    KnowledgeArticle, QuestionVote, AnswerVote
)
from django.contrib.auth.models import User
import json


def is_askgt_manager(user):
    """AskGT yöneticisi kontrolü"""
    return user.is_staff or user.groups.filter(name='AskGT Yöneticileri').exists()


@login_required
@user_passes_test(is_askgt_manager)
def askgt_management_dashboard(request):
    """AskGT yönetim ana sayfası"""
    # İstatistikler
    stats = {
        'total_questions': Question.objects.count(),
        'answered_questions': Question.objects.filter(answers__isnull=False).distinct().count(),
        'total_answers': Answer.objects.count(),
        'total_articles': KnowledgeArticle.objects.count(),
        'published_articles': KnowledgeArticle.objects.filter(status='published').count(),
        'total_faqs': FAQ.objects.count(),
        'active_faqs': FAQ.objects.filter(is_active=True).count(),
        'total_categories': KnowledgeCategory.objects.count(),
        'total_technologies': Technology.objects.count(),
        'pending_questions': Question.objects.filter(status='pending').count(),
        'pending_answers': Answer.objects.filter(is_approved=False).count(),
    }
    
    # Cevap oranı
    if stats['total_questions'] > 0:
        stats['answer_rate'] = round((stats['answered_questions'] / stats['total_questions']) * 100, 1)
    else:
        stats['answer_rate'] = 0
    
    # Son aktiviteler
    recent_questions = Question.objects.select_related(
        'author', 'category'
    ).order_by('-created_at')[:10]
    
    recent_answers = Answer.objects.select_related(
        'author', 'question'
    ).order_by('-created_at')[:10]
    
    # En aktif kullanıcılar
    active_users = User.objects.annotate(
        question_count=Count('questions'),
        answer_count=Count('answers')
    ).filter(
        Q(question_count__gt=0) | Q(answer_count__gt=0)
    ).order_by('-question_count', '-answer_count')[:10]
    
    # Popüler sorular
    popular_questions = Question.objects.filter(
        is_active=True
    ).order_by('-view_count')[:5]
    
    # Bekleyen onaylar
    pending_answers = Answer.objects.filter(
        is_approved=False
    ).select_related('author', 'question')[:5]
    
    context = {
        'stats': stats,
        'recent_questions': recent_questions,
        'recent_answers': recent_answers,
        'active_users': active_users,
        'popular_questions': popular_questions,
        'pending_answers': pending_answers,
    }
    
    return render(request, 'askgt/management/dashboard.html', context)


@login_required
@user_passes_test(is_askgt_manager)
def question_management(request):
    """Soru yönetimi"""
    questions = Question.objects.select_related('author', 'category').prefetch_related('technologies')
    
    # Filtreleme
    status = request.GET.get('status')
    if status:
        questions = questions.filter(status=status)
    
    category_id = request.GET.get('category')
    if category_id:
        questions = questions.filter(category_id=category_id)
    
    technology_id = request.GET.get('technology')
    if technology_id:
        questions = questions.filter(technologies__id=technology_id)
    
    search = request.GET.get('search')
    if search:
        questions = questions.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # Sıralama
    sort_by = request.GET.get('sort', '-created_at')
    questions = questions.order_by(sort_by)
    
    # Sayfalama
    paginator = Paginator(questions, 25)
    page = request.GET.get('page')
    questions = paginator.get_page(page)
    
    # Filtre seçenekleri
    categories = KnowledgeCategory.objects.filter(is_active=True)
    technologies = Technology.objects.filter(is_active=True)
    
    context = {
        'questions': questions,
        'categories': categories,
        'technologies': technologies,
        'status_choices': Question._meta.get_field('status').choices,
        'filters': {
            'status': status,
            'category': category_id,
            'technology': technology_id,
            'search': search,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/management/question_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
def question_detail_management(request, question_id):
    """Soru detay yönetimi"""
    question = get_object_or_404(
        Question.objects.select_related('author', 'category').prefetch_related('technologies'),
        id=question_id
    )
    
    # Cevaplar
    answers = question.answers.select_related('author').order_by('-created_at')
    
    # Oylar
    question_votes = question.votes.select_related('user')
    answer_votes = AnswerVote.objects.filter(
        answer__question=question
    ).select_related('user', 'answer')
    
    # İstatistikler
    stats = {
        'view_count': question.view_count,
        'answer_count': answers.count(),
        'upvotes': question_votes.filter(vote_type='up').count(),
        'downvotes': question_votes.filter(vote_type='down').count(),
        'days_since_created': (timezone.now() - question.created_at).days,
    }
    
    context = {
        'question': question,
        'answers': answers,
        'question_votes': question_votes,
        'answer_votes': answer_votes,
        'stats': stats,
    }
    
    return render(request, 'askgt/management/question_detail.html', context)


@login_required
@user_passes_test(is_askgt_manager)
@require_http_methods(["POST"])
def update_question_status(request, question_id):
    """Soru durumunu güncelle"""
    question = get_object_or_404(Question, id=question_id)
    
    new_status = request.POST.get('status')
    if new_status in dict(Question._meta.get_field('status').choices):
        question.status = new_status
        question.save()
        
        messages.success(request, f'Soru durumu "{question.get_status_display()}" olarak güncellendi.')
    else:
        messages.error(request, 'Geçersiz durum.')
    
    return redirect('askgt:management_question_detail', question_id=question.id)


@login_required
@user_passes_test(is_askgt_manager)
def answer_management(request):
    """Cevap yönetimi"""
    answers = Answer.objects.select_related('author', 'question')
    
    # Filtreleme
    is_approved = request.GET.get('approved')
    if is_approved == '1':
        answers = answers.filter(is_approved=True)
    elif is_approved == '0':
        answers = answers.filter(is_approved=False)
    
    is_accepted = request.GET.get('accepted')
    if is_accepted == '1':
        answers = answers.filter(is_accepted=True)
    elif is_accepted == '0':
        answers = answers.filter(is_accepted=False)
    
    search = request.GET.get('search')
    if search:
        answers = answers.filter(
            Q(content__icontains=search) | Q(question__title__icontains=search)
        )
    
    # Sıralama
    sort_by = request.GET.get('sort', '-created_at')
    answers = answers.order_by(sort_by)
    
    # Sayfalama
    paginator = Paginator(answers, 25)
    page = request.GET.get('page')
    answers = paginator.get_page(page)
    
    context = {
        'answers': answers,
        'filters': {
            'approved': is_approved,
            'accepted': is_accepted,
            'search': search,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/management/answer_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
@require_http_methods(["POST"])
def approve_answer(request, answer_id):
    """Cevabı onayla"""
    answer = get_object_or_404(Answer, id=answer_id)
    
    answer.is_approved = True
    answer.approved_by = request.user
    answer.approved_at = timezone.now()
    answer.save()
    
    messages.success(request, 'Cevap onaylandı.')
    
    return redirect('askgt:management_answer_list')


@login_required
@user_passes_test(is_askgt_manager)
@require_http_methods(["POST"])
def reject_answer(request, answer_id):
    """Cevabı reddet"""
    answer = get_object_or_404(Answer, id=answer_id)
    
    answer.is_approved = False
    answer.save()
    
    messages.success(request, 'Cevap reddedildi.')
    
    return redirect('askgt:management_answer_list')


@login_required
@user_passes_test(is_askgt_manager)
def article_management(request):
    """Makale yönetimi"""
    articles = KnowledgeArticle.objects.select_related('author', 'category').prefetch_related('technologies')
    
    # Filtreleme
    status = request.GET.get('status')
    if status:
        articles = articles.filter(status=status)
    
    category_id = request.GET.get('category')
    if category_id:
        articles = articles.filter(category_id=category_id)
    
    search = request.GET.get('search')
    if search:
        articles = articles.filter(
            Q(title__icontains=search) | Q(content__icontains=search)
        )
    
    # Sıralama
    sort_by = request.GET.get('sort', '-created_at')
    articles = articles.order_by(sort_by)
    
    # Sayfalama
    paginator = Paginator(articles, 25)
    page = request.GET.get('page')
    articles = paginator.get_page(page)
    
    # Filtre seçenekleri
    categories = KnowledgeCategory.objects.filter(is_active=True)
    
    context = {
        'articles': articles,
        'categories': categories,
        'status_choices': KnowledgeArticle._meta.get_field('status').choices,
        'filters': {
            'status': status,
            'category': category_id,
            'search': search,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/management/article_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
@require_http_methods(["POST"])
def update_article_status(request, article_id):
    """Makale durumunu güncelle"""
    article = get_object_or_404(KnowledgeArticle, id=article_id)
    
    new_status = request.POST.get('status')
    if new_status in dict(KnowledgeArticle._meta.get_field('status').choices):
        article.status = new_status
        if new_status == 'published':
            article.published_at = timezone.now()
        article.save()
        
        messages.success(request, f'Makale durumu "{article.get_status_display()}" olarak güncellendi.')
    else:
        messages.error(request, 'Geçersiz durum.')
    
    return redirect('askgt:management_article_list')


@login_required
@user_passes_test(is_askgt_manager)
def faq_management(request):
    """SSS yönetimi"""
    faqs = FAQ.objects.select_related('category')
    
    # Filtreleme
    is_active = request.GET.get('active')
    if is_active == '1':
        faqs = faqs.filter(is_active=True)
    elif is_active == '0':
        faqs = faqs.filter(is_active=False)
    
    category_id = request.GET.get('category')
    if category_id:
        faqs = faqs.filter(category_id=category_id)
    
    search = request.GET.get('search')
    if search:
        faqs = faqs.filter(
            Q(question__icontains=search) | Q(answer__icontains=search)
        )
    
    # Sıralama
    sort_by = request.GET.get('sort', 'order')
    faqs = faqs.order_by(sort_by)
    
    # Sayfalama
    paginator = Paginator(faqs, 25)
    page = request.GET.get('page')
    faqs = paginator.get_page(page)
    
    # Filtre seçenekleri
    categories = KnowledgeCategory.objects.filter(is_active=True)
    
    context = {
        'faqs': faqs,
        'categories': categories,
        'filters': {
            'active': is_active,
            'category': category_id,
            'search': search,
            'sort': sort_by,
        }
    }
    
    return render(request, 'askgt/management/faq_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
def category_management(request):
    """Kategori yönetimi"""
    categories = KnowledgeCategory.objects.annotate(
        question_count=Count('questions'),
        article_count=Count('articles'),
        faq_count=Count('faqs')
    ).order_by('name')
    
    context = {
        'categories': categories,
    }
    
    return render(request, 'askgt/management/category_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
def technology_management(request):
    """Teknoloji yönetimi"""
    technologies = Technology.objects.annotate(
        question_count=Count('questions'),
        article_count=Count('articles')
    ).order_by('name')
    
    context = {
        'technologies': technologies,
    }
    
    return render(request, 'askgt/management/technology_list.html', context)


@login_required
@user_passes_test(is_askgt_manager)
def user_statistics(request):
    """Kullanıcı istatistikleri"""
    # En aktif kullanıcılar
    active_users = User.objects.annotate(
        question_count=Count('questions'),
        answer_count=Count('answers'),
        article_count=Count('knowledgearticles')
    ).filter(
        Q(question_count__gt=0) | Q(answer_count__gt=0) | Q(article_count__gt=0)
    ).order_by('-question_count', '-answer_count', '-article_count')
    
    # Sayfalama
    paginator = Paginator(active_users, 25)
    page = request.GET.get('page')
    users = paginator.get_page(page)
    
    # Genel istatistikler
    stats = {
        'total_contributors': active_users.count(),
        'avg_questions_per_user': active_users.aggregate(Avg('question_count'))['question_count__avg'] or 0,
        'avg_answers_per_user': active_users.aggregate(Avg('answer_count'))['answer_count__avg'] or 0,
        'top_questioner': active_users.first() if active_users.exists() else None,
    }
    
    context = {
        'users': users,
        'stats': stats,
    }
    
    return render(request, 'askgt/management/user_statistics.html', context)


@login_required
@user_passes_test(is_askgt_manager)
@csrf_exempt
@require_http_methods(["POST"])
def bulk_action(request):
    """Toplu işlemler"""
    try:
        data = json.loads(request.body)
        action = data.get('action')
        item_type = data.get('item_type')  # question, answer, article, faq
        item_ids = data.get('item_ids', [])
        
        if not action or not item_type or not item_ids:
            return JsonResponse({'success': False, 'error': 'Geçersiz parametreler'})
        
        count = 0
        
        if item_type == 'question':
            items = Question.objects.filter(id__in=item_ids)
            
            if action == 'approve':
                items.update(status='approved')
                count = items.count()
                message = f'{count} soru onaylandı'
            elif action == 'reject':
                items.update(status='rejected')
                count = items.count()
                message = f'{count} soru reddedildi'
            elif action == 'delete':
                count = items.count()
                items.delete()
                message = f'{count} soru silindi'
            else:
                return JsonResponse({'success': False, 'error': 'Geçersiz işlem'})
        
        elif item_type == 'answer':
            items = Answer.objects.filter(id__in=item_ids)
            
            if action == 'approve':
                items.update(is_approved=True, approved_by=request.user, approved_at=timezone.now())
                count = items.count()
                message = f'{count} cevap onaylandı'
            elif action == 'reject':
                items.update(is_approved=False)
                count = items.count()
                message = f'{count} cevap reddedildi'
            elif action == 'delete':
                count = items.count()
                items.delete()
                message = f'{count} cevap silindi'
            else:
                return JsonResponse({'success': False, 'error': 'Geçersiz işlem'})
        
        else:
            return JsonResponse({'success': False, 'error': 'Desteklenmeyen öğe türü'})
        
        return JsonResponse({'success': True, 'message': message})
        
    except Exception as e:
        return JsonResponse({'success': False, 'error': str(e)})
