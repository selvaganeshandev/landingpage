from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import uuid


def default_expires_in_7_days():
    """Default function for expires_at field (7 days from now)"""
    return timezone.now() + timedelta(days=7)


def default_expires_in_1_hour():
    """Default function for expires_at field (1 hour from now)"""
    return timezone.now() + timedelta(hours=1)


class Organisation(models.Model):
    """
    Organisation model representing companies or entities using the LLM Monitor
    """
    INDUSTRY_CHOICES = [
        ('technology', 'Technology & Software'),
        ('ecommerce', 'E-Commerce & Retail'),
        ('marketing', 'Marketing & Advertising'),
        ('finance', 'Finance & Banking'),
        ('healthcare', 'Healthcare & Medical'),
        ('education', 'Education & Training'),
        ('saas', 'SaaS & B2B Services'),
        ('agency', 'Agency & Consulting'),
        ('other', 'Other'),
    ]

    COMPANY_SIZE_CHOICES = [
        ('1-10', '1-10 employees'),
        ('11-50', '11-50 employees'),
        ('51-200', '51-200 employees'),
        ('200+', '200+ employees'),
    ]

    name = models.CharField(max_length=255, help_text="Name of the organisation")
    industry = models.CharField(
        max_length=50,
        choices=INDUSTRY_CHOICES,
        blank=True,
        null=True,
        help_text="Industry vertical of the organisation"
    )
    company_size = models.CharField(
        max_length=20,
        choices=COMPANY_SIZE_CHOICES,
        blank=True,
        null=True,
        help_text="Number of employees in the organisation"
    )
    goals = models.JSONField(
        default=list,
        blank=True,
        help_text="List of primary goals for using the platform"
    )
    using_ai_monitoring = models.BooleanField(
        null=True,
        blank=True,
        help_text="Whether the organisation is currently using AI monitoring tools"
    )
    team_count = models.PositiveIntegerField(default=1, help_text="Number of team members")
    seo_keyword_limit = models.PositiveIntegerField(default=3000, help_text="Maximum number of SEO keywords allowed for this organisation")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the organisation was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the organisation was last modified")
    
    class Meta:
        db_table = 'organisations'
        verbose_name = 'Organisation'
        verbose_name_plural = 'Organisations'
        ordering = ['name']
    
    def __str__(self):
        return self.name


class Account(AbstractUser):
    """
    Account model extending Django's User model for custom user management
    """
    ROLE_CHOICES = [
        ('super_admin', 'Super Administrator'),
        ('admin', 'Administrator'),
        ('user', 'User'),
    ]

    JOB_ROLE_CHOICES = [
        ('founder', 'Founder / CEO'),
        ('marketing', 'Marketing Manager'),
        ('seo', 'SEO Specialist'),
        ('content', 'Content Strategist'),
        ('agency', 'Agency / Consultant'),
        ('other', 'Other'),
    ]

    email = models.EmailField(unique=True, help_text="Email address of the account")
    role = models.CharField(
        max_length=12,
        choices=ROLE_CHOICES,
        default='user',
        help_text="Role of the account (super-admin, admin or user)"
    )
    job_role = models.CharField(
        max_length=20,
        choices=JOB_ROLE_CHOICES,
        blank=True,
        null=True,
        help_text="Job role/title of the user"
    )
    organisation = models.ForeignKey(
        Organisation,
        on_delete=models.CASCADE,
        related_name='accounts',
        help_text="Organisation this account belongs to"
    )
    active_domain_id = models.IntegerField(
        null=True,
        blank=True,
        help_text="ID of the currently active domain for this user"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the account was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the account was last modified")
    
    # Use email as the unique identifier for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username']  # username still required by Django, but email is primary
    
    class Meta:
        db_table = 'accounts'
        verbose_name = 'Account'
        verbose_name_plural = 'Accounts'
        ordering = ['email']
        indexes = [
            models.Index(fields=['organisation', 'role', 'is_active']),
            models.Index(fields=['organisation', 'created_at']),
            models.Index(fields=['active_domain_id']),
        ]
    
    def clean(self):
        """Validate that active_domain_id belongs to user's organisation if set"""
        if self.active_domain_id:
            from domains.models import Domain
            try:
                domain = Domain.objects.get(id=self.active_domain_id)
                if domain.organisation_id != self.organisation_id:
                    raise ValidationError("Active domain must belong to the user's organisation")
            except Domain.DoesNotExist:
                raise ValidationError("Active domain does not exist")
    
    def __str__(self):
        return f"{self.email} ({self.role})"


class TeamInvitation(models.Model):
    """
    Team invitation model for inviting users to join organisations
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('accepted', 'Accepted'),
        ('declined', 'Declined'),
        ('expired', 'Expired'),
    ]
    
    ROLE_CHOICES = [
        ('admin', 'Administrator'),
        ('user', 'User'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    email = models.EmailField(help_text="Email address of the invited user")
    organisation = models.ForeignKey(
        Organisation, 
        on_delete=models.CASCADE, 
        related_name='invitations',
        help_text="Organisation the user is being invited to"
    )
    invited_by = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='sent_invitations',
        help_text="User who sent the invitation"
    )
    role = models.CharField(
        max_length=10, 
        choices=ROLE_CHOICES, 
        default='user',
        help_text="Role to be assigned to the invited user"
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current status of the invitation"
    )
    message = models.TextField(
        blank=True, 
        help_text="Optional message to include with the invitation"
    )
    expires_at = models.DateTimeField(
        default=default_expires_in_7_days,
        help_text="When the invitation expires"
    )
    accepted_at = models.DateTimeField(null=True, blank=True, help_text="When the invitation was accepted")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the invitation was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="When the invitation was last modified")
    
    class Meta:
        db_table = 'team_invitations'
        verbose_name = 'Team Invitation'
        verbose_name_plural = 'Team Invitations'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email', 'status']),
            models.Index(fields=['organisation', 'status', 'created_at']),
            models.Index(fields=['expires_at']),
        ]
        unique_together = ['email', 'organisation']
    
    def __str__(self):
        return f"Invitation to {self.email} for {self.organisation.name}"
    
    def is_expired(self):
        """Check if the invitation has expired"""
        return timezone.now() > self.expires_at
    
    def can_be_accepted(self):
        """Check if the invitation can be accepted"""
        return self.status == 'pending' and not self.is_expired()


class UserPermission(models.Model):
    """
    User permission model for module access control
    """
    MODULE_CHOICES = [
        # Overview
        ('dashboard', 'Dashboard'),
        
        # Tracking
        ('mentions', 'Mentions'),
        ('prompts', 'Prompts'),
        ('alerts', 'Alerts'),
        
        # Analytics
        ('sentiment_analysis', 'Sentiment Analysis'),
        ('topics', 'Topics'),
        ('share_of_voice', 'Share of Voice'),
        ('historical_trends', 'Historical Trends'),
        
        # Strategy
        ('content_gaps', 'Content Gaps'),
        ('competitors', 'Competitors'),
        
        # Advanced
        ('multilingual', 'Multilingual'),
        ('ai_copilot', 'AI Copilot'),
        ('prompt_insights', 'Prompt Insights'),
        ('agent_analytics', 'Agent Analytics'),
        ('ai_crawler', 'AI Crawler'),
        ('traffic_attribution', 'Traffic Attribution'),
        ('misinformation_alerts', 'Misinformation Alerts'),
        
        # SEO Monitoring
        ('keyword_rankings', 'Keyword Rankings'),
        ('seo_competitors', 'SEO Competitors'),
        ('organic_reports', 'Organic Reports'),

        # Reporting
        ('reports', 'Reports'),
        
        # Administration
        ('organization_settings', 'Organization Settings'),
        ('team_management', 'Team Management'),
    ]
    
    PERMISSION_CHOICES = [
        ('read', 'Read Only'),
        ('write', 'Read & Write'),
        ('admin', 'Full Access'),
    ]
    
    user = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='permissions',
        help_text="User the permission is assigned to"
    )
    module = models.CharField(
        max_length=30, 
        choices=MODULE_CHOICES,
        help_text="Module the permission applies to"
    )
    permission_level = models.CharField(
        max_length=10, 
        choices=PERMISSION_CHOICES,
        help_text="Level of permission for the module"
    )
    granted_by = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='granted_permissions',
        help_text="User who granted this permission"
    )
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the permission was granted")
    modified_at = models.DateTimeField(auto_now=True, help_text="When the permission was last modified")
    
    class Meta:
        db_table = 'user_permissions'
        verbose_name = 'User Permission'
        verbose_name_plural = 'User Permissions'
        ordering = ['user', 'module']
        unique_together = ['user', 'module']
        indexes = [
            models.Index(fields=['user', 'module']),  # CRITICAL: Permission checks
            models.Index(fields=['granted_by', 'created_at']),
        ]
    
    def __str__(self):
        return f"{self.user.email} - {self.module} ({self.permission_level})"

class PasswordResetToken(models.Model):
    """
    Password reset token model for handling password reset requests
    """
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('used', 'Used'),
        ('expired', 'Expired'),
    ]
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(
        Account, 
        on_delete=models.CASCADE, 
        related_name='password_reset_tokens',
        help_text="User requesting password reset"
    )
    status = models.CharField(
        max_length=10, 
        choices=STATUS_CHOICES, 
        default='pending',
        help_text="Current status of the reset token"
    )
    expires_at = models.DateTimeField(
        default=default_expires_in_1_hour,
        help_text="When the reset token expires"
    )
    used_at = models.DateTimeField(null=True, blank=True, help_text="When the token was used")
    created_at = models.DateTimeField(auto_now_add=True, help_text="When the token was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="When the token was last modified")
    
    class Meta:
        db_table = 'password_reset_tokens'
        verbose_name = 'Password Reset Token'
        verbose_name_plural = 'Password Reset Tokens'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"Password reset for {self.user.email}"
    
    def is_expired(self):
        """Check if the reset token has expired"""
        return timezone.now() > self.expires_at
    
    def can_be_used(self):
        """Check if the reset token can be used"""
        return self.status == 'pending' and not self.is_expired()