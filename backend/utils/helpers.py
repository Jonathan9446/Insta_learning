"""
Utility Helper Functions
Common helper functions used throughout the application
"""

import os
import re
import json
import hashlib
import tempfile
import shutil
from typing import Dict, List, Optional, Any, Union
from datetime import datetime, timedelta
from pathlib import Path
import random
import string

def generate_session_id(length: int = 16) -> str:
    """Generate a random session ID"""
    characters = string.ascii_letters + string.digits
    return ''.join(random.choice(characters) for _ in range(length))

def generate_video_hash(video_url: str) -> str:
    """Generate hash for video URL"""
    return hashlib.md5(video_url.encode()).hexdigest()

def format_timestamp(seconds: float) -> str:
    """Format seconds to HH:MM:SS or MM:SS"""
    if seconds < 0:
        return "00:00"
    
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"

def parse_timestamp(timestamp_str: str) -> float:
    """Parse timestamp string to seconds"""
    try:
        parts = timestamp_str.split(':')
        
        if len(parts) == 3:  # HH:MM:SS
            hours = int(parts[0])
            minutes = int(parts[1])
            seconds = float(parts[2])
            return hours * 3600 + minutes * 60 + seconds
        elif len(parts) == 2:  # MM:SS
            minutes = int(parts[0])
            seconds = float(parts[1])
            return minutes * 60 + seconds
        elif len(parts) == 1:  # SS
            return float(parts[0])
        else:
            return 0.0
    except:
        return 0.0

def truncate_text(text: str, max_length: int, suffix: str = "...") -> str:
    """Truncate text to maximum length"""
    if len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix

def extract_keywords(text: str, max_keywords: int = 10) -> List[str]:
    """Extract keywords from text (simple implementation)"""
    # Remove punctuation and convert to lowercase
    text = re.sub(r'[^\w\s]', ' ', text.lower())
    
    # Common stop words
    stop_words = {
        'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
        'of', 'with', 'by', 'as', 'is', 'are', 'was', 'were', 'be', 'been',
        'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would',
        'should', 'could', 'can', 'may', 'might', 'must', 'i', 'you', 'he',
        'she', 'it', 'we', 'they', 'me', 'him', 'her', 'us', 'them', 'my',
        'your', 'his', 'its', 'our', 'their', 'this', 'that', 'these', 'those'
    }
    
    # Split into words and filter
    words = text.split()
    filtered_words = [w for w in words if w not in stop_words and len(w) > 2]
    
    # Count frequencies
    word_freq = {}
    for word in filtered_words:
        word_freq[word] = word_freq.get(word, 0) + 1
    
    # Get top keywords
    sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
    keywords = [word for word, freq in sorted_words[:max_keywords]]
    
    return keywords

def clean_temp_files(temp_dir: str, max_age_hours: int = 24):
    """Clean up temporary files older than specified hours"""
    try:
        if not os.path.exists(temp_dir):
            return
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for item in os.listdir(temp_dir):
            item_path = os.path.join(temp_dir, item)
            
            # Skip if it's a directory
            if os.path.isdir(item_path):
                # Recursively clean subdirectories
                clean_temp_files(item_path, max_age_hours)
                
                # Remove empty directory
                if not os.listdir(item_path):
                    os.rmdir(item_path)
                continue
            
            # Check file age
            try:
                mod_time = datetime.fromtimestamp(os.path.getmtime(item_path))
                if mod_time < cutoff_time:
                    os.remove(item_path)
            except:
                pass
                
    except Exception as e:
        print(f"Error cleaning temp files: {e}")

def validate_url(url: str, allowed_domains: List[str] = None) -> bool:
    """Validate URL format and domain"""
    if allowed_domains is None:
        allowed_domains = ['youtube.com', 'youtu.be', 'facebook.com', 'fb.watch']
    
    try:
        # Basic URL validation
        if not url.startswith(('http://', 'https://')):
            return False
        
        # Check domain
        for domain in allowed_domains:
            if domain in url:
                return True
        
        return False
        
    except:
        return False

def extract_youtube_id(url: str) -> Optional[str]:
    """Extract YouTube video ID from URL"""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
        r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def extract_facebook_id(url: str) -> Optional[str]:
    """Extract Facebook video ID from URL"""
    patterns = [
        r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/[^\/]+\/videos\/(\d+)',
        r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/watch\/\?v=(\d+)',
        r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/video\.php\?v=(\d+)',
        r'(?:https?:\/\/)?fb\.watch\/([a-zA-Z0-9]+)'
    ]
    
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    
    return None

def safe_json_dumps(data: Any, indent: int = 2) -> str:
    """Safely convert data to JSON string"""
    def default_serializer(obj):
        if isinstance(obj, (datetime, timedelta)):
            return str(obj)
        raise TypeError(f"Type {type(obj)} not serializable")
    
    return json.dumps(data, default=default_serializer, indent=indent, ensure_ascii=False)

def create_temp_directory(prefix: str = "video_ai_") -> str:
    """Create a temporary directory"""
    return tempfile.mkdtemp(prefix=prefix)

def get_file_size_mb(file_path: str) -> float:
    """Get file size in MB"""
    try:
        return os.path.getsize(file_path) / (1024 * 1024)
    except:
        return 0.0

def is_video_too_large(file_path: str, max_size_mb: float = 100) -> bool:
    """Check if video file is too large"""
    size_mb = get_file_size_mb(file_path)
    return size_mb > max_size_mb

def split_video_by_duration(video_path: str, max_duration_seconds: int = 600):
    """Split video into chunks by duration (placeholder implementation)"""
    # This would use ffmpeg or similar in a real implementation
    return []

def estimate_processing_time(video_duration: float, 
                           has_transcript: bool = False) -> float:
    """Estimate processing time based on video duration"""
    base_time = 5.0  # Base processing time in seconds
    duration_factor = 0.1  # Additional time per second of video
    
    estimated_time = base_time + (video_duration * duration_factor)
    
    # Adjust based on transcript availability
    if not has_transcript:
        estimated_time *= 1.5  # 50% more time if transcribing
    
    return min(estimated_time, 300)  # Cap at 5 minutes

def format_file_size(bytes_size: int) -> str:
    """Format file size in human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"

def sanitize_filename(filename: str) -> str:
    """Sanitize filename to remove unsafe characters"""
    # Remove or replace unsafe characters
    filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
    filename = re.sub(r'\s+', '_', filename)
    filename = filename.strip('_. ')
    
    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[:255 - len(ext)] + ext
    
    return filename

def merge_dicts(dict1: Dict, dict2: Dict) -> Dict:
    """Merge two dictionaries, with dict2 taking precedence"""
    result = dict1.copy()
    result.update(dict2)
    return result

def get_platform_from_url(url: str) -> str:
    """Detect platform from URL"""
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    elif 'facebook.com' in url or 'fb.watch' in url:
        return 'facebook'
    else:
        return 'unknown'

def create_progress_tracker(total_steps: int = 5) -> Dict:
    """Create a progress tracker dictionary"""
    return {
        'total_steps': total_steps,
        'current_step': 0,
        'progress': 0.0,
        'status': 'initializing',
        'details': '',
        'start_time': datetime.now().isoformat(),
        'last_update': datetime.now().isoformat()
    }

def update_progress(tracker: Dict, step: int, status: str, details: str = ''):
    """Update progress tracker"""
    tracker['current_step'] = step
    tracker['progress'] = (step / tracker['total_steps']) * 100
    tracker['status'] = status
    tracker['details'] = details
    tracker['last_update'] = datetime.now().isoformat()
    return tracker

def calculate_word_density(text: str) -> Dict[str, float]:
    """Calculate word density statistics"""
    words = text.split()
    total_words = len(words)
    
    if total_words == 0:
        return {
            'total_words': 0,
            'unique_words': 0,
            'avg_word_length': 0,
            'word_density': 0
        }
    
    unique_words = len(set(words))
    total_chars = sum(len(word) for word in words)
    
    return {
        'total_words': total_words,
        'unique_words': unique_words,
        'avg_word_length': total_chars / total_words,
        'word_density': unique_words / total_words
    }

def generate_transcript_preview(transcript_data: Dict, max_sentences: int = 5) -> str:
    """Generate preview of transcript"""
    if not transcript_data or 'sentences' not in transcript_data:
        return "No transcript available."
    
    sentences = transcript_data['sentences'][:max_sentences]
    preview_lines = []
    
    for sentence in sentences:
        text = sentence.get('text', '')
        start = sentence.get('start', 0)
        
        if text:
            time_str = format_timestamp(start)
            preview_lines.append(f"[{time_str}] {text}")
    
    return '\n'.join(preview_lines)

def is_valid_json(data: str) -> bool:
    """Check if string is valid JSON"""
    try:
        json.loads(data)
        return True
    except:
        return False

def get_audio_duration(file_path: str) -> float:
    """Get audio duration in seconds (requires pydub)"""
    try:
        from pydub import AudioSegment
        audio = AudioSegment.from_file(file_path)
        return len(audio) / 1000.0  # Convert milliseconds to seconds
    except:
        return 0.0

def normalize_text(text: str) -> str:
    """Normalize text by removing extra whitespace and normalizing line endings"""
    # Remove extra whitespace
    text = re.sub(r'\s+', ' ', text)
    # Normalize line endings
    text = re.sub(r'\r\n', '\n', text)
    text = re.sub(r'\r', '\n', text)
    # Remove leading/trailing whitespace
    return text.strip()
