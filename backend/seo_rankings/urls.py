from django.urls import path
from . import views

urlpatterns = [
    # Keyword rankings
    path('keywords/', views.seo_keyword_list, name='seo-keyword-list'),
    path('keywords/add/', views.seo_keyword_add, name='seo-keyword-add'),
    path('keywords/bulk-add/', views.seo_keyword_bulk_add, name='seo-keyword-bulk-add'),
    path('keywords/<int:pk>/', views.seo_keyword_detail, name='seo-keyword-detail'),

    # Rank history
    path('keywords/<int:seo_kw_id>/history/', views.seo_rank_history, name='seo-rank-history'),

    # SERP features
    path('keywords/<int:seo_kw_id>/serp-features/', views.seo_serp_features, name='seo-serp-features'),

    # Domain-level metrics
    path('metrics/', views.seo_domain_metrics, name='seo-domain-metrics'),
    path('overview/', views.seo_domain_overview, name='seo-domain-overview'),

    # Bulk operations
    path('keywords/bulk-delete/', views.seo_keyword_bulk_delete, name='seo-keyword-bulk-delete'),
    path('keywords/update-tags/', views.seo_keyword_update_tags, name='seo-keyword-update-tags'),
    path('keywords/remove-tag/', views.seo_keyword_remove_tag, name='seo-keyword-remove-tag'),
    path('keywords/get-tags/', views.seo_keyword_get_tags, name='seo-keyword-get-tags'),
    path('keywords/favourite/', views.seo_keyword_toggle_favourite, name='seo-keyword-toggle-favourite'),

    # Engine trigger & refresh status
    path('trigger/', views.seo_trigger_ranking, name='seo-trigger-ranking'),
    path('refresh-status/', views.seo_refresh_status, name='seo-refresh-status'),
]
