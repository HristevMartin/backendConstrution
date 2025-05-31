from flask_mongoengine import MongoEngine

db = MongoEngine()


class UserTrackDb(db.Document):
    # create a such model
    page = db.StringField(required=False, null=True)
    userAgent = db.StringField(required=False, null=True)
    timestamp = db.DateTimeField(required=False, null=True)
    clientIP = db.StringField(required=False, null=True)
    
