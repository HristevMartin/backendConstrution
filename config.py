# config.py
import os

class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dasdasdadsdasdasdasdasdas')
    #development
    MONGODB_SETTINGS = {
        'db': os.getenv('MONGO_DB', 'travelDB'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '27017')),
    }

    #production
    # MONGODB_SETTINGS = {
    #     'host': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/travelDB')
    # }
    
    # # Google Cloud Storage Configuration
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'client_images_zoo')
    GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID', 'pure-zoo-466316-t4')
    GCS_CREDENTIALS_PATH = os.getenv('GCS_CREDENTIALS_PATH', 'C:/Users/hrist/constructionKeys/pure-zoo-466316-t4-b0c8401c6a9d.json')