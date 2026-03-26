from django.urls import path
from . import views

urlpatterns = [
    path('', views.domain_list, name='domain_list'),
    path('automated-onboard/', views.automated_domain_onboard, name='automated_domain_onboard'),
    path('fetch-brand-info/', views.fetch_brand_info, name='fetch_brand_info'),
    path('fetch-brand-niches/', views.fetch_brand_niches, name='fetch_brand_niches'),
    path('generate-semantic-keywords/', views.generate_semantic_keywords, name='generate_semantic_keywords'),
    path('<int:pk>/', views.domain_detail, name='domain_detail'),
    path('<int:pk>/keywords/', views.domain_keywords, name='domain_keywords'),
    path('<int:domain_id>/health-check/', views.domain_health_check, name='domain_health_check'),
    path('<int:domain_id>/health-check/history/', views.domain_health_check_history, name='domain_health_check_history'),

    # Domain Access Management
    path('user-access/<int:user_id>/', views.user_domain_access_list, name='user_domain_access_list'),
    path('<int:domain_id>/access/', views.domain_access_list, name='domain_access_list'),
    path('<int:domain_id>/access/<int:user_id>/', views.domain_access_detail, name='domain_access_detail'),
    path('<int:domain_id>/access/available-users/', views.available_users_for_domain, name='available_users_for_domain'),

    # Internal Link Map Management
    path('<int:domain_id>/internal-links/', views.internal_link_map_list, name='internal_link_map_list'),
    path('<int:domain_id>/internal-links/<int:link_id>/', views.internal_link_map_detail, name='internal_link_map_detail'),
    path('<int:domain_id>/internal-links/import/', views.internal_link_map_import_csv, name='internal_link_map_import_csv'),

    # Reference Repository Management
    path('<int:domain_id>/reference-repository/', views.reference_document_list, name='reference_document_list'),
    path('<int:domain_id>/reference-repository/<int:doc_id>/', views.reference_document_detail, name='reference_document_detail'),
]
