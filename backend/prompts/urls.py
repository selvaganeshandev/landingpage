from django.urls import path
from . import views
from . import test_views

urlpatterns = [
    # Test endpoint
    path('test/', test_views.test_view, name='test_view'),
    # Mentions endpoints
    path('mentions/', views.get_mentions, name='get_mentions'),
    path('mentions/filters/', views.get_mention_filters, name='get_mention_filters'),
    path('mentions/<int:analytics_id>/', views.get_mention_detail, name='get_mention_detail'),
    path('mentions/<int:analytics_id>/related/', views.get_related_mentions, name='get_related_mentions'),
    path('mentions/trends/', views.get_mention_trends, name='get_mention_trends'),
    path('mentions/analytics/', views.get_mention_analytics, name='get_mention_analytics'),
    path('mentions/export/', views.export_mentions, name='export_mentions'),
    
    # Prompt Groups endpoints
    path('groups/', views.prompt_groups_list, name='prompt_groups_list'),
    path('groups/<int:group_id>/', views.prompt_group_detail, name='prompt_group_detail'),
    
    # Prompts endpoints
    path('prompts/', views.prompts_list, name='prompts_list'),
    path('prompts/<int:prompt_id>/', views.prompt_detail, name='prompt_detail'),
    path('prompts/bulk-update/', views.bulk_update_prompts, name='bulk_update_prompts'),
    path('prompts/<int:prompt_id>/analytics/', views.prompt_analytics, name='prompt_analytics'),
]