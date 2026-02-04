"""
AI Routes Module
Flask routes for AI processing endpoints
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime

from config import config
from database import db_manager
from ai_orchestrator import ai_orchestrator
from utils.logger import setup_logger, timed_operation

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

# Create blueprint
ai_bp = Blueprint('ai', __name__)

@ai_bp.route('/models', methods=['GET'])
def get_ai_models():
    """Get available AI models"""
    try:
        models = ai_orchestrator.get_available_models()
        
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models),
            'default_model': 'gemini-2.0-flash',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting AI models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/model/<model_id>', methods=['GET'])
def get_model_info(model_id):
    """Get information about a specific AI model"""
    try:
        model_info = ai_orchestrator.get_model_capabilities(model_id)
        
        if not model_info:
            return jsonify({
                'success': False,
                'error': f'Model {model_id} not found'
            }), 404
        
        return jsonify({
            'success': True,
            'model': model_info,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting model info: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/query', methods=['POST'])
@timed_operation('ai_query')
def process_ai_query():
    """
    Process AI query for a video
    
    Expected JSON:
    {
        "session_id": "session_123",
        "query": "Summarize this video",
        "model_id": "gemini-2.0-flash",
        "enable_sync": true
    }
    """
    try:
        data = request.json
        
        # Validate required fields
        required_fields = ['session_id', 'query']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        session_id = data.get('session_id')
        user_query = data.get('query').strip()
        model_id = data.get('model_id', 'gemini-2.0-flash')
        enable_sync = data.get('enable_sync', True)
        
        # Get session data
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        if not session_data.get('transcript_available'):
            return jsonify({
                'success': False,
                'error': 'Transcript not available for this session'
            }), 400
        
        # Get transcript
        video_id = session_data.get('video_data', {}).get('video_info', {}).get('id', '')
        transcript_data = db_manager.get_transcript(session_id, video_id)
        
        if not transcript_data:
            return jsonify({
                'success': False,
                'error': 'Transcript data not found'
            }), 404
        
        # Check cache first
        cached_response = db_manager.get_cached_response(session_id, user_query)
        
        if cached_response:
            logger.info(f"Using cached AI response for session: {session_id}")
            
            # Update metadata
            cached_response['cached'] = True
            cached_response['timestamp'] = datetime.now().isoformat()
            
            # Save chat message
            db_manager.save_chat_message(
                session_id=session_id,
                role='assistant',
                content=cached_response.get('text', ''),
                model=model_id,
                metadata={
                    'cached': True,
                    'query': user_query
                }
            )
            
            return jsonify(cached_response), 200
        
        # Process with AI
        logger.info(f"Processing AI query for session {session_id}: {user_query[:50]}...")
        
        result = ai_orchestrator.process_query(
            transcript_data=transcript_data.get('data', {}),
            user_query=user_query,
            model_id=model_id,
            session_id=session_id,
            enable_sync=enable_sync
        )
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Save AI response to cache
        if result.get('success'):
            db_manager.save_ai_response(
                session_id=session_id,
                query=user_query,
                response=result,
                model=model_id
            )
            
            # Save chat messages
            # User message
            db_manager.save_chat_message(
                session_id=session_id,
                role='user',
                content=user_query,
                model=model_id,
                metadata={
                    'query_type': result.get('metadata', {}).get('query_type', 'general')
                }
            )
            
            # AI response
            db_manager.save_chat_message(
                session_id=session_id,
                role='assistant',
                content=result.get('text', ''),
                model=model_id,
                metadata=result.get('metadata', {})
            )
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing AI query: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/batch', methods=['POST'])
def batch_process_queries():
    """Process multiple AI queries in batch"""
    try:
        data = request.json
        
        if not data or 'queries' not in data:
            return jsonify({
                'success': False,
                'error': 'queries array is required'
            }), 400
        
        queries = data.get('queries', [])
        session_id = data.get('session_id')
        
        if not session_id:
            return jsonify({
                'success': False,
                'error': 'session_id is required for batch processing'
            }), 400
        
        # Get session data
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get transcript
        video_id = session_data.get('video_data', {}).get('video_info', {}).get('id', '')
        transcript_data = db_manager.get_transcript(session_id, video_id)
        
        if not transcript_data:
            return jsonify({
                'success': False,
                'error': 'Transcript not available'
            }), 404
        
        # Prepare queries for batch processing
        query_list = []
        for query_item in queries[:10]:  # Limit to 10 queries
            if 'query' in query_item:
                query_list.append({
                    'query': query_item['query'],
                    'model_id': query_item.get('model_id', 'gemini-2.0-flash'),
                    'transcript': transcript_data.get('data', {})
                })
        
        # Process batch
        results = ai_orchestrator.batch_process(query_list, session_id)
        
        # Save responses
        for result in results:
            if result['result'].get('success'):
                db_manager.save_ai_response(
                    session_id=session_id,
                    query=result['query'],
                    response=result['result'],
                    model=result['model']
                )
        
        return jsonify({
            'success': True,
            'count': len(results),
            'results': results,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in batch processing: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/compare', methods=['POST'])
def compare_models():
    """Compare responses from multiple AI models"""
    try:
        data = request.json
        
        required_fields = ['session_id', 'query', 'model_ids']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        session_id = data.get('session_id')
        user_query = data.get('query')
        model_ids = data.get('model_ids', [])
        
        # Limit to 5 models for comparison
        model_ids = model_ids[:5]
        
        # Get session data
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get transcript
        video_id = session_data.get('video_data', {}).get('video_info', {}).get('id', '')
        transcript_data = db_manager.get_transcript(session_id, video_id)
        
        if not transcript_data:
            return jsonify({
                'success': False,
                'error': 'Transcript not available'
            }), 404
        
        # Compare models
        comparisons = ai_orchestrator.compare_models(
            transcript_data=transcript_data.get('data', {}),
            user_query=user_query,
            model_ids=model_ids
        )
        
        return jsonify({
            'success': True,
            'query': user_query,
            'comparisons': comparisons,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error comparing models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/recommendations', methods=['POST'])
def get_recommendations():
    """Get recommended models for a query type"""
    try:
        data = request.json
        
        if not data or 'query' not in data:
            return jsonify({
                'success': False,
                'error': 'query is required'
            }), 400
        
        user_query = data.get('query')
        
        # Classify query
        query_type = ai_orchestrator._classify_query(user_query)
        
        # Get recommendations
        recommended_models = ai_orchestrator.get_recommendations(query_type)
        
        # Filter to available models
        available_models = ai_orchestrator.get_available_models()
        available_model_ids = [m['id'] for m in available_models]
        
        filtered_recommendations = [
            model_id for model_id in recommended_models 
            if model_id in available_model_ids
        ]
        
        return jsonify({
            'success': True,
            'query': user_query,
            'query_type': query_type,
            'recommended_models': filtered_recommendations,
            'explanation': f"Recommended models for {query_type} tasks",
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting recommendations: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/health', methods=['GET'])
def ai_health_check():
    """Check AI services health"""
    try:
        health_data = ai_orchestrator.health_check()
        
        return jsonify({
            'success': True,
            'health': health_data,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error in AI health check: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/clear_cache', methods=['POST'])
def clear_ai_cache():
    """Clear AI response cache"""
    try:
        # In a real implementation, this would clear the cache
        # For now, just acknowledge
        
        return jsonify({
            'success': True,
            'message': 'AI cache cleared',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing AI cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@ai_bp.route('/sync/jump', methods=['POST'])
def jump_to_timestamp():
    """Handle sync jump requests (for frontend)"""
    try:
        data = request.json
        
        if not data or 'timestamp' not in data:
            return jsonify({
                'success': False,
                'error': 'timestamp is required'
            }), 400
        
        timestamp = data.get('timestamp')
        session_id = data.get('session_id')
        
        # This endpoint is mainly for frontend coordination
        # The actual video jumping happens in the frontend
        
        logger.info(f"Sync jump requested: session={session_id}, time={timestamp}")
        
        return jsonify({
            'success': True,
            'timestamp': timestamp,
            'session_id': session_id,
            'message': 'Sync jump registered',
            'timestamp_formatted': f"{int(timestamp // 3600):02d}:{int((timestamp % 3600) // 60):02d}:{int(timestamp % 60):02d}"
        }), 200
        
    except Exception as e:
        logger.error(f"Error in sync jump: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
