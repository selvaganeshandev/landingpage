from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SentimentAnalyticsViewSet, ShareOfVoiceAnalyticsViewSet
from .views_dashboard import dashboard_summary

router = DefaultRouter()
router.register(r'sentiment-analytics', SentimentAnalyticsViewSet, basename='sentiment-analytics')
router.register(r'share-of-voice', ShareOfVoiceAnalyticsViewSet, basename='share-of-voice')

urlpatterns = [
    path('', include(router.urls)),
    path('dashboard/summary/', dashboard_summary),
]

