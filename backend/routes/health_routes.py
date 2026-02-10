"""
Health Check Routes
System health and status endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime
import psutil
import os

from backend.config import config
from backend.database.firebase_manager import db_manager
from backend.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

health_bp = Blueprint('health', __name__)


@health_bp.route('', methods=['GET'])
@health_bp.route('/', methods=['GET'])
def health_check():
    """Basic health check"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'app_name': config.APP_NAME,
        'version': config.APP_VERSION,
        'timestamp': datetime.now().isoformat()
    })


@health_bp.route('/detailed', methods=['GET'])
def detailed_health():
    """Detailed health check with system info"""
    try:
        # System metrics
        cpu_percent = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory()
        disk = psutil.disk_usage('/')
        
        # Database stats
        db_stats = db_manager.get_stats()
        
        # Check temp directory
        temp_exists = os.path.exists(config.TEMP_DIR)
        temp_writable = os.access(config.TEMP_DIR, os.W_OK) if temp_exists else False
        
        health_data = {
            'success': True,
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'system': {
                'cpu_percent': cpu_percent,
                'memory_percent': memory.percent,
                'memory_available_mb': memory.available / (1024 * 1024),
                'disk_percent': disk.percent,
                'disk_free_gb': disk.free / (1024 * 1024 * 1024)
            },
            'database': db_stats,
            'storage': {
                'temp_dir': config.TEMP_DIR,
                'temp_exists': temp_exists,
                'temp_writable': temp_writable
            },
            'services': {
                'gemini': bool(config.GEMINI_API_KEY),
                'openrouter': bool(config.OPENROUTER_API_KEY),
                'groq': bool(config.GROQ_API_KEY),
                'firebase': db_manager.storage_type == 'firebase'
            },
            'features': config.FEATURES
        }
        
        return jsonify(health_data)
        
    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'success': False,
            'status': 'unhealthy',
            'error': str(e)
        }), 500


@health_bp.route('/services', methods=['GET'])
def services_status():
    """Check status of all services"""
    services = {
        'ai_providers': {
            'gemini': {
                'available': bool(config.GEMINI_API_KEY),
                'status': 'active' if config.GEMINI_API_KEY else 'disabled'
            },
            'openrouter': {
                'available': bool(config.OPENROUTER_API_KEY),
                'status': 'active' if config.OPENROUTER_API_KEY else 'disabled'
            },
            'groq': {
                'available': bool(config.GROQ_API_KEY),
                'status': 'active' if config.GROQ_API_KEY else 'disabled'
            }
        },
        'video_platforms': {
            'youtube': {
                'available': True,
                'method': 'Piped API',
                'instances': len(config.PIPED_INSTANCES)
            },
            'facebook': {
                'available': bool(config.FACEBOOK_APP_ID),
                'status': 'active' if config.FACEBOOK_APP_ID else 'disabled'
            }
        },
        'database': {
            'type': db_manager.storage_type,
            'status': 'active'
        }
    }
    
    return jsonify({
        'success': True,
        'services': services,
        'timestamp': datetime.now().isoformat()
    })


@health_bp.route('/config', methods=['GET'])
def get_config():
    """Get public configuration"""
    public_config = {
        'app_name': config.APP_NAME,
        'version': config.APP_VERSION,
        'features': config.FEATURES,
        'limits': {
            'max_video_duration': config.MAX_VIDEO_DURATION,
            'max_chunk_duration': config.MAX_CHUNK_DURATION,
            'rate_limit': {
                'requests': config.RATE_LIMIT_REQUESTS,
                'window': config.RATE_LIMIT_WINDOW
            }
        }
    }
    
    return jsonify({
        'success': True,
        'config': public_config
    })
