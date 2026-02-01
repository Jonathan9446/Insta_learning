"""
Video Routes Module
Flask routes for video processing endpoints
"""

from flask import Blueprint, request, jsonify, session
from datetime import datetime
import time
import hashlib

from config import config
from database import db_manager
from youtube_processor import youtube_processor
from facebook_processor import facebook_processor
from utils.helpers import validate_url, generate_session_id
from utils.logger import setup_logger, timed_operation

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

# Create blueprint
video_bp = Blueprint('video', __name__)

@video_bp.route('/process', methods=['POST'])
@timed_operation('process_video')
def process_video():
    """
    Process video from URL (YouTube or Facebook)
    
    Expected JSON:
    {
        "video_url": "https://www.youtube.com/watch?v=...",
        "platform": "auto"  # auto, youtube, facebook
    }
    """
    try:
        data = request.json
        
        if not data or 'video_url' not in data:
            return jsonify({
                'success': False,
                'error': 'video_url is required'
            }), 400
        
        video_url = data.get('video_url').strip()
        platform = data.get('platform', 'auto').lower()
        
        # Validate URL
        if not validate_url(video_url):
            return jsonify({
                'success': False,
                'error': 'Invalid URL format'
            }), 400
        
        # Determine platform
        if platform == 'auto':
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                platform = 'youtube'
            elif 'facebook.com' in video_url or 'fb.watch' in video_url:
                platform = 'facebook'
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported platform. Please specify youtube or facebook.'
                }), 400
        
        # Generate session ID
        session_id = session.get('session_id') or generate_session_id()
        session['session_id'] = session_id
        
        # Check cache first
        video_hash = hashlib.md5(video_url.encode()).hexdigest()
        cached_session = db_manager.get_video_session(video_hash)
        
        if cached_session and cached_session.get('status') == 'completed':
            logger.info(f"Using cached session for video: {video_url}")
            
            # Get transcript from cache
            transcript = db_manager.get_transcript(video_hash)
            
            return jsonify({
                'success': True,
                'session_id': video_hash,
                'video_url': video_url,
                'platform': platform,
                'cached': True,
                'video_info': cached_session.get('video_data', {}),
                'transcript_available': bool(transcript),
                'processing_time': 0.1,
                'message': 'Loaded from cache'
            })
        
        # Process based on platform
        logger.info(f"Processing {platform} video: {video_url}")
        
        if platform == 'youtube':
            result = youtube_processor.process_youtube_video(video_url)
        elif platform == 'facebook':
            result = facebook_processor.process_facebook_video(video_url)
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported platform: {platform}'
            }), 400
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Extract video ID for session
        video_id = result.get('video_id', '')
        session_id = video_hash
        
        # Prepare video data for storage
        video_data = {
            'video_info': result.get('video_info', {}),
            'platform': platform,
            'duration': result.get('video_info', {}).get('duration', 0),
            'title': result.get('video_info', {}).get('title', ''),
            'thumbnail': result.get('video_info', {}).get('thumbnail', '')
        }
        
        # Save video session
        db_manager.save_video_session(
            session_id=session_id,
            video_url=video_url,
            video_data=video_data
        )
        
        # Save transcript if available
        transcript_data = result.get('transcript')
        if transcript_data:
            db_manager.save_transcript(
                session_id=session_id,
                video_id=video_id,
                transcript_data=transcript_data,
                source=transcript_data.get('source', 'unknown')
            )
            
            # Update session to mark transcript available
            db_manager.update_video_session(session_id, {
                'transcript_available': True,
                'status': 'completed'
            })
        
        # Add session info to response
        result['session_id'] = session_id
        result['platform'] = platform
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error processing video: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/status/<session_id>', methods=['GET'])
def get_video_status(session_id):
    """Get processing status for a video session"""
    try:
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get transcript if available
        transcript = None
        if session_data.get('transcript_available'):
            video_id = session_data.get('video_data', {}).get('video_info', {}).get('id', '')
            transcript = db_manager.get_transcript(session_id, video_id)
        
        response = {
            'success': True,
            'session_id': session_id,
            'status': session_data.get('status', 'unknown'),
            'video_url': session_data.get('video_url', ''),
            'platform': session_data.get('platform', 'unknown'),
            'transcript_available': session_data.get('transcript_available', False),
            'created_at': session_data.get('created_at'),
            'updated_at': session_data.get('updated_at'),
            'video_info': session_data.get('video_data', {}),
            'transcript_preview': transcript.get('data', {}) if transcript else None
        }
        
        return jsonify(response), 200
        
    except Exception as e:
        logger.error(f"Error getting video status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/transcript/<session_id>', methods=['GET'])
def get_transcript(session_id):
    """Get transcript for a video session"""
    try:
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
            }), 404
        
        # Get video ID
        video_id = session_data.get('video_data', {}).get('video_info', {}).get('id', '')
        
        # Get transcript
        transcript = db_manager.get_transcript(session_id, video_id)
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'Transcript not found'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'video_id': video_id,
            'transcript': transcript.get('data', {}),
            'source': transcript.get('source', 'unknown'),
            'metadata': {
                'sentences_count': transcript.get('sentences_count', 0),
                'word_count': transcript.get('word_count', 0),
                'duration': transcript.get('duration', 0),
                'created_at': transcript.get('created_at')
            }
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting transcript: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/embed/<session_id>', methods=['GET'])
def get_embed_code(session_id):
    """Get embed code for a video"""
    try:
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        platform = session_data.get('platform')
        video_url = session_data.get('video_url')
        video_info = session_data.get('video_data', {}).get('video_info', {})
        
        embed_code = ""
        
        if platform == 'youtube':
            video_id = video_info.get('id', '')
            if video_id:
                embed_code = f"""
                <iframe width="100%" height="500" 
                        src="https://www.youtube.com/embed/{video_id}" 
                        frameborder="0" 
                        allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture" 
                        allowfullscreen>
                </iframe>
                """
        
        elif platform == 'facebook':
            video_id = video_info.get('id', '')
            if video_id:
                embed_code = f"""
                <iframe 
                    src="https://www.facebook.com/plugins/video.php?href=https%3A%2F%2Fwww.facebook.com%2Fvideo.php%3Fv%3D{video_id}&show_text=false"
                    width="100%"
                    height="500"
                    style="border:none;overflow:hidden"
                    scrolling="no"
                    frameborder="0"
                    allowfullscreen="true"
                    allow="autoplay; clipboard-write; encrypted-media; picture-in-picture; web-share"
                    allowFullScreen="true">
                </iframe>
                """
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'platform': platform,
            'embed_code': embed_code,
            'video_url': video_url
        }), 200
        
    except Exception as e:
        logger.error(f"Error getting embed code: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/session/<session_id>', methods=['DELETE'])
def delete_session(session_id):
    """Delete a video session and associated data"""
    try:
        # TODO: Implement session deletion
        # For now, just mark as deleted
        
        db_manager.update_video_session(session_id, {
            'status': 'deleted',
            'deleted_at': datetime.now().isoformat()
        })
        
        return jsonify({
            'success': True,
            'message': f'Session {session_id} marked as deleted',
            'session_id': session_id
        }), 200
        
    except Exception as e:
        logger.error(f"Error deleting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/sessions', methods=['GET'])
def list_sessions():
    """List all video sessions for current user"""
    try:
        # This would normally filter by user ID
        # For now, return basic response
        
        return jsonify({
            'success': True,
            'message': 'Session listing endpoint',
            'note': 'User-specific session listing would be implemented with authentication'
        }), 200
        
    except Exception as e:
        logger.error(f"Error listing sessions: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/export/<session_id>', methods=['GET'])
def export_session_data(session_id):
    """Export all session data"""
    try:
        export_data = db_manager.export_session_data(session_id)
        
        if not export_data:
            return jsonify({
                'success': False,
                'error': 'Session data not found or export failed'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'export_data': export_data,
            'export_format': 'json',
            'timestamp': datetime.now().isoformat()
        }), 200
        
    except Exception as e:
        logger.error(f"Error exporting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@video_bp.route('/reprocess/<session_id>', methods=['POST'])
def reprocess_video(session_id):
    """Reprocess video (e.g., to get better transcript)"""
    try:
        session_data = db_manager.get_video_session(session_id)
        
        if not session_data:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        video_url = session_data.get('video_url')
        platform = session_data.get('platform')
        
        if not video_url or not platform:
            return jsonify({
                'success': False,
                'error': 'Invalid session data'
            }), 400
        
        logger.info(f"Reprocessing {platform} video: {video_url}")
        
        if platform == 'youtube':
            result = youtube_processor.process_youtube_video(video_url)
        elif platform == 'facebook':
            result = facebook_processor.process_facebook_video(video_url)
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported platform: {platform}'
            }), 400
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Update transcript if available
        transcript_data = result.get('transcript')
        if transcript_data:
            video_id = result.get('video_id', '')
            
            db_manager.save_transcript(
                session_id=session_id,
                video_id=video_id,
                transcript_data=transcript_data,
                source=transcript_data.get('source', 'unknown') + '_reprocessed'
            )
            
            # Update session
            db_manager.update_video_session(session_id, {
                'transcript_available': True,
                'status': 'reprocessed',
                'reprocessed_at': datetime.now().isoformat()
            })
        
        result['session_id'] = session_id
        result['reprocessed'] = True
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"Error reprocessing video: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
