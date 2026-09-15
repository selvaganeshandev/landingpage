"""URL surface exercised by the centralized backend test package."""
from django.urls import include, path


urlpatterns = [
    path("auth/", include("authentication.urls")),
    path("domains/", include("domains.urls")),
    path("alerts/", include("alerts.urls")),
    path("audits/", include("audits.urls")),
]
