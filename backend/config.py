"""
Configuration Manager
Loads and validates all environment variables
"""

import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """Application Configuration"""
    
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    FIREBASE_CONFIG = {
        'apiKey': os.getenv('FIREBASE_API_KEY'),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'projectId': os.getenv('FIREBASE_PROJECT_ID'),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        'appId': os.getenv('FIREBASE_APP_ID')
    }
    
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv(
        'FIREBASE_SERVICE_ACCOUNT_PATH',
        str(BASE_DIR / 'serviceAccountKey.json')
    )
    
    PIPED_INSTANCES = [
        os.getenv('PIPED_INSTANCE_1', 'https://pipedapi.kavin.rocks'),
        os.getenv('PIPED_INSTANCE_2', 'https://pipedapi-libre.kavin.rocks'),
        os.getenv('PIPED_INSTANCE_3', 'https://watchapi.whatever.social'),
        os.getenv('PIPED_INSTANCE_4', 'https://pipedapi.adminforge.de')
    ]
    
    FACEBOOK_APP_ID = os.getenv('FACEBOOK_APP_ID')
    FACEBOOK_APP_SECRET = os.getenv('FACEBOOK_APP_SECRET')
    FACEBOOK_ACCESS_TOKEN = os.getenv('FACEBOOK_ACCESS_TOKEN')
    
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))
    MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', 36000))
    MAX_CONCURRENT_PROCESSES = int(os.getenv('MAX_CONCURRENT_PROCESSES', 5))
    
    TEMP_DIR = os.getenv('TEMP_DIR', str(BASE_DIR / 'temp_videos'))
    MAX_TEMP_FILE_SIZE = int(os.getenv('MAX_TEMP_FILE_SIZE', 5368709120))
    CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', 3600))
    
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = os.getenv('CACHE_TYPE', 'simple')
    CACHE_DEFAULT_TIMEOUT = int(os.getenv('CACHE_DEFAULT_TIMEOUT', 300))
    
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', str(BASE_DIR / 'logs' / 'app.log'))
    LOG_MAX_BYTES = int(os.getenv('LOG_MAX_BYTES', 10485760))
    LOG_BACKUP_COUNT = int(os.getenv('LOG_BACKUP_COUNT', 5))
    
    APP_NAME = os.getenv('APP_NAME', 'AI Video Learning Platform')
    APP_VERSION = os.getenv('APP_VERSION', '1.0.0')
    MAX_CHUNK_DURATION = int(os.getenv('MAX_CHUNK_DURATION', 600))
    ENABLE_BACKGROUND_PROCESSING = os.getenv('ENABLE_BACKGROUND_PROCESSING', 'true').lower() == 'true'
    
    FEATURES = {
        'youtube_processing': True,
        'facebook_processing': True,
        'ai_chat': True,
        'transcript': True,
        'sync': True,
        'word_analysis': True,
        'multi_model': True,
        'caching': True,
        'chunking': True
    }
    
    @classmethod
    def validate(cls):
        """Validate critical configurations"""
        errors = []
        warnings = []
        
        if not cls.GEMINI_API_KEY:
            warnings.append('⚠️ GEMINI_API_KEY not set - Google Gemini disabled')
        
        if not cls.OPENROUTER_API_KEY:
            warnings.append('⚠️ OPENROUTER_API_KEY not set - OpenRouter models disabled')
        
        if not cls.GROQ_API_KEY:
            warnings.append('⚠️ GROQ_API_KEY not set - Groq Whisper disabled')
        
        if not all(cls.FIREBASE_CONFIG.values()):
            warnings.append('⚠️ Firebase config incomplete - Using local storage')
        
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        os.makedirs(os.path.dirname(cls.LOG_FILE), exist_ok=True)
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'warnings': warnings
        }
    
    @classmethod
    def get_summary(cls):
        """Get configuration summary"""
        return {
            'app_name': cls.APP_NAME,
            'version': cls.APP_VERSION,
            'debug': cls.DEBUG,
            'features': cls.FEATURES,
            'ai_providers': {
                'gemini': bool(cls.GEMINI_API_KEY),
                'openrouter': bool(cls.OPENROUTER_API_KEY),
                'groq': bool(cls.GROQ_API_KEY)
            },
            'video_platforms': {
                'youtube': True,
                'facebook': bool(cls.FACEBOOK_APP_ID)
            }
        }


config = Config()

validation_result = config.validate()

if validation_result['errors']:
    print("❌ Configuration Errors:")
    for error in validation_result['errors']:
        print(f"   {error}")

if validation_result['warnings']:
    print("⚠️  Configuration Warnings:")
    for warning in validation_result['warnings']:
        print(f"   {warning}")

print(f"\n✅ Configuration loaded for: {config.APP_NAME} v{config.APP_VERSION}")
