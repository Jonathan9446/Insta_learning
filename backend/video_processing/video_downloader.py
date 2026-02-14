"""
Video Downloader Module
Handles video/audio downloading using yt-dlp
"""

import os
import json
import subprocess
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from pathlib import Path

from config import config
from utils.helpers import cleanup_temp_files
from utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

class VideoDownloader:
    """Handles downloading of videos and audio using yt-dlp"""
    
    def __init__(self):
        self.temp_dir = config.TEMP_DIR
        os.makedirs(self.temp_dir, exist_ok=True)
        
        # Check if yt-dlp is available
        self.ytdlp_available = self._check_ytdlp()
        
    def _check_ytdlp(self) -> bool:
        """Check if yt-dlp is installed and available"""
        try:
            result = subprocess.run(['yt-dlp', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            logger.error(f"yt-dlp check failed: {e}")
            return False
    
    def get_video_info(self, video_url: str) -> Optional[Dict]:
        """
        Get detailed video information using yt-dlp
        """
        if not self.ytdlp_available:
            logger.error("yt-dlp is not available")
            return None
        
        try:
            temp_output = os.path.join(self.temp_dir, f"info_{hash(video_url)}.json")
            
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--no-warnings',
                '--ignore-errors',
                '-o', temp_output,
                video_url
            ]
            
            logger.info(f"Getting video info: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0:
                if os.path.exists(temp_output):
                    with open(temp_output, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # Cleanup temp file
                    os.remove(temp_output)
                    
                    # Extract relevant information
                    video_info = {
                        'id': data.get('id', ''),
                        'title': data.get('title', ''),
                        'description': data.get('description', ''),
                        'duration': data.get('duration', 0),
                        'thumbnail': data.get('thumbnail', ''),
                        'uploader': data.get('uploader', ''),
                        'upload_date': data.get('upload_date', ''),
                        'view_count': data.get('view_count', 0),
                        'like_count': data.get('like_count', 0),
                        'comment_count': data.get('comment_count', 0),
                        'categories': data.get('categories', []),
                        'tags': data.get('tags', []),
                        'formats': [],
                        'subtitles': [],
                        'automatic_captions': {},
                        'webpage_url': data.get('webpage_url', ''),
                        'extractor': data.get('extractor', ''),
                        'extractor_key': data.get('extractor_key', '')
                    }
                    
                    # Extract available formats (limited to first 10)
                    if 'formats' in data:
                        video_info['formats'] = [
                            {
                                'format_id': fmt.get('format_id', ''),
                                'ext': fmt.get('ext', ''),
                                'resolution': fmt.get('resolution', ''),
                                'filesize': fmt.get('filesize', 0),
                                'format_note': fmt.get('format_note', ''),
                                'vcodec': fmt.get('vcodec', ''),
                                'acodec': fmt.get('acodec', ''),
                                'abr': fmt.get('abr', 0),
                                'tbr': fmt.get('tbr', 0),
                                'fps': fmt.get('fps', 0)
                            }
                            for fmt in data['formats'][:10]
                        ]
                    
                    # Extract subtitles
                    if 'subtitles' in data:
                        for lang, subs in data['subtitles'].items():
                            for sub in subs:
                                video_info['subtitles'].append({
                                    'lang': lang,
                                    'name': sub.get('name', lang),
                                    'url': sub.get('url', ''),
                                    'ext': sub.get('ext', '')
                                })
                    
                    # Extract automatic captions
                    if 'automatic_captions' in data:
                        video_info['automatic_captions'] = data['automatic_captions']
                    
                    logger.info(f"Successfully extracted video info: {video_info['title'][:50]}...")
                    return video_info
                else:
                    logger.error(f"Output file not created: {temp_output}")
                    return None
            else:
                logger.error(f"yt-dlp info extraction failed: {result.stderr[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting video info: {e}")
            return None
    
    def download_audio(self, video_url: str, output_path: str = None) -> Optional[str]:
        """
        Download audio from video URL
        
        Args:
            video_url: URL of the video
            output_path: Custom output path (optional)
            
        Returns:
            Path to downloaded audio file or None
        """
        if not self.ytdlp_available:
            logger.error("yt-dlp is not available")
            return None
        
        try:
            if not output_path:
                # Create temp directory for audio
                temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
                output_path = os.path.join(temp_dir, 'audio.%(ext)s')
            
            cmd = [
                'yt-dlp',
                '-f', 'bestaudio',
                '--extract-audio',
                '--audio-format', 'mp3',
                '--audio-quality', '0',  # Best quality
                '--no-playlist',
                '--no-warnings',
                '--ignore-errors',
                '--output', output_path,
                video_url
            ]
            
            logger.info(f"Downloading audio: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
            
            if result.returncode == 0:
                # Find the downloaded file
                output_dir = os.path.dirname(output_path)
                audio_files = list(Path(output_dir).glob("*.mp3"))
                
                if audio_files:
                    audio_file = str(audio_files[0])
                    file_size = os.path.getsize(audio_file)
                    
                    logger.info(f"Audio downloaded successfully: {audio_file} ({file_size / 1024 / 1024:.2f} MB)")
                    return audio_file
                else:
                    logger.error(f"No audio file found in {output_dir}")
                    return None
            else:
                logger.error(f"Audio download failed: {result.stderr[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading audio: {e}")
            return None
    
    def download_video(self, video_url: str, output_path: str = None, 
                      quality: str = 'best') -> Optional[str]:
        """
        Download video file
        
        Args:
            video_url: URL of the video
            output_path: Custom output path (optional)
            quality: Video quality (best, worst, 720p, 480p, etc.)
            
        Returns:
            Path to downloaded video file or None
        """
        if not self.ytdlp_available:
            logger.error("yt-dlp is not available")
            return None
        
        try:
            if not output_path:
                # Create temp directory for video
                temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
                output_path = os.path.join(temp_dir, 'video.%(ext)s')
            
            cmd = [
                'yt-dlp',
                '-f', quality,
                '--no-playlist',
                '--no-warnings',
                '--ignore-errors',
                '--merge-output-format', 'mp4',
                '--output', output_path,
                video_url
            ]
            
            logger.info(f"Downloading video: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
            
            if result.returncode == 0:
                # Find the downloaded file
                output_dir = os.path.dirname(output_path)
                video_files = list(Path(output_dir).glob("*.mp4"))
                
                if not video_files:
                    video_files = list(Path(output_dir).glob("*.*"))
                
                if video_files:
                    video_file = str(video_files[0])
                    file_size = os.path.getsize(video_file)
                    
                    logger.info(f"Video downloaded successfully: {video_file} ({file_size / 1024 / 1024:.2f} MB)")
                    return video_file
                else:
                    logger.error(f"No video file found in {output_dir}")
                    return None
            else:
                logger.error(f"Video download failed: {result.stderr[:200]}")
                return None
                
        except Exception as e:
            logger.error(f"Error downloading video: {e}")
            return None
    
    def extract_subtitles(self, video_url: str, languages: List[str] = None) -> Dict[str, str]:
        """
        Extract subtitles from video
        
        Args:
            video_url: URL of the video
            languages: List of language codes to extract (default: ['en'])
            
        Returns:
            Dictionary with language codes as keys and subtitle content as values
        """
        if not self.ytdlp_available:
            logger.error("yt-dlp is not available")
            return {}
        
        if languages is None:
            languages = ['en']
        
        try:
            temp_dir = tempfile.mkdtemp(dir=self.temp_dir)
            output_template = os.path.join(temp_dir, 'subtitles')
            
            # Build command for subtitle extraction
            cmd = [
                'yt-dlp',
                '--write-sub',
                '--write-auto-sub',
                '--skip-download',
                '--no-playlist',
                '--no-warnings',
                '--ignore-errors',
                '--convert-subs', 'srt',
                '--output', output_template,
                video_url
            ]
            
            # Add language options
            for lang in languages:
                cmd.extend(['--sub-lang', lang])
            
            logger.info(f"Extracting subtitles: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            
            subtitles = {}
            
            if result.returncode == 0:
                # Look for subtitle files
                for ext in ['srt', 'vtt', 'ass', 'lrc']:
                    for file_path in Path(temp_dir).glob(f"*.{ext}"):
                        # Extract language from filename
                        filename = file_path.stem
                        lang_match = None
                        
                        # Try to extract language code (e.g., .en.srt)
                        for lang in languages:
                            if f'.{lang}.' in filename or filename.endswith(f'.{lang}'):
                                lang_match = lang
                                break
                        
                        if not lang_match:
                            # Default to first language or 'en'
                            lang_match = languages[0] if languages else 'en'
                        
                        # Read subtitle content
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                        
                        subtitles[lang_match] = content
                        logger.info(f"Extracted {lang_match} subtitles: {len(content)} characters")
                
                # Cleanup temp directory
                cleanup_temp_files(temp_dir)
                
                return subtitles
            else:
                logger.error(f"Subtitle extraction failed: {result.stderr[:200]}")
                cleanup_temp_files(temp_dir)
                return {}
                
        except Exception as e:
            logger.error(f"Error extracting subtitles: {e}")
            return {}
    
    def get_available_formats(self, video_url: str) -> List[Dict]:
        """
        Get list of available formats for a video
        """
        if not self.ytdlp_available:
            logger.error("yt-dlp is not available")
            return []
        
        try:
            cmd = [
                'yt-dlp',
                '--list-formats',
                '--no-playlist',
                '--no-warnings',
                video_url
            ]
            
            logger.info(f"Listing available formats: {' '.join(cmd[:5])}...")
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
            
            formats = []
            
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                in_formats_section = False
                
                for line in lines:
                    if 'format code' in line and 'extension' in line:
                        in_formats_section = True
                        continue
                    
                    if in_formats_section and line.strip():
                        # Parse format line
                        parts = line.split()
                        if len(parts) >= 5:
                            format_info = {
                                'format_id': parts[0],
                                'extension': parts[1],
                                'resolution': parts[2],
                                'note': ' '.join(parts[3:]) if len(parts) > 3 else ''
                            }
                            formats.append(format_info)
            
            logger.info(f"Found {len(formats)} available formats")
            return formats
            
        except Exception as e:
            logger.error(f"Error getting available formats: {e}")
            return []
    
    def check_url_supported(self, video_url: str) -> Tuple[bool, str]:
        """
        Check if a URL is supported by yt-dlp
        
        Returns:
            Tuple of (is_supported, platform_name)
        """
        if not self.ytdlp_available:
            return False, "yt-dlp not available"
        
        try:
            cmd = [
                'yt-dlp',
                '--dump-json',
                '--no-playlist',
                '--ignore-errors',
                '--simulate',
                video_url
            ]
            
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                # Try to parse JSON to get extractor info
                try:
                    data = json.loads(result.stdout)
                    extractor = data.get('extractor', 'generic')
                    extractor_key = data.get('extractor_key', 'generic')
                    
                    platform_map = {
                        'youtube': 'YouTube',
                        'facebook': 'Facebook',
                        'twitter': 'Twitter',
                        'instagram': 'Instagram',
                        'tiktok': 'TikTok',
                        'vimeo': 'Vimeo',
                        'dailymotion': 'Dailymotion'
                    }
                    
                    platform = platform_map.get(extractor_key, extractor_key.capitalize())
                    return True, platform
                    
                except json.JSONDecodeError:
                    return True, "Unknown"
            else:
                return False, "Unsupported URL"
                
        except Exception as e:
            logger.error(f"Error checking URL support: {e}")
            return False, "Error checking URL"


# Singleton instance for easy access
video_downloader = VideoDownloader()
