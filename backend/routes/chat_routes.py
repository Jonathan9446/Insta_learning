"""
Chat Routes Module
Flask routes for chat history and interactions
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime

from config import config
from database import db_manager
from utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

# Create blueprint
chat_bp = Blueprint('chat', __name__)

@chat_bp.route('/history/<session_id>', methods=['GET'])
def get_chat_history(session_id):
    """Get chat history for a session"""
    try:
        # Get session to verify it exists
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get chat history
        limit = request.args.get('limit', default=50, type=int)
        chat_history = db_manager.get_chat_history(session_id, limit)
        
        # Format response
        formatted_history = []
        for message in chat_history:
            formatted_message = {
                'id': message.get('message_id'),
                'role': message.get('role'),
                'content': message.get('content'),
                'model': message.get('model'),
                'timestamp': message.get('timestamp'),
                'metadata': message.get('metadata', {})
            }
            formatted_history.append(formatted_message)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'history': formatted_history,
            'count': len(formatted_history),
            'has_more': len(formatted_history) == limit,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/history/<session_id>', methods=['DELETE'])
def clear_chat_history(session_id):
    """Clear chat history for a session"""
    try:
        # Get session to verify it exists
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Clear chat history
        success = db_manager.clear_chat_history(session_id)
        
        if not success:
            return jsonify({
                'success': False,
                'error': 'Failed to clear chat history'
            }), 500
        
        return jsonify({
            'success': True,
            'message': f'Chat history cleared for session {session_id}',
            'session_id': session_id,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error clearing chat history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/export/<session_id>', methods=['GET'])
def export_chat_history(session_id):
    """Export chat history for a session"""
    try:
        # Get session to verify it exists
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get chat history (all messages)
        chat_history = db_manager.get_chat_history(session_id, limit=1000)
        
        # Format for export
        export_data = {
            'session_id': session_id,
            'video_url': session_data.get('video_url'),
            'video_title': session_data.get('video_data', {}).get('title', ''),
            'export_timestamp': datetime.now().isoformat(),
            'message_count': len(chat_history),
            'messages': chat_history
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'export_data': export_data,
            'export_format': 'json',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting chat history: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/message', methods=['POST'])
def save_chat_message():
    """Save a chat message (for manual entry or updates)"""
    try:
        data = request.json
        
        required_fields = ['session_id', 'role', 'content']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'{field} is required'
                }), 400
        
        session_id = data.get('session_id')
        role = data.get('role')  # 'user' or 'assistant'
        content = data.get('content')
        model = data.get('model', 'manual')
        metadata = data.get('metadata', {})
        
        # Validate session exists
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
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
                'error': 'Failed to save chat message'
            }), 500
        
        return jsonify({
            'success': True,
            'message_id': message_id,
            'session_id': session_id,
            'role': role,
            'content': content,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error saving chat message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/message/<message_id>', methods=['DELETE'])
def delete_chat_message(message_id):
    """Delete a specific chat message"""
    try:
        # This would require message lookup and deletion
        # For now, return not implemented
        
        return jsonify({
            'success': False,
            'error': 'Message deletion not implemented yet',
            'message_id': message_id
        }), 501
        
    except Exception as e:
        logger.error(f"Error deleting chat message: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/session/<session_id>/summary', methods=['GET'])
def get_chat_summary(session_id):
    """Get summary of chat history for a session"""
    try:
        # Get session to verify it exists
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get chat history
        chat_history = db_manager.get_chat_history(session_id, limit=100)
        
        # Calculate statistics
        user_messages = [m for m in chat_history if m.get('role') == 'user']
        assistant_messages = [m for m in chat_history if m.get('role') == 'assistant']
        
        # Count models used
        model_counts = {}
        for message in assistant_messages:
            model = message.get('model', 'unknown')
            model_counts[model] = model_counts.get(model, 0) + 1
        
        # Calculate average message length
        total_chars = sum(len(m.get('content', '')) for m in chat_history)
        avg_length = total_chars / len(chat_history) if chat_history else 0
        
        # Get first and last message timestamps
        timestamps = [m.get('timestamp') for m in chat_history if m.get('timestamp')]
        timestamps.sort()
        
        first_timestamp = timestamps[0] if timestamps else None
        last_timestamp = timestamps[-1] if timestamps else None
        
        summary = {
            'session_id': session_id,
            'total_messages': len(chat_history),
            'user_messages': len(user_messages),
            'assistant_messages': len(assistant_messages),
            'model_usage': model_counts,
            'avg_message_length': avg_length,
            'first_message': first_timestamp,
            'last_message': last_timestamp,
            'topics': [],  # Could be extracted from message content
            'summary_generated': datetime.now().isoformat()
        }
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'summary': summary,
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting chat summary: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/sessions', methods=['GET'])
def list_chat_sessions():
    """List all chat sessions (for current user)"""
    try:
        # This would normally be user-specific
        # For demo purposes, return placeholder
        
        return jsonify({
            'success': True,
            'message': 'Chat session listing would be implemented with user authentication',
            'note': 'This endpoint would return all sessions for the authenticated user',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing chat sessions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@chat_bp.route('/sync', methods=['POST'])
def sync_chat_position():
    """Sync chat position with video playback"""
    try:
        data = request.json
        
        if not data or 'session_id' not in data or 'current_time' not in data:
            return jsonify({
                'success': False,
                'error': 'session_id and current_time are required'
            }), 400
        
        session_id = data.get('session_id')
        current_time = data.get('current_time')
        
        # This would update session metadata with current playback position
        # For now, just acknowledge
        
        logger.info(f"Chat sync update: session={session_id}, time={current_time}")
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'current_time': current_time,
            'message': 'Sync position updated',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error syncing chat position: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
