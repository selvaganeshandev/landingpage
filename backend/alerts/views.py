from rest_framework import viewsets, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from django.utils import timezone
from django.shortcuts import get_object_or_404
from .models import Alert, AlertRule, AlertNotification, AlertConfiguration
from .serializers import AlertSerializer, AlertRuleSerializer, AlertNotificationSerializer, AlertConfigurationSerializer
from core.queryset_scoping import filter_by_accessible_domains


class AlertViewSet(viewsets.ModelViewSet):
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        base_qs = filter_by_accessible_domains(Alert.objects.all(), user, self.request)
        # Optional domain scoping via query param
        domain_id = self.request.query_params.get('domain_id') if hasattr(self, 'request') else None
        if domain_id:
            base_qs = base_qs.filter(domain_id=domain_id)
        return base_qs
    
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
        
        # Calculate average response time (time from alert creation to resolution)
        resolved_alerts = queryset.filter(
            status='resolved',
            resolved_at__isnull=False,
            created_at__isnull=False
        )
        
        avg_response_time = None
        if resolved_alerts.exists():
            response_times = []
            for alert in resolved_alerts:
                if alert.created_at and alert.resolved_at:
                    delta = alert.resolved_at - alert.created_at
                    hours = delta.total_seconds() / 3600
                    response_times.append(hours)
            
            if response_times:
                avg_response_time = round(sum(response_times) / len(response_times), 1)
        
        # Get email configuration for the domain
        email_address = None
        email_enabled = False
        if domain_id:
            try:
                config = AlertConfiguration.objects.filter(domain_id=domain_id).first()
                if config:
                    email_address = config.email_address
                    email_enabled = config.email_enabled
            except Exception:
                pass
        
        summary = {
            'total': queryset.count(),
            'active': queryset.filter(status='active').count(),
            'high_priority': queryset.filter(status='active', severity='high').count(),
            'resolved_today': queryset.filter(
                status='resolved',
                resolved_at__date=timezone.now().date()
            ).count(),
            'avg_response_time': avg_response_time,
            'email_address': email_address,
            'email_enabled': email_enabled,
        }
        return Response(summary)


class AlertRuleViewSet(viewsets.ModelViewSet):
    serializer_class = AlertRuleSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        user = self.request.user
        base_qs = filter_by_accessible_domains(AlertRule.objects.all(), user, self.request)
        # Optional domain scoping via query param
        domain_id = self.request.query_params.get('domain_id') if hasattr(self, 'request') else None
        if domain_id:
            base_qs = base_qs.filter(domain_id=domain_id)
        return base_qs
    
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
        return filter_by_accessible_domains(
            AlertNotification.objects.all(), user, self.request,
            domain_field='alert__domain_id',
        )


@api_view(['GET', 'POST', 'PUT'])
@permission_classes([IsAuthenticated])
def alert_configuration(request):
    """
    Get or update alert configuration for a domain.
    
    GET: Retrieve configuration for domain_id
    POST/PUT: Create or update configuration
    """
    domain_id = request.query_params.get('domain_id') or request.data.get('domain_id')
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    try:
        from domains.models import Domain
        domain = Domain.objects.get(id=domain_id)
        
        # Check permissions
        user = request.user
        if domain.organisation != user.organisation:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        if request.method == 'GET':
            # Get existing configuration or return defaults
            config = AlertConfiguration.objects.filter(domain_id=domain_id).first()
            if config:
                serializer = AlertConfigurationSerializer(config)
                return Response(serializer.data)
            else:
                # Return default configuration
                return Response({
                    'domain': domain_id,
                    'alerts_enabled': True,
                    'quiet_hours_enabled': False,
                    'quiet_hours_start': None,
                    'quiet_hours_end': None,
                    'digest_frequency': 'realtime',
                    'email_enabled': True,
                    'email_address': None,
                    'slack_enabled': False,
                    'slack_channel': None,
                    'slack_webhook_url': None,
                    'sms_enabled': False,
                    'phone_number': None,
                })
        
        elif request.method in ['POST', 'PUT']:
            # Create or update configuration
            # organisation is deliberately left NULL on a domain-scoped config.
            # AlertConfiguration has two partial unique constraints — one per
            # domain, one per organisation — so setting both FKs makes the row
            # occupy its organisation's single slot, and the *second* domain in
            # that org then fails with a unique_org_config violation on save.
            config, created = AlertConfiguration.objects.get_or_create(
                domain_id=domain_id,
                defaults={}
            )

            # Update fields from request data
            data = request.data.copy()
            data['domain'] = domain_id
            
            serializer = AlertConfigurationSerializer(config, data=data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data, status=status.HTTP_200_OK if not created else status.HTTP_201_CREATED)
            else:
                return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_email_config(request):
    """
    Update email address for alert configuration.
    
    POST: Update email address for domain_id
    """
    domain_id = request.data.get('domain_id')
    email_address = request.data.get('email_address')
    
    if not domain_id:
        return Response(
            {'error': 'domain_id is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    if not email_address:
        return Response(
            {'error': 'email_address is required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate every address. The field accepts a comma-separated list so a team
    # can be alerted, and one bad entry must fail the whole save rather than be
    # stored silently and then bounce at send time.
    from django.core.validators import validate_email
    from django.core.exceptions import ValidationError

    addresses = [part.strip() for part in str(email_address).split(',') if part.strip()]
    if not addresses:
        return Response(
            {'error': 'email_address is required'},
            status=status.HTTP_400_BAD_REQUEST
        )

    invalid = []
    for address in addresses:
        try:
            validate_email(address)
        except ValidationError:
            invalid.append(address)
    if invalid:
        return Response(
            {'error': f"Invalid email address format: {', '.join(invalid)}"},
            status=status.HTTP_400_BAD_REQUEST
        )

    # Store de-duplicated and normalised so the list stays readable on re-edit.
    seen = set()
    deduped = []
    for address in addresses:
        key = address.lower()
        if key not in seen:
            seen.add(key)
            deduped.append(address)
    email_address = ', '.join(deduped)
    
    try:
        from domains.models import Domain
        domain = Domain.objects.get(id=domain_id)
        
        # Check permissions
        user = request.user
        if domain.organisation != user.organisation:
            return Response(
                {'error': 'Permission denied'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Get or create configuration
        # Domain-scoped: organisation stays NULL. See the note in
        # alert_configuration — setting both FKs trips unique_org_config for
        # every domain after the first in the same organisation.
        config, created = AlertConfiguration.objects.get_or_create(
            domain_id=domain_id,
            defaults={
                'email_enabled': True,
                'email_address': email_address
            }
        )
        
        # Update email address
        config.email_address = email_address
        config.email_enabled = True
        config.save()
        
        serializer = AlertConfigurationSerializer(config)
        return Response(serializer.data, status=status.HTTP_200_OK)
    
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except Exception as e:
        return Response(
            {'error': str(e)}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

