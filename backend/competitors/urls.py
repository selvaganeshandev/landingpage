from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import CompetitorViewSet, CompetitorAnalyticsViewSet, CompetitorPromptViewSet

router = DefaultRouter()
router.register(r'competitors', CompetitorViewSet, basename='competitor')
router.register(r'competitor-analytics', CompetitorAnalyticsViewSet, basename='competitor-analytics')
router.register(r'competitor-prompts', CompetitorPromptViewSet, basename='competitor-prompt')

urlpatterns = [
    path('', include(router.urls)),
]

