# config.py
import os
from dotenv import load_dotenv

load_dotenv()

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
    
    # Google Cloud Storage Configuration
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'client_images_trader')
    GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID', 'regal-framework-475315-m1')
    GCS_CREDENTIALS_PATH = os.getenv('GCS_CREDENTIALS_PATH', '')
    
    # Email Configuration (SendGrid)
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'info@find-tradespeople.com')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'contact@find-tradespeople.com')
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Find Tradespeople')
    
    # Application Configuration
    APP_BASE_URL = os.getenv('APP_BASE_URL', 'http://localhost:8000')
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'http://192.168.0.46:8000')

    @classmethod
    def validate_email_config(cls):
        """Validate that email configuration is properly set"""
        missing = []
        if not cls.SENDGRID_API_KEY:
            missing.append('SENDGRID_API_KEY')
        if not cls.SENDGRID_FROM_EMAIL or cls.SENDGRID_FROM_EMAIL == 'noreply@yourcompany.com':
            missing.append('SENDGRID_FROM_EMAIL')
        if not cls.ADMIN_EMAIL or cls.ADMIN_EMAIL == 'admin@yourcompany.com':
            missing.append('ADMIN_EMAIL')
            
        if missing:
            print(f"Warning: Missing email configuration: {', '.join(missing)}")
            print("   Emails will not be sent until these are configured in your .env file")
            return False
        else:
            print("Email configuration validated successfully")
            return True