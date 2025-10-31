from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from .models import Integration
from .serializers import IntegrationSerializer, IntegrationPublicSerializer


class IntegrationViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        """Use public serializer for list/retrieve, full serializer for create/update."""
        if self.action in ['list', 'retrieve']:
            return IntegrationPublicSerializer
        return IntegrationSerializer
    
    def get_queryset(self):
        user = self.request.user
        if user.role == 'super_admin':
            return Integration.objects.all()
        return Integration.objects.filter(domain__organisation=user.organisation)
    
    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user)
    
    @action(detail=True, methods=['post'])
    def test_connection(self, request, pk=None):
        """Test the integration connection."""
        integration = self.get_object()
        
        # TODO: Implement actual connection testing logic based on integration type
        # For now, just mark as active
        integration.status = 'active'
        integration.last_sync_at = timezone.now()
        integration.error_message = None
        integration.save()
        
        return Response({
            'status': 'success',
            'message': f'{integration.get_type_display()} connection is active'
        })
    
    @action(detail=True, methods=['post'])
    def disconnect(self, request, pk=None):
        """Disconnect the integration."""
        integration = self.get_object()
        integration.status = 'disconnected'
        integration.credentials = {}  # Clear credentials
        integration.save()
        
        return Response({
            'status': 'disconnected',
            'message': f'{integration.get_type_display()} has been disconnected'
        })
    
    @action(detail=True, methods=['post'])
    def sync(self, request, pk=None):
        """Manually trigger a sync for this integration."""
        integration = self.get_object()
        
        # TODO: Implement actual sync logic based on integration type
        # For now, just update the last_sync_at timestamp
        integration.last_sync_at = timezone.now()
        integration.save()
        
        return Response({
            'status': 'synced',
            'last_sync_at': integration.last_sync_at
        })
    
    @action(detail=False, methods=['get'])
    def by_domain(self, request):
        """Get all integrations for a specific domain."""
        domain_id = request.query_params.get('domain_id')
        if not domain_id:
            return Response(
                {'error': 'domain_id is required'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        queryset = self.get_queryset().filter(domain_id=domain_id)
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def status_summary(self, request):
        """Get integration status summary."""
        domain_id = request.query_params.get('domain_id')
        queryset = self.get_queryset()
        
        if domain_id:
            queryset = queryset.filter(domain_id=domain_id)
        
        summary = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'error': queryset.filter(status='error').count(),
            'disconnected': queryset.filter(status='disconnected').count(),
        }
        return Response(summary)

