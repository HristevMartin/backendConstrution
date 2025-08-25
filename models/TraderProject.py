from mongoengine import Document, StringField, DateTimeField, ListField, BooleanField, IntField
from datetime import datetime
import uuid

class TraderProject(Document):
    # Unique project identifier
    project_id = StringField(required=True, unique=True, max_length=36)
    
    # User identifier (from auth system)
    userId = StringField(required=True, max_length=100)
    
    # Trader registration information
    name = StringField(required=True, max_length=200)
    email = StringField(required=True, max_length=200)
    phone = StringField(required=False, null=True, max_length=20)
    primaryTrade = StringField(required=True, max_length=100)
    otherServices = StringField(required=False, null=True, max_length=1000)  # JSON string
    city = StringField(required=True, max_length=100)
    postcode = StringField(required=True, max_length=20)
    radiusKm = StringField(required=True, max_length=10)
    experienceYears = StringField(required=False, null=True, max_length=10)
    certifications = StringField(required=False, null=True, max_length=500)
    bio = StringField(required=False, null=True, max_length=2000)
    marketingConsent = StringField(required=True, max_length=10)  # "true" or "false"
    
    # Basic project information (if applicable)
    projectTitle = StringField(required=False, null=True, max_length=200)
    projectDescription = StringField(required=False, null=True, max_length=2000)
    location = StringField(required=False, null=True, max_length=100)
    budget = StringField(required=False, null=True, max_length=50)
    timeline = StringField(required=False, null=True, max_length=100)
    specifications = ListField(StringField(max_length=100), required=False, default=list)
    projectImages = ListField(StringField(max_length=500), required=False, default=list)
    
    # Timestamps
    createdDate = DateTimeField(default=datetime.utcnow)
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    meta = {
        'collection': 'trader_projects',
        'indexes': [
            'project_id',
            'userId',
            'email',
            'primaryTrade',
            'city',
            'postcode',
            'projectTitle',
            'location',
            'createdDate',
            'created_at'
        ]
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(TraderProject, self).save(*args, **kwargs)

# Keep the old Project class for backward compatibility
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