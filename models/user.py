from datetime import datetime

from flask_mongoengine import MongoEngine
from mongoengine import IntField
from mongoengine import StringField, DateTimeField
from mongoengine import BooleanField

db = MongoEngine()


class Users(db.Document):
    email = db.EmailField(required=True, unique=True)
    password = db.StringField()

    google_id = StringField(unique=True, sparse=True) 
    auth_provider = StringField(default='email')  # 'email' or 'google'
    email_verified = BooleanField(default=False)
    name = StringField()  
    
    createdAt = db.DateTimeField(default=datetime.now)
    isDeleted = db.BooleanField(default=False)
    role = db.ListField()
    customerId = IntField(required=False)
    reset_token_hash = StringField()     
    reset_expires_at = DateTimeField()
    reset_used_at = DateTimeField()

    def __repr__(self):
        return f'<User {self.email}>'