from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompetitorViewSet, 
    CompetitorAnalyticsViewSet, 
    CompetitorPromptViewSet,
    CompetitorPromptAnalyticsViewSet,
    competitive_strength_analysis,
    competitive_insights,
    answer_gap_analysis
)

router = DefaultRouter()
router.register(r'competitors', CompetitorViewSet, basename='competitor')
router.register(r'competitor-analytics', CompetitorAnalyticsViewSet, basename='competitor-analytics')
router.register(r'competitor-prompts', CompetitorPromptViewSet, basename='competitor-prompt')
router.register(r'competitor-prompt-analytics', CompetitorPromptAnalyticsViewSet, basename='competitor-prompt-analytics')

from .views import process_competitor, process_competitor_single

urlpatterns = [
    # Custom routes first (more specific) to avoid router conflicts
    # Note: 'competitors/' prefix is already included in main urls.py
    path('process-single/', process_competitor_single, name='process_competitor_single'),
    path('<int:competitor_id>/process/', process_competitor, name='process_competitor'),
    path('competitive-strength-analysis/', competitive_strength_analysis, name='competitive_strength_analysis'),
    path('competitive-insights/', competitive_insights, name='competitive_insights'),
    path('answer-gap-analysis/', answer_gap_analysis, name='answer_gap_analysis'),
    # Router routes last
    path('', include(router.urls)),
]

