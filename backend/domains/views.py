from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.db.models import Q
from .models import Domain, DetectedModel, DomainAccess
from .serializers import (
    DomainSerializer, DomainDetailSerializer, DetectedModelSerializer,
    DomainAccessSerializer, DomainAccessCreateSerializer
)
from authentication.serializers import AccountSerializer
from authentication.models import Account


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def domain_list(request):
    """List all domains for the organization or create a new one"""
    if request.method == 'GET':
        # Filter domains by organization and user access
        if request.user.role == 'admin':
            # Admins can see all domains in their organization
            domains = Domain.objects.filter(organisation=request.user.organisation)
        else:
            # Regular users can only see domains they have access to
            domain_ids = DomainAccess.objects.filter(
                user=request.user,
                domain__organisation=request.user.organisation
            ).values_list('domain_id', flat=True)
            domains = Domain.objects.filter(id__in=domain_ids)
        
        serializer = DomainSerializer(domains, many=True)
        return Response({
            'domains': serializer.data
        })
    
    elif request.method == 'POST':
        # Only admins can create domains
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only organization administrators can add domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        # Add organization to the data
        data = request.data.copy()
        data['organisation'] = request.user.organisation.id
        
        serializer = DomainSerializer(data=data)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Domain added successfully',
                'domain': serializer.data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def domain_detail(request, pk):
    """Retrieve, update or delete a domain"""
    try:
        if request.user.role == 'admin':
            domain = Domain.objects.get(pk=pk, organisation=request.user.organisation)
        else:
            # Check if user has access to this domain
            domain_access = DomainAccess.objects.get(
                user=request.user,
                domain_id=pk,
                domain__organisation=request.user.organisation
            )
            domain = domain_access.domain
    except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
        return Response(
            {'error': 'Domain not found or you do not have access to this domain'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = DomainDetailSerializer(domain)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admins can update domains
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only organization administrators can update domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DomainSerializer(domain, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Domain updated successfully',
                'domain': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        # Only admins can delete domains
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only organization administrators can delete domains'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        domain.delete()
        return Response({
            'message': 'Domain deleted successfully'
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def domain_keywords(request, pk):
    """Get all keywords for a domain"""
    try:
        if request.user.role == 'admin':
            domain = Domain.objects.get(pk=pk, organisation=request.user.organisation)
        else:
            domain_access = DomainAccess.objects.get(
                user=request.user,
                domain_id=pk,
                domain__organisation=request.user.organisation
            )
            domain = domain_access.domain
    except (Domain.DoesNotExist, DomainAccess.DoesNotExist):
        return Response(
            {'error': 'Domain not found or you do not have access to this domain'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    keywords = domain.keywords.all()
    from keywords.serializers import KeywordSerializer
    serializer = KeywordSerializer(keywords, many=True)
    return Response(serializer.data)


# Domain Access Management Views
@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def domain_access_list(request, domain_id):
    """Get all users with access to a domain or grant access to a user"""
    # Only admins can manage domain access
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only organization administrators can manage domain access'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        access_list = DomainAccess.objects.filter(domain=domain)
        serializer = DomainAccessSerializer(access_list, many=True)
        return Response({
            'access_list': serializer.data
        })
    
    elif request.method == 'POST':
        serializer = DomainAccessCreateSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            # Check if user is in the same organization
            user_id = serializer.validated_data['user_id']
            try:
                user = Account.objects.get(id=user_id)
                if user.organisation != request.user.organisation:
                    return Response(
                        {'error': 'User must be in the same organization'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
            except Account.DoesNotExist:
                return Response(
                    {'error': 'User not found'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Set domain
            serializer.validated_data['domain'] = domain
            
            access = serializer.save()
            return Response({
                'message': 'Access granted successfully',
                'access': DomainAccessSerializer(access).data
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def domain_access_detail(request, domain_id, user_id):
    """Update or revoke domain access for a user"""
    # Only admins can manage domain access
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only organization administrators can manage domain access'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
        domain_access = DomainAccess.objects.get(domain=domain, user_id=user_id)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    except DomainAccess.DoesNotExist:
        return Response(
            {'error': 'User does not have access to this domain'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'PUT':
        serializer = DomainAccessSerializer(domain_access, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Access updated successfully',
                'access': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    elif request.method == 'DELETE':
        domain_access.delete()
        return Response({
            'message': 'Access revoked successfully'
        })


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def available_users_for_domain(request, domain_id):
    """Get users available for domain access (users in organization not already granted access)"""
    # Only admins can view available users
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only organization administrators can view available users'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    try:
        domain = Domain.objects.get(id=domain_id, organisation=request.user.organisation)
    except Domain.DoesNotExist:
        return Response(
            {'error': 'Domain not found or not in your organization'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Get users in organization who don't already have access to this domain
    users_with_access = DomainAccess.objects.filter(domain=domain).values_list('user_id', flat=True)
    available_users = request.user.organisation.accounts.exclude(id__in=users_with_access)
    
    users_data = []
    for user in available_users:
        users_data.append({
            'id': user.id,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'role': user.role,
        })
    
    return Response({
        'available_users': users_data
    })


# Detected Models Views
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def detected_models_list(request):
    """Get all detected models for the organization"""
    if request.user.role == 'admin':
        # Admins can see all detected models in their organization
        detected_models = DetectedModel.objects.filter(organisation=request.user.organisation)
    else:
        # Regular users can only see detected models for domains they have access to
        domain_ids = DomainAccess.objects.filter(
            user=request.user,
            domain__organisation=request.user.organisation
        ).values_list('domain_id', flat=True)
        detected_models = DetectedModel.objects.filter(
            domain_id__in=domain_ids,
            organisation=request.user.organisation
        )
    
    serializer = DetectedModelSerializer(detected_models, many=True)
    return Response({
        'detected_models': serializer.data
    })


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def detected_model_detail(request, pk):
    """Get or update a detected model"""
    try:
        if request.user.role == 'admin':
            detected_model = DetectedModel.objects.get(pk=pk, organisation=request.user.organisation)
        else:
            # Check if user has access to the domain
            detected_model = DetectedModel.objects.get(pk=pk, organisation=request.user.organisation)
            DomainAccess.objects.get(
                user=request.user,
                domain=detected_model.domain
            )
    except (DetectedModel.DoesNotExist, DomainAccess.DoesNotExist):
        return Response(
            {'error': 'Detected model not found or you do not have access'}, 
            status=status.HTTP_404_NOT_FOUND
        )
    
    if request.method == 'GET':
        serializer = DetectedModelSerializer(detected_model)
        return Response(serializer.data)
    
    elif request.method == 'PUT':
        # Only admins can update detected models
        if request.user.role != 'admin':
            return Response(
                {'error': 'Only organization administrators can update detected models'}, 
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = DetectedModelSerializer(detected_model, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'message': 'Detected model updated successfully',
                'detected_model': serializer.data
            })
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)