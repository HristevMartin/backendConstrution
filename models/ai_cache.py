from mongoengine import Document, StringField, DateTimeField, DictField
from datetime import datetime


import uuid

class AITraderCache(Document):
    key = StringField(required=True, unique=True)  
    value = DictField(required=True)              
    created_at = DateTimeField(default=datetime.utcnow)

    meta = {
        "collection": "ai_trader_cache",
        "indexes": [
            {"fields": ["created_at"], "expireAfterSeconds": 86400} 
        ]
    }