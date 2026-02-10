"""
Routes Module
API endpoint blueprints
"""

from .video_routes import video_bp
from .ai_routes import ai_bp
from .chat_routes import chat_bp
from .health_routes import health_bp

__all__ = [
    'video_bp',
    'ai_bp',
    'chat_bp',
    'health_bp'
]
