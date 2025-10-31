from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Alert, AlertRule, AlertNotification
from .serializers import AlertSerializer, AlertRuleSerializer, AlertNotificationSerializer


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Alert.objects.all()
        return Alert.objects.filter(domain__organisation=user.organisation)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def resolve(self, request, pk=None):
        """Mark alert as resolved."""
        alert = self.get_object()
        alert.status = 'resolved'
        alert.resolved_at = timezone.now()
        alert.save()
        return Response({'status': 'Alert resolved'})
    
    @action(detail=True, methods=['post'])
    def investigate(self, request, pk=None):
        """Mark alert as investigating."""
        alert = self.get_object()
        alert.status = 'investigating'
        alert.save()
        return Response({'status': 'Alert under investigation'})
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Get all active alerts."""
        queryset = self.get_queryset().filter(status='active')
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def summary(self, request):
        """Get alert summary statistics."""
        queryset = self.get_queryset()
        domain_id = request.query_params.get('domain_id')
        
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        
        summary = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'high_priority': queryset.filter(status='active', severity='high').count(),
            'investigating': queryset.filter(status='investigating').count(),
            'resolved_today': queryset.filter(
                status='resolved',
                resolved_at__date=timezone.now().date()
            ).count(),
        }
        return Response(summary)


class AlertRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AlertRule.objects.all()
        return AlertRule.objects.filter(domain__organisation=user.organisation)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def toggle(self, request, pk=None):
        """Toggle alert rule enabled status."""
        rule = self.get_object()
        rule.enabled = not rule.enabled
        rule.save()
        return Response({'enabled': rule.enabled})


class AlertNotificationViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = AlertNotificationSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return AlertNotification.objects.all()
        return AlertNotification.objects.filter(alert__domain__organisation=user.organisation)

