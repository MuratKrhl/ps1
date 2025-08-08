from django.urls import path
from . import views, management_views

app_name = 'askgt'

urlpatterns = [
    # Home
    path('', views.askgt_home, name='home'),
    
    # Questions
    path('sorular/', views.question_list, name='question_list'),
    path('soru/<int:question_id>/', views.question_detail, name='question_detail'),
    path('soru/<int:question_id>/oy/', views.vote_question, name='vote_question'),
    
    # Answers
    path('cevap/<int:answer_id>/oy/', views.vote_answer, name='vote_answer'),
    
    # Categories
    path('kategoriler/', views.category_list, name='category_list'),
    path('kategori/<int:category_id>/', views.category_detail, name='category_detail'),
    
    # FAQs
    path('sss/', views.faq_list, name='faq_list'),
    
    # Articles
    path('makaleler/', views.article_list, name='article_list'),
    path('makale/<int:article_id>/', views.article_detail, name='article_detail'),
    
    # Documents (External API)
    path('dokumanlar/', views.documents_dashboard, name='documents_dashboard'),
    path('dokumanlar/<str:kategori>/', views.document_list_by_category, name='document_list_by_category'),
    path('dokuman/<int:document_id>/git/', views.document_redirect, name='document_redirect'),
    
    # Management URLs
    path('yonetim/', management_views.askgt_management_dashboard, name='management_dashboard'),
    path('yonetim/sorular/', management_views.question_management, name='management_question_list'),
    path('yonetim/soru/<int:question_id>/', management_views.question_detail_management, name='management_question_detail'),
    path('yonetim/soru/<int:question_id>/durum/', management_views.update_question_status, name='management_update_question_status'),
    path('yonetim/cevaplar/', management_views.answer_management, name='management_answer_list'),
    path('yonetim/cevap/<int:answer_id>/onayla/', management_views.approve_answer, name='management_approve_answer'),
    path('yonetim/cevap/<int:answer_id>/reddet/', management_views.reject_answer, name='management_reject_answer'),
    path('yonetim/makaleler/', management_views.article_management, name='management_article_list'),
    path('yonetim/makale/<int:article_id>/durum/', management_views.update_article_status, name='management_update_article_status'),
    path('yonetim/sss/', management_views.faq_management, name='management_faq_list'),
    path('yonetim/kategoriler/', management_views.category_management, name='management_category_list'),
    path('yonetim/teknolojiler/', management_views.technology_management, name='management_technology_list'),
    path('yonetim/kullanici-istatistikleri/', management_views.user_statistics, name='management_user_statistics'),
    path('yonetim/toplu-islem/', management_views.bulk_action, name='management_bulk_action'),
]
