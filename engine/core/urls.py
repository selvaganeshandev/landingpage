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
    
    # Topic processing
    path('topics/start/', views.start_topic_processing, name='start_topic_processing'),
    path('topics/status/<int:domain_id>/', views.topic_analytics_status, name='topic_analytics_status'),
    path('topics/analytics/<int:domain_id>/', views.topic_analytics_summary, name='topic_analytics_summary'),
    
    # Competitor management
    path('competitors/', views.competitor_list, name='competitor_list'),
    path('competitors/<int:competitor_id>/', views.competitor_detail, name='competitor_detail'),
    path('competitors/process-single/', views.start_single_competitor_processing, name='start_single_competitor_processing'),
    path('competitors/<int:competitor_id>/process/', views.competitor_process, name='competitor_process'),
    path('competitors/<int:competitor_id>/analytics/', views.competitor_analytics, name='competitor_analytics'),
    
    # Competitor-Prompt Analytics
    path('competitor-prompt-analytics/', views.competitor_prompt_analytics_list, name='competitor_prompt_analytics_list'),
    path('competitor-prompt-analytics/gaps/', views.competitor_gaps, name='competitor_gaps'),
    
    # Share of Voice Analytics
    path('share-of-voice/', views.share_of_voice, name='share_of_voice'),
    path('competitor-analytics/trends/', views.competitor_analytics_trends, name='competitor_analytics_trends'),
    
    # Reset track status (for testing)
    path('reset-track-status/', views.reset_track_status, name='reset_track_status'),
    
    # Misinformation scanning
    path('misinformation/scan/', views.start_misinformation_scan, name='start_misinformation_scan'),
    path('topics/generate/', views.start_topic_generation, name='start_topic_generation'),
    
    # Integration Insights
    path('integrations/scheduler/start/', views.start_integration_insights_scheduler, name='start_integration_insights_scheduler'),
    path('integrations/process-pending/', views.process_pending_insights, name='process_pending_insights'),
    path('integrations/pending-insights/', views.get_pending_insights, name='get_pending_insights'),

    # SEO Ranking
    path('seo/process-keyword/', views.seo_process_keyword, name='seo_process_keyword'),
    path('seo/process-domain/', views.seo_process_domain, name='seo_process_domain'),
    path('seo/sync-volume/', views.seo_sync_volume, name='seo_sync_volume'),
    path('seo/analyze-competitors/', views.seo_analyze_competitors, name='seo_analyze_competitors'),
]
