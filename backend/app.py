"""
Main Flask Application
Entry point for the AI Video Learning Platform
"""

import os
import sys
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config import config
from backend.middleware.error_handler import register_error_handlers
from backend.utils.logger import setup_logger

# Import routes
from backend.routes.video_routes import video_bp
from backend.routes.ai_routes import ai_bp
from backend.routes.chat_routes import chat_bp
from backend.routes.health_routes import health_bp

# Setup logger
logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

# Create Flask app
app = Flask(__name__,
           static_folder='../frontend/static',
           template_folder='../frontend')

# Configure app
app.config['SECRET_KEY'] = config.SECRET_KEY
app.config['MAX_CONTENT_LENGTH'] = config.MAX_TEMP_FILE_SIZE

# Enable CORS
CORS(app, 
     origins=config.CORS_ORIGINS,
     supports_credentials=True,
     allow_headers=['Content-Type', 'Authorization'],
     methods=['GET', 'POST', 'PUT', 'DELETE', 'OPTIONS'])

# Register error handlers
register_error_handlers(app)

# Register blueprints
app.register_blueprint(video_bp, url_prefix='/api/video')
app.register_blueprint(ai_bp, url_prefix='/api/ai')
app.register_blueprint(chat_bp, url_prefix='/api/chat')
app.register_blueprint(health_bp, url_prefix='/api/health')

logger.info("✅ All blueprints registered")


# ============================================
# MAIN ROUTES
# ============================================

@app.route('/')
def index():
    """Serve main page"""
    try:
        return send_from_directory('../frontend', 'index.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return jsonify({'error': 'Frontend not found'}), 404


@app.route('/api')
def api_info():
    """API information endpoint"""
    return jsonify({
        'success': True,
        'app_name': config.APP_NAME,
        'version': config.APP_VERSION,
        'endpoints': {
            'video': '/api/video',
            'ai': '/api/ai',
            'chat': '/api/chat',
            'health': '/api/health'
        },
        'features': config.FEATURES,
        'timestamp': datetime.now().isoformat()
    })


# ============================================
# REQUEST HOOKS
# ============================================

@app.before_request
def before_request():
    """Log incoming requests"""
    from flask import request
    logger.debug(f"📥 {request.method} {request.path} - {request.remote_addr}")


@app.after_request
def after_request(response):
    """Add headers and log responses"""
    from flask import request
    
    # Add CORS headers
    response.headers['Access-Control-Allow-Origin'] = ', '.join(config.CORS_ORIGINS)
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type, Authorization'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, PUT, DELETE, OPTIONS'
    response.headers['Access-Control-Allow-Credentials'] = 'true'
    
    # Log response
    logger.debug(f"📤 {response.status_code} - {request.path}")
    
    return response


# ============================================
# CLEANUP ON SHUTDOWN
# ============================================

def cleanup_temp_files():
    """Cleanup temporary files"""
    from backend.utils.helpers import cleanup_temp_files
    logger.info("🧹 Cleaning up temporary files...")
    cleanup_temp_files(config.TEMP_DIR)


import atexit
atexit.register(cleanup_temp_files)


# ============================================
# RUN APPLICATION
# ============================================

if __name__ == '__main__':
    # Print startup info
    print("\n" + "="*60)
    print(f"🚀 {config.APP_NAME} v{config.APP_VERSION}")
    print("="*60)
    print(f"🌍 Environment: {'Development' if config.DEBUG else 'Production'}")
    print(f"🏠 Host: {config.HOST}:{config.PORT}")
    print(f"📁 Temp Directory: {config.TEMP_DIR}")
    print(f"📝 Log File: {config.LOG_FILE}")
    print("\n🤖 AI Providers:")
    print(f"   ✓ Google Gemini: {'Enabled' if config.GEMINI_API_KEY else 'Disabled'}")
    print(f"   ✓ OpenRouter: {'Enabled' if config.OPENROUTER_API_KEY else 'Disabled'}")
    print(f"   ✓ Groq Whisper: {'Enabled' if config.GROQ_API_KEY else 'Disabled'}")
    print("\n🎥 Video Platforms:")
    print(f"   ✓ YouTube: Enabled (Piped API)")
    print(f"   ✓ Facebook: {'Enabled' if config.FACEBOOK_APP_ID else 'Disabled'}")
    print("\n✨ Features:")
    for feature, enabled in config.FEATURES.items():
        status = '✅' if enabled else '❌'
        print(f"   {status} {feature.replace('_', ' ').title()}")
    print("\n" + "="*60)
    print(f"🎯 Server starting on http://{config.HOST}:{config.PORT}")
    print(f"📚 API Docs: http://{config.HOST}:{config.PORT}/api")
    print("="*60 + "\n")
    
    # Run app
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
)
