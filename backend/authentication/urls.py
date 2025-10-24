from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .simplified_auth_views import (
    login, profile, profile_update, logout,
    send_invitation, accept_invitation, 
    assign_permissions, check_permissions
)

urlpatterns = [
    # Simplified Authentication APIs
    path('login/', login, name='login'),
    path('profile/', profile, name='profile'),
    path('profile/update/', profile_update, name='profile_update'),
    path('logout/', logout, name='logout'),
    
    # Team Management APIs
    path('invite/', send_invitation, name='send_invitation'),
    path('accept-invitation/<uuid:invitation_id>/', accept_invitation, name='accept_invitation'),
    
    # Permission Management APIs
    path('permissions/assign/', assign_permissions, name='assign_permissions'),
    path('permissions/check/', check_permissions, name='check_permissions'),
    
    # Standard JWT endpoints
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]