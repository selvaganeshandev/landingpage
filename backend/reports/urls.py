from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    ReportTemplateViewSet,
    ScheduledReportViewSet,
    GeneratedReportViewSet,
    ReportGenerationViewSet,
    convert_report_html_to_pdf,
    get_report_preview_data,
    generate_custom_template_pdf
)

router = DefaultRouter()
router.register(r'templates', ReportTemplateViewSet, basename='report-template')
router.register(r'scheduled', ScheduledReportViewSet, basename='scheduled-report')
router.register(r'generated', GeneratedReportViewSet, basename='generated-report')
router.register(r'generation', ReportGenerationViewSet, basename='report-generation')

urlpatterns = [
    path('', include(router.urls)),
    path('convert-to-pdf/', convert_report_html_to_pdf, name='convert-report-to-pdf'),
    path('preview-data/', get_report_preview_data, name='report-preview-data'),
    path('generate-custom-pdf/', generate_custom_template_pdf, name='generate-custom-template-pdf'),
]
