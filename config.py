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
