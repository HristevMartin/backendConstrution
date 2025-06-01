# config.py
import os

class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dasdasdadsdasdasdasdasdas')
    # MONGODB_SETTINGS = {
    
    #     'db': os.getenv('MONGO_DB', 'travelDB'),
    #     'host': os.getenv('DB_HOST', 'localhost'),
    #     'port': int(os.getenv('DB_PORT', '27017')),
    # }
    MONGODB_SETTINGS = {
        'host': os.getenv('MONGODB_URI', 'mongodb://localhost:27017/travelDB')
    }
    
    # Google Cloud Storage Configuration
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'profile_images_custom_123123')
    GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID', 'stalwart-elixir-458022-d5')
    GCS_CREDENTIALS_PATH = os.getenv('GCS_CREDENTIALS_PATH', 'C:/Users/hrist/constructionKeys/stalwart-elixir-458022-d5-1a3a6e27ef1c.json')
