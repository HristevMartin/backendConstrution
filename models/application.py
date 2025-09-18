from mongoengine import Document, StringField, IntField, DateTimeField, BooleanField
from datetime import datetime
import uuid

class Application(Document):
    """
    MongoDB model for storing trader applications to jobs with payment tracking
    One application per trader per job (enforced by unique constraint)
    """
    
    application_id = StringField(required=True, unique=True, max_length=36, default=lambda: str(uuid.uuid4()))
    
    job_id = StringField(required=True, max_length=36)  
    trader_id = StringField(required=True, max_length=100)  
    
    stripe_pi_id = StringField(required=True, max_length=100)  
    amount = IntField(required=True)  # Amount in cents (e.g., 500 = £5.00)
    currency = StringField(required=True, max_length=3, default='gbp')
    
    status = StringField(required=True, max_length=20, default='initiated', 
                        choices=['initiated', 'paid', 'refunded', 'failed', 'cancelled'])
    
    application_message = StringField(max_length=2000)  # Trader's application message
    portfolio_images = StringField(max_length=1000)  # JSON string of portfolio image URLs
    
    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
    
    # MongoDB collection settings
    meta = {
        'collection': 'applications',
        'indexes': [
            'application_id',
            'job_id',
            'trader_id',
            'stripe_pi_id',
            'status',
            'created_at'
        ]
    }
    
    def save(self, *args, **kwargs):
        self.updated_at = datetime.utcnow()
        return super(Application, self).save(*args, **kwargs)
    
    def mark_as_paid(self):
        """Mark application as paid"""
        self.status = 'paid'
        self.save()
    
    def mark_as_refunded(self):
        """Mark application as refunded"""
        self.status = 'refunded'
        self.save()
    
    def mark_as_failed(self):
        """Mark application as failed"""
        self.status = 'failed'
        self.save()
    
    def __str__(self):
        return f'<Application {self.application_id}: Trader {self.trader_id} -> Job {self.job_id} ({self.status})>'
