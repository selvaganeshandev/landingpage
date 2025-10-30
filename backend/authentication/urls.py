from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .auth_views import (
    login, profile, profile_update, logout,
    send_invitation, get_invitation_details, accept_invitation, 
    assign_permissions, check_permissions,
    list_permissions, list_user_permissions, update_permission, 
    delete_permission, get_available_modules, bulk_assign_permissions,
    revoke_all_permissions, grant_all_permissions, get_permission_summary,
    organization_management, team_members, team_member_management,
    forgot_password, reset_password, verify_reset_token
)

urlpatterns = [
    # Simplified Authentication APIs
    path('login/', login, name='login'),
    path('profile/', profile, name='profile'),
    path('profile/update/', profile_update, name='profile_update'),
    path('logout/', logout, name='logout'),
    
    # Password Reset APIs
    path('forgot-password/', forgot_password, name='forgot_password'),
    path('reset-password/', reset_password, name='reset_password'),
    path('verify-reset-token/<uuid:token_id>/', verify_reset_token, name='verify_reset_token'),
    
    # Team Management APIs
    path('invite/', send_invitation, name='send_invitation'),
    path('invitation/<uuid:invitation_id>/', get_invitation_details, name='get_invitation_details'),
    path('accept-invitation/<uuid:invitation_id>/', accept_invitation, name='accept_invitation'),
    
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
    path('team-members/', team_members, name='team_members'),
    path('team-members/<int:member_id>/', team_member_management, name='team_member_management'),
    
    # Standard JWT endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]