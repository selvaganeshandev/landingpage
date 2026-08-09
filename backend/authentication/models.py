from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils import timezone
from django.core.exceptions import ValidationError
from datetime import timedelta
import uuid
import base64
from django.conf import settings
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

def get_fernet():
    # Derive a 32-byte Fernet key via PBKDF2 from the shared BYOK encryption
    # secret. This MUST match the engine's derivation (same secret + salt +
    # iterations) so the engine can decrypt keys the backend stored.
    secret = getattr(settings, 'API_KEY_ENCRYPTION_SECRET', None) or settings.SECRET_KEY
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b'llm-monitor-salt-123',
        iterations=100000,
    )
    key = base64.urlsafe_b64encode(kdf.derive(secret.encode()))
    return Fernet(key)

def encrypt_value(value: str) -> str:
    if not value:
        return ""
    try:
        f = get_fernet()
        return f.encrypt(value.encode()).decode()
    except Exception:
        return ""

def decrypt_value(encrypted_value: str) -> str:
    if not encrypted_value:
        return ""
    try:
        f = get_fernet()
        return f.decrypt(encrypted_value.encode()).decode()
    except Exception:
        return encrypted_value



def default_expires_in_7_days():
    """Default function for expires_at field (7 days from now)"""
    return timezone.now() + timedelta(days=7)


def default_expires_in_1_hour():
    """Default function for expires_at field (1 hour from now)"""
    return timezone.now() + timedelta(hours=1)


class Organisation(models.Model):
    """
    Organisation model representing companies or entities using Promptmaxx App
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

    # ----- Invoice details -------------------------------------------------
    # The Consignee / Buyer block on the tax invoice. These describe the
    # organisation itself, so they live here rather than on the invoicing
    # user's settings — each organisation owns its own registered particulars
    # and edits them under Organization Settings > Invoice Details.
    billing_legal_name = models.CharField(
        max_length=255, blank=True, default="",
        help_text="Registered name for invoices; falls back to `name` when blank",
    )
    billing_address = models.TextField(
        blank=True, default="", help_text="Registered address, one line per line",
    )
    billing_gstin = models.CharField(max_length=32, blank=True, default="")
    billing_state_name = models.CharField(max_length=64, blank=True, default="")
    billing_state_code = models.CharField(max_length=8, blank=True, default="")

    # A second set for the non-India region. The same organisation is often
    # invoiced through a different registered entity abroad — different legal
    # name, address and tax registration — so one block cannot serve both.
    billing_alt_legal_name = models.CharField(max_length=255, blank=True, default="")
    billing_alt_address = models.TextField(blank=True, default="")
    billing_alt_gstin = models.CharField(
        max_length=32, blank=True, default="",
        help_text="Tax registration for the other region (e.g. TRN)",
    )
    billing_alt_state_name = models.CharField(max_length=64, blank=True, default="")
    billing_alt_state_code = models.CharField(max_length=8, blank=True, default="")

    def invoice_party(self, region_key: str = "row") -> dict:
        """Consignee / Buyer block for this organisation, per invoice region.

        Falls back to the primary block when the other-region set is blank, so
        an unconfigured organisation still produces a usable invoice rather
        than an empty address panel.
        """
        if region_key and region_key != "row" and (
            self.billing_alt_legal_name or self.billing_alt_address or self.billing_alt_gstin
        ):
            return {
                "name": self.billing_alt_legal_name or self.name,
                "address": self.billing_alt_address,
                "gstin": self.billing_alt_gstin,
                "state_name": self.billing_alt_state_name,
                "state_code": self.billing_alt_state_code,
            }
        return {
            "name": self.billing_legal_name or self.name,
            "address": self.billing_address,
            "gstin": self.billing_gstin,
            "state_name": self.billing_state_name,
            "state_code": self.billing_state_code,
        }
    seo_keyword_limit = models.PositiveIntegerField(default=3000, help_text="Maximum number of SEO keywords allowed for this organisation")
    created_at = models.DateTimeField(auto_now_add=True, help_text="Timestamp when the organisation was created")
    modified_at = models.DateTimeField(auto_now=True, help_text="Timestamp when the organisation was last modified")
    
    # Encrypted API keys
    openai_api_key = models.TextField(blank=True, null=True, help_text="Encrypted OpenAI API Key")
    gemini_api_key = models.TextField(blank=True, null=True, help_text="Encrypted Gemini API Key")
    perplexity_api_key = models.TextField(blank=True, null=True, help_text="Encrypted Perplexity API Key")
    anthropic_api_key = models.TextField(blank=True, null=True, help_text="Encrypted Anthropic API Key")
    xai_api_key = models.TextField(blank=True, null=True, help_text="Encrypted xAI (Grok) API Key")
    deepseek_api_key = models.TextField(blank=True, null=True, help_text="Encrypted DeepSeek API Key")
    # The credential that actually authenticates ChatGPT, Claude and Perplexity
    # since they moved onto OpenRouter. api_key_service.get_api_key already
    # looks for `openrouter_api_key`; without this column the lookup always
    # missed and every organisation silently fell back to the .env key.
    openrouter_api_key = models.TextField(
        blank=True, null=True, help_text="Encrypted OpenRouter API Key (sk-or-...)"
    )

    # Enabled toggles
    openai_enabled = models.BooleanField(default=True, help_text="Whether OpenAI is enabled")
    gemini_enabled = models.BooleanField(default=True, help_text="Whether Gemini is enabled")
    perplexity_enabled = models.BooleanField(default=True, help_text="Whether Perplexity is enabled")
    anthropic_enabled = models.BooleanField(default=True, help_text="Whether Anthropic is enabled")
    xai_enabled = models.BooleanField(default=True, help_text="Whether xAI (Grok) is enabled")
    deepseek_enabled = models.BooleanField(default=True, help_text="Whether DeepSeek is enabled")
    openrouter_enabled = models.BooleanField(default=True, help_text="Whether OpenRouter is enabled")

    # Dedicated Content Generation key (Claude) — used ONLY by the Strategy
    # content-generation pipeline, never by the background scanning engines.
    content_generation_api_key = models.TextField(
        blank=True, null=True, help_text="Encrypted API Key for Content Generation"
    )
    # Dedicated Anthropic Admin key (sk-ant-admin) — used ONLY to fetch live
    # organisation usage/cost from Anthropic's usage_report API. It never
    # generates content.
    content_admin_api_key = models.TextField(
        blank=True, null=True,
        help_text="Encrypted Anthropic Admin API Key (sk-ant-admin) for live usage reporting"
    )

    # Cryptographic properties for transparent access
    @property
    def openai_key(self):
        return decrypt_value(self.openai_api_key)

    @openai_key.setter
    def openai_key(self, value):
        self.openai_api_key = encrypt_value(value) if value is not None else None

    @property
    def gemini_key(self):
        return decrypt_value(self.gemini_api_key)

    @gemini_key.setter
    def gemini_key(self, value):
        self.gemini_api_key = encrypt_value(value) if value is not None else None

    @property
    def perplexity_key(self):
        return decrypt_value(self.perplexity_api_key)

    @perplexity_key.setter
    def perplexity_key(self, value):
        self.perplexity_api_key = encrypt_value(value) if value is not None else None

    @property
    def anthropic_key(self):
        return decrypt_value(self.anthropic_api_key)

    @anthropic_key.setter
    def anthropic_key(self, value):
        self.anthropic_api_key = encrypt_value(value) if value is not None else None

    @property
    def xai_key(self):
        return decrypt_value(self.xai_api_key)

    @xai_key.setter
    def xai_key(self, value):
        self.xai_api_key = encrypt_value(value) if value is not None else None

    @property
    def deepseek_key(self):
        return decrypt_value(self.deepseek_api_key)

    @deepseek_key.setter
    def deepseek_key(self, value):
        self.deepseek_api_key = encrypt_value(value) if value is not None else None

    @property
    def openrouter_key(self):
        return decrypt_value(self.openrouter_api_key)

    @openrouter_key.setter
    def openrouter_key(self, value):
        self.openrouter_api_key = encrypt_value(value) if value is not None else None

    @property
    def content_generation_key(self):
        return decrypt_value(self.content_generation_api_key)

    @content_generation_key.setter
    def content_generation_key(self, value):
        self.content_generation_api_key = encrypt_value(value) if value is not None else None

    @property
    def content_admin_key(self):
        return decrypt_value(self.content_admin_api_key)

    @content_admin_key.setter
    def content_admin_key(self, value):
        self.content_admin_api_key = encrypt_value(value) if value else None

    # ----- DataForSEO (backlinks + keyword search volume) -----
    # Not an LLM provider, so deliberately outside LLM_PROVIDERS / BYOK: it is
    # never probed as a chat model and never appears in that list. It also
    # authenticates with HTTP Basic rather than a bearer token, hence two
    # fields — the login is an email address and is not a secret, so only the
    # password is encrypted.
    dataforseo_login = models.CharField(
        max_length=255, blank=True, default='',
        help_text="DataForSEO account login (an email address; not secret)",
    )
    dataforseo_password_enc = models.TextField(
        blank=True, null=True, help_text="Encrypted DataForSEO API password",
    )

    @property
    def dataforseo_password(self):
        return decrypt_value(self.dataforseo_password_enc)

    @dataforseo_password.setter
    def dataforseo_password(self, value):
        self.dataforseo_password_enc = encrypt_value(value) if value else None

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
        ('client', 'Client'),
    ]

    ACCOUNT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('suspended', 'Suspended'),
        ('pending', 'Pending'),
        ('disabled', 'Disabled'),
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
        help_text="Role of the account (super-admin, admin, user or client)"
    )
    account_status = models.CharField(
        max_length=15,
        choices=ACCOUNT_STATUS_CHOICES,
        default='active',
        help_text="Lifecycle status; non-active accounts are denied access even with a valid token"
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
        ('client', 'Client'),
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
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='client_invitations',
        help_text="Domain a client invitee is scoped to (client role only)"
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
        ('backlinks', 'Backlinks'),

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


class ClientActivityLog(models.Model):
    """
    Audit trail of client-account activity (login, logout, report export).

    Phase 1 records coarse events only — per-page 'view_dashboard' events are
    intentionally excluded because a single dashboard load fires many API calls
    and would flood this table; they can be added later behind a retention policy.
    """
    ACTION_CHOICES = [
        ('login', 'Login'),
        ('logout', 'Logout'),
        ('export_report', 'Export Report'),
    ]

    user = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        help_text="Account the activity belongs to"
    )
    domain = models.ForeignKey(
        'domains.Domain',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='client_activity_logs',
        help_text="Domain in context when the action occurred, if any"
    )
    action = models.CharField(
        max_length=50,
        choices=ACTION_CHOICES,
        help_text="What the client did"
    )
    details = models.JSONField(
        default=dict,
        blank=True,
        help_text="Optional structured context for the action"
    )
    ip_address = models.GenericIPAddressField(
        null=True,
        blank=True,
        help_text="Client IP address at the time of the action"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'client_activity_logs'
        verbose_name = 'Client Activity Log'
        verbose_name_plural = 'Client Activity Logs'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', '-created_at']),
        ]

    def __str__(self):
        return f"{self.user.email} - {self.action} @ {self.created_at:%Y-%m-%d %H:%M}"