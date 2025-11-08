from rest_framework import serializers
from .models import Organisation, Account, TeamInvitation, UserPermission, PasswordResetToken


class OrganisationSerializer(serializers.ModelSerializer):
    """Serializer for Organisation model"""
    
    class Meta:
        model = Organisation
        fields = [
            'id', 'name', 'team_count', 
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class AccountSerializer(serializers.ModelSerializer):
    """Serializer for Account model"""
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    
    class Meta:
        model = Account
        fields = [
            'id', 'email', 'first_name', 'last_name', 'role', 
            'organisation', 'organisation_name', 'is_active', 
            'active_domain_id',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
        extra_kwargs = {
            'password': {'write_only': True}
        }


class OrganisationDetailSerializer(OrganisationSerializer):
    """Detailed serializer for Organisation with related data"""
    accounts = AccountSerializer(many=True, read_only=True)
    
    class Meta(OrganisationSerializer.Meta):
        fields = OrganisationSerializer.Meta.fields + ['accounts']


class AccountCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating new accounts"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = Account
        fields = [
            'email', 'first_name', 'last_name', 'role', 
            'organisation', 'password', 'password_confirm'
        ]
    
    def validate(self, data):
        if data['password'] != data['password_confirm']:
            raise serializers.ValidationError("Passwords don't match")
        return data
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        password = validated_data.pop('password')
        account = Account.objects.create(**validated_data)
        account.set_password(password)
        account.save()
        return account


class AccountUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating accounts"""
    
    class Meta:
        model = Account
        fields = [
            'first_name', 'last_name', 'is_active'
        ]


class TeamInvitationSerializer(serializers.ModelSerializer):
    """Serializer for TeamInvitation model"""
    organisation_name = serializers.CharField(source='organisation.name', read_only=True)
    invited_by_name = serializers.CharField(source='invited_by.email', read_only=True)
    is_expired = serializers.SerializerMethodField()
    can_be_accepted = serializers.SerializerMethodField()
    
    class Meta:
        model = TeamInvitation
        fields = [
            'id', 'email', 'organisation', 'organisation_name', 'invited_by', 'invited_by_name',
            'role', 'status', 'message', 'expires_at', 'accepted_at', 'created_at', 'modified_at',
            'is_expired', 'can_be_accepted'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at', 'accepted_at']
    
    def get_is_expired(self, obj):
        return obj.is_expired()
    
    def get_can_be_accepted(self, obj):
        return obj.can_be_accepted()


class TeamInvitationCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating team invitations"""
    
    class Meta:
        model = TeamInvitation
        fields = ['email', 'role', 'message']
    
    def validate_email(self, value):
        """Check if user is already a member of the organisation"""
        # Get organisation from context (set in the view)
        organisation = self.context.get('organisation')
        if organisation:
            if Account.objects.filter(email=value, organisation=organisation).exists():
                raise serializers.ValidationError("User is already a member of this organisation")
        return value


class UserPermissionSerializer(serializers.ModelSerializer):
    """Serializer for UserPermission model"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    granted_by_email = serializers.CharField(source='granted_by.email', read_only=True)
    module_display = serializers.CharField(source='get_module_display', read_only=True)
    permission_display = serializers.CharField(source='get_permission_level_display', read_only=True)
    
    class Meta:
        model = UserPermission
        fields = [
            'id', 'user', 'user_email', 'module', 'module_display', 
            'permission_level', 'permission_display', 'granted_by', 'granted_by_email',
            'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']


class UserPermissionCreateSerializer(serializers.ModelSerializer):
    """Serializer for creating user permissions"""
    
    class Meta:
        model = UserPermission
        fields = ['user', 'module', 'permission_level']
    
    def validate(self, data):
        """Validate permission assignment"""
        user = data.get('user')
        module = data.get('module')
        
        # Check if user is trying to assign permissions to themselves
        if hasattr(self.context.get('request'), 'user') and self.context['request'].user == user:
            raise serializers.ValidationError("You cannot assign permissions to yourself")
        
        return data


class PasswordResetTokenSerializer(serializers.ModelSerializer):
    """Serializer for PasswordResetToken model"""
    user_email = serializers.CharField(source='user.email', read_only=True)
    can_be_used = serializers.SerializerMethodField()
    
    class Meta:
        model = PasswordResetToken
        fields = [
            'id', 'user', 'user_email', 'status', 'expires_at', 
            'used_at', 'can_be_used', 'created_at', 'modified_at'
        ]
        read_only_fields = ['id', 'created_at', 'modified_at']
    
    def get_can_be_used(self, obj):
        return obj.can_be_used()


class ForgotPasswordSerializer(serializers.Serializer):
    """Serializer for forgot password request"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Check if user exists"""
        if not Account.objects.filter(email=value, is_active=True).exists():
            raise serializers.ValidationError("No active account found with this email address")
        return value


class ResetPasswordSerializer(serializers.Serializer):
    """Serializer for password reset"""
    token = serializers.UUIDField()
    new_password = serializers.CharField(min_length=8, write_only=True)
    confirm_password = serializers.CharField(write_only=True)
    
    def validate(self, data):
        """Validate password reset data"""
        new_password = data.get('new_password')
        confirm_password = data.get('confirm_password')
        
        if new_password != confirm_password:
            raise serializers.ValidationError("Passwords do not match")
        
        return data
    
    def validate_token(self, value):
        """Validate reset token"""
        try:
            reset_token = PasswordResetToken.objects.get(id=value)
            if not reset_token.can_be_used():
                raise serializers.ValidationError("Invalid or expired reset token")
        except PasswordResetToken.DoesNotExist:
            raise serializers.ValidationError("Invalid reset token")
        
        return value
