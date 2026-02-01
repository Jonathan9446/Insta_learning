"""
Facebook Video Processor
Handles Facebook video extraction and processing
"""

import os
import re
import json
import time
import hashlib
import subprocess
import tempfile
from typing import Dict, List, Optional, Any
from datetime import datetime

import requests
from urllib.parse import urlparse, parse_qs

from config import config
from utils.helpers import cleanup_temp_files
from utils.logger import setup_logger
from transcript_processor import TranscriptProcessor

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

class FacebookProcessor:
    """Main Facebook video processing class"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate, br',
            'DNT': '1',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })
        self.temp_dir = config.TEMP_DIR
        
        # Facebook App credentials (from environment)
        self.facebook_app_id = os.getenv('FACEBOOK_APP_ID')
        self.facebook_app_secret = os.getenv('FACEBOOK_APP_SECRET')
        self.facebook_access_token = os.getenv('FACEBOOK_ACCESS_TOKEN')
        
    def extract_video_id(self, url: str) -> Optional[str]:
        """
        Extract Facebook video ID from various URL formats
        
        Supported formats:
        - https://www.facebook.com/username/videos/VIDEO_ID/
        - https://www.facebook.com/watch/?v=VIDEO_ID
        - https://www.facebook.com/video.php?v=VIDEO_ID
        - https://fb.watch/VIDEO_ID/
        - https://www.facebook.com/VIDEO_ID
        """
        patterns = [
            # Facebook watch page
            r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/watch\/\?v=(\d+)',
            # Facebook video page
            r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/[^\/]+\/videos\/(\d+)',
            # Facebook video.php
            r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/video\.php\?v=(\d+)',
            # fb.watch short URL
            r'(?:https?:\/\/)?fb\.watch\/([a-zA-Z0-9]+)',
            # Direct video ID
            r'(?:https?:\/\/)?(?:www\.)?facebook\.com\/(\d+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try to extract from query parameters
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        
        if 'v' in query_params:
            return query_params['v'][0]
        
        return None
    
    def get_video_info_graph_api(self, video_id: str) -> Optional[Dict]:
        """
        Get video information using Facebook Graph API
        """
        if not self.facebook_access_token:
            logger.warning("Facebook access token not configured")
            return None
        
        try:
            # Graph API endpoint for video
            graph_url = f"https://graph.facebook.com/v18.0/{video_id}"
            
            params = {
                'access_token': self.facebook_access_token,
                'fields': 'id,title,description,embed_html,length,created_time,updated_time,permalink_url'
            }
            
            logger.info(f"Fetching video info from Facebook Graph API: {video_id}")
            response = self.session.get(graph_url, params=params, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                video_info = {
                    'id': data.get('id', ''),
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'duration': data.get('length', 0),
                    'embed_html': data.get('embed_html', ''),
                    'permalink_url': data.get('permalink_url', ''),
                    'created_time': data.get('created_time', ''),
                    'updated_time': data.get('updated_time', ''),
                    'source': 'facebook_graph_api'
                }
                
                logger.info(f"Successfully fetched Facebook video info: {video_info['id']}")
                return video_info
            else:
                logger.warning(f"Graph API returned {response.status_code}: {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching video info from Graph API: {e}")
            return None
    
    def get_video_info_alternative(self, video_url: str) -> Optional[Dict]:
        """
        Get video information using alternative methods (when Graph API is not available)
        """
        try:
            # Try to fetch video page and extract metadata
            logger.info(f"Fetching Facebook video page: {video_url}")
            response = self.session.get(video_url, timeout=10)
            
            if response.status_code == 200:
                html_content = response.text
                
                # Extract metadata from HTML
                video_info = {
                    'id': self.extract_video_id(video_url) or '',
                    'url': video_url,
                    'source': 'facebook_webpage',
                    'duration': 0,
                    'title': '',
                    'description': ''
                }
                
                # Extract title from meta tags
                title_patterns = [
                    r'<meta property="og:title" content="([^"]+)"',
                    r'<title>([^<]+)</title>'
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, html_content)
                    if match:
                        video_info['title'] = match.group(1)
                        break
                
                # Extract description from meta tags
                desc_pattern = r'<meta property="og:description" content="([^"]+)"'
                match = re.search(desc_pattern, html_content)
                if match:
                    video_info['description'] = match.group(1)
                
                # Extract video duration (if available in meta tags)
                duration_pattern = r'"video:duration" content="(\d+)"'
                match = re.search(duration_pattern, html_content)
                if match:
                    video_info['duration'] = int(match.group(1))
                
                logger.info(f"Extracted Facebook video info from webpage: {video_info['title'][:50]}...")
                return video_info
            else:
                logger.warning(f"Failed to fetch Facebook page: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"Error fetching video info from webpage: {e}")
            return None
    
    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """
        Get Facebook video information
        """
        video_id = self.extract_video_id(video_url)
        if not video_id:
            logger.error(f"Could not extract video ID from URL: {video_url}")
            return None
        
        # Try Graph API first
        video_info = self.get_video_info_graph_api(video_id)
        
        # If Graph API fails, try alternative method
        if not video_info:
            video_info = self.get_video_info_alternative(video_url)
        
        return video_info
    
    def extract_transcript_ytdlp(self, video_url: str) -> Optional[Dict]:
        """
        Extract transcript using yt-dlp for Facebook videos
        """
        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            output_template = os.path.join(temp_dir, '%(title)s.%(ext)s')
            
            # Try to get subtitles if available
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--write-sub',
                '--skip-download',
                '--sub-lang', 'en',  # Try English first
                '--convert-subs', 'srt',
                '--output', output_template,
                '--no-warnings',
                video_url
            ]
            
            logger.info(f"Running yt-dlp for Facebook video subtitles: {' '.join(cmd[:5])}...")
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
                    
                    # Parse subtitle content (similar to YouTube processor)
                    from youtube_processor import YouTubeProcessor
                    youtube_processor = YouTubeProcessor()
                    
                    transcript_data = youtube_processor._parse_subtitle_content(
                        subtitle_content,
                        'en'
                    )
                    
                    if transcript_data:
                        transcript_data['source'] = 'yt_dlp_facebook'
                        transcript_data['language'] = 'en'
                        transcript_data['file_format'] = os.path.splitext(subtitle_file)[1][1:]
                        
                        logger.info(f"Successfully extracted Facebook video subtitles via yt-dlp ({len(transcript_data['sentences'])} sentences)")
                        
                        # Cleanup temp directory
                        cleanup_temp_files(temp_dir)
                        
                        return transcript_data
            
            # Cleanup temp directory
            cleanup_temp_files(temp_dir)
            return None
            
        except Exception as e:
            logger.error(f"Error extracting transcript via yt-dlp for Facebook: {e}")
            return None
    
    def download_and_transcribe_audio(self, video_url: str) -> Optional[Dict]:
        """
        Download audio from Facebook video and transcribe
        """
        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            audio_file = os.path.join(temp_dir, "audio.mp3")
            
            # Download audio using yt-dlp
            cmd_download = [
                'yt-dlp',
                '-f', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', audio_file,
                '--no-warnings',
                video_url
            ]
            
            logger.info(f"Downloading Facebook video audio: {' '.join(cmd_download[:5])}...")
            download_result = subprocess.run(cmd_download, capture_output=True, text=True, timeout=300)
            
            if download_result.returncode != 0:
                logger.error(f"Facebook audio download failed: {download_result.stderr[:200]}")
                cleanup_temp_files(temp_dir)
                return None
            
            # Check if audio file exists
            if not os.path.exists(audio_file) or os.path.getsize(audio_file) == 0:
                logger.error("Facebook audio file not created or empty")
                cleanup_temp_files(temp_dir)
                return None
            
            # Transcribe using Groq Whisper
            logger.info("Transcribing Facebook audio with Groq Whisper...")
            transcript_processor = TranscriptProcessor()
            transcript_data = transcript_processor.transcribe_with_groq(audio_file)
            
            if transcript_data:
                transcript_data['source'] = 'groq_whisper_facebook'
                transcript_data['language'] = 'en'
                transcript_data['audio_file_size'] = os.path.getsize(audio_file)
                
                logger.info(f"Successfully transcribed Facebook audio ({len(transcript_data.get('sentences', []))} sentences)")
            
            # Cleanup
            cleanup_temp_files(temp_dir)
            
            return transcript_data
            
        except Exception as e:
            logger.error(f"Error in Facebook audio download and transcription: {e}")
            return None
    
    def extract_transcript(self, video_url: str) -> Optional[Dict]:
        """
        Extract transcript from Facebook video
        
        1. Try yt-dlp for existing subtitles
        2. Download audio and transcribe with Groq Whisper
        """
        logger.info(f"Starting transcript extraction for Facebook video")
        
        # Step 1: Try yt-dlp for subtitles
        logger.info("Step 1: Trying yt-dlp for Facebook video subtitles...")
        transcript_data = self.extract_transcript_ytdlp(video_url)
        if transcript_data:
            return transcript_data
        
        # Step 2: Download audio and transcribe
        logger.info("Step 2: Downloading audio and transcribing...")
        transcript_data = self.download_and_transcribe_audio(video_url)
        if transcript_data:
            return transcript_data
        
        logger.error("All Facebook transcript extraction methods failed")
        return None
    
    def generate_embed_code(self, video_id: str, video_info: Dict) -> str:
        """
        Generate Facebook video embed code
        """
        if video_info.get('embed_html'):
            return video_info['embed_html']
        
        # Fallback embed code
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
        
        return embed_code
    
    def process_facebook_video(self, video_url: str) -> Dict:
        """
        Complete Facebook video processing pipeline
        """
        start_time = time.time()
        logger.info(f"Processing Facebook video: {video_url}")
        
        # Get video information
        video_info = self.get_video_info(video_url)
        if not video_info:
            return {
                'success': False,
                'error': 'Could not fetch Facebook video information',
                'video_url': video_url
            }
        
        video_id = video_info.get('id', '')
        
        # Check if video is too long
        if video_info.get('duration', 0) > config.MAX_VIDEO_DURATION:
            return {
                'success': False,
                'error': f'Video too long (max {config.MAX_VIDEO_DURATION // 3600} hours allowed)',
                'video_id': video_id,
                'duration': video_info.get('duration', 0)
            }
        
        # Extract transcript
        transcript_data = self.extract_transcript(video_url)
        
        # Generate embed code
        embed_code = self.generate_embed_code(video_id, video_info)
        
        # Prepare response
        processing_time = time.time() - start_time
        
        result = {
            'success': True,
            'video_id': video_id,
            'video_url': video_url,
            'video_info': video_info,
            'embed_code': embed_code,
            'transcript': transcript_data,
            'processing_time': processing_time,
            'transcript_available': bool(transcript_data),
            'timestamp': datetime.now().isoformat(),
            'platform': 'facebook'
        }
        
        if transcript_data:
            result['transcript_source'] = transcript_data.get('source', 'unknown')
            result['sentence_count'] = len(transcript_data.get('sentences', []))
            result['word_count'] = sum(len(s['text'].split()) for s in transcript_data.get('sentences', []))
        
        logger.info(f"Facebook video processing completed in {processing_time:.2f} seconds")
        return result


# Singleton instance for easy access
facebook_processor = FacebookProcessor()
