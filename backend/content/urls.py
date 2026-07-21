from django.urls import path
from . import views

app_name = 'content'

urlpatterns = [
    # Content generation endpoints
    path('generate/', views.generate_content, name='generate_content'),
    path('generate-outline/', views.generate_outline, name='generate_outline'),
    path('generate-from-outline/', views.generate_content_from_outline, name='generate_content_from_outline'),
    path('rewrite/', views.rewrite_content, name='rewrite_content'),
    path('', views.get_generated_contents, name='get_generated_contents'),
    path('<int:content_id>/', views.get_generated_content, name='get_generated_content'),
    path('<int:content_id>/update/', views.update_generated_content, name='update_generated_content'),
    path('<int:content_id>/delete/', views.delete_generated_content, name='delete_generated_content'),

    # Export endpoints
    path('<int:content_id>/export/docx/', views.export_content_docx, name='export_content_docx'),

    # Humanise endpoints
    path('<int:content_id>/humanise/', views.humanise_content, name='humanise_content'),
    path('<int:content_id>/humanise-status/', views.humanise_status, name='humanise_status'),
    path('<int:content_id>/humanise-undo/', views.humanise_undo, name='humanise_undo'),

    # Publishing endpoints
    path('publish/', views.publish_content, name='publish_content'),

    # AI Detection endpoint
    path('detect-ai/', views.detect_ai_content, name='detect_ai_content'),

    # CMS Provider management endpoints
    path('cms-providers/', views.cms_provider_list, name='cms_provider_list'),
    path('cms-providers/<int:provider_id>/', views.cms_provider_detail, name='cms_provider_detail'),
    path('cms-providers/<int:provider_id>/test/', views.test_cms_provider_connection, name='test_cms_provider_connection'),

    # Content Comment endpoints (Google Docs-style)
    path('<int:content_id>/comments/', views.content_comments, name='content_comments'),
    path('<int:content_id>/comments/<int:comment_id>/', views.content_comment_detail, name='content_comment_detail'),

    # Bulk Upload endpoints
    path('bulk-upload/template/', views.download_bulk_upload_template, name='bulk_upload_template'),
    path('bulk-upload/template-docx/', views.download_bulk_upload_docx_template, name='bulk_upload_template_docx'),
    path('bulk-upload/', views.bulk_upload_content, name='bulk_upload_content'),
    path('bulk-upload/docx/', views.bulk_upload_content_docx, name='bulk_upload_content_docx'),
    path('bulk-upload/batches/', views.get_bulk_upload_batches, name='bulk_upload_batches'),
    path('bulk-upload/batches/<int:batch_id>/', views.get_bulk_upload_batch_detail, name='bulk_upload_batch_detail'),
    path('bulk-upload/items/<int:item_id>/retry/', views.retry_bulk_upload_item, name='bulk_upload_item_retry'),
    path('bulk-upload/items/<int:item_id>/status/', views.update_bulk_upload_item_status, name='bulk_upload_item_status'),

    # Issue 8A: URL Reading
    path('read-url/', views.read_url, name='read_url'),

    # Issue 8B: Keyword Suggestions
    path('suggest-keywords/', views.suggest_keywords, name='suggest_keywords'),

    # Issue 8C: Content Planning & Rescheduling
    path('plan/', views.plan_content, name='plan_content'),
    path('<int:content_id>/reschedule/', views.reschedule_content, name='reschedule_content'),

    # Issue 8D: Content Refurbishing
    path('refurbish/', views.refurbish_content, name='refurbish_content'),

    # Issue 12: File text extraction for references
    path('extract-file-text/', views.extract_file_text, name='extract_file_text'),
]


