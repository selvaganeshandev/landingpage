"""
URL Configuration for Misinformation Module
"""
from django.urls import path
from . import views

app_name = 'misinformation'

urlpatterns = [
    # Dashboard
    path('dashboard/', views.dashboard, name='dashboard'),

    # Alerts
    path('alerts/', views.alert_list, name='alert-list'),
    path('alerts/<int:alert_id>/', views.alert_detail, name='alert-detail'),

    # Scans
    path('scan/', views.trigger_scan, name='trigger-scan'),
    path('scan/<int:scan_id>/', views.scan_status, name='scan-status'),
    path('scans/', views.scan_list, name='scan-list'),

    # Analytics
    path('analytics/', views.analytics, name='analytics'),
]
