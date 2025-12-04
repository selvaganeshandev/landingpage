from rest_framework import serializers
from .models import ChatConversation, ChatMessage


class ChatMessageSerializer(serializers.ModelSerializer):
    """Serializer for chat messages"""

    class Meta:
        model = ChatMessage
        fields = [
            'id',
            'role',
            'content',
            'function_calls',
            'function_results',
            'model_used',
            'tokens_used',
            'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class ChatConversationSerializer(serializers.ModelSerializer):
    """Serializer for chat conversations"""
    messages = ChatMessageSerializer(many=True, read_only=True)
    domain_name = serializers.CharField(source='domain.name', read_only=True)

    class Meta:
        model = ChatConversation
        fields = [
            'id',
            'domain',
            'domain_name',
            'title',
            'created_at',
            'updated_at',
            'messages'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']


class ChatConversationListSerializer(serializers.ModelSerializer):
    """Lightweight serializer for listing conversations"""
    domain_name = serializers.CharField(source='domain.name', read_only=True)
    last_message = serializers.SerializerMethodField()
    message_count = serializers.SerializerMethodField()

    class Meta:
        model = ChatConversation
        fields = [
            'id',
            'domain',
            'domain_name',
            'title',
            'last_message',
            'message_count',
            'created_at',
            'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']

    def get_last_message(self, obj):
        """Get preview of last message"""
        last_msg = obj.messages.last()
        if last_msg:
            return {
                'role': last_msg.role,
                'content': last_msg.content[:100],
                'created_at': last_msg.created_at
            }
        return None

    def get_message_count(self, obj):
        """Get total message count"""
        return obj.messages.count()
