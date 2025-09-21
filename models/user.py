from datetime import datetime

from flask_mongoengine import MongoEngine
from mongoengine import IntField
from mongoengine import StringField, DateTimeField

db = MongoEngine()


class Users(db.Document):
    email = db.EmailField(required=True, unique=True)
    password = db.StringField(required=True)
    createdAt = db.DateTimeField(default=datetime.now)
    isDeleted = db.BooleanField(default=False)
    role = db.ListField()
    customerId = IntField(required=False)
    reset_token_hash = StringField()     
    reset_expires_at = DateTimeField()
    reset_used_at = DateTimeField()

    def __repr__(self):
        return f'<User {self.email}>'


class BlacklistedToken(db.Document):
    token = db.StringField(required=True, unique=True)
    expiresAt = db.DateTimeField(required=True)
    blacklistedAt = db.DateTimeField(default=datetime.utcnow)
    reason = db.StringField(required=True)
    userId = db.ObjectIdField(required=True)
    email = db.EmailField(required=True)
    role = db.ListField()

    def __repr__(self):
        return f'<BlacklistedToken {self.token}>'