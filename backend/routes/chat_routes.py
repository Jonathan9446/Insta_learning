"""
Chat Routes
Endpoints for chat history and sync features
"""

from flask import Blueprint, request, jsonify
from datetime import datetime

from backend.config import config
from backend.database.firebase_manager import db_manager
from backend.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

chat_bp = Blueprint('chat', __name__)


@chat_bp.route('/history/<session_id>', methods=['GET'])
def get_history(session_id):
    """Get chat history for session"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        limit = request.args.get('limit', default=50, type=int)
        history = db_manager.get_chat_history(session_id, limit)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'history': history,
            'count': len(history),
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting chat history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/history/<session_id>', methods=['DELETE'])
def clear_history(session_id):
    """Clear chat history for session"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        success = db_manager.clear_chat_history(session_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to clear chat history'
            }), 500
        
        return jsonify({
            'success': True,
            'message': 'Chat history cleared',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error clearing chat history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/message', methods=['POST'])
def save_message():
    """
    Save chat message manually
    
    Body:
    {
        "session_id": "abc123",
        "role": "user",
        "content": "Hello",
        "model": "manual",
        "metadata": {}
    }
    """
    try:
        data = request.json
        
        required = ['session_id', 'role', 'content']
        for field in required:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        session_id = data.get('session_id')
        role = data.get('role')
        content = data.get('content')
        model = data.get('model', 'manual')
        metadata = data.get('metadata', {})
        
        # Validate session
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Validate role
        if role not in ['user', 'assistant']:
            return jsonify({
                'success': False,
                'error': 'role must be "user" or "assistant"'
            }), 400
        
        # Save message
        message_id = db_manager.save_chat_message(
            session_id=session_id,
            role=role,
            content=content,
            model=model,
            metadata=metadata
        )
        
        if not message_id:
            return jsonify({
                'success': False,
                'error': 'Failed to save message'
            }), 500
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error saving message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/export/<session_id>', methods=['GET'])
def export_history(session_id):
    """Export chat history"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        history = db_manager.get_chat_history(session_id, 1000)
        
        export_data = {
            'session_id': session_id,
            'video_url': session.get('video_url'),
            'video_title': session.get('video_data', {}).get('title', ''),
            'platform': session.get('platform', ''),
            'messages': history,
            'message_count': len(history),
            'exported_at': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'export_data': export_data
        })
        
    except Exception as e:
        logger.error(f"❌ Error exporting chat: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/summary/<session_id>', methods=['GET'])
def get_summary(session_id):
    """Get chat summary statistics"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        history = db_manager.get_chat_history(session_id, 100)
        
        # Calculate statistics
        user_messages = [m for m in history if m.get('role') == 'user']
        assistant_messages = [m for m in history if m.get('role') == 'assistant']
        
        # Model usage
        model_counts = {}
        for msg in assistant_messages:
            model = msg.get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # Timestamps
        timestamps = [m.get('timestamp') for m in history if m.get('timestamp')]
        timestamps.sort()
        
        summary = {
            'session_id': session_id,
            'total_messages': len(history),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'model_usage': model_counts,
            'first_message': timestamps[0] if timestamps else None,
            'last_message': timestamps[-1] if timestamps else None,
            'timestamp': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'summary': summary
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@chat_bp.route('/sync', methods=['POST'])
def sync_position():
    """
    Sync chat with video position
    
    Body:
    {
        "session_id": "abc123",
        "current_time": 125.5,
        "sync_enabled": true
    }
    """
    try:
        data = request.json
        
        if not data or 'session_id' not in data or 'current_time' not in data:
            return jsonify({
                'success': False,
                'error': 'session_id and current_time are required'
            }), 400
        
        session_id = data.get('session_id')
        current_time = data.get('current_time')
        sync_enabled = data.get('sync_enabled', True)
        
        logger.info(f"🔄 Sync update: {session_id} @ {current_time}s")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'current_time': current_time,
            'sync_enabled': sync_enabled,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error syncing position: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
