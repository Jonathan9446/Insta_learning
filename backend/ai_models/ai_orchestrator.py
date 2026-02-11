"""
AI Orchestrator
Unified interface for all AI models
"""

from typing import Dict, List, Optional
from backend.config import config
from backend.utils.logger import setup_logger
from backend.utils.sync_manager import sync_manager
from backend.ai_models.gemini_handler import gemini_handler
from backend.ai_models.openrouter_handler import openrouter_handler
from backend.ai_models.model_configs import ALL_MODELS, get_model_by_id

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class AIOrchestrator:
    """Orchestrate multiple AI providers"""
    
    def __init__(self):
        self.gemini = gemini_handler
        self.openrouter = openrouter_handler
        self.available_models = self._get_available_models()
    
    def _get_available_models(self) -> Dict:
        """Get available models based on API keys"""
        available = {}
        
        # Add Gemini models if available
        if self.gemini.available:
            for model_id, model_config in ALL_MODELS.items():
                if model_config['provider'] == 'google':
                    available[model_id] = model_config
        
        # Add OpenRouter models if available
        if self.openrouter.available:
            for model_id, model_config in ALL_MODELS.items():
                if model_config['provider'] == 'openrouter':
                    available[model_id] = model_config
        
        logger.info(f"✅ {len(available)} AI models available")
        return available
    
    def get_models_list(self) -> List[Dict]:
        """Get formatted list of available models"""
        models_list = []
        
        for model_id, config in self.available_models.items():
            models_list.append({
                'id': model_id,
                'name': config['name'],
                'provider': config['provider'],
                'description': config['description'],
                'context_window': config['context_window'],
                'free': config.get('free', True),
                'recommended_for': config.get('recommended_for', [])
            })
        
        # Sort by provider then name
        models_list.sort(key=lambda x: (x['provider'], x['name']))
        
        return models_list
    
    def query(self, model_id: str, user_prompt: str, 
             transcript_data: Dict, enable_sync: bool = True) -> Dict:
        """
        Query AI model with transcript context
        
        Args:
            model_id: AI model identifier
            user_prompt: User's query/command
            transcript_data: Video transcript data
            enable_sync: Enable video-AI synchronization
        
        Returns:
            AI response dictionary
        """
        
        # Validate model
        if model_id not in self.available_models:
            return {
                'success': False,
                'error': f'Model {model_id} not available',
                'available_models': list(self.available_models.keys())
            }
        
        model_config = self.available_models[model_id]
        provider = model_config['provider']
        
        # Prepare transcript context
        transcript_text = self._format_transcript(
            transcript_data,
            model_config['context_window']
        )
        
        logger.info(f"🤖 Querying {model_config['name']}...")
        
        # Route to appropriate provider
        if provider == 'google':
            result = self.gemini.generate_response(
                model_id,
                user_prompt,
                transcript_text
            )
        elif provider == 'openrouter':
            result = self.openrouter.generate_response(
                model_id,
                user_prompt,
                transcript_text
            )
        else:
            return {
                'success': False,
                'error': f'Unknown provider: {provider}'
            }
        
        # Add sync markers if enabled and successful
        if result.get('success') and enable_sync:
            result['text'] = sync_manager.add_clickable_timestamps(result['text'])
            result['sync_enabled'] = True
        
        # Add metadata
        if result.get('success'):
            result['metadata'] = {
                'model_id': model_id,
                'model_name': model_config['name'],
                'provider': provider,
                'query_type': self._classify_query(user_prompt),
                'sync_enabled': enable_sync
            }
        
        return result
    
    def _format_transcript(self, transcript_data: Dict, max_context: int) -> str:
        """Format transcript for AI context"""
        segments = transcript_data.get('segments', [])
        
        if not segments:
            return "No transcript available."
        
        # Calculate available space (rough estimate: 4 chars per token)
        max_chars = max_context * 4
        reserved_chars = 2000  # Reserve for prompt and response
        available_chars = max_chars - reserved_chars
        
        # Build transcript with timestamps
        lines = []
        current_length = 0
        
        for segment in segments:
            text = segment.get('text', '').strip()
            start = segment.get('start', 0)
            
            if not text:
                continue
            
            # Format: [00:05:20] Text
            time_str = sync_manager.format_timestamp(start)
            line = f"[{time_str}] {text}"
            
            # Check if adding this would exceed limit
            if current_length + len(line) > available_chars:
                lines.append("... [transcript truncated]")
                break
            
            lines.append(line)
            current_length += len(line)
        
        return '\n'.join(lines)
    
    def _classify_query(self, query: str) -> str:
        """Classify query type"""
        query_lower = query.lower()
        
        if any(word in query_lower for word in ['summary', 'summarize', 'overview']):
            return 'summary'
        elif any(word in query_lower for word in ['word', 'vocabulary', 'pronunciation', 'meaning']):
            return 'word_analysis'
        elif any(word in query_lower for word in ['sentence', 'phrase', 'breakdown']):
            return 'sentence_analysis'
        elif any(word in query_lower for word in ['translate', 'hindi', 'translation']):
            return 'translation'
        elif any(word in query_lower for word in ['explain', 'what is', 'how']):
            return 'explanation'
        elif any(word in query_lower for word in ['quiz', 'question', 'test']):
            return 'quiz'
        else:
            return 'general'
    
    def compare_models(self, model_ids: List[str], user_prompt: str,
                      transcript_data: Dict) -> Dict:
        """Compare responses from multiple models"""
        
        if len(model_ids) > 5:
            model_ids = model_ids[:5]  # Limit to 5 models
        
        comparisons = {}
        
        for model_id in model_ids:
            if model_id in self.available_models:
                result = self.query(model_id, user_prompt, transcript_data, enable_sync=False)
                
                comparisons[model_id] = {
                    'model_name': self.available_models[model_id]['name'],
                    'success': result.get('success', False),
                    'response': result.get('text', '') if result.get('success') else result.get('error', ''),
                    'provider': self.available_models[model_id]['provider']
                }
        
        return {
            'success': True,
            'query': user_prompt,
            'comparisons': comparisons,
            'models_compared': len(comparisons)
        }
    
    def get_recommended_models(self, query_type: str = None) -> List[str]:
        """Get recommended models for query type"""
        
        if not query_type:
            # Default recommendations
            return ['gemini-2.0-flash-exp', 'openai/gpt-3.5-turbo']
        
        recommended = []
        
        for model_id, config in self.available_models.items():
            if query_type in config.get('recommended_for', []):
                recommended.append(model_id)
        
        # Fallback to default if no specific recommendations
        if not recommended:
            recommended = ['gemini-2.0-flash-exp']
        
        return recommended
    
    def batch_query(self, queries: List[Dict]) -> List[Dict]:
        """Process multiple queries in batch"""
        results = []
        
        for query_item in queries[:10]:  # Limit to 10
            model_id = query_item.get('model_id', 'gemini-2.0-flash-exp')
            user_prompt = query_item.get('prompt')
            transcript_data = query_item.get('transcript_data')
            
            if user_prompt and transcript_data:
                result = self.query(model_id, user_prompt, transcript_data)
                results.append({
                    'query': user_prompt,
                    'model': model_id,
                    'result': result
                })
        
        return results
    
    def health_check(self) -> Dict:
        """Check AI providers health"""
        return {
            'gemini': {
                'available': self.gemini.available,
                'models': len([m for m in self.available_models.values() 
                              if m['provider'] == 'google'])
            },
            'openrouter': {
                'available': self.openrouter.available,
                'models': len([m for m in self.available_models.values()
                              if m['provider'] == 'openrouter'])
            },
            'total_models': len(self.available_models)
        }


# Global instance
ai_orchestrator = AIOrchestrator()
