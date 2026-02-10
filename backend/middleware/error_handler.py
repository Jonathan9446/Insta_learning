"""
Error Handler Middleware
Global error handling
"""

from flask import jsonify, request
from werkzeug.exceptions import HTTPException
import traceback
from backend.utils.logger import setup_logger
from backend.config import config

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class ErrorHandler:
    """Centralized error handling"""
    
    @staticmethod
    def handle_http_error(error):
        """Handle HTTP errors"""
        response = {
            'success': False,
            'error': error.description,
            'status_code': error.code
        }
        
        logger.warning(f"HTTP Error {error.code}: {error.description} - {request.path}")
        
        return jsonify(response), error.code
    
    @staticmethod
    def handle_generic_error(error):
        """Handle generic exceptions"""
        logger.error(f"Unhandled error: {str(error)}")
        logger.error(traceback.format_exc())
        
        response = {
            'success': False,
            'error': 'Internal server error',
            'message': str(error) if config.DEBUG else 'An error occurred'
        }
        
        return jsonify(response), 500
    
    @staticmethod
    def handle_404(error):
        """Handle 404 errors"""
        return jsonify({
            'success': False,
            'error': 'Not found',
            'path': request.path
        }), 404
    
    @staticmethod
    def handle_405(error):
        """Handle method not allowed"""
        return jsonify({
            'success': False,
            'error': 'Method not allowed',
            'method': request.method,
            'path': request.path
        }), 405
    
    @staticmethod
    def handle_400(error):
        """Handle bad request"""
        return jsonify({
            'success': False,
            'error': 'Bad request',
            'message': str(error.description) if hasattr(error, 'description') else 'Invalid request'
        }), 400
    
    @staticmethod
    def handle_500(error):
        """Handle internal server error"""
        logger.error(f"Internal server error: {str(error)}")
        logger.error(traceback.format_exc())
        
        return jsonify({
            'success': False,
            'error': 'Internal server error',
            'message': 'Something went wrong on our end'
        }), 500


def register_error_handlers(app):
    """Register all error handlers with Flask app"""
    
    error_handler = ErrorHandler()
    
    # HTTP errors
    app.register_error_handler(400, error_handler.handle_400)
    app.register_error_handler(404, error_handler.handle_404)
    app.register_error_handler(405, error_handler.handle_405)
    app.register_error_handler(500, error_handler.handle_500)
    
    # Generic HTTP exceptions
    app.register_error_handler(HTTPException, error_handler.handle_http_error)
    
    # All other exceptions
    app.register_error_handler(Exception, error_handler.handle_generic_error)
    
    logger.info("✅ Error handlers registered")


# Global instance
error_handler = ErrorHandler()
