from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IntegrationViewSet
from .google_oauth import (
    google_auth_url,
    google_callback,
    get_ga_properties,
    select_ga_property,
    get_ga_data,
    get_ai_referral_data,
)

router = DefaultRouter()
router.register(r'integrations', IntegrationViewSet, basename='integration')

urlpatterns = [
    path('', include(router.urls)),

    # Google OAuth endpoints
    path('google/auth-url/', google_auth_url, name='google_auth_url'),
    path('google/callback/', google_callback, name='google_callback'),
    path('google/properties/', get_ga_properties, name='get_ga_properties'),
    path('google/select-property/', select_ga_property, name='select_ga_property'),
    path('google/analytics-data/', get_ga_data, name='get_ga_data'),
    path('google/ai-referrals/', get_ai_referral_data, name='get_ai_referral_data'),
]

