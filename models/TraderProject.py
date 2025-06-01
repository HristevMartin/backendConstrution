from mongoengine import Document, StringField, DateTimeField, ListField
from datetime import datetime

class Project(Document):
    # Basic project information
    title = StringField(required=True, max_length=200)
    description = StringField(required=False, null=True, max_length=2000)
    projectDate = StringField(required=False, null=True, max_length=10) 
    specifications = ListField(StringField(max_length=100), required=False, default=list)
    projectImages = ListField(StringField(max_length=500), required=False, default=list)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    userId = StringField(required=False, null=True)
    
    meta = {
        'collection': 'projects',
        'indexes': [
            'title',
            'projectDate',
            'specifications',
            'created_at'
        ]
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Project, self).save(*args, **kwargs)