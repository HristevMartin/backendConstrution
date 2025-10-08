from mongoengine import Document, StringField, IntField, DateTimeField
import datetime
from flask_mongoengine import MongoEngine

db = MongoEngine()

class TraderRating(db.Document):
    userId = StringField(required=True)
    homeownerId = StringField(required=True)
    jobId = StringField(required=True)
    rating = IntField(required=True)
    comment = StringField(required=True)
    createdDate = DateTimeField(required=True)
    updatedDate = DateTimeField(required=True)
    
    meta = {
        'collection': 'trader_ratings',
        'indexes': [
            {'fields': ['userId']},
            {'fields': ['jobId']},
            {'fields': ['homeownerId']},
            {'fields': ['jobId', 'homeownerId'], 'unique': True} 
        ]
    }