"""
Facebook Processor
2-tier extraction: yt-dlp subtitles → Groq Whisper transcription
"""

import os
import re
import subprocess
import tempfile
import requests
from typing import Dict, Optional
from urllib.parse import urlparse, parse_qs

from backend.config import config
from backend.utils.logger import setup_logger
from backend.utils.helpers import cleanup_temp_files

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class FacebookProcessor:
    """Process Facebook videos"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract Facebook video ID"""
        patterns = [
            r'facebook\.com\/[^\/]+\/videos\/(\d+)',
            r'facebook\.com\/watch\/\?v=(\d+)',
            r'facebook\.com\/video\.php\?v=(\d+)',
            r'fb\.watch\/([a-zA-Z0-9]+)'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try query params
        parsed = urlparse(url)
        query_params = parse_qs(parsed.query)
        if 'v' in query_params:
            return query_params['v'][0]
        
        return None
    
    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """Get Facebook video info"""
        try:
            logger.info(f"📥 Fetching Facebook video info...")
            
            response = self.session.get(video_url, timeout=10)
            
            if response.status_code == 200:
                html = response.text
                
                video_info = {
                    'id': self.extract_video_id(video_url) or '',
                    'url': video_url,
                    'title': '',
                    'description': '',
                    'source': 'facebook'
                }
                
                # Extract title
                title_patterns = [
                    r'<meta property="og:title" content="([^"]+)"',
                    r'<title>([^<]+)</title>'
                ]
                
                for pattern in title_patterns:
                    match = re.search(pattern, html)
                    if match:
                        video_info['title'] = match.group(1)
                        break
                
                # Extract description
                desc_pattern = r'<meta property="og:description" content="([^"]+)"'
                match = re.search(desc_pattern, html)
                if match:
                    video_info['description'] = match.group(1)
                
                logger.info(f"✅ Video info: {video_info['title'][:50]}...")
                return video_info
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Error fetching video info: {e}")
            return None
    
    def extract_transcript_ytdlp(self, video_url: str) -> Optional[Dict]:
        """STEP 1: Try yt-dlp for subtitles"""
        try:
            temp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
            
            logger.info("🔍 Checking for Facebook subtitles with yt-dlp...")
            
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--write-sub',
                '--skip-download',
                '--sub-lang', 'en',
                '--convert-subs', 'srt',
                '--output', os.path.join(temp_dir, 'temp_fb'),
                '--no-warnings',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=60)
            
            # Find subtitle files
            subtitle_files = [f for f in os.listdir(temp_dir) if f.endswith('.srt')]
            
            if subtitle_files:
                subtitle_path = os.path.join(temp_dir, subtitle_files[0])
                
                with open(subtitle_path, 'r', encoding='utf-8') as f:
                    srt_content = f.read()
                
                transcript_data = self._parse_srt(srt_content)
                transcript_data['source'] = 'yt-dlp'
                transcript_data['language'] = 'en'
                
                logger.info(f"✅ yt-dlp subtitles: {len(transcript_data['segments'])} segments")
                
                cleanup_temp_files(temp_dir)
                return transcript_data
            
            cleanup_temp_files(temp_dir)
            return None
            
        except Exception as e:
            logger.error(f"❌ yt-dlp error: {e}")
            return None
    
    def transcribe_audio_groq(self, video_url: str) -> Optional[Dict]:
        """STEP 2: Download audio and transcribe with Groq"""
        try:
            from backend.video_processing.transcript_processor import transcript_processor
            
            temp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
            audio_file = os.path.join(temp_dir, "audio_fb.mp3")
            
            logger.info("📥 Downloading Facebook audio...")
            
            cmd = [
                'yt-dlp',
                '-f', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',
                '--output', audio_file,
                '--no-warnings',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode != 0 or not os.path.exists(audio_file):
                logger.error("❌ Audio download failed")
                cleanup_temp_files(temp_dir)
                return None
            
            logger.info(f"✅ Audio downloaded: {os.path.getsize(audio_file) / 1024 / 1024:.2f} MB")
            
            # Transcribe
            logger.info("🎙️ Transcribing with Groq Whisper...")
            transcript_data = transcript_processor.transcribe_with_groq(audio_file)
            
            cleanup_temp_files(temp_dir)
            
            if transcript_data and transcript_data.get('success'):
                logger.info(f"✅ Groq transcription: {len(transcript_data.get('segments', []))} segments")
                return transcript_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Groq error: {e}")
            return None
    
    def get_transcript(self, video_url: str) -> Optional[Dict]:
        """2-tier transcript extraction"""
        logger.info("🎬 Getting Facebook transcript...")
        
        # STEP 1: Try yt-dlp
        logger.info("━━━ STEP 1: yt-dlp ━━━")
        transcript = self.extract_transcript_ytdlp(video_url)
        if transcript:
            return transcript
        
        # STEP 2: Groq Whisper
        logger.info("━━━ STEP 2: Groq Whisper ━━━")
        transcript = self.transcribe_audio_groq(video_url)
        if transcript:
            return transcript
        
        logger.error("❌ All transcript methods failed")
        return None
    
    def _parse_srt(self, content: str) -> Dict:
        """Parse SRT content"""
        try:
            lines = content.split('\n')
            segments = []
            current_segment = None
            
            for line in lines:
                line = line.strip()
                
                if not line or line.isdigit():
                    continue
                
                if '-->' in line:
                    if current_segment and current_segment.get('text'):
                        segments.append(current_segment)
                    
                    parts = line.split('-->')
                    if len(parts) == 2:
                        start = self._timestamp_to_seconds(parts[0].strip())
                        end = self._timestamp_to_seconds(parts[1].strip())
                        
                        current_segment = {
                            'start': start,
                            'end': end,
                            'text': '',
                            'words': []
                        }
                    continue
                
                if current_segment is not None:
                    if current_segment['text']:
                        current_segment['text'] += ' ' + line
                    else:
                        current_segment['text'] = line
            
            if current_segment and current_segment.get('text'):
                segments.append(current_segment)
            
            return {
                'segments': segments,
                'duration': segments[-1]['end'] if segments else 0,
                'language': 'en'
            }
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return {'segments': [], 'duration': 0}
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp to seconds"""
        try:
            parts = timestamp.replace(',', '.').split(':')
            
            if len(parts) == 3:
                return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
            elif len(parts) == 2:
                return int(parts[0]) * 60 + float(parts[1])
            else:
                return float(parts[0])
        except:
            return 0.0
    
    def process_video(self, video_url: str) -> Dict:
        """Complete Facebook processing"""
        try:
            video_id = self.extract_video_id(video_url)
            
            # Get video info
            video_info = self.get_video_info(video_url)
            
            if not video_info:
                return {
                    'success': False,
                    'error': 'Could not fetch video information'
                }
            
            # Get transcript
            transcript = self.get_transcript(video_url)
            
            return {
                'success': True,
                'video_id': video_id or '',
                'video_url': video_url,
                'platform': 'facebook',
                'video_info': video_info,
                'transcript': transcript,
                'transcript_available': bool(transcript)
            }
            
        except Exception as e:
            logger.error(f"❌ Processing error: {e}")
            return {
                'success': False,
                'error': str(e)
            }


# Global instance
facebook_processor = FacebookProcessor()
