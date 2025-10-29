from django.urls import path
from . import views

app_name = 'core'

urlpatterns = [
    # Processing status and control
    path('status/', views.processing_status, name='processing_status'),
    path('start/', views.start_processing, name='start_processing'),
    
    # Domain management
    path('domains/', views.domain_list, name='domain_list'),
    path('domains/<int:domain_id>/', views.domain_detail, name='domain_detail'),
    path('domains/schedule/', views.schedule_domain, name='schedule_domain'),
    path('domains/reset/', views.reset_domain, name='reset_domain'),
    
    # Prompt analytics processing
    path('prompts/process/', views.start_prompt_analytics_processing, name='start_prompt_analytics_processing'),
    path('prompts/process-single/', views.start_single_prompt_processing, name='start_single_prompt_processing'),
    path('prompts/start/', views.start_prompt_processing, name='start_prompt_processing'),
    path('prompts/status/<int:domain_id>/', views.prompt_analytics_status, name='prompt_analytics_status'),
    path('prompts/summary/<int:domain_id>/', views.prompt_analytics_summary, name='prompt_analytics_summary'),
]
