from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # Content generation endpoints
    path('generate/', views.generate_content, name='generate_content'),
    path('', views.get_generated_contents, name='get_generated_contents'),
    path('<int:content_id>/', views.get_generated_content, name='get_generated_content'),
    path('<int:content_id>/update/', views.update_generated_content, name='update_generated_content'),
    path('<int:content_id>/delete/', views.delete_generated_content, name='delete_generated_content'),
    
    # Publishing endpoints
    path('publish/', views.publish_content, name='publish_content'),
    
    # CMS Provider management endpoints
    path('cms-providers/', views.cms_provider_list, name='cms_provider_list'),
    path('cms-providers/<int:provider_id>/', views.cms_provider_detail, name='cms_provider_detail'),
    path('cms-providers/<int:provider_id>/test/', views.test_cms_provider_connection, name='test_cms_provider_connection'),
]


