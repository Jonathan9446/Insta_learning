"""
AI Routes
Endpoints for AI model queries and interactions
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from backend.config import config
from backend.database.firebase_manager import db_manager
from backend.ai_models.ai_orchestrator import ai_orchestrator
from backend.utils.logger import setup_logger
from backend.middleware.rate_limiter import rate_limit

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

ai_bp = Blueprint('ai', __name__)


@ai_bp.route('/models', methods=['GET'])
def get_models():
    """Get list of available AI models"""
    try:
        models = ai_orchestrator.get_models_list()
        
        return jsonify({
            'success': True,
            'models': models,
            'total': len(models),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/query', methods=['POST'])
@rate_limit
def query_ai():
    """
    Query AI model with video transcript
    
    Body:
    {
        "session_id": "abc123",
        "prompt": "Summarize this video",
        "model_id": "gemini-2.0-flash-exp",
        "enable_sync": true
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        if not data or 'session_id' not in data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': 'session_id and prompt are required'
            }), 400
        
        session_id = data.get('session_id')
        user_prompt = data.get('prompt').strip()
        model_id = data.get('model_id', 'gemini-2.0-flash-exp')
        enable_sync = data.get('enable_sync', True)
        
        if not user_prompt:
            return jsonify({
                'success': False,
                'error': 'prompt cannot be empty'
            }), 400
        
        # Get session
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        if not session.get('transcript_available'):
            return jsonify({
                'success': False,
                'error': 'Transcript not available for this video'
            }), 400
        
        # Get transcript
        transcript = db_manager.get_transcript(session_id)
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'Transcript data not found'
            }), 404
        
        # Check cache
        cached_response = db_manager.get_cached_response(session_id, user_prompt, model_id)
        
        if cached_response:
            logger.info(f"✅ Using cached AI response")
            return jsonify({
                'success': True,
                'text': cached_response.get('text', ''),
                'model': model_id,
                'cached': True,
                'metadata': cached_response.get('metadata', {})
            })
        
        # Query AI
        logger.info(f"🤖 Processing AI query: {user_prompt[:50]}...")
        
        result = ai_orchestrator.query(
            model_id=model_id,
            user_prompt=user_prompt,
            transcript_data=transcript.get('data', {}),
            enable_sync=enable_sync
        )
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Save to cache
        db_manager.save_ai_response(session_id, user_prompt, result, model_id)
        
        # Save chat messages
        db_manager.save_chat_message(
            session_id=session_id,
            role='user',
            content=user_prompt,
            model=model_id,
            metadata={'query_type': result.get('metadata', {}).get('query_type', 'general')}
        )
        
        db_manager.save_chat_message(
            session_id=session_id,
            role='assistant',
            content=result.get('text', ''),
            model=model_id,
            metadata=result.get('metadata', {})
        )
        
        result['cached'] = False
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error processing AI query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/compare', methods=['POST'])
@rate_limit
def compare_models():
    """
    Compare responses from multiple models
    
    Body:
    {
        "session_id": "abc123",
        "prompt": "Summarize this video",
        "model_ids": ["gemini-2.0-flash-exp", "openai/gpt-3.5-turbo"]
    }
    """
    try:
        data = request.json
        
        if not data or 'session_id' not in data or 'prompt' not in data or 'model_ids' not in data:
            return jsonify({
                'success': False,
                'error': 'session_id, prompt, and model_ids are required'
            }), 400
        
        session_id = data.get('session_id')
        user_prompt = data.get('prompt')
        model_ids = data.get('model_ids', [])[:5]  # Limit to 5
        
        # Get transcript
        transcript = db_manager.get_transcript(session_id)
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'Transcript not available'
            }), 404
        
        # Compare models
        result = ai_orchestrator.compare_models(
            model_ids=model_ids,
            user_prompt=user_prompt,
            transcript_data=transcript.get('data', {})
        )
        
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"❌ Error comparing models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/recommendations', methods=['POST'])
def get_recommendations():
    """Get recommended models for query"""
    try:
        data = request.json
        
        if not data or 'prompt' not in data:
            return jsonify({
                'success': False,
                'error': 'prompt is required'
            }), 400
        
        user_prompt = data.get('prompt')
        query_type = ai_orchestrator._classify_query(user_prompt)
        
        recommended = ai_orchestrator.get_recommended_models(query_type)
        
        return jsonify({
            'success': True,
            'query': user_prompt,
            'query_type': query_type,
            'recommended_models': recommended
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@ai_bp.route('/health', methods=['GET'])
def ai_health():
    """Check AI services health"""
    try:
        health = ai_orchestrator.health_check()
        
        return jsonify({
            'success': True,
            'health': health,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ AI health check error: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
