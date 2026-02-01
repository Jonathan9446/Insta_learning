"""
Main Flask Application for AI Video Platform
Entry point for the backend server
"""

import os
import sys
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime

# Add current directory to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import configuration
from config import config

# Import routes
from routes.video_routes import video_bp
from routes.ai_routes import ai_bp
from routes.chat_routes import chat_bp

# Import utilities
from utils.logger import setup_logger
from utils.helpers import cleanup_temp_files

# Initialize Flask app
app = Flask(__name__, 
           static_folder='../frontend/static',
           template_folder='../frontend')

# Configure CORS
CORS(app, origins=config.CORS_ORIGINS, supports_credentials=True)

# Set secret key
app.secret_key = config.SECRET_KEY

# Setup logging
logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

# Register blueprints (routes)
app.register_blueprint(video_bp, url_prefix='/api/video')
app.register_blueprint(ai_bp, url_prefix='/api/ai')
app.register_blueprint(chat_bp, url_prefix='/api/chat')

@app.route('/')
def index():
    """Serve main frontend page"""
    try:
        return app.send_static_file('index.html')
    except Exception as e:
        logger.error(f"Error serving index: {e}")
        return jsonify({'error': 'Frontend not found'}), 404

@app.route('/api/health', methods=['GET'])
def health_check():
    """Health check endpoint"""
    try:
        # Basic health check
        health_data = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'service': config.APP_NAME,
            'version': config.APP_VERSION,
            'environment': 'production' if not config.DEBUG else 'development',
            'features': config.FEATURES,
            'available_models': list(config.get_available_models().keys())
        }
        
        # Check external services
        external_services = {
            'firebase': False,
            'gemini': bool(config.GEMINI_API_KEY),
            'openrouter': bool(config.OPENROUTER_API_KEY),
            'groq': bool(config.GROQ_API_KEY)
        }
        
        health_data['external_services'] = external_services
        return jsonify(health_data), 200
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({'status': 'unhealthy', 'error': str(e)}), 500

@app.route('/api/config', methods=['GET'])
def get_config():
    """Get public configuration (safe to expose)"""
    public_config = {
        'app_name': config.APP_NAME,
        'version': config.APP_VERSION,
        'features': config.FEATURES,
        'available_models': config.get_available_models(),
        'max_video_duration': config.MAX_VIDEO_DURATION,
        'rate_limit': {
            'requests': config.RATE_LIMIT_REQUESTS,
            'window': config.RATE_LIMIT_WINDOW
        }
    }
    return jsonify(public_config), 200

@app.route('/api/stats', methods=['GET'])
def get_stats():
    """Get application statistics"""
    from database import DatabaseManager
    
    try:
        db = DatabaseManager()
        stats = {
            'timestamp': datetime.now().isoformat(),
            'service': config.APP_NAME,
            'uptime': 'N/A',  # Can be implemented with process start time
            'memory_usage': 'N/A',
            'active_sessions': 0,
            'database_stats': db.get_stats()
        }
        return jsonify(stats), 200
    except Exception as e:
        logger.error(f"Stats error: {e}")
        return jsonify({'error': str(e)}), 500

@app.before_request
def before_request():
    """Log incoming requests"""
    logger.info(f"{request.method} {request.path} - {request.remote_addr}")

@app.after_request
def after_request(response):
    """Log outgoing responses and add CORS headers"""
    # Add CORS headers
    response.headers.add('Access-Control-Allow-Origin', ', '.join(config.CORS_ORIGINS))
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    response.headers.add('Access-Control-Allow-Credentials', 'true')
    
    # Log response
    logger.info(f"Response: {response.status_code} - {request.path}")
    
    return response

@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found', 'path': request.path}), 404

@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    logger.error(f"Internal server error: {error}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def rate_limit_error(error):
    """Handle rate limit errors"""
    return jsonify({'error': 'Rate limit exceeded', 'retry_after': 60}), 429

# Global exception handler
@app.errorhandler(Exception)
def handle_exception(error):
    """Handle all uncaught exceptions"""
    logger.error(f"Unhandled exception: {error}", exc_info=True)
    return jsonify({'error': 'Internal server error', 'message': str(error)}), 500

def cleanup_on_shutdown():
    """Cleanup temporary files on shutdown"""
    logger.info("Cleaning up temporary files...")
    cleanup_temp_files(config.TEMP_DIR)

# Register cleanup on shutdown
import atexit
atexit.register(cleanup_on_shutdown)

if __name__ == '__main__':
    """Run the Flask application"""
    # Log startup information
    logger.info(f"Starting {config.APP_NAME} v{config.APP_VERSION}")
    logger.info(f"Environment: {'Development' if config.DEBUG else 'Production'}")
    logger.info(f"Host: {config.HOST}, Port: {config.PORT}")
    logger.info(f"Available models: {list(config.get_available_models().keys())}")
    logger.info(f"Features enabled: {[k for k, v in config.FEATURES.items() if v]}")
    
    # Run the app
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
)
