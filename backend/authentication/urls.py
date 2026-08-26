from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .auth_views import (
    login, profile, profile_update, update_active_domain, logout,
    send_invitation, get_invitation_details, accept_invitation, delete_invitation,
    assign_permissions, check_permissions,
    list_permissions, list_user_permissions, update_permission,
    delete_permission, get_available_modules, bulk_assign_permissions,
    revoke_all_permissions, grant_all_permissions, get_permission_summary,
    organization_management, reveal_api_key, team_members, team_member_management,
    openrouter_balance,
    dataforseo_credentials, reveal_dataforseo_password,
    forgot_password, reset_password, verify_reset_token,
    content_generation_key, reveal_content_key, content_generation_usage,
    reveal_admin_key
)

from .service_key_views import (
    service_api_keys, revoke_service_api_key,
    reveal_service_api_key, service_api_key_usage,
)

urlpatterns = [
    # Service API keys (Settings > API keys) — machine credentials, org read-only
    path('service-api-keys/', service_api_keys, name='service_api_keys'),
    path('service-api-keys/<int:key_id>/revoke/', revoke_service_api_key, name='revoke_service_api_key'),
    path('service-api-keys/<int:key_id>/reveal/', reveal_service_api_key, name='reveal_service_api_key'),
    path('service-api-keys/<int:key_id>/usage/', service_api_key_usage, name='service_api_key_usage'),
    # Simplified Authentication APIs
    path('login/', login, name='login'),
    path('profile/', profile, name='profile'),
    path('profile/update/', profile_update, name='profile_update'),
    path('active-domain/', update_active_domain, name='update_active_domain'),
    path('logout/', logout, name='logout'),
    
    # Password Reset APIs
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password, name='reset_password'),
    path('verify-reset-token/<uuid:token_id>/', verify_reset_token, name='verify_reset_token'),
    
    # Team Management APIs
    path('invite/', send_invitation, name='send_invitation'),
    path('invitation/<uuid:invitation_id>/', get_invitation_details, name='get_invitation_details'),
    path('accept-invitation/<uuid:invitation_id>/', accept_invitation, name='accept_invitation'),
    path('invitation/<uuid:invitation_id>/delete/', delete_invitation, name='delete_invitation'),
    
    # Permission Management APIs
    path('permissions/assign/', assign_permissions, name='assign_permissions'),
    path('permissions/check/', check_permissions, name='check_permissions'),
    
    # Enhanced Permission Management APIs
    path('permissions/', list_permissions, name='list_permissions'),
    path('permissions/user/<int:user_id>/', list_user_permissions, name='list_user_permissions'),
    path('permissions/<int:permission_id>/', update_permission, name='update_permission'),
    path('permissions/<int:permission_id>/delete/', delete_permission, name='delete_permission'),
    path('permissions/bulk-assign/', bulk_assign_permissions, name='bulk_assign_permissions'),
    path('permissions/modules/', get_available_modules, name='get_available_modules'),
    path('permissions/summary/', get_permission_summary, name='get_permission_summary'),
    path('permissions/user/<int:user_id>/revoke-all/', revoke_all_permissions, name='revoke_all_permissions'),
    path('permissions/user/<int:user_id>/grant-all/', grant_all_permissions, name='grant_all_permissions'),
    
    # Organization Management APIs
    path('organization/', organization_management, name='organization_management'),
    path('organization/api-keys/<str:provider>/reveal/', reveal_api_key, name='reveal_api_key'),
    path('organization/openrouter/balance/', openrouter_balance, name='openrouter_balance'),
    path('organization/dataforseo/', dataforseo_credentials, name='dataforseo_credentials'),
    path('organization/dataforseo/reveal/', reveal_dataforseo_password, name='reveal_dataforseo_password'),

    # Dedicated Content Generation key (Claude) — super admin only
    path('organization/content-key/', content_generation_key, name='content_generation_key'),
    path('organization/content-key/reveal/', reveal_content_key, name='reveal_content_key'),
    path('organization/content-key/admin/reveal/', reveal_admin_key, name='reveal_admin_key'),
    path('organization/content-key/usage/', content_generation_usage, name='content_generation_usage'),
    path('team-members/', team_members, name='team_members'),
    path('team-members/<int:member_id>/', team_member_management, name='team_member_management'),
    
    # Standard JWT endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]