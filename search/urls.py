from django.urls import path
from . import views

app_name = 'search'

urlpatterns = [
    # Global search
    path('', views.global_search, name='global_search'),
    
    # Advanced search
    path('gelismis/', views.AdvancedSearchView.as_view(), name='advanced_search'),
    
    # API endpoints
    path('api/', views.search_api, name='search_api'),
    path('api/oneriler/', views.search_suggestions, name='search_suggestions'),
    path('api/gelismis/', views.advanced_search_api, name='advanced_search_api'),
]
