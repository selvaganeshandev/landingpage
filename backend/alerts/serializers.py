from rest_framework import serializers
from .models import Alert, AlertRule, AlertNotification


class AlertSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = Alert
        fields = [
            'id', 'domain', 'domain_name', 'type', 'severity', 'title', 
            'message', 'platform', 'metric', 'status', 'resolved_at',
            'created_by', 'created_by_email', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at', 'domain_name', 'created_by_email']


class AlertRuleSerializer(serializers.ModelSerializer):
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    created_by_email = serializers.CharField(source='created_by.email', read_only=True, allow_null=True)
    
    class Meta:
        model = AlertRule
        fields = [
            'id', 'domain', 'domain_name', 'name', 'description', 'enabled',
            'conditions', 'notification_channel_list', 'detection_count',
            'last_triggered_at', 'created_by', 'created_by_email', 
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'detection_count', 'last_triggered_at', 'created_at', 'modified_at']


class AlertNotificationSerializer(serializers.ModelSerializer):
    alert_title = serializers.CharField(source='alert.title', read_only=True)
    
    class Meta:
        model = AlertNotification
        fields = [
            'id', 'alert', 'alert_title', 'channel', 'recipient',
            'sent_at', 'status', 'error_message'
        ]
        read_only_fields = ['id', 'sent_at', 'alert_title']

