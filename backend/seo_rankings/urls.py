from django.urls import path
from . import views

urlpatterns = [
    # Keyword rankings
    path('keywords/', views.seo_keyword_list, name='seo-keyword-list'),
    path('keywords/add/', views.seo_keyword_add, name='seo-keyword-add'),
    path('keywords/bulk-add/', views.seo_keyword_bulk_add, name='seo-keyword-bulk-add'),
    path('keywords/import/', views.seo_keyword_import, name='seo-keyword-import'),
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

    # PDF export (WeasyPrint — Rankmaxx-style report)
    path('keywords/pdf-export/', views.seo_pdf_export, name='seo-pdf-export'),

    # Competitor Analysis
    path('competitors/start/', views.seo_competitor_start, name='seo-competitor-start'),
    path('competitors/status/', views.seo_competitor_status, name='seo-competitor-status'),
    path('competitors/add/', views.seo_competitor_add, name='seo-competitor-add'),
    path('competitors/<int:pk>/delete/', views.seo_competitor_delete, name='seo-competitor-delete'),
    path('competitors/projects/', views.seo_competitor_projects, name='seo-competitor-projects'),
    path('competitors/<int:pk>/keywords/', views.seo_competitor_keywords, name='seo-competitor-keywords'),

    # SEO Report Sheets
    path('report-sheets/', views.seo_report_sheet_list, name='seo-report-sheet-list'),
    path('report-sheets/add/', views.seo_report_sheet_add, name='seo-report-sheet-add'),
    path('report-sheets/<int:pk>/delete/', views.seo_report_sheet_delete, name='seo-report-sheet-delete'),
    path('report-sheets/<int:pk>/update/', views.seo_report_sheet_update, name='seo-report-sheet-update'),
    path('report-sheets/data/', views.seo_report_sheet_data, name='seo-report-sheet-data'),
]
