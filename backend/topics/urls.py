from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TopicViewSet, TopicAnalyticsViewSet

router = DefaultRouter()
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'topic-analytics', TopicAnalyticsViewSet, basename='topic-analytics')
urlpatterns = [
    path('', include(router.urls)),
]

