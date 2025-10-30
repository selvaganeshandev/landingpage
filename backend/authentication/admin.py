from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Organisation, Account, TeamInvitation, UserPermission, PasswordResetToken


@admin.register(Organisation)
class OrganisationAdmin(admin.ModelAdmin):
    list_display = ['name', 'team_count', 'created_at', 'modified_at']
    list_filter = ['created_at']
    search_fields = ['name']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['name']


@admin.register(Account)
class AccountAdmin(UserAdmin):
    list_display = ['email', 'first_name', 'last_name', 'role', 'organisation', 'is_active', 'created_at']
    list_filter = ['role', 'is_active', 'organisation', 'created_at']
    search_fields = ['email', 'first_name', 'last_name']
    readonly_fields = ['created_at', 'modified_at', 'date_joined']
    ordering = ['email']
    
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name')}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
        ('Custom fields', {'fields': ('role', 'organisation', 'created_at', 'modified_at')}),
    )
    
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2', 'role', 'organisation'),
        }),
    )


@admin.register(TeamInvitation)
class TeamInvitationAdmin(admin.ModelAdmin):
    list_display = [
        'email', 'organisation', 'role', 'status', 'invited_by', 
        'expires_at', 'created_at'
    ]
    list_filter = ['status', 'role', 'organisation', 'created_at']
    search_fields = ['email', 'organisation__name', 'invited_by__email']
    readonly_fields = ['id', 'created_at', 'modified_at', 'accepted_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Invitation Details', {
            'fields': ('email', 'organisation', 'role', 'message')
        }),
        ('Status', {
            'fields': ('status', 'expires_at', 'accepted_at')
        }),
        ('Metadata', {
            'fields': ('invited_by', 'id', 'created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(UserPermission)
class UserPermissionAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'module', 'permission_level', 'granted_by', 'created_at'
    ]
    list_filter = ['module', 'permission_level', 'created_at']
    search_fields = ['user__email', 'granted_by__email']
    readonly_fields = ['created_at', 'modified_at']
    ordering = ['user', 'module']
    
    fieldsets = (
        ('Permission Details', {
            'fields': ('user', 'module', 'permission_level')
        }),
        ('Metadata', {
            'fields': ('granted_by', 'created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(PasswordResetToken)
class PasswordResetTokenAdmin(admin.ModelAdmin):
    list_display = [
        'user', 'status', 'expires_at', 'used_at', 'created_at'
    ]
    list_filter = ['status', 'created_at', 'expires_at']
    search_fields = ['user__email']
    readonly_fields = ['id', 'created_at', 'modified_at']
    ordering = ['-created_at']
    
    fieldsets = (
        ('Token Details', {
            'fields': ('user', 'status', 'expires_at', 'used_at')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'modified_at'),
            'classes': ('collapse',)
        }),
    )