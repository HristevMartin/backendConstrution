from celery import Celery
import os
from mongoengine import connect

REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
DB_HOST = os.getenv('DB_HOST', 'localhost')
DB_PORT = int(os.getenv('DB_PORT', '27017'))
MONGO_DB = os.getenv('MONGO_DB', 'travelDB')

print("=" * 50)
print(" Celery App Configuration")
print("=" * 50)
print(f" Redis URL: {REDIS_URL}")
print(f"  MongoDB: {DB_HOST}:{DB_PORT}/{MONGO_DB}")
print("=" * 50)

# Configure Celery
celery = Celery(
    'jobhub',
    broker=REDIS_URL,
    backend=REDIS_URL,
    include=['tasks']
)

celery.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='Europe/London',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=30 * 60, 
    broker_connection_retry_on_startup=True,
)

@celery.on_after_configure.connect
def setup_mongodb(sender, **kwargs):
    """Establish MongoDB connection for Celery workers"""
    try:
        print(f"🔌 Connecting to MongoDB at {DB_HOST}:{DB_PORT}/{MONGO_DB}...")
        
        connect(host=DB_HOST, port=DB_PORT, db=MONGO_DB, alias='default')
        
        print(f"✓ MongoDB connected for Celery worker to {DB_HOST}:{DB_PORT}/{MONGO_DB}")
    except Exception as e:
        print(f"❌ MongoDB connection failed: {str(e)}")
        raise 


import tasks 