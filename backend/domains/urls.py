from django.urls import path
from . import views

urlpatterns = [
    path('', views.domain_list, name='domain_list'),
    path('fetch-brand-info/', views.fetch_brand_info, name='fetch_brand_info'),
    path('fetch-brand-niches/', views.fetch_brand_niches, name='fetch_brand_niches'),
    path('<int:pk>/', views.domain_detail, name='domain_detail'),
    path('<int:pk>/keywords/', views.domain_keywords, name='domain_keywords'),

    # Domain Access Management
    path('<int:domain_id>/access/', views.domain_access_list, name='domain_access_list'),
    path('<int:domain_id>/access/<int:user_id>/', views.domain_access_detail, name='domain_access_detail'),
    path('<int:domain_id>/access/available-users/', views.available_users_for_domain, name='available_users_for_domain'),
]
