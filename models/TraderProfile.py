from flask_mongoengine import MongoEngine

db = MongoEngine()


class TraderProfile(db.Document):
    fullName = db.StringField(required=False, null=True)
    company = db.StringField(required=False, null=True)
    bio = db.StringField(required=False, null=True)
    yearsExperience = db.StringField(required=False, null=True)
    specialties = db.StringField(required=False, null=True)
    selectedTrades = db.StringField(required=False, null=True)
    profileImage = db.StringField(required=False, null=True)
    createdDate = db.DateTimeField(required=False, null=True)
    isActive = db.BooleanField(required=False, default=True)
    isDeleted = db.BooleanField(required=False, default=False)
    userId = db.StringField(required=False, null=True)
    
