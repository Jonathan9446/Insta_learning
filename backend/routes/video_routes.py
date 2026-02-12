"""
Video Routes
Endpoints for YouTube and Facebook video processing
"""

from flask import Blueprint, request, jsonify
from datetime import datetime
import hashlib

from backend.config import config
from backend.database.firebase_manager import db_manager
from backend.video_processing.youtube_processor import youtube_processor
from backend.video_processing.facebook_processor import facebook_processor
from backend.utils.logger import setup_logger
from backend.utils.helpers import validate_url
from backend.middleware.rate_limiter import rate_limit

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

video_bp = Blueprint('video', __name__)


@video_bp.route('/process', methods=['POST'])
@rate_limit
def process_video():
    """
    Process video from YouTube or Facebook
    
    Body:
    {
        "video_url": "https://youtube.com/watch?v=...",
        "platform": "auto"  // auto, youtube, facebook
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
        
        # Auto-detect platform
        if platform == 'auto':
            if 'youtube.com' in video_url or 'youtu.be' in video_url:
                platform = 'youtube'
            elif 'facebook.com' in video_url or 'fb.watch' in video_url:
                platform = 'facebook'
            else:
                return jsonify({
                    'success': False,
                    'error': 'Unsupported platform. Please use YouTube or Facebook.'
                }), 400
        
        # Generate session ID
        session_id = hashlib.md5(video_url.encode()).hexdigest()
        
        # Check cache
        cached_session = db_manager.get_video_session(session_id)
        if cached_session and cached_session.get('transcript_available'):
            logger.info(f"✅ Using cached session: {session_id}")
            
            transcript = db_manager.get_transcript(session_id)
            
            return jsonify({
                'success': True,
                'session_id': session_id,
                'video_url': video_url,
                'platform': platform,
                'cached': True,
                'video_info': cached_session.get('video_data', {}),
                'transcript_available': True,
                'transcript_source': transcript.get('source') if transcript else None
            })
        
        # Process video
        logger.info(f"🎬 Processing {platform} video: {video_url}")
        
        if platform == 'youtube':
            result = youtube_processor.process_video(video_url)
        elif platform == 'facebook':
            result = facebook_processor.process_video(video_url)
        else:
            return jsonify({
                'success': False,
                'error': f'Unsupported platform: {platform}'
            }), 400
        
        if not result.get('success'):
            return jsonify(result), 400
        
        # Save to database
        video_data = {
            'platform': platform,
            'video_info': result.get('video_info', {}),
            'duration': result.get('video_info', {}).get('duration', 0),
            'title': result.get('video_info', {}).get('title', '')
        }
        
        db_manager.save_video_session(session_id, video_url, video_data)
        
        # Save transcript if available
        if result.get('transcript'):
            db_manager.save_transcript(
                session_id,
                result.get('video_id', ''),
                result['transcript'],
                result['transcript'].get('source', 'unknown')
            )
        
        # Add session ID to result
        result['session_id'] = session_id
        result['cached'] = False
        
        return jsonify(result), 200
        
    except Exception as e:
        logger.error(f"❌ Error processing video: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get video session info"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        # Get transcript if available
        transcript = None
        if session.get('transcript_available'):
            transcript = db_manager.get_transcript(session_id)
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'session': session,
            'transcript_available': bool(transcript),
            'transcript_source': transcript.get('source') if transcript else None
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/transcript/<session_id>', methods=['GET'])
def get_transcript(session_id):
    """Get transcript for session"""
    try:
        session = db_manager.get_video_session(session_id)
        
        if not session:
            return jsonify({
                'success': False,
                'error': 'Session not found'
            }), 404
        
        if not session.get('transcript_available'):
            return jsonify({
                'success': False,
                'error': 'Transcript not available'
            }), 404
        
        transcript = db_manager.get_transcript(session_id)
        
        if not transcript:
            return jsonify({
                'success': False,
                'error': 'Transcript not found'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'transcript': transcript.get('data', {}),
            'source': transcript.get('source', 'unknown'),
            'metadata': {
                'segments_count': len(transcript.get('data', {}).get('segments', [])),
                'duration': transcript.get('data', {}).get('duration', 0),
                'language': transcript.get('data', {}).get('language', 'en')
            }
        })
        
    except Exception as e:
        logger.error(f"❌ Error getting transcript: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@video_bp.route('/search', methods=['GET'])
def search_videos():
    """Search for videos (placeholder for future feature)"""
    query = request.args.get('q', '')
    platform = request.args.get('platform', 'youtube')
    
    return jsonify({
        'success': False,
        'message': 'Search feature coming soon',
        'query': query,
        'platform': platform
    }), 501


@video_bp.route('/export/<session_id>', methods=['GET'])
def export_session(session_id):
    """Export session data"""
    try:
        export_data = db_manager.export_session_data(session_id)
        
        if not export_data:
            return jsonify({
                'success': False,
                'error': 'Session not found or export failed'
            }), 404
        
        return jsonify({
            'success': True,
            'session_id': session_id,
            'export_data': export_data,
            'timestamp': datetime.now().isoformat()
        })
        
    except Exception as e:
        logger.error(f"❌ Error exporting session: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
