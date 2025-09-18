from mongoengine import Document, StringField, DateTimeField, DictField
from datetime import datetime
import uuid

class Message(Document):
    """
    MongoDB model for storing individual messages within conversations
    """
    
    # Reference to conversation (FK)
    conversation_id = StringField(required=True, max_length=36)
    
    # Message details
    sender_id = StringField(required=True, max_length=100)  # User ID who sent the message
    body = StringField(required=True)  # Message text/JSON content
    
    # Optional attachments
    attachments_json = StringField(required=False, null=True)  # JSON string of attachments
    
    # Timestamps (nullable as requested)
    created_at = DateTimeField(default=datetime.utcnow)
    edited_at = DateTimeField(null=True)
    deleted_at = DateTimeField(null=True)
    
    # MongoDB collection settings
    meta = {
        'collection': 'messages',
        'indexes': [
            'conversation_id',
            'sender_id',
            'created_at',
            'deleted_at'
        ]
    }
    
    def mark_as_edited(self):
        """Mark message as edited"""
        self.edited_at = datetime.utcnow()
        self.save()
    
    def mark_as_deleted(self):
        """Soft delete message"""
        self.deleted_at = datetime.utcnow()
        self.save()
    
    def is_deleted(self):
        """Check if message is deleted"""
        return self.deleted_at is not None
    
    def __str__(self):
        return f'<Message {self.pk}: {self.sender_id} -> {self.body[:50]}...>'
