from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TopicViewSet, TopicAnalyticsViewSet, TopicPromptViewSet

router = DefaultRouter()
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'topic-analytics', TopicAnalyticsViewSet, basename='topic-analytics')
router.register(r'topic-prompts', TopicPromptViewSet, basename='topic-prompt')

urlpatterns = [
    path('', include(router.urls)),
]

