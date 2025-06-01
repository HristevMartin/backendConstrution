from mongoengine import Document, StringField, DateTimeField
from datetime import datetime

class Comment(Document):
    # Comment information
    projectId = StringField(required=True, max_length=100)  # References the project/user
    user = StringField(required=True, max_length=100)       # User who made the comment
    comment = StringField(required=True, max_length=1000)   # The comment text
    date = StringField(required=False, null=True, max_length=20)  # Date as string from frontend
    created_at = DateTimeField(default=datetime.utcnow)     # Auto timestamp
    updated_at = DateTimeField(default=datetime.utcnow)     # Auto timestamp
    
    meta = {
        'collection': 'comments',
        'indexes': [
            'projectId',
            'user',
            'created_at'
        ]
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Comment, self).save(*args, **kwargs) 