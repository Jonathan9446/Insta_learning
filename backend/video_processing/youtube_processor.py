"""
YouTube Processor
3-tier transcript extraction: Piped API → yt-dlp → Groq Whisper
"""

import os
import re
import subprocess
import tempfile
import requests
from typing import Dict, List, Optional
from urllib.parse import urlparse, parse_qs

from backend.config import config
from backend.utils.logger import setup_logger
from backend.utils.helpers import cleanup_temp_files

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class YouTubeProcessor:
    """Process YouTube videos with 3-tier fallback system"""
    
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.piped_instances = config.PIPED_INSTANCES
    
    def extract_video_id(self, url: str) -> Optional[str]:
        """Extract YouTube video ID from URL"""
        patterns = [
            r'(?:https?:\/\/)?(?:www\.)?(?:youtube\.com\/watch\?v=|youtu\.be\/)([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/embed\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/shorts\/([a-zA-Z0-9_-]{11})',
            r'(?:https?:\/\/)?(?:www\.)?youtube\.com\/v\/([a-zA-Z0-9_-]{11})'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, url)
            if match:
                return match.group(1)
        
        # Try query parameters
        parsed = urlparse(url)
        if parsed.netloc in ['youtube.com', 'www.youtube.com', 'm.youtube.com']:
            query_params = parse_qs(parsed.query)
            if 'v' in query_params:
                return query_params['v'][0]
        
        return None
    
    def get_video_info_piped(self, video_id: str, instance_url: str) -> Optional[Dict]:
        """Get video info from Piped API"""
        try:
            endpoint = f"{instance_url}/streams/{video_id}"
            logger.info(f"🔍 Trying Piped: {instance_url}")
            
            response = self.session.get(endpoint, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                
                video_info = {
                    'id': video_id,
                    'title': data.get('title', ''),
                    'description': data.get('description', ''),
                    'duration': data.get('duration', 0),
                    'thumbnail': data.get('thumbnailUrl', ''),
                    'uploader': data.get('uploader', ''),
                    'views': data.get('views', 0),
                    'subtitles': data.get('subtitles', []),
                    'source': 'piped'
                }
                
                logger.info(f"✅ Piped success: {video_info['title']}")
                return video_info
            
            return None
            
        except Exception as e:
            logger.warning(f"⚠️ Piped instance failed: {e}")
            return None
    
    def get_video_info(self, video_id: str) -> Optional[Dict]:
        """Get video info with Piped fallback"""
        # Try each Piped instance
        for instance in self.piped_instances:
            video_info = self.get_video_info_piped(video_id, instance)
            if video_info:
                return video_info
        
        logger.warning("⚠️ All Piped instances failed")
        return None
    
    def extract_transcript_piped(self, video_id: str, instance_url: str) -> Optional[Dict]:
        """STEP 1: Extract transcript from Piped API"""
        try:
            video_info = self.get_video_info_piped(video_id, instance_url)
            
            if not video_info or not video_info.get('subtitles'):
                return None
            
            # Find English subtitles
            target_sub = None
            for sub in video_info['subtitles']:
                if sub.get('code', '').startswith('en'):
                    target_sub = sub
                    break
            
            if not target_sub and video_info['subtitles']:
                target_sub = video_info['subtitles'][0]
            
            if not target_sub:
                return None
            
            # Download subtitle
            logger.info(f"📥 Downloading subtitles from Piped...")
            sub_response = self.session.get(target_sub['url'], timeout=10)
            
            if sub_response.status_code == 200:
                transcript_data = self._parse_subtitle_content(sub_response.text)
                transcript_data['source'] = 'piped_api'
                transcript_data['language'] = target_sub.get('code', 'en')
                
                logger.info(f"✅ Piped transcript: {len(transcript_data['segments'])} segments")
                return transcript_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Piped transcript error: {e}")
            return None
    
    def extract_transcript_ytdlp(self, video_id: str) -> Optional[Dict]:
        """STEP 2: Extract transcript using yt-dlp"""
        try:
            temp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.info("🔍 Trying yt-dlp auto-subtitles...")
            
            cmd = [
                'yt-dlp',
                '--write-auto-sub',
                '--write-sub',
                '--skip-download',
                '--sub-lang', 'en',
                '--convert-subs', 'srt',
                '--output', os.path.join(temp_dir, f'temp_yt_{video_id}'),
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
                
                transcript_data = self._parse_subtitle_content(srt_content)
                transcript_data['source'] = 'yt-dlp'
                transcript_data['language'] = 'en'
                
                logger.info(f"✅ yt-dlp transcript: {len(transcript_data['segments'])} segments")
                
                cleanup_temp_files(temp_dir)
                return transcript_data
            
            cleanup_temp_files(temp_dir)
            return None
            
        except Exception as e:
            logger.error(f"❌ yt-dlp error: {e}")
            return None
    
    def transcribe_audio_groq(self, video_id: str) -> Optional[Dict]:
        """STEP 3: Download audio and transcribe with Groq Whisper"""
        try:
            from backend.video_processing.transcript_processor import transcript_processor
            
            temp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
            audio_file = os.path.join(temp_dir, f"audio_{video_id}.mp3")
            video_url = f"https://www.youtube.com/watch?v={video_id}"
            
            logger.info("📥 Downloading audio with yt-dlp...")
            
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
            
            # Transcribe with Groq
            logger.info("🎙️ Transcribing with Groq Whisper...")
            transcript_data = transcript_processor.transcribe_with_groq(audio_file)
            
            cleanup_temp_files(temp_dir)
            
            if transcript_data and transcript_data.get('success'):
                logger.info(f"✅ Groq transcription: {len(transcript_data.get('segments', []))} segments")
                return transcript_data
            
            return None
            
        except Exception as e:
            logger.error(f"❌ Groq transcription error: {e}")
            return None
    
    def get_transcript(self, video_id: str) -> Optional[Dict]:
        """3-tier transcript extraction"""
        logger.info(f"🎬 Getting transcript for: {video_id}")
        
        # STEP 1: Try Piped API
        logger.info("━━━ STEP 1: Piped API ━━━")
        for instance in self.piped_instances:
            transcript = self.extract_transcript_piped(video_id, instance)
            if transcript:
                return transcript
        
        # STEP 2: Try yt-dlp
        logger.info("━━━ STEP 2: yt-dlp ━━━")
        transcript = self.extract_transcript_ytdlp(video_id)
        if transcript:
            return transcript
        
        # STEP 3: Groq Whisper
        logger.info("━━━ STEP 3: Groq Whisper ━━━")
        transcript = self.transcribe_audio_groq(video_id)
        if transcript:
            return transcript
        
        logger.error("❌ All transcript methods failed")
        return None
    
    def _parse_subtitle_content(self, content: str) -> Dict:
        """Parse SRT/VTT to structured format"""
        try:
            lines = content.split('\n')
            segments = []
            current_segment = None
            
            for line in lines:
                line = line.strip()
                
                if not line or line.isdigit():
                    continue
                
                # Timestamp line
                if '-->' in line:
                    if current_segment and current_segment.get('text'):
                        segments.append(current_segment)
                    
                    parts = line.split('-->')
                    if len(parts) == 2:
                        start = self._timestamp_to_seconds(parts[0].strip())
                        end = self._timestamp_to_seconds(parts[1].strip().split()[0])
                        
                        current_segment = {
                            'start': start,
                            'end': end,
                            'text': '',
                            'words': []
                        }
                    continue
                
                # Skip headers
                if line.startswith('WEBVTT') or line.startswith('NOTE'):
                    continue
                
                # Text content
                if current_segment is not None:
                    if current_segment['text']:
                        current_segment['text'] += ' ' + line
                    else:
                        current_segment['text'] = line
            
            # Add last segment
            if current_segment and current_segment.get('text'):
                segments.append(current_segment)
            
            # Generate word timings
            for segment in segments:
                if segment['text']:
                    words = segment['text'].split()
                    duration = (segment['end'] - segment['start']) / max(len(words), 1)
                    
                    for i, word in enumerate(words):
                        segment['words'].append({
                            'text': word,
                            'start': segment['start'] + i * duration,
                            'end': segment['start'] + (i + 1) * duration
                        })
            
            return {
                'segments': segments,
                'duration': segments[-1]['end'] if segments else 0,
                'language': 'en'
            }
            
        except Exception as e:
            logger.error(f"❌ Parse error: {e}")
            return {'segments': [], 'duration': 0, 'language': 'en'}
    
    def _timestamp_to_seconds(self, timestamp: str) -> float:
        """Convert timestamp to seconds"""
        try:
            parts = timestamp.replace(',', '.').split(':')
            
            if len(parts) == 3:
                h, m, s = parts
                return int(h) * 3600 + int(m) * 60 + float(s)
            elif len(parts) == 2:
                m, s = parts
                return int(m) * 60 + float(s)
            else:
                return float(parts[0])
        except:
            return 0.0
    
    def process_video(self, video_url: str) -> Dict:
        """Complete YouTube processing pipeline"""
        try:
            video_id = self.extract_video_id(video_url)
            
            if not video_id:
                return {
                    'success': False,
                    'error': 'Invalid YouTube URL'
                }
            
            # Get video info
            video_info = self.get_video_info(video_id)
            
            if not video_info:
                return {
                    'success': False,
                    'error': 'Could not fetch video information'
                }
            
            # Get transcript
            transcript = self.get_transcript(video_id)
            
            return {
                'success': True,
                'video_id': video_id,
                'video_url': video_url,
                'platform': 'youtube',
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
youtube_processor = YouTubeProcessor()
