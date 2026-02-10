"""
Rate Limiter Middleware
Handles API rate limiting
"""

from functools import wraps
from flask import request, jsonify
import time
from collections import defaultdict
from backend.config import config


class RateLimiter:
    """Simple in-memory rate limiter"""
    
    def __init__(self):
        self.requests = defaultdict(list)
        self.max_requests = config.RATE_LIMIT_REQUESTS
        self.window = config.RATE_LIMIT_WINDOW
    
    def is_allowed(self, identifier: str) -> tuple[bool, int]:
        """Check if request is allowed"""
        now = time.time()
        
        # Clean old requests
        self.requests[identifier] = [
            req_time for req_time in self.requests[identifier]
            if now - req_time < self.window
        ]
        
        # Check limit
        if len(self.requests[identifier]) >= self.max_requests:
            oldest_request = min(self.requests[identifier])
            retry_after = int(self.window - (now - oldest_request))
            return False, retry_after
        
        # Add current request
        self.requests[identifier].append(now)
        return True, 0
    
    def get_identifier(self) -> str:
        """Get identifier for rate limiting"""
        # Use IP address as identifier
        return request.remote_addr or 'unknown'
    
    def cleanup(self):
        """Clean up old entries"""
        now = time.time()
        keys_to_remove = []
        
        for identifier, timestamps in self.requests.items():
            # Remove old timestamps
            self.requests[identifier] = [
                t for t in timestamps if now - t < self.window
            ]
            
            # Mark for removal if empty
            if not self.requests[identifier]:
                keys_to_remove.append(identifier)
        
        for key in keys_to_remove:
            del self.requests[key]


# Global rate limiter
rate_limiter = RateLimiter()


def rate_limit(f):
    """Rate limiting decorator"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        identifier = rate_limiter.get_identifier()
        allowed, retry_after = rate_limiter.is_allowed(identifier)
        
        if not allowed:
            return jsonify({
                'success': False,
                'error': 'Rate limit exceeded',
                'retry_after': retry_after,
                'message': f'Please wait {retry_after} seconds before trying again'
            }), 429
        
        return f(*args, **kwargs)
    
    return decorated_function
