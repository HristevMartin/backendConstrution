from mongoengine import Document, StringField, DateTimeField
from datetime import datetime
import uuid

class ConversationParticipant(Document):
    """
    MongoDB model for tracking per-user state in conversations
    Simplified version with only essential fields
    """
    
    # References
    conversation_id = StringField(required=True, max_length=36)  # FK to conversations
    user_id = StringField(required=True, max_length=100)  # User ID
    role = StringField(required=True, max_length=20, choices=['homeowner', 'trader'])
    
    # User state tracking
    last_read_at = DateTimeField(null=True)  # When user last read messages
    unread_count = StringField(default='0', max_length=10)  # Number of unread messages
    
    # Mute functionality (optional)
    muted_until = DateTimeField(null=True)  # If null, not muted. If set, muted until this time
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    
    # MongoDB collection settings
    meta = {
        'collection': 'conversation_participants',
        'indexes': [
            'conversation_id',
            'user_id',
            'role',
            'last_read_at',
            'muted_until'
        ]
    }
    
    def save(self, *args, **kwargs):
        return super(ConversationParticipant, self).save(*args, **kwargs)
    
    def mark_as_read(self):
        """Mark conversation as read for this user"""
        self.last_read_at = datetime.utcnow()
        self.unread_count = '0'
        self.save()
    
    def increment_unread(self):
        """Increment unread count for this user"""
        self.unread_count = str(int(self.unread_count) + 1)
        self.save()
    
    def mute_until(self, mute_until_date):
        """Mute conversation until specified date"""
        self.muted_until = mute_until_date
        self.save()
    
    def unmute(self):
        """Remove mute from conversation"""
        self.muted_until = None
        self.save()
    
    def is_currently_muted(self):
        """Check if conversation is currently muted"""
        if not self.muted_until:
            return False
        return datetime.utcnow() < self.muted_until
    
    def __str__(self):
        return f'<Participant {self.user_id} ({self.role}) in conversation {self.conversation_id}>'
