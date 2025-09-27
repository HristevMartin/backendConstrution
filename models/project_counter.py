from mongoengine import Document, StringField, IntField, DateTimeField
from datetime import datetime



class JobApplicationCounter(Document):
    job_id = StringField(required=True, unique=True, max_length=100) 
    applied_count = IntField(required=True, default=0)
    updated_at = DateTimeField(default=datetime.utcnow)

    meta = {
        'collection': 'job_application_counts',
        'indexes': [
            {'fields': ['job_id'], 'unique': True}
        ]
    }
