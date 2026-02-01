"""
AI Orchestrator Module
Manages multiple AI models: Google Gemini + OpenRouter models
"""

import os
import json
import time
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from enum import Enum

import requests
from dataclasses import dataclass

from config import config
from utils.helpers import truncate_text, extract_keywords, format_timestamp
from utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

class AIProvider(Enum):
    """AI Providers Enum"""
    GOOGLE_GEMINI = "google_gemini"
    OPENROUTER = "openrouter"
    OPENAI = "openai"
    GROQ = "groq"

@dataclass
class AIModelConfig:
    """AI Model Configuration"""
    id: str
    name: str
    provider: AIProvider
    context_length: int
    max_tokens: int
    supports_timestamps: bool
    supports_multimodal: bool
    speed: str  # fast, medium, slow
    cost: str   # free, low, medium, high
    description: str
    enabled: bool = True

class AIOrchestrator:
    """Orchestrates multiple AI models for video analysis"""
    
    def __init__(self):
        self.config = config
        self.available_models = self._load_models()
        self.response_cache = {}
        self.cache_max_size = 100
        self.cache_ttl = 300  # 5 minutes
        
        # Initialize providers
        self.providers = {
            AIProvider.GOOGLE_GEMINI: self._init_gemini(),
            AIProvider.OPENROUTER: self._init_openrouter()
        }
    
    def _load_models(self) -> Dict[str, AIModelConfig]:
        """Load and configure available AI models"""
        models = {}
        
        # Google Gemini Models
        if self.config.GEMINI_API_KEY:
            models.update({
                'gemini-2.0-flash': AIModelConfig(
                    id='gemini-2.0-flash',
                    name='Gemini 2.0 Flash',
                    provider=AIProvider.GOOGLE_GEMINI,
                    context_length=1000000,
                    max_tokens=8192,
                    supports_timestamps=True,
                    supports_multimodal=True,
                    speed='fast',
                    cost='free',
                    description='Fast and efficient for most tasks'
                ),
                'gemini-2.0-pro': AIModelConfig(
                    id='gemini-2.0-pro',
                    name='Gemini 2.0 Pro',
                    provider=AIProvider.GOOGLE_GEMINI,
                    context_length=2000000,
                    max_tokens=8192,
                    supports_timestamps=True,
                    supports_multimodal=True,
                    speed='medium',
                    cost='free',
                    description='Advanced reasoning for complex tasks'
                )
            })
        
        # OpenRouter Models
        if self.config.OPENROUTER_API_KEY:
            models.update({
                'openai/gpt-3.5-turbo': AIModelConfig(
                    id='openai/gpt-3.5-turbo',
                    name='ChatGPT 3.5 Turbo',
                    provider=AIProvider.OPENROUTER,
                    context_length=16384,
                    max_tokens=4096,
                    supports_timestamps=True,
                    supports_multimodal=False,
                    speed='fast',
                    cost='free_tier',
                    description='OpenAI\'s fast and capable model'
                ),
                'anthropic/claude-3-haiku': AIModelConfig(
                    id='anthropic/claude-3-haiku',
                    name='Claude 3 Haiku',
                    provider=AIProvider.OPENROUTER,
                    context_length=200000,
                    max_tokens=4096,
                    supports_timestamps=True,
                    supports_multimodal=False,
                    speed='very_fast',
                    cost='free_tier',
                    description='Anthropic\'s fastest and most affordable model'
                ),
                'mistralai/mistral-small': AIModelConfig(
                    id='mistralai/mistral-small',
                    name='Mistral Small',
                    provider=AIProvider.OPENROUTER,
                    context_length=32000,
                    max_tokens=8192,
                    supports_timestamps=True,
                    supports_multimodal=False,
                    speed='fast',
                    cost='free_tier',
                    description='Efficient and capable small model'
                ),
                'google/gemma-2-2b-it': AIModelConfig(
                    id='google/gemma-2-2b-it',
                    name='Gemma 2 (2B)',
                    provider=AIProvider.OPENROUTER,
                    context_length=8000,
                    max_tokens=4096,
                    supports_timestamps=False,
                    supports_multimodal=False,
                    speed='very_fast',
                    cost='free',
                    description='Lightweight model for quick responses'
                ),
                'qwen/qwen-2.5-7b-instruct': AIModelConfig(
                    id='qwen/qwen-2.5-7b-instruct',
                    name='Qwen 2.5 (7B)',
                    provider=AIProvider.OPENROUTER,
                    context_length=32000,
                    max_tokens=8192,
                    supports_timestamps=True,
                    supports_multimodal=False,
                    speed='medium',
                    cost='free_tier',
                    description='Strong multilingual capabilities'
                )
            })
        
        # Filter enabled models
        enabled_models = {k: v for k, v in models.items() if v.enabled}
        
        logger.info(f"Loaded {len(enabled_models)} AI models")
        return enabled_models
    
    def _init_gemini(self) -> bool:
        """Initialize Google Gemini"""
        try:
            if not self.config.GEMINI_API_KEY:
                return False
            
            import google.generativeai as genai
            genai.configure(api_key=self.config.GEMINI_API_KEY)
            
            # Test connection
            models = genai.list_models()
            gemini_models = [model.name for model in models if 'gemini' in model.name]
            
            logger.info(f"Gemini initialized successfully. Available models: {gemini_models}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize Gemini: {e}")
            return False
    
    def _init_openrouter(self) -> bool:
        """Initialize OpenRouter"""
        if not self.config.OPENROUTER_API_KEY:
            return False
        
        # Test connection
        try:
            headers = {
                "Authorization": f"Bearer {self.config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            }
            
            response = requests.get(
                "https://openrouter.ai/api/v1/models",
                headers=headers,
                timeout=10
            )
            
            if response.status_code == 200:
                models = response.json().get('data', [])
                logger.info(f"OpenRouter initialized successfully. {len(models)} models available")
                return True
            else:
                logger.warning(f"OpenRouter test failed: {response.status_code}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to initialize OpenRouter: {e}")
            return False
    
    def get_available_models(self) -> List[Dict]:
        """Get list of available AI models"""
        models_list = []
        
        for model_id, model_config in self.available_models.items():
            models_list.append({
                'id': model_id,
                'name': model_config.name,
                'provider': model_config.provider.value,
                'context_length': model_config.context_length,
                'max_tokens': model_config.max_tokens,
                'supports_timestamps': model_config.supports_timestamps,
                'speed': model_config.speed,
                'cost': model_config.cost,
                'description': model_config.description
            })
        
        return models_list
    
    def get_model_capabilities(self, model_id: str) -> Optional[Dict]:
        """Get capabilities of a specific model"""
        if model_id not in self.available_models:
            return None
        
        model_config = self.available_models[model_id]
        
        return {
            'id': model_id,
            'name': model_config.name,
            'provider': model_config.provider.value,
            'context_length': model_config.context_length,
            'max_tokens': model_config.max_tokens,
            'supports_timestamps': model_config.supports_timestamps,
            'supports_multimodal': model_config.supports_multimodal,
            'speed': model_config.speed,
            'cost': model_config.cost,
            'description': model_config.description
        }
    
    def process_query(self, transcript_data: Dict, user_query: str,
                     model_id: str, session_id: str = None,
                     enable_sync: bool = True) -> Dict:
        """
        Process user query with selected AI model
        
        Args:
            transcript_data: Video transcript data
            user_query: User's question/command
            model_id: AI model to use
            session_id: User session ID
            enable_sync: Whether to enable video-AI sync
            
        Returns:
            AI response dictionary
        """
        # Check cache first
        cache_key = self._generate_cache_key(session_id, model_id, user_query)
        cached_response = self._get_cached_response(cache_key)
        
        if cached_response:
            logger.info(f"Using cached response for: {user_query[:30]}...")
            cached_response['cached'] = True
            return cached_response
        
        # Validate model
        if model_id not in self.available_models:
            logger.error(f"Model not available: {model_id}")
            return {
                'success': False,
                'error': f"Model {model_id} is not available",
                'model_id': model_id
            }
        
        model_config = self.available_models[model_id]
        
        try:
            # Prepare context
            context = self._prepare_context(transcript_data, user_query, 
                                          model_config.context_length)
            
            # Build prompt
            prompt = self._build_prompt(context, user_query, model_config, enable_sync)
            
            # Process with appropriate provider
            start_time = time.time()
            
            if model_config.provider == AIProvider.GOOGLE_GEMINI:
                response = self._call_gemini(prompt, model_id)
            elif model_config.provider == AIProvider.OPENROUTER:
                response = self._call_openrouter(prompt, model_id)
            else:
                response = {
                    'success': False,
                    'error': f"Provider {model_config.provider} not implemented"
                }
            
            processing_time = time.time() - start_time
            
            # Add metadata
            if response.get('success', False):
                response['metadata'] = {
                    'model_used': model_id,
                    'model_name': model_config.name,
                    'provider': model_config.provider.value,
                    'query_type': self._classify_query(user_query),
                    'processing_time': processing_time,
                    'timestamp': datetime.now().isoformat(),
                    'sync_enabled': enable_sync,
                    'session_id': session_id,
                    'cached': False
                }
                
                # Add sync markers if enabled
                if enable_sync and 'text' in response:
                    response['text'] = self._add_sync_markers(
                        response['text'], 
                        transcript_data
                    )
                
                # Cache the response
                self._cache_response(cache_key, response)
            
            return response
            
        except Exception as e:
            logger.error(f"Error processing query: {e}")
            return {
                'success': False,
                'error': str(e),
                'model_id': model_id,
                'timestamp': datetime.now().isoformat()
            }
    
    def _prepare_context(self, transcript_data: Dict, user_query: str, 
                        max_context_length: int) -> str:
        """Prepare transcript context for AI prompt"""
        if not transcript_data or 'sentences' not in transcript_data:
            return "No transcript available."
        
        sentences = transcript_data['sentences']
        
        # Calculate available context (reserve space for prompt and response)
        available_chars = max_context_length * 4  # Approximate characters per token
        reserved_chars = 2000  # For prompt and response
        
        max_transcript_chars = available_chars - reserved_chars - len(user_query)
        
        # Build context with timestamps
        context_parts = []
        current_length = 0
        
        for sentence in sentences:
            text = sentence.get('text', '').strip()
            start = sentence.get('start', 0)
            
            if not text:
                continue
            
            # Format: [00:05:20] Sentence text
            time_str = format_timestamp(start)
            formatted_sentence = f"[{time_str}] {text}"
            
            # Check if adding this would exceed limit
            if current_length + len(formatted_sentence) > max_transcript_chars:
                # Add continuation marker
                context_parts.append("... [transcript truncated]")
                break
            
            context_parts.append(formatted_sentence)
            current_length += len(formatted_sentence)
        
        return '\n'.join(context_parts)
    
    def _build_prompt(self, context: str, user_query: str, 
                     model_config: AIModelConfig, enable_sync: bool) -> str:
        """Build AI prompt based on query type and model capabilities"""
        query_type = self._classify_query(user_query)
        
        # Base system prompt
        system_prompt = """You are an AI assistant helping users understand video content.
Your task is to analyze the video transcript and respond to user queries accurately and helpfully."""
        
        # Add specialized instructions based on query type
        query_instructions = {
            'summary': "Provide a comprehensive summary with main points and timestamps.",
            'word_analysis': "Break down difficult words with pronunciation (Hindi/English) and meanings.",
            'quiz': "Create a quiz with 5-10 multiple choice questions based on video content.",
            'translation': "Provide translation while maintaining context and meaning.",
            'explanation': "Explain concepts in simple terms with examples.",
            'general': "Answer the query based on the transcript content."
        }
        
        instruction = query_instructions.get(query_type, query_instructions['general'])
        
        # Add sync instructions if enabled and model supports it
        sync_instruction = ""
        if enable_sync and model_config.supports_timestamps:
            sync_instruction = "\n\nINCLUDE TIMESTAMPS: When referring to specific parts of the video, include timestamps in format [HH:MM:SS] so they can be synced with video playback."
        
        # Build final prompt
        prompt = f"""{system_prompt}

VIDEO TRANSCRIPT:
{context}

USER QUERY: {user_query}

SPECIAL INSTRUCTIONS FOR THIS TASK ({query_type.upper()}):
{instruction}{sync_instruction}

RESPONSE FORMAT:
- Be clear and concise
- Use bullet points or numbered lists when appropriate
- Reference specific parts of the transcript when possible
- If the query is about words or phrases, provide detailed analysis

RESPONSE:"""
        
        return prompt
    
    def _call_gemini(self, prompt: str, model_id: str) -> Dict:
        """Call Google Gemini API"""
        try:
            import google.generativeai as genai
            
            # Initialize model
            model = genai.GenerativeModel(model_id)
            
            # Generate content
            response = model.generate_content(
                prompt,
                generation_config={
                    'temperature': 0.7,
                    'top_p': 0.8,
                    'top_k': 40,
                    'max_output_tokens': 2048,
                }
            )
            
            return {
                'success': True,
                'text': response.text,
                'model': model_id,
                'provider': 'google_gemini'
            }
            
        except Exception as e:
            logger.error(f"Gemini API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': model_id,
                'provider': 'google_gemini'
            }
    
    def _call_openrouter(self, prompt: str, model_id: str) -> Dict:
        """Call OpenRouter API"""
        try:
            headers = {
                "Authorization": f"Bearer {self.config.OPENROUTER_API_KEY}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://video-ai-platform.com",
                "X-Title": "AI Video Platform"
            }
            
            payload = {
                "model": model_id,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 2048,
                "temperature": 0.7,
                "top_p": 0.9
            }
            
            response = requests.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                
                return {
                    'success': True,
                    'text': result['choices'][0]['message']['content'],
                    'model': model_id,
                    'provider': 'openrouter',
                    'usage': result.get('usage', {})
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
            logger.error(f"OpenRouter API error: {e}")
            return {
                'success': False,
                'error': str(e),
                'model': model_id,
                'provider': 'openrouter'
            }
    
    def _classify_query(self, query: str) -> str:
        """Classify the type of user query"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['summary', 'summarize', 'overview', 'brief']):
            return 'summary'
        elif any(word in query_lower for word in ['word', 'vocabulary', 'pronunciation', 'meaning']):
            return 'word_analysis'
        elif any(word in query_lower for word in ['quiz', 'question', 'test', 'exam']):
            return 'quiz'
        elif any(word in query_lower for word in ['translate', 'hindi', 'english', 'language']):
            return 'translation'
        elif any(word in query_lower for word in ['explain', 'what is', 'how to', 'why']):
            return 'explanation'
        else:
            return 'general'
    
    def _add_sync_markers(self, response_text: str, transcript_data: Dict) -> str:
        """Add synchronization markers to AI response"""
        # This is a simplified implementation
        # In a real app, you'd do more sophisticated timestamp extraction
        
        import re
        
        # Pattern for timestamps like [00:05:20] or [05:20]
        timestamp_pattern = r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]'
        
        def replace_timestamp(match):
            hours = int(match.group(1)) if match.group(3) is not None else 0
            minutes = int(match.group(2))
            seconds = int(match.group(3)) if match.group(3) is not None else 0
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            # Return clickable timestamp
            original_text = match.group(0)
            return f'<span class="timestamp" data-time="{total_seconds}">{original_text}</span>'
        
        # Replace timestamps with clickable versions
        response_text = re.sub(timestamp_pattern, replace_timestamp, response_text)
        
        return response_text
    
    def _generate_cache_key(self, session_id: str, model_id: str, query: str) -> str:
        """Generate cache key for response"""
        import hashlib
        
        key_string = f"{session_id or 'no_session'}:{model_id}:{query}"
        return hashlib.md5(key_string.encode()).hexdigest()
    
    def _get_cached_response(self, cache_key: str) -> Optional[Dict]:
        """Get cached response if available and not expired"""
        if cache_key in self.response_cache:
            cached_data = self.response_cache[cache_key]
            
            # Check if cache is still valid
            cache_time = cached_data.get('cache_time', 0)
            if time.time() - cache_time < self.cache_ttl:
                return cached_data['response']
            else:
                # Remove expired cache
                del self.response_cache[cache_key]
        
        return None
    
    def _cache_response(self, cache_key: str, response: Dict):
        """Cache AI response"""
        # Limit cache size
        if len(self.response_cache) >= self.cache_max_size:
            # Remove oldest entry
            oldest_key = min(self.response_cache.keys(), 
                           key=lambda k: self.response_cache[k]['cache_time'])
            del self.response_cache[oldest_key]
        
        # Add to cache
        self.response_cache[cache_key] = {
            'response': response,
            'cache_time': time.time()
        }
    
    def batch_process(self, queries: List[Dict], session_id: str = None) -> List[Dict]:
        """Process multiple queries in batch"""
        results = []
        
        for query_data in queries:
            transcript = query_data.get('transcript')
            query = query_data.get('query')
            model_id = query_data.get('model_id', 'gemini-2.0-flash')
            
            if transcript and query:
                result = self.process_query(transcript, query, model_id, session_id)
                results.append({
                    'query': query,
                    'model': model_id,
                    'result': result
                })
        
        return results
    
    def compare_models(self, transcript_data: Dict, user_query: str, 
                      model_ids: List[str]) -> Dict:
        """Compare responses from multiple models"""
        comparisons = {}
        
        for model_id in model_ids:
            if model_id in self.available_models:
                result = self.process_query(transcript_data, user_query, model_id)
                comparisons[model_id] = {
                    'success': result.get('success', False),
                    'response': result.get('text', '') if result.get('success') else result.get('error', ''),
                    'processing_time': result.get('metadata', {}).get('processing_time', 0),
                    'model_name': self.available_models[model_id].name
                }
        
        return comparisons
    
    def get_recommendations(self, query_type: str) -> List[str]:
        """Get recommended models for a query type"""
        recommendations = {
            'summary': ['gemini-2.0-flash', 'gemini-2.0-pro'],
            'word_analysis': ['gemini-2.0-flash', 'openai/gpt-3.5-turbo'],
            'quiz': ['gemini-2.0-pro', 'anthropic/claude-3-haiku'],
            'translation': ['gemini-2.0-flash', 'qwen/qwen-2.5-7b-instruct'],
            'explanation': ['gemini-2.0-pro', 'openai/gpt-3.5-turbo'],
            'general': ['gemini-2.0-flash', 'openai/gpt-3.5-turbo']
        }
        
        return recommendations.get(query_type, ['gemini-2.0-flash'])
    
    def health_check(self) -> Dict:
        """Check health of AI providers"""
        health = {
            'timestamp': datetime.now().isoformat(),
            'available_models': len(self.available_models),
            'cache_size': len(self.response_cache),
            'providers': {}
        }
        
        # Check Gemini
        health['providers']['google_gemini'] = {
            'available': bool(self.config.GEMINI_API_KEY),
            'initialized': self.providers.get(AIProvider.GOOGLE_GEMINI, False),
            'models': [m for m in self.available_models.values() 
                      if m.provider == AIProvider.GOOGLE_GEMINI]
        }
        
        # Check OpenRouter
        health['providers']['openrouter'] = {
            'available': bool(self.config.OPENROUTER_API_KEY),
            'initialized': self.providers.get(AIProvider.OPENROUTER, False),
            'models': [m for m in self.available_models.values() 
                      if m.provider == AIProvider.OPENROUTER]
        }
        
        return health


# Singleton instance for easy access
ai_orchestrator = AIOrchestrator()  
