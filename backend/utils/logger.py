"""
Logging Configuration Module
Sets up logging for the application
"""

import os
import logging
import sys
from logging.handlers import RotatingFileHandler
from datetime import datetime

from config import config

def setup_logger(name: str, log_level: str = "INFO", log_file: str = None) -> logging.Logger:
    """
    Setup and configure a logger
    
    Args:
        name: Logger name
        log_level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        log_file: Path to log file (optional)
        
    Returns:
        Configured logger instance
    """
    # Create logger
    logger = logging.getLogger(name)
    
    # Remove existing handlers
    logger.handlers.clear()
    
    # Set log level
    level = getattr(logging, log_level.upper(), logging.INFO)
    logger.setLevel(level)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler (if log file specified)
    if log_file:
        # Create log directory if it doesn't exist
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
        
        # Create rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10 MB
            backupCount=5
        )
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    # Don't propagate to root logger
    logger.propagate = False
    
    return logger

def get_request_logger():
    """Get logger for request logging"""
    return setup_logger('request', config.LOG_LEVEL, config.LOG_FILE)

def get_app_logger():
    """Get logger for application logging"""
    return setup_logger('app', config.LOG_LEVEL, config.LOG_FILE)

def get_error_logger():
    """Get logger for error logging"""
    return setup_logger('error', config.LOG_LEVEL, config.LOG_FILE)

def get_database_logger():
    """Get logger for database operations"""
    return setup_logger('database', config.LOG_LEVEL, config.LOG_FILE)

def get_ai_logger():
    """Get logger for AI operations"""
    return setup_logger('ai', config.LOG_LEVEL, config.LOG_FILE)

def get_video_logger():
    """Get logger for video processing"""
    return setup_logger('video', config.LOG_LEVEL, config.LOG_FILE)

class RequestLogger:
    """Logger for HTTP requests"""
    
    def __init__(self):
        self.logger = get_request_logger()
    
    def log_request(self, method: str, path: str, status: int, 
                   duration: float, ip: str = None):
        """Log HTTP request"""
        ip_info = f" - {ip}" if ip else ""
        self.logger.info(
            f"{method} {path} - {status} - {duration:.3f}s{ip_info}"
        )
    
    def log_error(self, method: str, path: str, error: str, 
                 status: int = 500, ip: str = None):
        """Log HTTP error"""
        ip_info = f" - {ip}" if ip else ""
        self.logger.error(
            f"{method} {path} - {status} - {error}{ip_info}"
        )

class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self):
        self.logger = get_app_logger()
    
    def log_performance(self, operation: str, duration: float, 
                       details: Dict = None):
        """Log performance metric"""
        details_str = f" - {details}" if details else ""
        self.logger.info(
            f"Performance: {operation} - {duration:.3f}s{details_str}"
        )
    
    def log_slow_operation(self, operation: str, duration: float, 
                          threshold: float = 5.0):
        """Log slow operations"""
        if duration > threshold:
            self.logger.warning(
                f"Slow operation: {operation} - {duration:.3f}s (threshold: {threshold}s)"
            )

# Create global logger instances
request_logger = RequestLogger()
performance_logger = PerformanceLogger()

# Default logger for general use
default_logger = get_app_logger()

def log_exception(exc: Exception, context: str = ""):
    """Log exception with context"""
    error_logger = get_error_logger()
    context_info = f" in {context}" if context else ""
    error_logger.error(f"Exception{context_info}: {exc}", exc_info=True)

def log_debug(message: str, **kwargs):
    """Log debug message"""
    default_logger.debug(message, **kwargs)

def log_info(message: str, **kwargs):
    """Log info message"""
    default_logger.info(message, **kwargs)

def log_warning(message: str, **kwargs):
    """Log warning message"""
    default_logger.warning(message, **kwargs)

def log_error(message: str, **kwargs):
    """Log error message"""
    default_logger.error(message, **kwargs)

def log_critical(message: str, **kwargs):
    """Log critical message"""
    default_logger.critical(message, **kwargs)

# Context manager for timing operations
class TimedOperation:
    """Context manager for timing operations"""
    
    def __init__(self, operation_name: str):
        self.operation_name = operation_name
        self.start_time = None
    
    def __enter__(self):
        self.start_time = datetime.now()
        log_info(f"Starting operation: {self.operation_name}")
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (datetime.now() - self.start_time).total_seconds()
        
        if exc_type:
            log_error(f"Operation failed: {self.operation_name} - {duration:.3f}s - {exc_val}")
        else:
            log_info(f"Completed operation: {self.operation_name} - {duration:.3f}s")
            performance_logger.log_performance(self.operation_name, duration)
        
        # Don't suppress exceptions
        return False

# Decorator for timing functions
def timed_operation(operation_name: str = None):
    """Decorator for timing functions"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            name = operation_name or func.__name__
            
            with TimedOperation(name):
                return func(*args, **kwargs)
        
        return wrapper
    return decorator

# Logging middleware for Flask (to be used in app.py)
class LoggingMiddleware:
    """Middleware for logging Flask requests"""
    
    def __init__(self, app):
        self.app = app
        self.logger = get_request_logger()
    
    def __call__(self, environ, start_response):
        start_time = datetime.now()
        
        def custom_start_response(status, headers, *args):
            # Log after response
            duration = (datetime.now() - start_time).total_seconds()
            method = environ.get('REQUEST_METHOD')
            path = environ.get('PATH_INFO')
            ip = environ.get('REMOTE_ADDR')
            
            status_code = int(status.split()[0])
            
            if status_code >= 400:
                self.logger.error(f"{method} {path} - {status_code} - {duration:.3f}s - {ip}")
            else:
                self.logger.info(f"{method} {path} - {status_code} - {duration:.3f}s - {ip}")
            
            return start_response(status, headers, *args)
        
        return self.app(environ, custom_start_response)
