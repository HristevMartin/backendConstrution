from flask_mongoengine import MongoEngine

db = MongoEngine()

class ClientUserCompletedJobs(db.Document):
    id = db.StringField(required=True, primary_key=True)
    userId = db.StringField(required=True)
    jobId = db.StringField(required=True)   
    completed_jobs = db.IntField(default=0) 
    cancelled_jobs = db.IntField(default=0) 
    posted_jobs = db.IntField(default=0)    
    last_completed_at = db.DateTimeField()   
    first_posted_at = db.DateTimeField()    
    response_rate = db.FloatField(default=0)
    reliable = db.BooleanField(default=False)
    created_at = db.DateTimeField(required=True)
    updated_at = db.DateTimeField(required=True)