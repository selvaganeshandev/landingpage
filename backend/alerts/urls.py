from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AlertViewSet, 
    AlertRuleViewSet, 
    AlertNotificationViewSet,
    alert_configuration,
    update_email_config
)

router = DefaultRouter()
router.register(r'alerts', AlertViewSet, basename='alert')
router.register(r'alert-rules', AlertRuleViewSet, basename='alert-rule')
router.register(r'alert-notifications', AlertNotificationViewSet, basename='alert-notification')

urlpatterns = [
    path('', include(router.urls)),
    path('alert-configuration/', alert_configuration, name='alert-configuration'),
    path('alert-configuration/email/', update_email_config, name='update-email-config'),
]

