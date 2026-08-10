from django.urls import path
from . import views, views_billing, views_invoice_settings, views_insights, views_backlinks, views_content_gap

urlpatterns = [
    # Keyword rankings
    path('keywords/', views.seo_keyword_list, name='seo-keyword-list'),
    path('keywords/add/', views.seo_keyword_add, name='seo-keyword-add'),
    path('keywords/bulk-add/', views.seo_keyword_bulk_add, name='seo-keyword-bulk-add'),
    path('keywords/import/', views.seo_keyword_import, name='seo-keyword-import'),
    path('keywords/remaining/', views.seo_keyword_remaining, name='seo-keyword-remaining'),
    path('keywords/<int:pk>/', views.seo_keyword_detail, name='seo-keyword-detail'),

    # Rank history
    path('keywords/<int:seo_kw_id>/history/', views.seo_rank_history, name='seo-rank-history'),

    # SERP features
    path('keywords/<int:seo_kw_id>/serp-features/', views.seo_serp_features, name='seo-serp-features'),

    # Domain-level metrics
    path('metrics/', views.seo_domain_metrics, name='seo-domain-metrics'),
    path('overview/', views.seo_domain_overview, name='seo-domain-overview'),

    # Insights
    path('opportunities/', views_insights.seo_opportunities, name='seo-opportunities'),
    path('share-of-voice/', views_insights.seo_share_of_voice, name='seo-share-of-voice'),
    path('opportunities/export/', views_insights.seo_opportunities_export, name='seo-opportunities-export'),
    path('opportunities/<int:seo_kw_id>/', views_insights.seo_opportunity_detail, name='seo-opportunity-detail'),

    # Backlinks (DataForSEO) — manual fetch, monthly refresh
    path('backlinks/', views_backlinks.backlinks_overview, name='seo-backlinks-overview'),
    path('backlinks/list/', views_backlinks.backlinks_list, name='seo-backlinks-list'),
    path('backlinks/fetch/', views_backlinks.backlinks_fetch, name='seo-backlinks-fetch'),
    path('backlinks/export/', views_backlinks.backlinks_export, name='seo-backlinks-export'),

    # Content gaps (organic search) — distinct from competitors/content-gaps/,
    # which is the GEO/LLM version.
    path('content-gaps/', views_content_gap.seo_content_gaps, name='seo-content-gaps'),
    path('content-gaps/export/', views_content_gap.seo_content_gaps_export, name='seo-content-gaps-export'),
    path('content-gaps/<int:seo_kw_id>/', views_content_gap.seo_content_gap_detail, name='seo-content-gap-detail'),

    # Bulk operations
    path('keywords/bulk-delete/', views.seo_keyword_bulk_delete, name='seo-keyword-bulk-delete'),
    path('keywords/update-tags/', views.seo_keyword_update_tags, name='seo-keyword-update-tags'),
    path('keywords/remove-tag/', views.seo_keyword_remove_tag, name='seo-keyword-remove-tag'),
    path('keywords/get-tags/', views.seo_keyword_get_tags, name='seo-keyword-get-tags'),
    path('keywords/favourite/', views.seo_keyword_toggle_favourite, name='seo-keyword-toggle-favourite'),

    # Engine trigger & refresh status
    path('trigger/', views.seo_trigger_ranking, name='seo-trigger-ranking'),
    path('refresh-status/', views.seo_refresh_status, name='seo-refresh-status'),
    path('force-rescrape/', views.seo_force_rescrape, name='seo-force-rescrape'),

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
    path('report-sheets/secondary-domain/resolve/', views.seo_secondary_domain_resolve, name='seo-secondary-domain-resolve'),
    path('report-sheets/', views.seo_report_sheet_list, name='seo-report-sheet-list'),
    path('report-sheets/add/', views.seo_report_sheet_add, name='seo-report-sheet-add'),
    path('report-sheets/<int:pk>/delete/', views.seo_report_sheet_delete, name='seo-report-sheet-delete'),
    path('report-sheets/<int:pk>/update/', views.seo_report_sheet_update, name='seo-report-sheet-update'),
    path('report-sheets/data/', views.seo_report_sheet_data, name='seo-report-sheet-data'),
    path('report-sheets/export/', views.seo_report_export_xlsx, name='seo-report-sheet-export'),

    # Keyword Detail — Notes
    path('keywords/<int:seo_kw_id>/notes/', views.seo_keyword_notes_list, name='seo-keyword-notes-list'),
    path('keywords/<int:seo_kw_id>/notes/create/', views.seo_keyword_note_create, name='seo-keyword-note-create'),
    path('keywords/<int:seo_kw_id>/notes/<int:note_id>/', views.seo_keyword_note_detail, name='seo-keyword-note-detail'),

    # Keyword Detail — Volume History
    path('keywords/<int:seo_kw_id>/volume/', views.seo_keyword_volume, name='seo-keyword-volume'),

    # Keyword Detail — Competitors
    path('keywords/<int:seo_kw_id>/competitors/', views.seo_keyword_competitors, name='seo-keyword-competitors'),

    # Billing — per-project keyword charges (super admin only)
    path('billing/', views_billing.billing_summary, name='seo-billing-summary'),
    path('billing/export/', views_billing.billing_export, name='seo-billing-export'),
    path('billing/invoice/', views_billing.billing_invoice, name='seo-billing-invoice'),
    path('billing/invoice-settings/', views_invoice_settings.invoice_settings, name='seo-invoice-settings'),
]
