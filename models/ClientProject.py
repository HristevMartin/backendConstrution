# models/client_project.py

from mongoengine import Document, StringField, ListField, IntField, DateTimeField, DictField, BooleanField
from datetime import datetime
import uuid

class ClientProject(Document):
    """
    MongoDB model for storing client project submissions
    """
    # Unique project identifier
    project_id = StringField(required=True, unique=True, max_length=36)
    
    # User identifier (from auth system)
    user_id = StringField(required=True, max_length=100)
    
    # User contact information
    first_name = StringField(max_length=100)
    email = StringField(required=True, max_length=255)
    phone = StringField(max_length=20)
    contact_method = StringField(max_length=20, choices=['email', 'phone', 'whatsapp'])
    
    # Project details
    job_title = StringField(max_length=200)
    job_description = StringField()
    location = StringField(max_length=100)
    budget = StringField(max_length=50)
    urgency = StringField(max_length=20, choices=['asap', 'this_week', 'this_month', 'flexible'], null=True)
    country = StringField(max_length=5)  # Country code like 'BG', 'US', etc.
    service_category = StringField(max_length=100)
    
    # Image storage
    image_urls = ListField(StringField())  # List of GCS URLs
    image_count = IntField(default=0)
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    status = StringField(max_length=20, default='pending', 
                        choices=['pending', 'contacted', 'quoted', 'accepted', 'completed', 'cancelled'])
    
    # GDPR compliance
    gdpr_consent = BooleanField(default=False)
    
    # Additional flexible data storage
    additional_data = DictField()
    
    # MongoDB collection settings
    meta = {
        'collection': 'client_projects',
        'indexes': [
            'project_id',
            'user_id',
            'email',
            'created_at',
            'status',
            'location',
            'country',
            'service_category'
        ]
    }
    
    def save(self, *args, **kwargs):
        """Override save to update timestamp"""
        self.updated_at = datetime.utcnow()
        return super().save(*args, **kwargs)
    
    @classmethod
    def create_project(cls, form_data, image_urls):
        """
        Factory method to create a new project from form data
        """
        project = cls(
            project_id=form_data.get('project_id', str(uuid.uuid4())),
            user_id=form_data.get('userId') or form_data.get('user_id', ''),
            first_name=form_data.get('firstName', ''),
            email=form_data.get('email', ''),
            phone=form_data.get('phone', ''),
            contact_method=form_data.get('contactMethod', 'email'),
            job_title=form_data.get('jobTitle', ''),
            job_description=form_data.get('jobDescription', ''),
            location=form_data.get('location', ''),
            budget=form_data.get('budget', ''),
            urgency=form_data.get('urgency', 'flexible'),
            country=form_data.get('country', ''),
            service_category=form_data.get('service_category', ''),
            image_urls=image_urls,
            image_count=len(image_urls),
            gdpr_consent=form_data.get('gdprConsent') == 'true',
            additional_data=form_data  # Store all form data for reference
        )
        return project
    
    def to_dict(self):
        """Convert to dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'project_id': self.project_id,
            'user_id': self.user_id,
            'first_name': self.first_name,
            'email': self.email,
            'phone': self.phone,
            'contact_method': self.contact_method,
            'job_title': self.job_title,
            'job_description': self.job_description,
            'location': self.location,
            'budget': self.budget,
            'urgency': self.urgency,
            'country': self.country,
            'service_category': self.service_category,
            'image_urls': self.image_urls,
            'image_count': self.image_count,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'status': self.status,
            'gdpr_consent': self.gdpr_consent,
            'additional_data': self.additional_data
        }
    
    @classmethod 
    def get_by_project_id(cls, project_id):
        """Get project by project_id"""
        try:
            return cls.objects(project_id=project_id).first()
        except Exception as e:
            print(f"Error fetching project {project_id}: {str(e)}")
            return None
    
    @classmethod
    def get_by_user_id(cls, user_id):
        """Get all projects by user_id"""
        try:
            return cls.objects(user_id=user_id).order_by('-created_at')
        except Exception as e:
            print(f"Error fetching projects for user {user_id}: {str(e)}")
            return []
    
    @classmethod
    def get_by_email(cls, email):
        """Get all projects by email"""
        try:
            return cls.objects(email=email).order_by('-created_at')
        except Exception as e:
            print(f"Error fetching projects for email {email}: {str(e)}")
            return []
    
    @classmethod
    def get_recent_projects(cls, limit=50):
        """Get recent projects"""
        try:
            return cls.objects().order_by('-created_at').limit(limit)
        except Exception as e:
            print(f"Error fetching recent projects: {str(e)}")
            return []
    
    def __str__(self):
        return f"ClientProject({self.project_id}): {self.email}"