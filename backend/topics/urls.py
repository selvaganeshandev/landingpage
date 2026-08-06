from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import TopicViewSet, TopicAnalyticsViewSet
from .views_performance import topic_performance, generate_topics, topic_generation_status

router = DefaultRouter()
router.register(r'topics', TopicViewSet, basename='topic')
router.register(r'topic-analytics', TopicAnalyticsViewSet, basename='topic-analytics')
urlpatterns = [
    path('performance/', topic_performance, name='topic-performance'),
    path('generate/', generate_topics, name='topic-generate'),
    path('generation-status/', topic_generation_status, name='topic-generation-status'),
    path('', include(router.urls)),
]

