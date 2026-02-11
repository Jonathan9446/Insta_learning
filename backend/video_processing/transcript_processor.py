"""
Transcript Processor
Handles audio transcription using Groq Whisper API
"""

import os
import requests
from typing import Dict, Optional

from backend.config import config
from backend.utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)


class TranscriptProcessor:
    """Transcribe audio using Groq Whisper"""
    
    def __init__(self):
        self.groq_api_key = config.GROQ_API_KEY
        self.groq_url = "https://api.groq.com/openai/v1/audio/transcriptions"
    
    def transcribe_with_groq(self, audio_file_path: str, language: str = "en") -> Optional[Dict]:
        """Transcribe audio with Groq Whisper API"""
        
        if not self.groq_api_key:
            logger.error("❌ Groq API key not configured")
            return {
                'success': False,
                'error': 'Groq API key missing'
            }
        
        try:
            file_size = os.path.getsize(audio_file_path)
            max_size = 25 * 1024 * 1024  # 25 MB limit
            
            if file_size > max_size:
                logger.warning(f"⚠️ Audio file too large: {file_size / 1024 / 1024:.2f} MB")
                return self._transcribe_large_file(audio_file_path, language)
            
            logger.info(f"🎙️ Transcribing with Groq Whisper ({file_size / 1024 / 1024:.2f} MB)...")
            
            headers = {
                "Authorization": f"Bearer {self.groq_api_key}"
            }
            
            with open(audio_file_path, 'rb') as audio_file:
                files = {
                    'file': audio_file,
                    'model': (None, 'whisper-large-v3'),
                    'response_format': (None, 'verbose_json'),
                    'language': (None, language)
                }
                
                response = requests.post(
                    self.groq_url,
                    headers=headers,
                    files=files,
                    timeout=300
                )
            
            if response.status_code == 200:
                result = response.json()
                
                transcript_data = {
                    'success': True,
                    'text': result.get('text', ''),
                    'segments': [],
                    'language': result.get('language', language),
                    'duration': result.get('duration', 0)
                }
                
                # Process segments
                for segment in result.get('segments', []):
                    processed_segment = {
                        'start': segment.get('start', 0),
                        'end': segment.get('end', 0),
                        'text': segment.get('text', '').strip(),
                        'words': []
                    }
                    
                    # Process words if available
                    if 'words' in segment:
                        for word_info in segment['words']:
                            processed_segment['words'].append({
                                'text': word_info.get('word', '').strip(),
                                'start': word_info.get('start', processed_segment['start']),
                                'end': word_info.get('end', processed_segment['end'])
                            })
                    else:
                        # Estimate word timings
                        words = processed_segment['text'].split()
                        duration = (processed_segment['end'] - processed_segment['start']) / max(len(words), 1)
                        
                        for i, word in enumerate(words):
                            processed_segment['words'].append({
                                'text': word,
                                'start': processed_segment['start'] + i * duration,
                                'end': processed_segment['start'] + (i + 1) * duration
                            })
                    
                    transcript_data['segments'].append(processed_segment)
                
                logger.info(f"✅ Transcription complete: {len(transcript_data['segments'])} segments")
                return transcript_data
            
            else:
                error_msg = f"Groq API error: {response.status_code}"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('error', {}).get('message', error_msg)
                except:
                    pass
                
                logger.error(f"❌ {error_msg}")
                return {
                    'success': False,
                    'error': error_msg
                }
        
        except Exception as e:
            logger.error(f"❌ Groq transcription error: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def _transcribe_large_file(self, audio_file_path: str, language: str) -> Optional[Dict]:
        """Handle large files by chunking (not implemented yet)"""
        logger.warning("⚠️ Large file transcription not yet implemented")
        return {
            'success': False,
            'error': 'File too large (max 25MB)'
        }


# Global instance
transcript_processor = TranscriptProcessor()
