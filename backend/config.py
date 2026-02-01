"""
Configuration Manager for AI Video Platform
Loads environment variables and provides configuration settings
"""

import os
import json
from typing import Dict, Any
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class Config:
    """Central configuration class"""
    
    # Flask Configuration
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key-change-in-production')
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    PORT = int(os.getenv('PORT', 5000))
    HOST = os.getenv('HOST', '0.0.0.0')
    
    # CORS Configuration
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:3000').split(',')
    
    # AI APIs Configuration
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    
    # Firebase Configuration
    FIREBASE_CONFIG = {
        'apiKey': os.getenv('FIREBASE_API_KEY'),
        'authDomain': os.getenv('FIREBASE_AUTH_DOMAIN'),
        'projectId': os.getenv('FIREBASE_PROJECT_ID'),
        'storageBucket': os.getenv('FIREBASE_STORAGE_BUCKET'),
        'messagingSenderId': os.getenv('FIREBASE_MESSAGING_SENDER_ID'),
        'appId': os.getenv('FIREBASE_APP_ID')
    }
    
    FIREBASE_SERVICE_ACCOUNT_PATH = os.getenv('FIREBASE_SERVICE_ACCOUNT_PATH')
    
    # YouTube Processing Configuration
    PIPED_INSTANCES = [
        os.getenv('PIPED_INSTANCE_1', 'https://pipedapi.kavin.rocks'),
        os.getenv('PIPED_INSTANCE_2', 'https://pipedapi-libre.kavin.rocks'),
        os.getenv('PIPED_INSTANCE_3', 'https://watchapi.whatever.social')
    ]
    
    # Rate Limiting
    RATE_LIMIT_REQUESTS = int(os.getenv('RATE_LIMIT_REQUESTS', 100))
    RATE_LIMIT_WINDOW = int(os.getenv('RATE_LIMIT_WINDOW', 60))
    MAX_VIDEO_DURATION = int(os.getenv('MAX_VIDEO_DURATION', 72000))
    MAX_CONCURRENT_PROCESSES = int(os.getenv('MAX_CONCURRENT_PROCESSES', 5))
    
    # Temporary Storage
    TEMP_DIR = os.getenv('TEMP_DIR', './temp_videos')
    MAX_TEMP_FILE_SIZE = int(os.getenv('MAX_TEMP_FILE_SIZE', 5368709120))
    CLEANUP_INTERVAL = int(os.getenv('CLEANUP_INTERVAL', 3600))
    
    # Logging
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO')
    LOG_FILE = os.getenv('LOG_FILE', './logs/app.log')
    
    # Application Settings
    APP_NAME = "AI Video Intelligence Platform"
    APP_VERSION = "1.0.0"
    
    # AI Models Configuration
    AI_MODELS = {
        'gemini-2.0-flash': {
            'name': 'Gemini 2.0 Flash',
            'provider': 'google',
            'context_length': 1000000,
            'max_tokens': 8192,
            'supports_timestamps': True
        },
        'gemini-2.0-pro': {
            'name': 'Gemini 2.0 Pro',
            'provider': 'google',
            'context_length': 2000000,
            'max_tokens': 8192,
            'supports_timestamps': True
        },
        'openai/gpt-3.5-turbo': {
            'name': 'ChatGPT 3.5 Turbo',
            'provider': 'openrouter',
            'context_length': 16384,
            'max_tokens': 4096,
            'supports_timestamps': True
        },
        'anthropic/claude-3-haiku': {
            'name': 'Claude 3 Haiku',
            'provider': 'openrouter',
            'context_length': 200000,
            'max_tokens': 4096,
            'supports_timestamps': True
        }
    }
    
    # Feature Flags
    FEATURES = {
        'youtube_processing': True,
        'facebook_processing': True,
        'ai_chat': True,
        'transcript': True,
        'sync': True,
        'word_analysis': True,
        'quiz_generation': True,
        'translation': True,
        'audio_upload': True,
        'export_options': True
    }
    
    @classmethod
    def validate(cls) -> Dict[str, Any]:
        """Validate configuration and return status"""
        validation_result = {
            'valid': True,
            'errors': [],
            'warnings': []
        }
        
        # Check required API keys
        if not cls.GEMINI_API_KEY:
            validation_result['warnings'].append('GEMINI_API_KEY is not set - Google Gemini features will be disabled')
        
        if not cls.OPENROUTER_API_KEY:
            validation_result['warnings'].append('OPENROUTER_API_KEY is not set - OpenRouter features will be disabled')
        
        if not cls.GROQ_API_KEY:
            validation_result['warnings'].append('GROQ_API_KEY is not set - Whisper transcription will use fallback')
        
        # Check Firebase configuration
        firebase_configured = all(cls.FIREBASE_CONFIG.values())
        if not firebase_configured:
            validation_result['warnings'].append('Firebase configuration is incomplete - Using local JSON storage')
        
        # Create temp directory if it doesn't exist
        os.makedirs(cls.TEMP_DIR, exist_ok=True)
        
        # Create logs directory
        os.makedirs(os.path.dirname(cls.LOG_FILE), exist_ok=True)
        
        return validation_result
    
    @classmethod
    def get_available_models(cls) -> Dict[str, Any]:
        """Get available AI models based on configuration"""
        available_models = {}
        
        # Add Gemini models if API key is available
        if cls.GEMINI_API_KEY:
            available_models.update({
                'gemini-2.0-flash': cls.AI_MODELS['gemini-2.0-flash'],
                'gemini-2.0-pro': cls.AI_MODELS['gemini-2.0-pro']
            })
        
        # Add OpenRouter models if API key is available
        if cls.OPENROUTER_API_KEY:
            available_models.update({
                'openai/gpt-3.5-turbo': cls.AI_MODELS['openai/gpt-3.5-turbo'],
                'anthropic/claude-3-haiku': cls.AI_MODELS['anthropic/claude-3-haiku']
            })
        
        return available_models
    
    @classmethod
    def to_dict(cls) -> Dict[str, Any]:
        """Convert configuration to dictionary"""
        config_dict = {}
        
        for key in dir(cls):
            if not key.startswith('_') and not callable(getattr(cls, key)):
                value = getattr(cls, key)
                if not isinstance(value, (type, classmethod, staticmethod)):
                    config_dict[key] = value
        
        return config_dict


# Create global configuration instance
config = Config()

# Validate configuration on import
config_validation = config.validate()
if config_validation['errors']:
    print("Configuration Errors:", config_validation['errors'])
if config_validation['warnings']:
    print("Configuration Warnings:", config_validation['warnings'])
