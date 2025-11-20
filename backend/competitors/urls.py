from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompetitorViewSet, 
    CompetitorAnalyticsViewSet, 
    CompetitorPromptViewSet,
    CompetitorPromptAnalyticsViewSet,
    CompetitorMetricSnapshotViewSet,
    competitive_strength_analysis,
    competitive_insights,
    answer_gap_analysis,
    competitor_heatmap
)

router = DefaultRouter()
router.register(r'competitors', CompetitorViewSet, basename='competitor')
router.register(r'competitor-analytics', CompetitorAnalyticsViewSet, basename='competitor-analytics')
router.register(r'competitor-prompts', CompetitorPromptViewSet, basename='competitor-prompt')
router.register(r'competitor-prompt-analytics', CompetitorPromptAnalyticsViewSet, basename='competitor-prompt-analytics')
router.register(r'competitor-metric-snapshots', CompetitorMetricSnapshotViewSet, basename='competitor-metric-snapshots')

from .views import process_competitor, process_competitor_single, start_competitor_analysis

urlpatterns = [
    # Custom routes first (more specific) to avoid router conflicts
    # Note: 'competitors/' prefix is already included in main urls.py
    path('start-analysis/', start_competitor_analysis, name='start_competitor_analysis'),
    path('process-single/', process_competitor_single, name='process_competitor_single'),
    path('<int:competitor_id>/process/', process_competitor, name='process_competitor'),
    path('competitive-strength-analysis/', competitive_strength_analysis, name='competitive_strength_analysis'),
    path('competitive-insights/', competitive_insights, name='competitive_insights'),
    path('answer-gap-analysis/', answer_gap_analysis, name='answer_gap_analysis'),
    path('heatmap/', competitor_heatmap, name='competitor_heatmap'),
    # Router routes last
    path('', include(router.urls)),
]

