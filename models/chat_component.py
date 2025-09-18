from mongoengine import Document, StringField, DateTimeField, BooleanField, ReferenceField
from datetime import datetime
import uuid

class Conversation(Document):
    """
    MongoDB model for storing conversations between homeowners and traders for specific jobs
    One row per homeowner–trader–job thread
    """
    
    # Unique conversation identifier
    conversation_id = StringField(required=True, unique=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    # References
    job_id = StringField(required=True, max_length=36)  # References ClientProject.project_id
    homeowner_id = StringField(required=True, max_length=100)  # User ID of homeowner
    trader_id = StringField(required=True, max_length=100)  # User ID of trader
    
    # Conversation status
    status = StringField(required=True, max_length=20, default='open', 
                        choices=['open', 'closed', 'archived'])
    
    # Contact permissions (what the trader can see about homeowner)
    can_view_phone = BooleanField(default=False)
    can_view_email = BooleanField(default=True)  # Email is usually visible
    
    # Message tracking
    last_message_at = DateTimeField(default=datetime.utcnow)
    message_count = StringField(default='0', max_length=10)  # Total messages in conversation
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    # MongoDB collection settings
    meta = {
        'collection': 'conversations',
        'indexes': [
            'conversation_id',
            'job_id',
            'homeowner_id',
            'trader_id',
            'status',
            'last_message_at',
            'created_at'
        ]
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Conversation, self).save(*args, **kwargs)
    
    def __str__(self):
        return f'<Conversation {self.conversation_id}: {self.homeowner_id} <-> {self.trader_id}>'