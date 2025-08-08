from django.urls import path
from . import views

app_name = 'linkler'

urlpatterns = [
    # Dashboard
    path('', views.linkler_dashboard, name='dashboard'),
    
    # Links
    path('liste/', views.link_list, name='link_list'),
    path('git/<int:link_id>/', views.link_redirect, name='link_redirect'),
    path('kategori/<int:category_id>/', views.category_links, name='category_links'),
    
    # Quick links
    path('hizli/', views.quick_links, name='quick_links'),
    
    # Collections
    path('koleksiyonlar/', views.collections, name='collections'),
    path('koleksiyon/<int:collection_id>/', views.collection_detail, name='collection_detail'),
    
    # Personal bookmarks
    path('yerimlerim/', views.my_bookmarks, name='my_bookmarks'),
    path('klasor/<int:folder_id>/', views.bookmark_folder, name='bookmark_folder'),
]
