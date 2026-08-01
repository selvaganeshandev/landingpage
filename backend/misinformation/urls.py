"""
URL Configuration for Misinformation Module
"""
from django.urls import path
from . import views
from . import views_citations_export

app_name = 'misinformation'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Alerts
    path('alerts/', views.alert_list, name='alert-list'),
    path('alerts/<int:alert_id>/', views.alert_detail, name='alert-detail'),
    path('alerts/<int:alert_id>/comparison/', views.alert_full_comparison, name='alert-full-comparison'),

    # Scans
    path('scan/', views.trigger_scan, name='trigger-scan'),
    path('scan/<int:scan_id>/', views.scan_status, name='scan-status'),
    path('scans/', views.scan_list, name='scan-list'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),

    # Citations
    path('citations/dashboard/', views.citations_dashboard, name='citations-dashboard'),
    path('citations/', views.citations_list, name='citations-list'),
    path('citations/<int:citation_id>/', views.citation_detail, name='citation-detail'),
    path('citations/by-source/', views.citations_by_source, name='citations-by-source'),
    path('citations/validate/', views.validate_citations, name='citations-validate'),
    path('citations/export/', views_citations_export.citations_export, name='citations-export'),
]
