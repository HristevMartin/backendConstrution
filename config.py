# config.py
import os
# from dotenv import load_dotenv

# load_dotenv()

class Config:
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY', 'dasdasdadsdasdasdasdasdas')
    
    # Environment mode: 'production' or 'development'
    ENV = os.getenv('FLASK_ENV', 'production').lower()
    IS_PRODUCTION = ENV == 'production'
    
    # MongoDB Settings
    MONGODB_SETTINGS = {
        'db': os.getenv('MONGO_DB', 'travelDB'),
        'host': os.getenv('DB_HOST', 'localhost'),
        'port': int(os.getenv('DB_PORT', '27017')),
    } 

    # GCS Configuration
    GCS_BUCKET_NAME = os.getenv('GCS_BUCKET_NAME', 'client_images_trader')
    GCS_PROJECT_ID = os.getenv('GCS_PROJECT_ID', 'regal-framework-475315-m1')
    GCS_CREDENTIALS_PATH = os.getenv('GCS_CREDENTIALS_PATH', '')
    
    # Email Configuration (SendGrid)
    SENDGRID_API_KEY = os.getenv('SENDGRID_API_KEY', '')
    print('show me the sendgrid api key', SENDGRID_API_KEY[:15])
    SENDGRID_FROM_EMAIL = os.getenv('SENDGRID_FROM_EMAIL', 'noreply@find-tradespeople.com')
    ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', 'contact@find-tradespeople.com')
    COMPANY_NAME = os.getenv('COMPANY_NAME', 'Find Tradespeople')
    
    # Application Configuration
    APP_BASE_URL = os.getenv('APP_BASE_URL', 'https://find-tradespeople.com')
    FRONTEND_BASE_URL = os.getenv('FRONTEND_BASE_URL', 'https://find-tradespeople.com')

    # Cookie domain configurationss
    _cookie_domain_env = os.getenv('COOKIE_DOMAIN', '').strip()

    GOOGLE_CLIENT_ID = os.getenv('GOOGLE_CLIENT_ID')
    
    if _cookie_domain_env:
        COOKIE_DOMAIN = _cookie_domain_env
    elif IS_PRODUCTION:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(FRONTEND_BASE_URL)
            host = (parsed.hostname or "").strip()
            # Use .domain.com format to support both www and non-www
            if host:
                # Remove www. prefix if present, then add leading dot
                base_domain = host.replace('www.', '')
                COOKIE_DOMAIN = f'.{base_domain}'  # e.g., .find-tradespeople.com
            else:
                COOKIE_DOMAIN = None
        except Exception:
            COOKIE_DOMAIN = None
    else:
        COOKIE_DOMAIN = None

    # Cookie Security Settings
    COOKIE_SECURE = IS_PRODUCTION
    COOKIE_HTTPONLY = True
    COOKIE_SAMESITE = 'None' if IS_PRODUCTION else 'Lax'
    COOKIE_PATH = '/'

    @classmethod
    def get_cookie_config(cls):
        """Returns cookie configuration as a dictionary"""
        config = {
            'httponly': cls.COOKIE_HTTPONLY,
            'secure': cls.COOKIE_SECURE,
            'samesite': cls.COOKIE_SAMESITE,
            'path': cls.COOKIE_PATH
        }
        # Only add domain if it's explicitly set
        if cls.COOKIE_DOMAIN:
            config['domain'] = cls.COOKIE_DOMAIN
        return config
    
    @classmethod
    def log_cookie_settings(cls):
        """Log current cookie settings for debugging"""
        print(f"🍪 Cookie Configuration:")
        print(f"   Environment: {cls.ENV}")
        print(f"   Domain: {cls.COOKIE_DOMAIN}")
        print(f"   Secure: {cls.COOKIE_SECURE}")
        print(f"   SameSite: {cls.COOKIE_SAMESITE}")
        print(f"   HttpOnly: {cls.COOKIE_HTTPONLY}")

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
            print(f"⚠️  Warning: Missing email configuration: {', '.join(missing)}")
            print("   Emails will not be sent until these are configured in your .env file")
            return False
        else:
            print("✅ Email configuration validated successfully")
            return True