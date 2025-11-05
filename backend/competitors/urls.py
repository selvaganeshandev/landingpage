from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CompetitorViewSet, 
    CompetitorAnalyticsViewSet, 
    CompetitorPromptViewSet,
    CompetitorPromptAnalyticsViewSet
)

router = DefaultRouter()
router.register(r'competitors', CompetitorViewSet, basename='competitor')
router.register(r'competitor-analytics', CompetitorAnalyticsViewSet, basename='competitor-analytics')
router.register(r'competitor-prompts', CompetitorPromptViewSet, basename='competitor-prompt')
router.register(r'competitor-prompt-analytics', CompetitorPromptAnalyticsViewSet, basename='competitor-prompt-analytics')

urlpatterns = [
    path('', include(router.urls)),
]

