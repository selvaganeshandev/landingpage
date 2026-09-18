from django.urls import path

from . import views

app_name = 'audits'

urlpatterns = [
    path('', views.audit_list_create, name='audit_list_create'),
    path('config/', views.audit_config, name='audit_config'),
    path('public/<str:token>/', views.audit_public, name='audit_public'),
    path('public/<str:token>/pdf/', views.audit_public_pdf, name='audit_public_pdf'),
    path('public/<str:token>/issues.csv', views.audit_public_issues_csv, name='audit_public_issues_csv'),
    path('<int:pk>/pdf/', views.audit_pdf, name='audit_pdf'),
    path('<int:pk>/issues.csv', views.audit_issues_csv, name='audit_issues_csv'),
    path('claim/<str:token>/', views.audit_claim_by_token, name='audit_claim_by_token'),
    path('<int:pk>/', views.audit_detail, name='audit_detail'),
    path('<int:pk>/claim/', views.audit_claim, name='audit_claim'),
    path('<int:pk>/rerun/', views.audit_rerun, name='audit_rerun'),
]
