from datetime import datetime
from flask_mongoengine import MongoEngine
from mongoengine import StringField, DateTimeField, IntField

db = MongoEngine()


class PageVisit(db.Document):
    """Model for tracking page visits and user analytics"""
    
    # Page information
    page = StringField(required=True, max_length=500)  # The page/route visited
    url = StringField(required=True, max_length=1000)  # Full URL
    
    # User tracking
    ip_address = StringField(required=True, max_length=45)  # IPv4 or IPv6
    user_agent = StringField(max_length=1000)  # Browser/device info
    
    # Timing
    timestamp = DateTimeField(required=True)  # When the visit occurred
    created_at = DateTimeField(default=datetime.utcnow)  # When record was saved
    
    # Optional referrer and session tracking
    referrer = StringField(max_length=1000)  # Where they came from
    session_id = StringField(max_length=100)  # Session identifier if available
    
    # Geolocation (optional for future use)
    country = StringField(max_length=100)
    city = StringField(max_length=100)
    
    # Device/browser info (optional)
    device_type = StringField(max_length=50)  # mobile, desktop, tablet
    browser = StringField(max_length=100)
    os = StringField(max_length=100)
    
    meta = {
        'collection': 'page_visits',
        'indexes': [
            'ip_address',
            'page',
            'timestamp',
            'created_at',
            ('page', 'timestamp'),  # Compound index for page analytics
            ('ip_address', 'timestamp'),  # Compound index for user tracking
        ]
    }

    def __repr__(self):
        return f'<PageVisit {self.page} from {self.ip_address} at {self.timestamp}>'

    def to_dict(self):
        """Convert the document to a dictionary for JSON serialization"""
        return {
            'id': str(self.id),
            'page': self.page,
            'url': self.url,
            'ip_address': self.ip_address,
            'user_agent': self.user_agent,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'referrer': self.referrer,
            'session_id': self.session_id,
            'country': self.country,
            'city': self.city,
            'device_type': self.device_type,
            'browser': self.browser,
            'os': self.os
        }
