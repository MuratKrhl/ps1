from django.urls import path
from . import views

app_name = 'duyurular'

urlpatterns = [
    # Public announcement views
    path('', views.AnnouncementListView.as_view(), name='announcement_list'),
    path('<int:pk>/', views.AnnouncementDetailView.as_view(), name='announcement_detail'),
    
    # Admin CRUD views
    path('create/', views.AnnouncementCreateView.as_view(), name='announcement_create'),
    path('<int:pk>/update/', views.AnnouncementUpdateView.as_view(), name='announcement_update'),
    path('<int:pk>/delete/', views.AnnouncementDeleteView.as_view(), name='announcement_delete'),
    
    # API endpoints for AJAX operations
    path('api/announcement/create/', views.announcement_create_api, name='announcement_create_api'),
    path('api/announcement/<int:pk>/', views.announcement_detail_api, name='announcement_detail_api'),
    path('api/announcement/<int:pk>/update/', views.announcement_update_api, name='announcement_update_api'),
    path('api/announcement/<int:pk>/delete/', views.announcement_delete_api, name='announcement_delete_api'),
    path('api/announcement/<int:pk>/status/', views.announcement_status_api, name='announcement_status_api'),
    
    # Legacy URLs for compatibility
    path('duyurular/', views.AnnouncementListView.as_view(), name='announcement_list_legacy'),
    path('duyuru/<int:pk>/', views.AnnouncementDetailView.as_view(), name='announcement_detail_legacy'),
    path('onemli/', views.AnnouncementListView.as_view(), {'filter_important': True}, name='important_announcements'),
]
