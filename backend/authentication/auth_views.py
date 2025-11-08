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
from .models import Account, Organisation, TeamInvitation, UserPermission, PasswordResetToken
from .serializers import (
    AccountSerializer, AccountUpdateSerializer,
    TeamInvitationSerializer, TeamInvitationCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer,
    PasswordResetTokenSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
)


@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate using email (USERNAME_FIELD is now 'email')
    user = authenticate(request, email=email, password=password)
    if user and user.is_active:
        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        access_token['email'] = user.email
        access_token['role'] = user.role
        access_token['organisation_id'] = user.organisation.id if user.organisation else None
        access_token['organisation_name'] = user.organisation.name if user.organisation else None
        permissions = UserPermission.objects.filter(user=user)
        permission_data = UserPermissionSerializer(permissions, many=True).data
        return Response({
            'access': str(access_token),
            'refresh': str(refresh),
            'user': AccountSerializer(user).data,
            'permissions': permission_data,
            'message': 'Login successful'
        })
    return Response({'error': 'Invalid credentials or account inactive'}, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request):
    user = request.user
    permissions = UserPermission.objects.filter(user=user)
    return Response({'user': AccountSerializer(user).data, 'permissions': UserPermissionSerializer(permissions, many=True).data})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def profile_update(request):
    user = request.user
    serializer = AccountUpdateSerializer(user, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response({'message': 'Profile updated successfully', 'user': AccountSerializer(user).data})
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['PUT', 'PATCH'])
@permission_classes([IsAuthenticated])
def update_active_domain(request):
    """
    Update the active domain for the current user.
    Validates that the domain exists and belongs to the user's organisation.
    """
    import logging
    logger = logging.getLogger(__name__)
    
    user = request.user
    domain_id = request.data.get('domain_id')
    
    logger.info(f"[update_active_domain] User {user.id} ({user.email}) - Received domain_id: {domain_id} (type: {type(domain_id)})")
    logger.info(f"[update_active_domain] Request data: {request.data}")
    
    if domain_id is None:
        # Allow clearing the active domain
        logger.info(f"[update_active_domain] Clearing active domain for user {user.id}")
        user.active_domain_id = None
        user.save(update_fields=['active_domain_id', 'modified_at'])
        return Response({
            'message': 'Active domain cleared successfully',
            'user': AccountSerializer(user).data
        })
    
    try:
        domain_id = int(domain_id)
        logger.info(f"[update_active_domain] Converted domain_id to int: {domain_id}")
    except (ValueError, TypeError) as e:
        logger.error(f"[update_active_domain] Failed to convert domain_id to int: {e}")
        return Response(
            {'error': 'domain_id must be a valid integer'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # Validate domain exists and belongs to user's organisation
    from domains.models import Domain
    try:
        domain = Domain.objects.get(id=domain_id)
        logger.info(f"[update_active_domain] Found domain: {domain.id} ({domain.name}) - Organisation: {domain.organisation_id}")
        if domain.organisation_id != user.organisation_id:
            logger.warning(f"[update_active_domain] Domain {domain_id} does not belong to user's organisation {user.organisation_id}")
            return Response(
                {'error': 'Domain does not belong to your organisation'},
                status=status.HTTP_403_FORBIDDEN
            )
    except Domain.DoesNotExist:
        logger.error(f"[update_active_domain] Domain {domain_id} not found")
        return Response(
            {'error': 'Domain not found'},
            status=status.HTTP_404_NOT_FOUND
        )
    
    # Update active domain
    logger.info(f"[update_active_domain] Updating user {user.id} active_domain_id from {user.active_domain_id} to {domain_id}")
    user.active_domain_id = domain_id
    user.save(update_fields=['active_domain_id', 'modified_at'])
    
    # Verify it was saved
    user.refresh_from_db()
    logger.info(f"[update_active_domain] Verified saved active_domain_id: {user.active_domain_id}")
    
    return Response({
        'message': 'Active domain updated successfully',
        'user': AccountSerializer(user).data
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout(request):
    try:
        refresh_token = request.data.get('refresh')
        if refresh_token:
            try:
                token = RefreshToken(refresh_token)
                if hasattr(token, 'blacklist'):
                    token.blacklist()
                return Response({'message': 'Logout successful'})
            except Exception:
                return Response({'message': 'Logout successful (token was already invalid)'})
        return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        return Response({'error': f'Logout failed: {str(e)}'}, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_invitation(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can send invitations'}, status=status.HTTP_403_FORBIDDEN)
    serializer = TeamInvitationCreateSerializer(data=request.data, context={'organisation': request.user.organisation})
    if serializer.is_valid():
        invitation = serializer.save(invited_by=request.user, organisation=request.user.organisation, expires_at=timezone.now() + timezone.timedelta(days=7))
        try:
            subject = f"Invitation to join {invitation.organisation.name}"
            invitation_url = f"{settings.SITE_URL}/accept-invitation/{invitation.id}"
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
            send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[invitation.email], fail_silently=False)
            return Response({'message': 'Invitation sent successfully', 'invitation': TeamInvitationSerializer(invitation).data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_invitation_details(request, invitation_id):
    try:
        invitation = get_object_or_404(TeamInvitation, id=invitation_id)
        if not invitation.can_be_accepted():
            return Response({'error': 'Invitation has expired or is no longer valid'}, status=status.HTTP_400_BAD_REQUEST)
        if Account.objects.filter(email=invitation.email).exists():
            return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        return Response(TeamInvitationSerializer(invitation).data, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': f'Failed to get invitation details: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def accept_invitation(request, invitation_id):
    try:
        invitation = get_object_or_404(TeamInvitation, id=invitation_id)
        if not invitation.can_be_accepted():
            return Response({'error': 'Invitation has expired or is no longer valid'}, status=status.HTTP_400_BAD_REQUEST)
        if Account.objects.filter(email=invitation.email).exists():
            return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        user = Account.objects.create_user(username=invitation.email, email=invitation.email, password=password, first_name=first_name, last_name=last_name, role=invitation.role, organisation=invitation.organisation, is_active=True)
        invitation.status = 'accepted'
        invitation.accepted_at = timezone.now()
        invitation.save()
        default_permissions = [('dashboard', 'read'), ('mentions', 'read'), ('prompts', 'read')]
        for module, permission_level in default_permissions:
            UserPermission.objects.create(user=user, module=module, permission_level=permission_level, granted_by=invitation.invited_by)
        return Response({'message': 'Invitation accepted successfully', 'user': AccountSerializer(user).data}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({'error': f'Failed to accept invitation: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password(request):
    serializer = ForgotPasswordSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        try:
            user = Account.objects.get(email=email, is_active=True)
            PasswordResetToken.objects.filter(user=user, status='pending').update(status='expired')
            reset_token = PasswordResetToken.objects.create(user=user, expires_at=timezone.now() + timezone.timedelta(hours=1))
            subject = "Password Reset Request - LLM Monitor"
            reset_url = f"{settings.SITE_URL}/reset-password/{reset_token.id}"
            message = f"""
            Hello {user.first_name or 'User'},

            You have requested to reset your password for your LLM Monitor account.

            To reset your password, click the link below:
            {reset_url}

            This link will expire in 1 hour for security reasons.

            If you did not request this password reset, please ignore this email.
            Your password will remain unchanged.

            Best regards,
            LLM Monitor Team
            """
            send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[email], fail_silently=False)
            return Response({'message': 'Password reset email sent successfully', 'email': email}, status=status.HTTP_200_OK)
        except Account.DoesNotExist:
            return Response({'message': 'If an account with this email exists, a password reset email has been sent'}, status=status.HTTP_200_OK)
        except Exception as e:
            return Response({'error': f'Failed to send password reset email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request):
    serializer = ResetPasswordSerializer(data=request.data)
    if serializer.is_valid():
        token_id = serializer.validated_data['token']
        new_password = serializer.validated_data['new_password']
        try:
            reset_token = PasswordResetToken.objects.get(id=token_id)
            if not reset_token.can_be_used():
                return Response({'error': 'Invalid or expired reset token'}, status=status.HTTP_400_BAD_REQUEST)
            user = reset_token.user
            user.set_password(new_password)
            user.save()
            reset_token.status = 'used'
            reset_token.used_at = timezone.now()
            reset_token.save()
            PasswordResetToken.objects.filter(user=user, status='pending').exclude(id=token_id).update(status='expired')
            return Response({'message': 'Password reset successfully', 'email': user.email}, status=status.HTTP_200_OK)
        except PasswordResetToken.DoesNotExist:
            return Response({'error': 'Invalid reset token'}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({'error': f'Failed to reset password: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_reset_token(request, token_id):
    try:
        reset_token = PasswordResetToken.objects.get(id=token_id)
        if reset_token.can_be_used():
            return Response({'valid': True, 'email': reset_token.user.email, 'expires_at': reset_token.expires_at}, status=status.HTTP_200_OK)
        return Response({'valid': False, 'error': 'Token has expired or been used'}, status=status.HTTP_400_BAD_REQUEST)
    except PasswordResetToken.DoesNotExist:
        return Response({'valid': False, 'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


# The rest of the permission and organization management endpoints remain identical
# Import all remaining functions from the existing simplified_auth_views to avoid duplication during refactor
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def assign_permissions(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can assign permissions'}, status=status.HTTP_403_FORBIDDEN)
    serializer = UserPermissionCreateSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        permission = serializer.save(granted_by=request.user)
        return Response({'message': 'Permission assigned successfully', 'permission': UserPermissionSerializer(permission).data}, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_permissions(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can view permissions'}, status=status.HTTP_403_FORBIDDEN)
    org_users = Account.objects.filter(organisation=request.user.organisation)
    permissions = UserPermission.objects.filter(user__in=org_users)
    user_id = request.GET.get('user_id')
    module = request.GET.get('module')
    if user_id:
        permissions = permissions.filter(user_id=user_id)
    if module:
        permissions = permissions.filter(module=module)
    serializer = UserPermissionSerializer(permissions, many=True)
    return Response({'permissions': serializer.data, 'total_count': permissions.count(), 'filters_applied': {'user_id': user_id, 'module': module}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_user_permissions(request, user_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can view user permissions'}, status=status.HTTP_403_FORBIDDEN)
    try:
        target_user = Account.objects.get(id=user_id, organisation=request.user.organisation)
    except Account.DoesNotExist:
        return Response({'error': 'User not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    permissions = UserPermission.objects.filter(user=target_user)
    serializer = UserPermissionSerializer(permissions, many=True)
    return Response({'user': AccountSerializer(target_user).data, 'permissions': serializer.data, 'total_count': permissions.count()})


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_permission(request, permission_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can modify permissions'}, status=status.HTTP_403_FORBIDDEN)
    try:
        permission = UserPermission.objects.get(id=permission_id)
    except UserPermission.DoesNotExist:
        return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)
    if permission.user.organisation != request.user.organisation:
        return Response({'error': 'Permission does not belong to your organization'}, status=status.HTTP_403_FORBIDDEN)
    new_permission_level = request.data.get('permission_level')
    if not new_permission_level:
        return Response({'error': 'permission_level is required'}, status=status.HTTP_400_BAD_REQUEST)
    valid_levels = [choice[0] for choice in UserPermission.PERMISSION_CHOICES]
    if new_permission_level not in valid_levels:
        return Response({'error': f'Invalid permission level. Must be one of: {valid_levels}'}, status=status.HTTP_400_BAD_REQUEST)
    permission.permission_level = new_permission_level
    permission.save()
    return Response({'message': 'Permission updated successfully', 'permission': UserPermissionSerializer(permission).data})


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_permission(request, permission_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can delete permissions'}, status=status.HTTP_403_FORBIDDEN)
    try:
        permission = UserPermission.objects.get(id=permission_id)
    except UserPermission.DoesNotExist:
        return Response({'error': 'Permission not found'}, status=status.HTTP_404_NOT_FOUND)
    if permission.user.organisation != request.user.organisation:
        return Response({'error': 'Permission does not belong to your organization'}, status=status.HTTP_403_FORBIDDEN)
    permission.delete()
    return Response({'message': 'Permission deleted successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_available_modules(request):
    return Response({
        'modules': [{'value': choice[0], 'label': choice[1]} for choice in UserPermission.MODULE_CHOICES],
        'permission_levels': [{'value': choice[0], 'label': choice[1]} for choice in UserPermission.PERMISSION_CHOICES]
    })


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def bulk_assign_permissions(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can bulk assign permissions'}, status=status.HTTP_403_FORBIDDEN)
    permissions_data = request.data.get('permissions', [])
    if not permissions_data:
        return Response({'error': 'permissions array is required'}, status=status.HTTP_400_BAD_REQUEST)
    created_permissions = []
    errors = []
    for perm_data in permissions_data:
        try:
            user_id = perm_data.get('user')
            if not user_id:
                errors.append({'error': 'user is required', 'data': perm_data})
                continue
            try:
                user = Account.objects.get(id=user_id, organisation=request.user.organisation)
            except Account.DoesNotExist:
                errors.append({'error': 'User not found or not in organization', 'data': perm_data})
                continue
            permission, created = UserPermission.objects.get_or_create(
                user=user,
                module=perm_data.get('module'),
                defaults={'permission_level': perm_data.get('permission_level'), 'granted_by': request.user}
            )
            if not created:
                permission.permission_level = perm_data.get('permission_level')
                permission.granted_by = request.user
                permission.save()
            created_permissions.append(UserPermissionSerializer(permission).data)
        except Exception as e:
            errors.append({'error': str(e), 'data': perm_data})
    return Response({'message': f'Bulk assignment completed. {len(created_permissions)} permissions processed.', 'created_permissions': created_permissions, 'errors': errors, 'success_count': len(created_permissions), 'error_count': len(errors)})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def revoke_all_permissions(request, user_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can revoke permissions'}, status=status.HTTP_403_FORBIDDEN)
    try:
        target_user = Account.objects.get(id=user_id, organisation=request.user.organisation)
    except Account.DoesNotExist:
        return Response({'error': 'User not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    deleted_count = UserPermission.objects.filter(user=target_user).delete()[0]
    return Response({'message': f'All permissions revoked successfully. {deleted_count} permissions removed.', 'deleted_count': deleted_count})


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def grant_all_permissions(request, user_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can grant permissions'}, status=status.HTTP_403_FORBIDDEN)
    try:
        target_user = Account.objects.get(id=user_id, organisation=request.user.organisation)
    except Account.DoesNotExist:
        return Response({'error': 'User not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    permission_level = request.data.get('permission_level', 'read')
    valid_levels = [choice[0] for choice in UserPermission.PERMISSION_CHOICES]
    if permission_level not in valid_levels:
        return Response({'error': f'Invalid permission level. Must be one of: {valid_levels}'}, status=status.HTTP_400_BAD_REQUEST)
    created_permissions = []
    for module_value, module_label in UserPermission.MODULE_CHOICES:
        permission, created = UserPermission.objects.get_or_create(
            user=target_user,
            module=module_value,
            defaults={'permission_level': permission_level, 'granted_by': request.user}
        )
        if created:
            created_permissions.append(UserPermissionSerializer(permission).data)
    return Response({'message': f'All permissions granted successfully. {len(created_permissions)} permissions created.', 'created_permissions': created_permissions, 'created_count': len(created_permissions)})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_permission_summary(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can view permission summary'}, status=status.HTTP_403_FORBIDDEN)
    org_users = Account.objects.filter(organisation=request.user.organisation)
    module_counts = {}
    for module_value, module_label in UserPermission.MODULE_CHOICES:
        count = UserPermission.objects.filter(user__in=org_users, module=module_value).count()
        module_counts[module_value] = {'label': module_label, 'count': count, 'total_users': org_users.count()}
    user_permission_counts = []
    total_modules = len(UserPermission.MODULE_CHOICES)
    for user in org_users:
        permission_count = UserPermission.objects.filter(user=user).count()
        user_permission_counts.append({'user_id': user.id, 'user_email': user.email, 'user_name': f"{user.first_name} {user.last_name}".strip(), 'permission_count': permission_count, 'total_modules': total_modules, 'percentage': round((permission_count / total_modules) * 100, 1) if total_modules > 0 else 0})
    return Response({'module_counts': module_counts, 'user_permission_counts': user_permission_counts, 'total_users': org_users.count(), 'total_modules': total_modules})


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def organization_management(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can manage organization settings'}, status=status.HTTP_403_FORBIDDEN)
    organization = request.user.organisation
    if request.method == 'GET':
        return Response({'id': organization.id, 'name': organization.name, 'team_count': organization.team_count, 'created_at': organization.created_at, 'modified_at': organization.modified_at})
    name = request.data.get('name')
    if name:
        organization.name = name
    organization.save()
    return Response({'message': 'Organization updated successfully', 'organization': {'id': organization.id, 'name': organization.name, 'team_count': organization.team_count, 'created_at': organization.created_at, 'modified_at': organization.modified_at}})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members(request):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can view team members'}, status=status.HTTP_403_FORBIDDEN)
    members = Account.objects.filter(organisation=request.user.organisation).exclude(role='super_admin')
    members_data = []
    for member in members:
        members_data.append({'id': member.id, 'email': member.email, 'first_name': member.first_name, 'last_name': member.last_name, 'role': member.role, 'organisation': member.organisation.id, 'organisation_name': member.organisation.name, 'is_active': member.is_active, 'created_at': member.created_at, 'modified_at': member.modified_at})
    invitations_qs = TeamInvitation.objects.filter(organisation=request.user.organisation).exclude(status='accepted').order_by('-created_at')
    invitations_data = []
    for inv in invitations_qs:
        invitations_data.append({'id': str(inv.id), 'email': inv.email, 'role': inv.role, 'status': inv.status, 'invited_by': inv.invited_by.id, 'invited_by_email': inv.invited_by.email, 'expires_at': inv.expires_at, 'accepted_at': inv.accepted_at, 'created_at': inv.created_at})
    return Response({'members': members_data, 'invitations': invitations_data})


@api_view(['PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def team_member_management(request, member_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can manage team members'}, status=status.HTTP_403_FORBIDDEN)
    try:
        member = Account.objects.get(id=member_id, organisation=request.user.organisation)
    except Account.DoesNotExist:
        return Response({'error': 'Team member not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    if member.role == 'super_admin':
        return Response({'error': 'Super admin accounts cannot be viewed or edited via team management'}, status=status.HTTP_403_FORBIDDEN)
    if request.method == 'PUT':
        new_role = request.data.get('role')
        if new_role not in ['admin', 'user']:
            return Response({'error': 'Invalid role. Must be admin or user'}, status=status.HTTP_400_BAD_REQUEST)
        member.role = new_role
        member.save()

        # Synchronize module permissions based on updated role
        module_values = [value for value, _ in UserPermission.MODULE_CHOICES]
        if new_role == 'admin':
            for module_value in module_values:
                perm, created = UserPermission.objects.get_or_create(
                    user=member,
                    module=module_value,
                    defaults={'permission_level': 'admin', 'granted_by': request.user}
                )
                if not created:
                    perm.permission_level = 'admin'
                    perm.granted_by = request.user
                    perm.save()
        else:
            for module_value in module_values:
                if module_value == 'organization_settings':
                    UserPermission.objects.filter(user=member, module=module_value).delete()
                    continue
                perm, created = UserPermission.objects.get_or_create(
                    user=member,
                    module=module_value,
                    defaults={'permission_level': 'read', 'granted_by': request.user}
                )
                if not created:
                    perm.permission_level = 'read'
                    perm.granted_by = request.user
                    perm.save()

        return Response({'message': 'Team member role updated successfully', 'member': {'id': member.id, 'email': member.email, 'first_name': member.first_name, 'last_name': member.last_name, 'role': member.role, 'organisation': member.organisation.id, 'organisation_name': member.organisation.name, 'is_active': member.is_active, 'created_at': member.created_at, 'modified_at': member.modified_at}})
    member.is_active = False
    member.save()
    organization = request.user.organisation
    organization.team_count = Account.objects.filter(organisation=organization, is_active=True).count()
    organization.save()
    return Response({'message': 'Team member removed successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def check_permissions(request):
    module = request.GET.get('module')
    if module:
        try:
            permission = UserPermission.objects.get(user=request.user, module=module)
            return Response({'module': module, 'permission_level': permission.permission_level, 'has_access': True})
        except UserPermission.DoesNotExist:
            return Response({'module': module, 'permission_level': None, 'has_access': False})
    permissions = UserPermission.objects.filter(user=request.user)
    serializer = UserPermissionSerializer(permissions, many=True)
    return Response({'permissions': serializer.data, 'user': AccountSerializer(request.user).data})


