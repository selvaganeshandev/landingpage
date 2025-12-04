from django.contrib import admin
from .models import ChatConversation, ChatMessage


@admin.register(ChatConversation)
class ChatConversationAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'domain', 'title', 'created_at', 'updated_at']
    list_filter = ['created_at', 'domain']
    search_fields = ['user__email', 'domain__name', 'title']
    readonly_fields = ['created_at', 'updated_at']


@admin.register(ChatMessage)
class ChatMessageAdmin(admin.ModelAdmin):
    list_display = ['id', 'conversation', 'role', 'content_preview', 'model_used', 'tokens_used', 'created_at']
    list_filter = ['role', 'model_used', 'created_at']
    search_fields = ['content', 'conversation__user__email']
    readonly_fields = ['created_at']

    def content_preview(self, obj):
        return obj.content[:100] + '...' if len(obj.content) > 100 else obj.content
    content_preview.short_description = 'Content'
