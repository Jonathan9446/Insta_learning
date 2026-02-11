"""
OpenRouter Handler
Handles OpenRouter API calls for multiple models
"""

import requests
from typing import Dict
from backend.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class OpenRouterHandler:
    """Handle OpenRouter API requests"""
    
    def __init__(self):
        self.api_key = config.OPENROUTER_API_KEY
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.available = bool(self.api_key)
    
    def generate_response(self, model_id: str, prompt: str,
                         transcript_context: str) -> Dict:
        """Generate response from OpenRouter"""
        
        if not self.available:
            return {
                'success': False,
                'error': 'OpenRouter API key not configured'
            }
        
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://ai-video-platform.com",
                "X-Title": "AI Video Learning Platform"
            }
            
            messages = [
                {
                    "role": "system",
                    "content": "You are a helpful AI assistant analyzing video transcripts. Respond to user requests based on the provided transcript."
                },
                {
                    "role": "user",
                    "content": f"""VIDEO TRANSCRIPT:
{transcript_context}

USER REQUEST:
{prompt}

Please respond according to the user's request."""
                }
            ]
            
            payload = {
                "model": model_id,
                "messages": messages,
                "max_tokens": 4096,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            logger.info(f"🤖 Calling OpenRouter: {model_id}")
            
            response = requests.post(
                self.base_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            if response.status_code == 200:
                data = response.json()
                
                return {
                    'success': True,
                    'text': data['choices'][0]['message']['content'],
                    'model': model_id,
                    'provider': 'openrouter',
                    'usage': data.get('usage', {})
                }
            else:
                error_msg = f"API Error {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    pass
                
                return {
                    'success': False,
                    'error': error_msg,
                    'model': model_id,
                    'provider': 'openrouter'
                }
        
        except Exception as e:
            logger.error(f"❌ OpenRouter error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': model_id,
                'provider': 'openrouter'
            }


# Global instance
openrouter_handler = OpenRouterHandler()
