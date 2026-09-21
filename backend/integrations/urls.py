from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IntegrationViewSet, start_traffic_processing, get_traffic_insights, get_gsc_keywords
from .google_oauth import (
    google_auth_url,
    google_callback,
    get_ga_properties,
    select_ga_property,
    get_ga_data,
    get_ai_referral_data,
    get_ai_referral_timeseries,
    get_gsc_sites,
    select_gsc_site,
)
from .google_proxy import ga4_run_report, gsc_search_analytics

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
    path('google/ai-referrals/timeseries/', get_ai_referral_timeseries, name='get_ai_referral_timeseries'),
    # Google Search Console endpoints
    path('google/search-console/sites/', get_gsc_sites, name='get_gsc_sites'),
    path('google/search-console/select-site/', select_gsc_site, name='select_gsc_site'),
    # Raw report proxies for external consumers (service API keys). GET-only;
    # caller describes dimensions/metrics/filters, Google returns the rows.
    path('google/ga4/run-report/', ga4_run_report, name='ga4_run_report'),
    path('google/search-console/query/', gsc_search_analytics, name='gsc_search_analytics'),
    
    # Traffic insights endpoints
    path('start/', start_traffic_processing, name='start_traffic_processing'),  # Deprecated - use engine endpoints
    path('traffic-insights/', get_traffic_insights, name='get_traffic_insights'),
    path('gsc-keywords/', get_gsc_keywords, name='get_gsc_keywords'),
]

