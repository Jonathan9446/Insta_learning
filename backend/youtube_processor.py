"""
YouTube Video Processor
Handles YouTube video extraction, transcript fetching, and processing
Uses Piped API (public instances) + yt-dlp fallback + Groq Whisper transcription
"""

import os
import re
import json
import time
import hashlib
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import requests
from urllib.parse import urlparse, parse_qs

from config import config
from utils.helpers import cleanup_temp_files, format_timestamp
from utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

class YouTubeProcessor:
    """Main YouTube video processing class"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.temp_dir = config.TEMP_DIR
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract YouTube video ID from various URL formats
        
        Supported formats:
        - https://www.youtube.com/watch?v=VIDEO_ID
        - https://youtu.be/VIDEO_ID
        - https://www.youtube.com/embed/VIDEO_ID
        - https://www.youtube.com/v/VIDEO_ID
        - https://www.youtube.com/shorts/VIDEO_ID
        """
        patterns = [
            # Regular YouTube watch URL
            r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            # YouTube embed URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            # YouTube short URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
            # YouTube v URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})',
            # YouTube live URL
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/live\/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters
        parsed = urlparse(url)
        if parsed.netloc in ['youtube.com', 'www.youtube.com', 'm.youtube.com']:
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        return None
    
    def get_video_info_piped(self, video_id: str, instance_url: str) -> Optional[Dict]:
        """
        Get video information from Piped API
        
        Args:
            video_id: YouTube video ID
            instance_url: Piped API instance URL
            
        Returns:
            Video information dictionary or None
        """
        try:
            endpoint = f"{instance_url}/streams/{video_id}"
            logger.info(f"Fetching video info from Piped: {endpoint}")
            
            response = self.session.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                # Extract video information
                video_info = {
                    'id': video_id,
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnailUrl', ''),
                    'uploader': data.get('uploader', ''),
                    'upload_date': data.get('uploadDate', ''),
                    'view_count': data.get('views', 0),
                    'likes': data.get('likes', 0),
                    'categories': data.get('category', ''),
                    'available_formats': [],
                    'subtitles': [],
                    'piped_instance': instance_url
                }
                
                # Extract available formats
                if 'videoStreams' in data:
                    video_info['available_formats'] = [
                        {
                            'format': f"{stream.get('quality', '')} {stream.get('format', '')}",
                            'url': stream.get('url', ''),
                            'codec': stream.get('codec', ''),
                            'bitrate': stream.get('bitrate', 0)
                        }
                        for stream in data['videoStreams']
                    ]
                
                # Extract available subtitles
                if 'subtitles' in data:
                    video_info['subtitles'] = [
                        {
                            'code': sub.get('code', ''),
                            'name': sub.get('name', ''),
                            'url': sub.get('url', '')
                        }
                        for sub in data['subtitles']
                    ]
                
                logger.info(f"Successfully fetched video info: {video_info['title']}")
                return video_info
            else:
                logger.warning(f"Piped API returned {response.status_code} for video {video_id}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching video info from Piped: {e}")
            return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """
        Get video information with multiple Piped instance fallback
        """
        logger.info(f"Getting video info for: {video_id}")
        
        # Try each Piped instance
        for instance in config.PIPED_INSTANCES:
            video_info = self.get_video_info_piped(video_id, instance)
            if video_info:
                video_info['source'] = 'piped_api'
                video_info['instance_used'] = instance
                return video_info
        
        # If all Piped instances fail, try yt-dlp as fallback
        logger.info("All Piped instances failed, falling back to yt-dlp")
        return self.get_video_info_ytdlp(video_id)
    
    def get_video_info_ytdlp(self, video_id: str) -> Optional[Dict]:
        """
        Get video information using yt-dlp
        """
        try:
            temp_output = os.path.join(self.temp_dir, f"video_info_{video_id}.json")
            
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--no-warnings',
                '-o', temp_output,
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            
            logger.info(f"Running yt-dlp command: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                with open(temp_output, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                video_info = {
                    'id': video_id,
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnail', ''),
                    'uploader': data.get('uploader', ''),
                    'upload_date': data.get('upload_date', ''),
                    'view_count': data.get('view_count', 0),
                    'like_count': data.get('like_count', 0),
                    'categories': data.get('categories', []),
                    'tags': data.get('tags', []),
                    'available_formats': [],
                    'subtitles': [],
                    'source': 'yt_dlp',
                    'automatic_captions': bool(data.get('automatic_captions', {}))
                }
                
                # Extract formats
                if 'formats' in data:
                    video_info['available_formats'] = [
                        {
                            'format_id': fmt.get('format_id', ''),
                            'ext': fmt.get('ext', ''),
                            'resolution': fmt.get('resolution', ''),
                            'filesize': fmt.get('filesize', 0)
                        }
                        for fmt in data['formats'][:5]  # Limit to first 5 formats
                    ]
                
                # Extract subtitles if available
                if 'subtitles' in data:
                    for lang, subs in data['subtitles'].items():
                        for sub in subs:
                            video_info['subtitles'].append({
                                'code': lang,
                                'name': sub.get('name', lang),
                                'url': sub.get('url', '')
                            })
                
                # Cleanup temp file
                if os.path.exists(temp_output):
                    os.remove(temp_output)
                
                logger.info(f"Successfully fetched video info via yt-dlp: {video_info['title']}")
                return video_info
            else:
                logger.error(f"yt-dlp failed: {result.stderr}")
                return None
                
        except Exception as e:
            logger.error(f"Error in yt-dlp video info fetch: {e}")
            return None
    
    def extract_transcript_piped(self, video_id: str, instance_url: str) -> Optional[Dict]:
        """
        Extract transcript using Piped API (existing subtitles)
        """
        try:
            # First get video info to check for subtitles
            video_info = self.get_video_info_piped(video_id, instance_url)
            if not video_info or not video_info.get('subtitles'):
                return None
            
            # Look for English subtitles first
            target_subs = None
            for sub in video_info['subtitles']:
                if sub['code'] == 'en' or sub['code'].startswith('en'):
                    target_subs = sub
                    break
            
            # If no English, take first available
            if not target_subs and video_info['subtitles']:
                target_subs = video_info['subtitles'][0]
            
            if not target_subs:
                return None
            
            # Download subtitle content
            logger.info(f"Downloading subtitles from: {target_subs['url']}")
            response = self.session.get(target_subs['url'], timeout=10)
            
            if response.status_code == 200:
                transcript_data = self._parse_subtitle_content(
                    response.text, 
                    target_subs['code']
                )
                
                if transcript_data:
                    transcript_data['source'] = 'piped_subtitles'
                    transcript_data['language'] = target_subs['code']
                    transcript_data['subtitle_name'] = target_subs.get('name', '')
                    transcript_data['piped_instance'] = instance_url
                    
                    logger.info(f"Successfully extracted transcript via Piped ({len(transcript_data['sentences'])} sentences)")
                    return transcript_data
            
            return None
            
        except Exception as e:
            logger.error(f"Error extracting transcript via Piped: {e}")
            return None
    
    def extract_transcript_ytdlp(self, video_id: str) -> Optional[Dict]:
        """
        Extract transcript using yt-dlp auto-generated subtitles
        """
        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
            
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--skip-download',
                '--sub-lang', 'en',  # Try English first
                '--convert-subs', 'srt',
                '--output', output_template,
                '--no-warnings',
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            
            logger.info(f"Running yt-dlp for auto-subtitles: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            if result.returncode == 0:
                # Look for generated subtitle files
                subtitle_files = []
                for ext in ['srt', 'vtt', 'ass', 'lrc']:
                    subtitle_files.extend([f for f in os.listdir(temp_dir) if f.endswith(f'.{ext}')])
                
                if subtitle_files:
                    subtitle_file = os.path.join(temp_dir, subtitle_files[0])
                    
                    with open(subtitle_file, 'r', encoding='utf-8') as f:
                        subtitle_content = f.read()
                    
                    transcript_data = self._parse_subtitle_content(
                        subtitle_content,
                        'en'
                    )
                    
                    if transcript_data:
                        transcript_data['source'] = 'yt_dlp_auto_sub'
                        transcript_data['language'] = 'en'
                        transcript_data['file_format'] = os.path.splitext(subtitle_file)[1][1:]
                        
                        logger.info(f"Successfully extracted auto-subtitles via yt-dlp ({len(transcript_data['sentences'])} sentences)")
                        
                        # Cleanup temp directory
                        cleanup_temp_files(temp_dir)
                        
                        return transcript_data
            
            # Cleanup temp directory
            cleanup_temp_files(temp_dir)
            return None
            
        except Exception as e:
            logger.error(f"Error extracting transcript via yt-dlp: {e}")
            return None
    
    def download_and_transcribe_audio(self, video_id: str) -> Optional[Dict]:
        """
        Download audio and transcribe using Groq Whisper API
        """
        try:
            from transcript_processor import TranscriptProcessor
            
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            audio_file = os.path.join(temp_dir, f"audio_{video_id}.mp3")
            
            # Download audio using yt-dlp
            cmd_download = [
                'yt-dlp',
                '-f', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',  # Best quality
                '--output', audio_file,
                '--no-warnings',
                f"https://www.youtube.com/watch?v={video_id}"
            ]
            
            logger.info(f"Downloading audio: {' '.join(cmd_download)}")
            download_result = subprocess.run(cmd_download, capture_output=True, text=True, timeout=300)
            
            if download_result.returncode != 0:
                logger.error(f"Audio download failed: {download_result.stderr}")
                cleanup_temp_files(temp_dir)
                return None
            
            # Check if audio file exists and has content
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
                logger.error("Audio file not created or empty")
                cleanup_temp_files(temp_dir)
                return None
            
            # Transcribe using Groq Whisper
            logger.info(f"Transcribing audio file: {audio_file}")
            transcript_processor = TranscriptProcessor()
            transcript_data = transcript_processor.transcribe_with_groq(audio_file)
            
            if transcript_data:
                transcript_data['source'] = 'groq_whisper'
                transcript_data['language'] = 'en'
                transcript_data['audio_file_size'] = os.path.getsize(audio_file)
                
                logger.info(f"Successfully transcribed audio via Groq Whisper ({len(transcript_data.get('sentences', []))} sentences)")
            
            # Cleanup
            cleanup_temp_files(temp_dir)
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error in audio download and transcription: {e}")
            return None
    
    def extract_transcript(self, video_id: str) -> Optional[Dict]:
        """
        Extract transcript using 3-step fallback method
        
        1. Try Piped API (existing subtitles)
        2. Try yt-dlp auto-generated subtitles
        3. Download audio and transcribe with Groq Whisper
        """
        logger.info(f"Starting transcript extraction for video: {video_id}")
        
        # Step 1: Try Piped API
        logger.info("Step 1: Trying Piped API for existing subtitles...")
        for instance in config.PIPED_INSTANCES:
            transcript_data = self.extract_transcript_piped(video_id, instance)
            if transcript_data:
                return transcript_data
        
        # Step 2: Try yt-dlp auto-generated subtitles
        logger.info("Step 2: Trying yt-dlp auto-generated subtitles...")
        transcript_data = self.extract_transcript_ytdlp(video_id)
        if transcript_data:
            return transcript_data
        
        # Step 3: Download audio and transcribe
        logger.info("Step 3: Downloading audio and transcribing with Groq Whisper...")
        transcript_data = self.download_and_transcribe_audio(video_id)
        if transcript_data:
            return transcript_data
        
        logger.error("All transcript extraction methods failed")
        return None
    
    def _parse_subtitle_content(self, content: str, language: str) -> Dict:
        """
        Parse subtitle content (SRT/VTT format) into structured data
        """
        try:
            lines = content.split('\n')
            sentences = []
            current_sentence = None
            
            for line in lines:
                line = line.strip()
                
                if not line:
                    continue
                
                # Check for timestamp line (SRT: 00:00:10,000 --> 00:00:15,000)
                if '-->' in line:
                    if current_sentence:
                        sentences.append(current_sentence)
                    
                    # Parse timestamp
                    timestamp_parts = line.split('-->')
                    if len(timestamp_parts) == 2:
                        start_str = timestamp_parts[0].strip().replace(',', '.')
                        end_str = timestamp_parts[1].strip().split(' ')[0].replace(',', '.')
                        
                        start_time = self._timestamp_to_seconds(start_str)
                        end_time = self._timestamp_to_seconds(end_str)
                        
                        current_sentence = {
                            'text': '',
                            'start': start_time,
                            'end': end_time,
                            'words': []
                        }
                    continue
                
                # Skip SRT counter lines
                if line.isdigit():
                    continue
                
                # Skip VTT headers and metadata
                if line.startswith('WEBVTT') or line.startswith('NOTE') or \
                   line.startswith('Kind:') or line.startswith('Language:'):
                    continue
                
                # Add text to current sentence
                if current_sentence:
                    if current_sentence['text']:
                        current_sentence['text'] += ' ' + line
                    else:
                        current_sentence['text'] = line
            
            # Add the last sentence
                if current_sentence:
                    if current_sentence['text']:
                        current_sentence['text'] += ' ' + line
                    else:
                        current_sentence['text'] = line
            
            # Add the last sentence
            if current_sentence and current_sentence['text']:
                sentences.append(current_sentence)
            
            # Process words if needed
            for sentence in sentences:
                if sentence['text']:
                    words = sentence['text'].split()
                    word_duration = (sentence['end'] - sentence['start']) / max(len(words), 1)
                    
                    for i, word in enumerate(words):
                        word_start = sentence['start'] + (i * word_duration)
                        word_end = word_start + word_duration
                        
                        sentence['words'].append({
                            'text': word,
                            'start': word_start,
                            'end': word_end
                        })
            
            return {
                'language': language,
                'sentences': sentences,
                'total_duration': sentences[-1]['end'] if sentences else 0,
                'word_count': sum(len(s['text'].split()) for s in sentences),
                'sentence_count': len(sentences)
            }
            
        except Exception as e:
            logger.error(f"Error parsing subtitle content: {e}")
            return {'sentences': [], 'language': language, 'error': str(e)}
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """
        Convert timestamp string to seconds
        
        Formats supported:
        - HH:MM:SS.mmm
        - MM:SS.mmm
        - SS.mmm
        """
        try:
            parts = timestamp.replace(',', '.').split(':')
            
            if len(parts) == 3:  # HH:MM:SS.mmm
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = float(parts[2])
                return hours * 3600 + minutes * 60 + seconds
            elif len(parts) == 2:  # MM:SS.mmm
                minutes = int(parts[0])
                seconds = float(parts[1])
                return minutes * 60 + seconds
            else:  # SS.mmm
                return float(parts[0])
        except:
            return 0.0
    
    def process_youtube_video(self, video_url: str) -> Dict:
        """
        Complete YouTube video processing pipeline
        
        Returns:
            Dictionary with video info and transcript data
        """
        start_time = time.time()
        logger.info(f"Processing YouTube video: {video_url}")
        
        # Extract video ID
        video_id = self.extract_video_id(video_url)
        if not video_id:
            return {
                'success': False,
                'error': 'Invalid YouTube URL',
                'video_url': video_url
            }
        
        # Get video information
        video_info = self.get_video_info(video_id)
        if not video_info:
            return {
                'success': False,
                'error': 'Could not fetch video information',
                'video_id': video_id
            }
        
        # Check if video is too long
        if video_info['duration'] > config.MAX_VIDEO_DURATION:
            return {
                'success': False,
                'error': f'Video too long (max {config.MAX_VIDEO_DURATION // 3600} hours allowed)',
                'video_id': video_id,
                'duration': video_info['duration']
            }
        
        # Extract transcript
        transcript_data = self.extract_transcript(video_id)
        
        # Prepare response
        processing_time = time.time() - start_time
        
        result = {
            'success': True,
            'video_id': video_id,
            'video_url': video_url,
            'video_info': video_info,
            'transcript': transcript_data,
            'processing_time': processing_time,
            'transcript_available': bool(transcript_data),
            'timestamp': datetime.now().isoformat()
        }
        
        if transcript_data:
            result['transcript_source'] = transcript_data.get('source', 'unknown')
            result['sentence_count'] = len(transcript_data.get('sentences', []))
            result['word_count'] = sum(len(s['text'].split()) for s in transcript_data.get('sentences', []))
        
        logger.info(f"YouTube video processing completed in {processing_time:.2f} seconds")
        return result


# Singleton instance for easy access
youtube_processor = YouTubeProcessor()
