from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.contrib.auth.models import update_last_login
from django.shortcuts import get_object_or_404
from llm_monitor.email_utils import send_mail
from django.utils import timezone
from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from .models import Account, Organisation, TeamInvitation, UserPermission, PasswordResetToken, decrypt_value
from domains.models import Domain, DomainAccess
from .services import ClientService  # used for client login activity logging
from .serializers import (
    AccountSerializer, AccountUpdateSerializer,
    TeamInvitationSerializer, TeamInvitationCreateSerializer,
    UserPermissionSerializer, UserPermissionCreateSerializer,
    PasswordResetTokenSerializer, ForgotPasswordSerializer, ResetPasswordSerializer
)


import logging

logger = logging.getLogger(__name__)

LLM_PROVIDERS = ['openrouter', 'openai', 'gemini', 'perplexity', 'anthropic', 'xai', 'deepseek']


def _byok_providers():
    """Providers whose per-org key is genuinely used; see BYOK_PROVIDERS.

    Kept as a function so the setting is read at call time and the list can be
    changed in .env without a deploy. Anything outside it is neither shown nor
    accepted — storing a key nothing reads only creates false confidence.
    """
    configured = getattr(settings, 'BYOK_PROVIDERS', None) or ['gemini']
    return [p for p in LLM_PROVIDERS if p in configured]

# Map the engine quota-probe states → status strings the frontend renders.
_PROBE_STATE_TO_UI = {
    'OK': 'CONNECTED',
    'INVALID_KEY': 'INVALID_KEY',
    'RATE_LIMIT': 'RATE_LIMITED',
    'OUT_OF_CREDITS': 'OUT_OF_CREDITS',
    'MODEL_UNAVAILABLE': 'MODEL_UNAVAILABLE',
    'ERROR': 'ERROR',
}


def _key_status_cache_key(org_id, provider):
    return f'org_{org_id}_{provider}_keystatus'


def _validate_api_key(provider, raw_key):
    """Live-probe a freshly saved key and return a UI status string.

    Falls back to 'CONNECTED' (stored-but-unverified) if the probe genuinely
    can't run — e.g. the provider SDK isn't installed — so we never mislabel a
    real key as broken because of an environment issue.
    """
    try:
        from engine.core.quota_monitor import probe_key_state
        state, detail = probe_key_state(provider, raw_key)
        if state == 'ERROR' and 'no module named' in (detail or '').lower():
            return 'CONNECTED'
        return _PROBE_STATE_TO_UI.get(state, 'CONNECTED')
    except Exception as e:
        logger.warning(f"Key validation probe failed for {provider}: {e}")
        return 'CONNECTED'


def _get_provider_status(org, provider):
    """Return the status string for a given provider.

    Prefers the last *live-validated* status (cached when the key was saved);
    otherwise falls back to a presence-based check.
    """
    enabled = getattr(org, f'{provider}_enabled', False)
    if not enabled:
        return 'DISABLED'
    encrypted_key = getattr(org, f'{provider}_api_key', None)
    if not encrypted_key:
        # Check .env fallback
        env_map = {
            'openai': 'OPENAI_API_KEY',
            'gemini': 'GEMINI_API_KEY',
            'perplexity': 'PERPLEXITY_API_KEY',
            'anthropic': 'ANTHROPIC_API_KEY',
            'xai': 'XAI_API_KEY',
            'deepseek': 'DEEPSEEK_API_KEY',
        }
        env_key = getattr(settings, env_map.get(provider, ''), None)
        if env_key:
            return 'CONNECTED'
        return 'NOT_CONFIGURED'
    # Org key present — use the validated status from when it was saved, if known.
    validated = cache.get(_key_status_cache_key(org.id, provider))
    if validated:
        return validated
    return 'CONNECTED'


def _mask_key(raw_key):
    """Return a safe masked preview of the API key."""
    if not raw_key or len(raw_key) < 8:
        return None
    return raw_key[:6] + '••••'


def _build_api_keys_payload(org):
    """Build the API keys section of the organization GET response.

    Returns a per-provider nested object so the frontend can read
    api_keys[provider].{configured,preview,enabled,status} directly:
        {"openai": {"configured": true, "preview": "sk-abc••••",
                     "enabled": true, "status": "CONNECTED"}, ...}
    """
    payload = {}
    for provider in _byok_providers():
        encrypted = getattr(org, f'{provider}_api_key', None)
        raw = decrypt_value(encrypted) if encrypted else ''
        enabled = getattr(org, f'{provider}_enabled', True)
        payload[provider] = {
            'configured': bool(raw),
            'preview': _mask_key(raw) if raw else None,
            'enabled': enabled,
            'status': _get_provider_status(org, provider),
        }
    return payload


# Modules that confer administrative power and must never be handed out by the
# blanket "grant everything" defaults. They are granted only when an admin
# deliberately sets them, because team_management gates invitation sending —
# a read-level row here previously let any user mint new ADMIN accounts.
PRIVILEGED_MODULES = ('organization_settings', 'team_management')


def _has_team_management(user):
    """Full team management: invite any role, change roles, remove members.

    Requires the 'admin' level, not merely the presence of a row. Every invited
    user used to receive a read-level row for every module, so an existence
    check granted team management — and therefore the ability to mint ADMIN
    accounts — to the entire organisation.
    """
    if user.role in ['admin', 'super_admin']:
        return True
    return UserPermission.objects.filter(
        user=user, module='team_management', permission_level='admin'
    ).exists()


def _can_view_team(user):
    """Who may see the team roster. Everyone but clients, who are domain-scoped
    outsiders and must never enumerate the organisation's staff."""
    return user.role in ['admin', 'super_admin', 'user']


def _invitable_roles(user):
    """Roles this actor is allowed to hand out.

    A regular user may invite peers so teams can grow without an admin in the
    loop, but may not create admins (privilege escalation) or clients (that
    grants domain access, which is an administrative decision).
    """
    if _has_team_management(user):
        return {'admin', 'user', 'client'}
    if user.role == 'user':
        return {'user'}
    return set()



@api_view(['POST'])
@permission_classes([AllowAny])
def login(request):
    email = request.data.get('email')
    password = request.data.get('password')
    if not email or not password:
        return Response({'error': 'Email and password are required'}, status=status.HTTP_400_BAD_REQUEST)
    
    # Authenticate using email (USERNAME_FIELD is now 'email')
    user = authenticate(request, email=email, password=password)
    # account_status must be active: a suspended account can have is_active=True
    # but must not be allowed to start a new session.
    if user and user.is_active and getattr(user, 'account_status', 'active') == 'active':
        # This API is stateless, so it never calls django.contrib.auth.login()
        # and the user_logged_in signal that normally maintains last_login never
        # fires. Without this the column stays NULL for everyone, which makes
        # "never signed in" indistinguishable from "signs in daily" — the figure
        # is used to judge who is dormant and whether invited users onboarded.
        #
        # Only a password login counts. Token refreshes are deliberately not
        # recorded: a browser quietly renewing a token would otherwise keep a
        # dormant account looking active.
        update_last_login(None, user)

        refresh = RefreshToken.for_user(user)
        access_token = refresh.access_token
        access_token['email'] = user.email
        access_token['role'] = user.role
        access_token['organisation_id'] = user.organisation.id if user.organisation else None
        access_token['organisation_name'] = user.organisation.name if user.organisation else None
        permissions = UserPermission.objects.filter(user=user)
        permission_data = UserPermissionSerializer(permissions, many=True).data
        if user.role == 'client':
            ClientService.log_activity(user, 'login', request=request)
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
        # Domain-scoped users (user, client) may only pin a domain they have been
        # granted. Without this a client could set another client's domain active.
        from core.queryset_scoping import user_can_access_domain
        if not user_can_access_domain(user, domain_id, request):
            logger.warning(f"[update_active_domain] User {user.id} lacks access to domain {domain_id}")
            return Response(
                {'error': 'You do not have access to this domain'},
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
    allowed_roles = _invitable_roles(request.user)
    if not allowed_roles:
        return Response({'error': 'You do not have permission to send invitations'}, status=status.HTTP_403_FORBIDDEN)
    # The role is checked BEFORE the serializer so a user cannot escalate by
    # inviting an admin. Defaults to 'user' to match the serializer's default.
    requested_role = request.data.get('role', 'user')
    if requested_role not in allowed_roles:
        return Response(
            {'error': f"You can only invite the following role(s): {', '.join(sorted(allowed_roles))}"},
            status=status.HTTP_403_FORBIDDEN,
        )
    serializer = TeamInvitationCreateSerializer(data=request.data, context={'organisation': request.user.organisation})
    if serializer.is_valid():
        # TeamInvitation is unique on (email, organisation), so re-inviting
        # someone who was previously invited — a removed member, or a lapsed
        # invite — has to replace the old row instead of adding one. Without
        # this the save raised an unhandled IntegrityError.
        TeamInvitation.objects.filter(
            email=serializer.validated_data['email'],
            organisation=request.user.organisation,
        ).delete()
        invitation = serializer.save(invited_by=request.user, organisation=request.user.organisation, expires_at=timezone.now() + timezone.timedelta(days=7))
        try:
            subject = f"Invitation to join {invitation.organisation.name}"
            invitation_url = f"{settings.SITE_URL}/accept-invitation/{invitation.id}"
            message = f"""
            Hello,

            You have been invited to join {invitation.organisation.name} on Promptmaxx App.

            Role: {invitation.get_role_display()}
            Invited by: {invitation.invited_by.email}

            {invitation.message if invitation.message else ''}

            To accept this invitation, click the link below:
            {invitation_url}

            This invitation will expire on {invitation.expires_at.strftime('%Y-%m-%d %H:%M')}.

            If you don't want to join, you can simply ignore this email.

            Best regards,
            Promptmaxx App Team
            """
            send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[invitation.email], fail_silently=False)
            return Response({'message': 'Invitation sent successfully', 'invitation': TeamInvitationSerializer(invitation).data}, status=status.HTTP_201_CREATED)
        except Exception as e:
            invitation.delete()
            return Response({'error': f'Failed to send email: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


def _account_for_invitation(invitation):
    """Resolve the existing account behind an invited address as
    ``(reinstatable, conflicting)``.

    Removing a member only flips ``is_active`` off (see
    ``team_member_management``) so their reports, comments and access grants
    stay attached to them. ``Account.email`` is globally unique, so re-inviting
    that person has to revive the existing row rather than create a second one.
    Any other match — an account still active, or one in another organisation —
    is a genuine conflict and must keep being rejected.
    """
    account = Account.objects.filter(email=invitation.email).first()
    if account is None:
        return None, None
    if account.is_active or account.organisation_id != invitation.organisation_id:
        return None, account
    return account, None


def _provision_invited_user(user, invitation):
    """Give a newly accepted invitee the default rights for their role.

    Grant-everything defaults apply to staff only. Clients are domain-scoped to
    exactly the domain their invitation targeted. Callers must have cleared any
    prior grants first, so this produces the same result for a returning member
    as for a first-time invitee.
    """
    if user.role == 'client':
        if invitation.domain_id:
            # update_or_create, not get_or_create: a returning member has a
            # revoked row for this domain that needs re-enabling, and defaults
            # only apply on insert.
            DomainAccess.objects.update_or_create(
                user=user,
                domain=invitation.domain,
                defaults={'granted_by': invitation.invited_by, 'is_active': True},
            )
            user.active_domain_id = invitation.domain_id
            user.save(update_fields=['active_domain_id', 'modified_at'])
        return

    # Grant all module permissions by default - admin can revoke specific ones later.
    # PRIVILEGED_MODULES are excluded: granting team_management here (even at
    # 'read') is what let every invited user send invitations, including for
    # ADMIN accounts. Admins do not need the row — their role short-circuits
    # the check — so nothing is lost by withholding it from everyone.
    all_modules = [m[0] for m in UserPermission.MODULE_CHOICES if m[0] not in PRIVILEGED_MODULES]
    for module in all_modules:
        UserPermission.objects.create(user=user, module=module, permission_level='read', granted_by=invitation.invited_by)

    # Grant access to all existing domains in the organization
    org_domains = Domain.objects.filter(organisation=invitation.organisation)
    for domain in org_domains:
        DomainAccess.objects.update_or_create(
            user=user,
            domain=domain,
            defaults={'granted_by': invitation.invited_by, 'is_active': True}
        )


@api_view(['GET'])
@permission_classes([AllowAny])
def get_invitation_details(request, invitation_id):
    try:
        invitation = get_object_or_404(TeamInvitation, id=invitation_id)
        if not invitation.can_be_accepted():
            return Response({'error': 'Invitation has expired or is no longer valid'}, status=status.HTTP_400_BAD_REQUEST)
        _, conflict = _account_for_invitation(invitation)
        if conflict:
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
        returning_member, conflict = _account_for_invitation(invitation)
        if conflict:
            return Response({'error': 'User with this email already exists'}, status=status.HTTP_400_BAD_REQUEST)
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        password = request.data.get('password')
        if not password:
            return Response({'error': 'Password is required'}, status=status.HTTP_400_BAD_REQUEST)
        # Reactivation clears permissions before re-granting them, so a failure
        # part-way through would otherwise leave a live account with no access.
        with transaction.atomic():
            if returning_member:
                # Revive the removed member's own account so every report,
                # comment and grant they created stays theirs. They set a fresh
                # password here — the old one is not carried over.
                user = returning_member
                user.first_name = first_name
                user.last_name = last_name
                user.role = invitation.role
                user.is_active = True
                user.account_status = 'active'
                user.active_domain_id = None
                user.set_password(password)
                user.save()
                # Re-grant from a clean slate below, so a returning member lands
                # on exactly the rights a brand-new invitee of this role would
                # get. Keeping the old rows would carry a former admin's module
                # permissions, or a former staffer's org-wide domain access,
                # into a re-invite that deliberately assigns a lesser role.
                UserPermission.objects.filter(user=user).delete()
                DomainAccess.objects.filter(user=user).update(is_active=False)
            else:
                user = Account.objects.create_user(username=invitation.email, email=invitation.email, password=password, first_name=first_name, last_name=last_name, role=invitation.role, organisation=invitation.organisation, is_active=True)
            _provision_invited_user(user, invitation)
            invitation.status = 'accepted'
            invitation.accepted_at = timezone.now()
            invitation.save()
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
            subject = "Password Reset Request - Promptmaxx App"
            reset_url = f"{settings.SITE_URL}/reset-password/{reset_token.id}"
            message = f"""
            Hello {user.first_name or 'User'},

            You have requested to reset your password for your Promptmaxx App account.

            To reset your password, click the link below:
            {reset_url}

            This link will expire in 1 hour for security reasons.

            If you did not request this password reset, please ignore this email.
            Your password will remain unchanged.

            Best regards,
            Promptmaxx App Team
            """
            send_mail(subject=subject, message=message, from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[email], fail_silently=False)
            return Response({'message': 'Password reset email sent successfully', 'email': email}, status=status.HTTP_200_OK)
        except Account.DoesNotExist:
            return Response({'message': 'If an account with this email exists, a password reset email has been sent'}, status=status.HTTP_200_OK)
        except Exception as e:
            if 'reset_token' in locals():
                reset_token.delete()
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
    user = request.user

    if request.method == 'GET':
        response_data = {
            'id': organization.id,
            'name': organization.name,
            'industry': organization.industry,
            'company_size': organization.company_size,
            'goals': organization.goals,
            'using_ai_monitoring': organization.using_ai_monitoring,
            'team_count': organization.team_count,
            'created_at': organization.created_at,
            'modified_at': organization.modified_at,
            # Invoice Details tab — the Consignee / Buyer block.
            **{f: getattr(organization, f) for f in ('billing_legal_name', 'billing_address', 'billing_gstin', 'billing_state_name', 'billing_state_code', 'billing_alt_legal_name', 'billing_alt_address', 'billing_alt_gstin', 'billing_alt_state_name', 'billing_alt_state_code')},
        }
        if request.user.role == 'super_admin':
            response_data['api_keys'] = _build_api_keys_payload(organization)
        return Response(response_data)

    # ----- PUT -----
    # Update general organization fields
    if 'name' in request.data:
        organization.name = request.data.get('name')
    if 'industry' in request.data:
        organization.industry = request.data.get('industry')
    if 'company_size' in request.data:
        organization.company_size = request.data.get('company_size')
    if 'goals' in request.data:
        organization.goals = request.data.get('goals', [])
    for field in ('billing_legal_name', 'billing_address', 'billing_gstin', 'billing_state_name', 'billing_state_code', 'billing_alt_legal_name', 'billing_alt_address', 'billing_alt_gstin', 'billing_alt_state_name', 'billing_alt_state_code'):
        if field in request.data:
            setattr(organization, field, request.data.get(field) or "")
    # Update API keys and enabled toggles per provider
    is_key_update = False
    for provider in LLM_PROVIDERS:
        if f'{provider}_api_key' in request.data or f'{provider}_enabled' in request.data:
            is_key_update = True
            if provider not in _byok_providers():
                return Response(
                    {'error': f'{provider} is not configurable: it authenticates through '
                              f'OpenRouter or is not an enabled platform.'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            break

    if is_key_update and request.user.role != 'super_admin':
        return Response({'error': 'Only super administrators can manage API keys'}, status=status.HTTP_403_FORBIDDEN)

    if 'using_ai_monitoring' in request.data:
        organization.using_ai_monitoring = request.data.get('using_ai_monitoring')

    # Update API keys and enabled toggles per provider
    from .models import encrypt_value
    for provider in _byok_providers():
        key_field = f'{provider}_api_key'
        enabled_field = f'{provider}_enabled'

        # Toggle update
        if enabled_field in request.data:
            setattr(organization, enabled_field, bool(request.data.get(enabled_field)))

        # Key update — only if field is present in request
        if key_field in request.data:
            new_key = request.data.get(key_field)
            if new_key == '' or new_key is None:
                # Empty string or null → delete the key
                setattr(organization, key_field, None)
                cache.delete(_key_status_cache_key(organization.id, provider))
            else:
                # Encrypt and store the new key, then live-validate it so the UI
                # reflects whether the key actually works (not just that it exists).
                new_key = new_key.strip()
                setattr(organization, key_field, encrypt_value(new_key))
                validated_status = _validate_api_key(provider, new_key)
                cache.set(
                    _key_status_cache_key(organization.id, provider),
                    validated_status,
                    86400,  # 24h; re-validated whenever the key is re-saved
                )

    organization.save()

    # Invalidate the Redis cache for this organisation's settings
    cache.delete(f'org_{organization.id}_settings')

    # Update user's job role if provided
    if 'user_role' in request.data:
        user.job_role = request.data.get('user_role')
        user.save(update_fields=['job_role', 'modified_at'])

    response_payload = {
        'message': 'Organization updated successfully',
        'organization': {
            'id': organization.id,
            'name': organization.name,
            'industry': organization.industry,
            'company_size': organization.company_size,
            'goals': organization.goals,
            'using_ai_monitoring': organization.using_ai_monitoring,
            'team_count': organization.team_count,
            'created_at': organization.created_at,
            'modified_at': organization.modified_at,
            # Invoice Details tab — the Consignee / Buyer block.
            **{f: getattr(organization, f) for f in ('billing_legal_name', 'billing_address', 'billing_gstin', 'billing_state_name', 'billing_state_code', 'billing_alt_legal_name', 'billing_alt_address', 'billing_alt_gstin', 'billing_alt_state_name', 'billing_alt_state_code')},
        }
    }
    if request.user.role == 'super_admin':
        response_payload['organization']['api_keys'] = _build_api_keys_payload(organization)

    return Response(response_payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reveal_api_key(request, provider):
    """Return the decrypted plaintext API key for a single provider, on demand.

    The default organization settings response only exposes a masked preview
    (see _build_api_keys_payload). This endpoint lets an authorised admin
    reveal or copy the real key without it ever being preloaded into the page.

    Security:
      - Admin / super_admin only (same gate as organization_management).
      - Provider name is validated against the known LLM_PROVIDERS allow-list.
      - The decrypted key is never logged.
      - Response is marked no-store so it is never cached by browsers/proxies.
    """
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can reveal API keys'},
            status=status.HTTP_403_FORBIDDEN,
        )

    if provider not in _byok_providers():
        return Response(
            {'error': 'Unknown provider'},
            status=status.HTTP_400_BAD_REQUEST,
        )

    organization = request.user.organisation
    encrypted = getattr(organization, f'{provider}_api_key', None)
    raw = decrypt_value(encrypted) if encrypted else ''
    if not raw:
        return Response(
            {'error': 'No API key configured for this provider'},
            status=status.HTTP_404_NOT_FOUND,
        )

    response = Response({'provider': provider, 'api_key': raw})
    # Never let the plaintext key linger in any cache layer.
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


# ---------------------------------------------------------------------------
# Dedicated Content Generation key (Claude) — Super Admin only.
# Used exclusively by the Strategy content-generation pipeline.
# ---------------------------------------------------------------------------

def _content_key_status_cache_key(org_id):
    return f'org_{org_id}_content_key_status'


def _validate_content_key(raw_key):
    """Live-probe a Content Generation (Claude) key before it is committed.

    Returns (is_valid, detail). Only an explicit INVALID_KEY verdict rejects the
    key — transient/probe-environment failures fall back to accepting it as
    stored-but-unverified so we never block a real key on an environment issue.
    """
    try:
        from engine.core.quota_monitor import probe_key_state
        state, detail = probe_key_state('anthropic', raw_key)
        if state == 'INVALID_KEY':
            return False, detail or 'The key was rejected by Anthropic.'
        return True, state
    except Exception as e:
        logger.warning(f"Content key validation probe failed: {e}")
        return True, 'CONNECTED'


class AnthropicCreditError(Exception):
    """Raised when Anthropic's usage/billing API signals exhausted credits."""
    pass


# Anthropic pricing in USD per MILLION tokens. Update this map when Anthropic
# changes rates — nothing else needs changing. Prefix-matched (see
# _get_model_rates) so dated model ids like 'claude-sonnet-4-5-20250929'
# resolve to their family entry.
# We define:
# - input_uncached: Standard input tokens
# - input_cached: Tokens read from prompt cache (typically 10% of base rate)
# - input_cache_creation: Tokens written to prompt cache (typically 125% of base rate)
# - output: Output tokens generated
ANTHROPIC_PRICING = {
    # Haiku family
    'claude-3-5-haiku':  {'input_uncached': 0.80,  'input_cached': 0.08, 'input_cache_creation': 1.00,  'output': 4.00},
    'claude-3-haiku':    {'input_uncached': 0.25,  'input_cached': 0.03, 'input_cache_creation': 0.31,  'output': 1.25},
    'claude-haiku':      {'input_uncached': 1.00,  'input_cached': 0.10, 'input_cache_creation': 1.25,  'output': 5.00},
    # Sonnet family
    'claude-3-5-sonnet': {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    # Sonnet 5 (current model, served via OpenRouter) is cheaper than 4.5.
    'claude-sonnet-5':   {'input_uncached': 2.00,  'input_cached': 0.20, 'input_cache_creation': 2.50,  'output': 10.00},
    'claude-sonnet-4-5': {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    'claude-3-sonnet':   {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    'claude-sonnet':     {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
    # Opus family
    'claude-3-opus':     {'input_uncached': 15.00, 'input_cached': 1.50, 'input_cache_creation': 18.75, 'output': 75.00},
    'claude-opus':       {'input_uncached': 15.00, 'input_cached': 1.50, 'input_cache_creation': 18.75, 'output': 75.00},
    # Default fallback — sonnet rates
    '_default':          {'input_uncached': 3.00,  'input_cached': 0.30, 'input_cache_creation': 3.75,  'output': 15.00},
}


def _get_model_rates(model_name: str) -> dict:
    """Return pricing rates for a model name, prefix-matched against
    ANTHROPIC_PRICING (longest match wins), falling back to '_default'."""
    model_lower = (model_name or '').lower()
    # OpenRouter slugs are vendor-prefixed ('anthropic/claude-sonnet-5'). Strip the
    # prefix so the same rate table serves both transports — without this every
    # OpenRouter-tagged row silently fell through to the _default sonnet rates.
    if model_lower.startswith('anthropic/'):
        model_lower = model_lower[len('anthropic/'):]
    best_key = None
    for key in ANTHROPIC_PRICING:
        if key == '_default':
            continue
        if model_lower.startswith(key) and (best_key is None or len(key) > len(best_key)):
            best_key = key
    return ANTHROPIC_PRICING[best_key] if best_key else ANTHROPIC_PRICING['_default']


def _validate_admin_key(raw_key):
    """Live-probe an Anthropic Admin key. Returns (is_valid, detail).

    Only an explicit authentication failure (401/403, or a 400 whose body names
    an auth problem) rejects the key. Transient/network/param issues accept it as
    stored-but-unverified so a real key is never blocked on an environment issue.
    """
    import requests as req
    from datetime import timedelta
    now = timezone.now()
    start = (now - timedelta(hours=1)).strftime('%Y-%m-%dT%H:%M:%SZ')
    end = now.strftime('%Y-%m-%dT%H:%M:%SZ')
    try:
        r = req.get(
            'https://api.anthropic.com/v1/organizations/usage_report/messages',
            headers={'x-api-key': raw_key, 'anthropic-version': '2023-06-01'},
            params={'starting_at': start, 'ending_at': end, 'bucket_width': '1h'},
            timeout=15,
        )
    except Exception:
        return True, 'CONNECTED'  # network issue — accept key, mark unverified

    if r.status_code == 200:
        return True, 'CONNECTED'
    if r.status_code in (401, 403):
        return False, 'INVALID_KEY'
    if r.status_code == 400:
        # Only reject if the 400 is about authentication, not parameters.
        try:
            body = r.json()
            err = (body.get('error', {}).get('message') or '').lower()
            if any(w in err for w in ('authentication', 'api key', 'unauthorized', 'forbidden')):
                return False, 'INVALID_KEY'
        except Exception:
            pass
        return True, 'CONNECTED'  # bad params but key authenticated
    return True, 'CONNECTED'  # 5xx or other — accept, retry later


def _fetch_live_anthropic_usage(admin_key, start_dt, end_dt):
    """Call Anthropic's usage_report API and return aggregated stats:
    input_tokens, output_tokens, total_tokens, estimated_cost_usd,
    caching_savings_usd, caching_savings_pct, source, last_synced.
    Raises AnthropicCreditError when credits are exhausted."""
    import requests as req
    r = req.get(
        'https://api.anthropic.com/v1/organizations/usage_report/messages',
        headers={'x-api-key': admin_key, 'anthropic-version': '2023-06-01'},
        params={
            'starting_at': start_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'ending_at': end_dt.strftime('%Y-%m-%dT%H:%M:%SZ'),
            'bucket_width': '1d',
            'group_by[]': 'model',
        },
        timeout=20,
    )

    if r.status_code == 402:
        raise AnthropicCreditError('OUT_OF_CREDITS')
    if r.status_code != 200:
        try:
            msg = (r.json().get('error', {}).get('message') or '').lower()
            if any(w in msg for w in ('credit', 'billing', 'insufficient')):
                raise AnthropicCreditError('OUT_OF_CREDITS')
        except AnthropicCreditError:
            raise
        except Exception:
            pass
        r.raise_for_status()

    data = r.json().get('data', [])
    total_input = total_output = 0.0
    total_cost = 0.0
    total_normal_input_cost = 0.0
    total_actual_input_cost = 0.0

    for bucket in data:
        rates = _get_model_rates(bucket.get('model', ''))
        
        uncached_inp = bucket.get('uncached_input_tokens', 0) or 0
        cached_read = bucket.get('cache_read_input_tokens', 0) or 0
        
        cache_write_obj = bucket.get('cache_creation', {}) or {}
        if not cache_write_obj:
            cache_write_obj = {}
        cached_write = (cache_write_obj.get('ephemeral_5m_input_tokens', 0) or 0) + \
                       (cache_write_obj.get('ephemeral_1h_input_tokens', 0) or 0)
        
        inp = uncached_inp + cached_read + cached_write
        out = bucket.get('output_tokens', 0) or 0
        
        total_input += inp
        total_output += out
        
        cost_uncached = (uncached_inp / 1_000_000) * rates['input_uncached']
        cost_cached = (cached_read / 1_000_000) * rates['input_cached']
        cost_write = (cached_write / 1_000_000) * rates['input_cache_creation']
        cost_out = (out / 1_000_000) * rates['output']
        
        total_cost += cost_uncached + cost_cached + cost_write + cost_out
        total_actual_input_cost += cost_uncached + cost_cached + cost_write
        total_normal_input_cost += (inp / 1_000_000) * rates['input_uncached']

    caching_savings_usd = max(0.0, total_normal_input_cost - total_actual_input_cost)
    caching_savings_pct = (caching_savings_usd / total_normal_input_cost * 100.0) if total_normal_input_cost > 0 else 0.0

    return {
        'input_tokens': int(total_input),
        'output_tokens': int(total_output),
        'total_tokens': int(total_input + total_output),
        'estimated_cost_usd': round(total_cost, 4),
        'caching_savings_usd': round(caching_savings_usd, 4),
        'caching_savings_pct': round(caching_savings_pct, 2),
        'source': 'anthropic_api',
        'last_synced': timezone.now().isoformat(),
    }


def _build_content_key_payload(org):
    """Build the content-generation-key section of the response."""
    encrypted = org.content_generation_api_key
    raw = decrypt_value(encrypted) if encrypted else ''
    configured = bool(raw)
    status_str = 'NOT_CONFIGURED'
    if configured:
        status_str = cache.get(_content_key_status_cache_key(org.id)) or 'CONNECTED'

    # --- admin (usage-reporting) key ---
    adm_raw = decrypt_value(org.content_admin_api_key) if org.content_admin_api_key else ''
    adm_configured = bool(adm_raw)
    adm_status = 'NOT_CONFIGURED'
    if adm_configured:
        adm_status = cache.get(f'org_{org.id}_admin_key_status') or 'CONNECTED'

    return {
        'configured': configured,
        'preview': _mask_key(raw) if raw else None,
        'status': status_str,
        # Admin key fields
        'admin_key_configured': adm_configured,
        'admin_key_preview': _mask_key(adm_raw) if adm_raw else None,
        'admin_key_status': adm_status,
    }


@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def content_generation_key(request):
    """Manage the dedicated Content Generation (Claude) key and token limit.

    Super-admin only. The key is validated against Anthropic before it is
    encrypted and stored. The monthly token limit is a soft/informational
    setting — it never blocks content generation.
    """
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can manage the content generation key'},
            status=status.HTTP_403_FORBIDDEN,
        )
    organization = request.user.organisation

    if request.method == 'GET':
        return Response(_build_content_key_payload(organization))

    if request.method == 'DELETE':
        organization.content_generation_api_key = None
        organization.content_admin_api_key = None
        organization.save(update_fields=['content_generation_api_key', 'content_admin_api_key', 'modified_at'])
        cache.delete(_content_key_status_cache_key(organization.id))
        cache.delete(f'org_{organization.id}_admin_key_status')
        cache.delete(f'org_{organization.id}_settings')
        payload = _build_content_key_payload(organization)
        payload['message'] = 'Content generation key removed'
        return Response(payload)

    # ----- PUT -----
    from .models import encrypt_value
    data = request.data
    updated_fields = []

    # NOTE: a legacy `token_limit` field in the PUT body is silently ignored
    # (the monthly-limit concept was removed in favour of live Anthropic usage).

    # Optional key update — validated before commit. An empty value here is a
    # no-op (use DELETE to clear the key) so the limit can be edited alone.
    if 'api_key' in data or 'content_generation_api_key' in data:
        new_key = data.get('api_key', data.get('content_generation_api_key'))
        if new_key is not None and str(new_key).strip() != '':
            new_key = str(new_key).strip()
            is_valid, detail = _validate_content_key(new_key)
            if not is_valid:
                return Response(
                    {'error': f'Invalid Claude API key: {detail}', 'status': 'INVALID_KEY'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            organization.content_generation_api_key = encrypt_value(new_key)
            updated_fields.append('content_generation_api_key')
            cache.set(_content_key_status_cache_key(organization.id), 'CONNECTED', 86400)

    # Optional admin (usage-reporting) key — validated before commit. An empty
    # value here is a no-op (use DELETE to clear).
    if 'admin_api_key' in data or 'content_admin_api_key' in data:
        new_admin = data.get('admin_api_key', data.get('content_admin_api_key'))
        if new_admin is not None and str(new_admin).strip() != '':
            new_admin = str(new_admin).strip()
            is_valid, detail = _validate_admin_key(new_admin)
            if not is_valid:
                return Response(
                    {'error': f'Invalid Anthropic Admin key: {detail}', 'status': 'INVALID_KEY'},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            organization.content_admin_api_key = encrypt_value(new_admin)
            updated_fields.append('content_admin_api_key')
            cache.set(f'org_{organization.id}_admin_key_status', 'CONNECTED', 86400)

    if updated_fields:
        updated_fields.append('modified_at')
        organization.save(update_fields=updated_fields)
        cache.delete(f'org_{organization.id}_settings')

    payload = _build_content_key_payload(organization)
    payload['message'] = 'Content generation key updated'
    return Response(payload)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reveal_content_key(request):
    """Return the decrypted Content Generation key on demand. Super-admin only."""
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can reveal the content generation key'},
            status=status.HTTP_403_FORBIDDEN,
        )
    organization = request.user.organisation
    encrypted = organization.content_generation_api_key
    raw = decrypt_value(encrypted) if encrypted else ''
    if not raw:
        return Response(
            {'error': 'No content generation key configured'},
            status=status.HTTP_404_NOT_FOUND,
        )
    response = Response({'api_key': raw})
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reveal_admin_key(request):
    """Return the decrypted Anthropic Admin (usage-reporting) key on demand.
    Super-admin only. Mirrors reveal_content_key."""
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can reveal the admin key'},
            status=status.HTTP_403_FORBIDDEN,
        )
    organization = request.user.organisation
    encrypted = organization.content_admin_api_key
    raw = decrypt_value(encrypted) if encrypted else ''
    if not raw:
        return Response(
            {'error': 'No admin key configured'},
            status=status.HTTP_404_NOT_FOUND,
        )
    response = Response({'api_key': raw})
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def content_generation_usage(request):
    """Live Anthropic usage for the organisation. Super-admin only.

    Pulls today + month-to-date token usage and estimated cost directly from
    Anthropic's usage_report API using the org's Admin key. Returns
    {'source': 'not_configured'} when no Admin key is set, or
    {'source': 'anthropic_api', 'status': 'OUT_OF_CREDITS'} when credits are
    exhausted.
    """
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can view content generation usage'},
            status=status.HTTP_403_FORBIDDEN,
        )
    organization = request.user.organisation
    admin_key = organization.content_admin_key  # decrypted

    if not admin_key:
        return Response({'source': 'not_configured'})

    now = timezone.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    try:
        today = _fetch_live_anthropic_usage(admin_key, today_start, now)
        month = _fetch_live_anthropic_usage(admin_key, month_start, now)
    except AnthropicCreditError:
        return Response({'source': 'anthropic_api', 'status': 'OUT_OF_CREDITS'})
    except Exception as e:
        logger.error(f'[AdminUsage] live usage fetch failed: {e}')
        return Response({'source': 'error', 'detail': str(e)}, status=status.HTTP_502_BAD_GATEWAY)

    return Response({
        'today': today,
        'month': month,
        'last_synced': month['last_synced'],
        'source': 'anthropic_api',
    })


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_invitation(request, invitation_id):
    if request.user.role not in ['admin', 'super_admin']:
        return Response({'error': 'Only organisation administrators can delete invitations'}, status=status.HTTP_403_FORBIDDEN)
    try:
        invitation = TeamInvitation.objects.get(id=invitation_id, organisation=request.user.organisation)
    except TeamInvitation.DoesNotExist:
        return Response({'error': 'Invitation not found or not in your organization'}, status=status.HTTP_404_NOT_FOUND)
    invitation.delete()
    return Response({'message': 'Invitation deleted successfully'})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def team_members(request):
    if not _can_view_team(request.user):
        return Response({'error': 'You do not have permission to view team members'}, status=status.HTTP_403_FORBIDDEN)
    # Removed members are deactivated rather than deleted so their work stays
    # attributed to them, but they are no longer part of the team and must not
    # be listed — this also keeps the list consistent with Organisation.team_count,
    # which has always counted active accounts only. Re-inviting them revives
    # the account (see accept_invitation) and brings them back here.
    members = Account.objects.filter(organisation=request.user.organisation, is_active=True).exclude(role='super_admin')
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
                if module_value in PRIVILEGED_MODULES:
                    # Demotion must strip administrative modules outright. Leaving a
                    # read-level team_management row behind kept the demoted user able
                    # to send invitations.
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
    # Soft delete: the row survives so everything the member created stays
    # attributed to them, and re-inviting them revives this same account.
    # account_status is the gate core.authorization and jwt_auth check, so it
    # has to move in step with is_active — matching how client removal works.
    member.is_active = False
    member.account_status = 'disabled'
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


# Client accounts are managed per-domain from the domains app
# (see domains.views.domain_client_access) — the domain is the client.
# Existing members' per-domain access is managed via the domains app's
# domain_access endpoints (surfaced in the UI as "Manage Project Access").




# ---------------------------------------------------------------------------
# DataForSEO credentials — Super Admin only.
#
# Used by SEO backlinks and keyword search volume. Deliberately NOT part of the
# LLM provider list: it is not a chat model, is never quota-probed as one, and
# authenticates with HTTP Basic (login + password) rather than a bearer token.
# ---------------------------------------------------------------------------

@api_view(['GET', 'PUT', 'DELETE'])
@permission_classes([IsAuthenticated])
def dataforseo_credentials(request):
    """Read, save or clear this organisation's DataForSEO credentials.

    GET returns the masked state plus the live balance — the balance endpoint
    is free, so showing it costs nothing and answers the question anyone
    opening this screen actually has.

    DELETE clears the pair, which falls the organisation back to the system
    account rather than switching the integration off.
    """
    from seo_rankings.services import dataforseo_credentials as creds

    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can manage DataForSEO credentials'},
            status=status.HTTP_403_FORBIDDEN,
        )

    org = request.user.organisation

    if request.method == 'PUT':
        login = (request.data.get('login') or '').strip()
        password = (request.data.get('password') or '').strip()
        if not login or not password:
            return Response(
                {'error': 'Both login and password are required.'},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Validate before storing: the probe is free, and a stored-but-broken
        # credential would only surface later as a failed backlink fetch that
        # has already spent nothing but looks like an outage.
        result = creds.probe(login, password)
        if not result['valid']:
            return Response({'error': result['error']}, status=status.HTTP_400_BAD_REQUEST)

        org.dataforseo_login = login
        org.dataforseo_password = password
        org.save(update_fields=['dataforseo_login', 'dataforseo_password_enc'])
        logger.info("DataForSEO credentials updated for organisation %s", org.id)

    elif request.method == 'DELETE':
        org.dataforseo_login = ''
        org.dataforseo_password = None
        org.save(update_fields=['dataforseo_login', 'dataforseo_password_enc'])
        logger.info("DataForSEO credentials cleared for organisation %s", org.id)

    login, password, source = creds.credentials_for(org)
    probe = creds.probe(login, password) if login and password else {
        'valid': False, 'balance': None, 'error': 'No credentials configured.',
    }

    payload = {
        'configured': bool((org.dataforseo_login or '').strip() and org.dataforseo_password),
        'source': source,
        'login': login,
        'login_preview': _mask_key(login) if login else None,
        'password_preview': _mask_key(password) if password else None,
        'status': 'CONNECTED' if probe['valid'] else 'INVALID_KEY',
        'balance': probe.get('balance'),
        'error': probe.get('error') or '',
    }
    response = Response(payload)
    response['Cache-Control'] = 'no-store'
    return response


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def reveal_dataforseo_password(request):
    """Return the decrypted DataForSEO password on demand. Super Admin only.

    Only ever reveals the ORGANISATION's own password. The system-level pair in
    .env is deliberately not exposed through the API — an org admin has no
    business reading the shared account's credentials.
    """
    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can reveal API keys'},
            status=status.HTTP_403_FORBIDDEN,
        )

    org = request.user.organisation
    raw = org.dataforseo_password
    if not raw:
        return Response(
            {'error': 'No DataForSEO password configured for this organisation'},
            status=status.HTTP_404_NOT_FOUND,
        )

    response = Response({'login': org.dataforseo_login, 'password': raw})
    response['Cache-Control'] = 'no-store'
    response['Pragma'] = 'no-cache'
    return response


# ---------------------------------------------------------------------------
# OpenRouter balance
# ---------------------------------------------------------------------------
# Every tracked prompt for ChatGPT, Claude and Perplexity bills to this one
# account, so "how much is left" is the question anyone opening the API Keys
# screen actually has. OpenRouter answers it for free — no tokens, no model
# call — which is the same reason the DataForSEO balance is shown there.

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def openrouter_balance(request):
    """Live credit balance for the OpenRouter account in use.

    Read-only and free. Cached briefly so opening the settings page repeatedly
    does not hammer the endpoint, but short enough that a top-up shows up
    without waiting.
    """
    import requests

    if request.user.role != 'super_admin':
        return Response(
            {'error': 'Only super administrators can view the balance'},
            status=status.HTTP_403_FORBIDDEN,
        )

    org = request.user.organisation
    cache_key = f'org_{org.id}_openrouter_balance'
    cached = cache.get(cache_key)
    if cached:
        return Response(cached)

    # Same resolution order the engine uses: this organisation's own key if it
    # has one, otherwise the system key.
    key = None
    encrypted = getattr(org, 'openrouter_api_key', None)
    if encrypted:
        try:
            key = decrypt_value(encrypted)
        except Exception:
            key = None
    if not key:
        key = getattr(settings, 'OPENROUTER_API_KEY', '') or ''

    if not key:
        payload = {'configured': False, 'balance': None,
                   'error': 'No OpenRouter key configured.'}
        response = Response(payload)
        response['Cache-Control'] = 'no-store'
        return response

    try:
        r = requests.get(
            'https://openrouter.ai/api/v1/credits',
            headers={'Authorization': f'Bearer {key}'},
            timeout=10,
        )
        if r.status_code == 401:
            payload = {'configured': True, 'balance': None,
                       'error': 'The key was rejected.'}
        else:
            r.raise_for_status()
            data = r.json().get('data') or {}
            credits = float(data.get('total_credits') or 0)
            used = float(data.get('total_usage') or 0)
            payload = {
                'configured': True,
                # What is actually left to spend. OpenRouter reports the two
                # halves separately and never the difference, which is the one
                # number worth showing.
                'balance': round(credits - used, 2),
                'total_credits': round(credits, 2),
                'total_usage': round(used, 2),
                'error': '',
            }
            cache.set(cache_key, payload, 120)
    except Exception as exc:
        logger.warning("OpenRouter balance lookup failed: %s", exc)
        payload = {'configured': True, 'balance': None,
                   'error': 'Could not reach OpenRouter.'}

    response = Response(payload)
    response['Cache-Control'] = 'no-store'
    return response
