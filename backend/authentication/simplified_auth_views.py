from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.shortcuts import get_object_or_404
from django.core.mail import send_mail
from django.utils import timezone
from django.conf import settings
from .models import Account, Organisation, TeamInvitation, UserPermission
from .serializers import (
    AccountSerializer, AccountUpdateSerializer,
    TeamInvitationSerializer, TeamInvitationCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    """
    Login API for organisation or user
    Returns JWT tokens for further API access
    """
    email = request.data.get('email')
    password = request.data.get('password')
    
    if not email or not password:
        return Response(
            {'error': 'Email and password are required'}, 
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Authenticate user
    user = authenticate(username=email, password=password)
    if user and user.is_active:
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        
        # Add custom claims to access token
        access_token['email'] = user.email
        access_token['role'] = user.role
        access_token['organisation_id'] = user.organisation.id if user.organisation else None
        access_token['organisation_name'] = user.organisation.name if user.organisation else None
        
        # Get user permissions
        permissions = UserPermission.objects.filter(user=user)
        permission_data = UserPermissionSerializer(permissions, many=True).data
        
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': AccountSerializer(user).data,
            'permissions': permission_data,
            'message': 'Login successful'
        })
    else:
        return Response(
            {'error': 'Invalid credentials or account inactive'}, 
            status=status.HTTP_401_UNAUTHORIZED
        )


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    """
    Get current user profile
    """
    user = request.user
    permissions = UserPermission.objects.filter(user=user)
    
    return Response({
        'user': AccountSerializer(user).data,
        'permissions': UserPermissionSerializer(permissions, many=True).data
    })


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    """
    Update current user profile
    """
    user = request.user
    serializer = AccountUpdateSerializer(user, data=request.data, partial=True)
    
    if serializer.is_valid():
        serializer.save()
        return Response({
            'message': 'Profile updated successfully',
            'user': AccountSerializer(user).data
        })
    else:
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    """
    Logout and blacklist refresh token
    """
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                # Try to blacklist the token
                if hasattr(token, 'blacklist'):
                    token.blacklist()
                else:
                    # If blacklist is not available, just return success
                    # The token will expire naturally
                    pass
                return Response({'message': 'Logout successful'})
            except Exception as token_error:
                # If token is invalid or expired, still return success
                return Response({'message': 'Logout successful (token was already invalid)'})
        else:
            return Response(
                {'error': 'Refresh token is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
    except Exception as e:
        return Response(
            {'error': f'Logout failed: {str(e)}'}, 
            status=status.HTTP_400_BAD_REQUEST
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invitation(request):
    """
    Send team invitation (Organisation admin only)
    """
    # Check if user is organisation admin
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only organisation administrators can send invitations'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = TeamInvitationCreateSerializer(
        data=request.data, 
        context={'organisation': request.user.organisation}
    )
    if serializer.is_valid():
        # Create invitation
        invitation = serializer.save(
            invited_by=request.user,
            organisation=request.user.organisation,
            expires_at=timezone.now() + timezone.timedelta(days=7)
        )
        
        # Send email invitation
        try:
            subject = f"Invitation to join {invitation.organisation.name}"
            invitation_url = f"http://localhost:3000/accept-invitation/{invitation.id}"
            
            message = f"""
            Hello,
            
            You have been invited to join {invitation.organisation.name} on LLM Monitor.
            
            Role: {invitation.get_role_display()}
            Invited by: {invitation.invited_by.email}
            
            {invitation.message if invitation.message else ''}
            
            To accept this invitation, click the link below:
            {invitation_url}
            
            This invitation will expire on {invitation.expires_at.strftime('%Y-%m-%d %H:%M')}.
            
            If you don't want to join, you can simply ignore this email.
            
            Best regards,
            LLM Monitor Team
            """
            
            send_mail(
                subject=subject,
                message=message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[invitation.email],
                fail_silently=False,
            )
            
            return Response({
                'message': 'Invitation sent successfully',
                'invitation': TeamInvitationSerializer(invitation).data
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Failed to send email: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_invitation(request, invitation_id):
    """
    Accept team invitation and create user account
    """
    try:
        invitation = get_object_or_404(TeamInvitation, id=invitation_id)
        
        if not invitation.can_be_accepted():
            return Response(
                {'error': 'Invitation has expired or is no longer valid'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if user already exists
        if Account.objects.filter(email=invitation.email).exists():
            return Response(
                {'error': 'User with this email already exists'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Get user data from request
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        password = request.data.get('password')
        
        if not password:
            return Response(
                {'error': 'Password is required'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Create user account
        user = Account.objects.create_user(
            username=invitation.email,
            email=invitation.email,
            password=password,
            first_name=first_name,
            last_name=last_name,
            role=invitation.role,
            organisation=invitation.organisation,
            is_active=True
        )
        
        # Update invitation status
        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()
        
        # Create default permissions for the user
        default_permissions = [
            ('dashboard', 'read'),
            ('domains', 'read'),
            ('keywords', 'read'),
        ]
        
        for module, permission_level in default_permissions:
            UserPermission.objects.create(
                user=user,
                module=module,
                permission_level=permission_level,
                granted_by=invitation.invited_by
            )
        
        return Response({
            'message': 'Invitation accepted successfully',
            'user': AccountSerializer(user).data
        }, status=status.HTTP_201_CREATED)
        
    except Exception as e:
        return Response(
            {'error': f'Failed to accept invitation: {str(e)}'}, 
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_permissions(request):
    """
    Assign permissions to users (Organisation admin only)
    """
    # Check if user is organisation admin
    if request.user.role != 'admin':
        return Response(
            {'error': 'Only organisation administrators can assign permissions'}, 
            status=status.HTTP_403_FORBIDDEN
        )
    
    serializer = UserPermissionCreateSerializer(
        data=request.data, 
        context={'request': request}
    )
    
    if serializer.is_valid():
        permission = serializer.save(granted_by=request.user)
        return Response({
            'message': 'Permission assigned successfully',
            'permission': UserPermissionSerializer(permission).data
        }, status=status.HTTP_201_CREATED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_permissions(request):
    """
    Check user permissions for accessing modules
    """
    module = request.GET.get('module')
    
    if module:
        # Check specific module permission
        try:
            permission = UserPermission.objects.get(
                user=request.user, 
                module=module
            )
            return Response({
                'module': module,
                'permission_level': permission.permission_level,
                'has_access': True
            })
        except UserPermission.DoesNotExist:
            return Response({
                'module': module,
                'permission_level': None,
                'has_access': False
            })
    else:
        # Return all user permissions
        permissions = UserPermission.objects.filter(user=request.user)
        serializer = UserPermissionSerializer(permissions, many=True)
        return Response({
            'permissions': serializer.data,
            'user': AccountSerializer(request.user).data
        })
