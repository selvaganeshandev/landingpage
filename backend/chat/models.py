from django.db import models
from authentication.models import Account
from domains.models import Domain


class ChatConversation(models.Model):
    """
    Chat conversation session between user and the agentic chatbot
    Scoped to a specific domain for security and context
    """
    user = models.ForeignKey(
        Account,
        on_delete=models.CASCADE,
        related_name='chat_conversations',
        help_text="User who owns this conversation"
    )
    domain = models.ForeignKey(
        Domain,
        on_delete=models.CASCADE,
        related_name='chat_conversations',
        help_text="Domain this conversation is about"
    )
    title = models.CharField(
        max_length=255,
        blank=True,
        null=True,
        help_text="Auto-generated title from first message"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'chat_conversations'
        verbose_name = 'Chat Conversation'
        verbose_name_plural = 'Chat Conversations'
        ordering = ['-updated_at']
        indexes = [
            models.Index(fields=['user', 'domain', '-updated_at']),
            models.Index(fields=['domain', '-created_at']),
        ]

    def __str__(self):
        return f"Chat: {self.user.email} - {self.domain.name} ({self.id})"


class ChatMessage(models.Model):
    """
    Individual message in a chat conversation
    Stores both user messages and AI assistant responses
    """
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
        ('system', 'System'),
    ]

    conversation = models.ForeignKey(
        ChatConversation,
        on_delete=models.CASCADE,
        related_name='messages',
        help_text="Conversation this message belongs to"
    )
    role = models.CharField(
        max_length=10,
        choices=ROLE_CHOICES,
        help_text="Role of the message sender"
    )
    content = models.TextField(
        help_text="Message content"
    )
    function_calls = models.JSONField(
        null=True,
        blank=True,
        help_text="Function calls made by the assistant (if any)"
    )
    function_results = models.JSONField(
        null=True,
        blank=True,
        help_text="Results from function calls"
    )
    model_used = models.CharField(
        max_length=50,
        null=True,
        blank=True,
        help_text="AI model used for this message (e.g., gpt-4o-mini)"
    )
    tokens_used = models.IntegerField(
        null=True,
        blank=True,
        help_text="Total tokens used for this message"
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'chat_messages'
        verbose_name = 'Chat Message'
        verbose_name_plural = 'Chat Messages'
        ordering = ['created_at']
        indexes = [
            models.Index(fields=['conversation', 'created_at']),
            models.Index(fields=['role', 'created_at']),
        ]

    def __str__(self):
        return f"{self.role}: {self.content[:50]}..."
