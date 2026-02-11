"""
Google Gemini Handler
Handles Google Gemini API calls
"""

from typing import Dict, Optional
from backend.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

try:
    import google.generativeai as genai
    GEMINI_AVAILABLE = True
except ImportError:
    GEMINI_AVAILABLE = False
    logger.warning("⚠️ google-generativeai not installed")


class GeminiHandler:
    """Handle Google Gemini API requests"""
    
    def __init__(self):
        self.api_key = config.GEMINI_API_KEY
        self.available = GEMINI_AVAILABLE and bool(self.api_key)
        
        if self.available:
            self._initialize()
    
    def _initialize(self):
        """Initialize Gemini"""
        try:
            genai.configure(api_key=self.api_key)
            logger.info("✅ Gemini initialized")
        except Exception as e:
            logger.error(f"❌ Gemini init failed: {e}")
            self.available = False
    
    def generate_response(self, model_id: str, prompt: str, 
                         transcript_context: str) -> Dict:
        """Generate response from Gemini"""
        
        if not self.available:
            return {
                'success': False,
                'error': 'Gemini not available'
            }
        
        try:
            model = genai.GenerativeModel(model_id)
            
            full_prompt = f"""VIDEO TRANSCRIPT:
{transcript_context}

USER REQUEST:
{prompt}

Please respond according to the user's request using the transcript above."""
            
            logger.info(f"🤖 Calling Gemini: {model_id}")
            
            response = model.generate_content(
                full_prompt,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 8192,
                }
            )
            
            return {
                'success': True,
                'text': response.text,
                'model': model_id,
                'provider': 'google'
            }
            
        except Exception as e:
            logger.error(f"❌ Gemini error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': model_id,
                'provider': 'google'
            }


# Global instance
gemini_handler = GeminiHandler()
