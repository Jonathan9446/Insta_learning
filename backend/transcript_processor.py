"""
Transcript Processor Module
Handles audio transcription using Groq Whisper API and fallback methods
"""

import os
import json
import time
import tempfile
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime

import requests
from pydub import AudioSegment
import speech_recognition as sr

from config import config
from utils.helpers import cleanup_temp_files, format_timestamp
from utils.logger import setup_logger

logger = setup_logger(__name__, config.LOG_LEVEL, config.LOG_FILE)

class TranscriptProcessor:
    """Handles audio transcription using multiple methods"""
    
    def __init__(self):
        self.groq_api_key = config.GROQ_API_KEY
        self.recognizer = sr.Recognizer()
        
    def transcribe_with_groq(self, audio_file_path: str, language: str = "en") -> Optional[Dict]:
        """
        Transcribe audio using Groq Cloud Whisper API
        
        Args:
            audio_file_path: Path to audio file
            language: Language code (default: "en")
            
        Returns:
            Structured transcript data or None
        """
        if not self.groq_api_key:
            logger.warning("Groq API key not configured")
            return self.transcribe_with_whisper_local(audio_file_path, language)
        
        try:
            # Check file size (Groq has limits)
            file_size = os.path.getsize(audio_file_path)
            max_size = 25 * 1024 * 1024  # 25 MB
            
            if file_size > max_size:
                logger.warning(f"Audio file too large ({file_size/1024/1024:.2f} MB), splitting...")
                return self._transcribe_large_audio_groq(audio_file_path, language)
            
            # Prepare for Groq API
            import groq
            
            client = groq.Client(api_key=self.groq_api_key)
            
            logger.info(f"Transcribing with Groq Whisper: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                start_time = time.time()
                
                transcription = client.audio.transcriptions.create(
                    file=audio_file,
                    model="whisper-large-v3",
                    response_format="verbose_json",
                    language=language,
                    temperature=0.0,
                    prompt="Transcribe accurately with word-level timestamps."
                )
                
                processing_time = time.time() - start_time
                
                # Process the response
                transcript_data = self._process_whisper_response(transcription, language)
                transcript_data['processing_time'] = processing_time
                transcript_data['api_used'] = 'groq_whisper'
                transcript_data['file_size_mb'] = file_size / (1024 * 1024)
                
                logger.info(f"Groq transcription complete: {len(transcript_data['sentences'])} sentences in {processing_time:.2f}s")
                return transcript_data
                
        except ImportError:
            logger.error("Groq library not installed")
            return self.transcribe_with_whisper_api(audio_file_path, language)
        except Exception as e:
            logger.error(f"Groq transcription error: {e}")
            return self.transcribe_with_whisper_api(audio_file_path, language)
    
    def transcribe_with_whisper_api(self, audio_file_path: str, language: str = "en") -> Optional[Dict]:
        """
        Transcribe audio using OpenAI Whisper API (fallback)
        """
        try:
            from openai import OpenAI
            
            client = OpenAI(api_key=os.getenv('OPENAI_API_KEY'))
            
            if not client.api_key:
                logger.warning("OpenAI API key not configured")
                return self.transcribe_with_whisper_local(audio_file_path, language)
            
            logger.info(f"Transcribing with OpenAI Whisper: {audio_file_path}")
            
            with open(audio_file_path, "rb") as audio_file:
                start_time = time.time()
                
                transcription = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    response_format="verbose_json",
                    language=language
                )
                
                processing_time = time.time() - start_time
                
                transcript_data = self._process_whisper_response(transcription, language)
                transcript_data['processing_time'] = processing_time
                transcript_data['api_used'] = 'openai_whisper'
                
                logger.info(f"OpenAI Whisper transcription complete: {len(transcript_data['sentences'])} sentences")
                return transcript_data
                
        except Exception as e:
            logger.error(f"OpenAI Whisper API error: {e}")
            return self.transcribe_with_whisper_local(audio_file_path, language)
    
    def transcribe_with_whisper_local(self, audio_file_path: str, language: str = "en") -> Optional[Dict]:
        """
        Transcribe audio using local Whisper model (fallback when APIs fail)
        """
        try:
            # This requires whisper to be installed locally
            import whisper
            
            logger.info(f"Transcribing with local Whisper model: {audio_file_path}")
            
            # Load model (base is smallest, large is most accurate but slower)
            model = whisper.load_model("base")
            
            start_time = time.time()
            
            # Transcribe with word timestamps
            result = model.transcribe(
                audio_file_path,
                language=language,
                verbose=False,
                word_timestamps=True
            )
            
            processing_time = time.time() - start_time
            
            # Process the result
            transcript_data = self._process_whisper_response(result, language)
            transcript_data['processing_time'] = processing_time
            transcript_data['api_used'] = 'local_whisper'
            transcript_data['model'] = 'base'
            
            logger.info(f"Local Whisper transcription complete: {len(transcript_data['sentences'])} sentences")
            return transcript_data
            
        except ImportError:
            logger.error("Whisper library not installed")
            return self.transcribe_with_speech_recognition(audio_file_path, language)
        except Exception as e:
            logger.error(f"Local Whisper error: {e}")
            return self.transcribe_with_speech_recognition(audio_file_path, language)
    
    def transcribe_with_speech_recognition(self, audio_file_path: str, language: str = "en") -> Optional[Dict]:
        """
        Transcribe audio using SpeechRecognition library (fallback)
        """
        try:
            logger.info(f"Transcribing with SpeechRecognition: {audio_file_path}")
            
            # Convert audio format if needed
            audio_file = self._convert_audio_format(audio_file_path, "wav")
            if not audio_file:
                return None
            
            # Load audio file
            with sr.AudioFile(audio_file) as source:
                audio_data = self.recognizer.record(source)
                
                start_time = time.time()
                
                # Try Google Speech Recognition (free but requires internet)
                text = self.recognizer.recognize_google(audio_data, language=language)
                
                processing_time = time.time() - start_time
            
            # Create basic transcript structure
            transcript_data = {
                'language': language,
                'sentences': [{
                    'text': text,
                    'start': 0,
                    'end': processing_time,
                    'words': []
                }],
                'total_duration': processing_time,
                'word_count': len(text.split()),
                'sentence_count': 1,
                'api_used': 'speech_recognition',
                'processing_time': processing_time
            }
            
            logger.info(f"SpeechRecognition complete: {len(text)} characters")
            return transcript_data
            
        except sr.UnknownValueError:
            logger.error("SpeechRecognition could not understand audio")
            return None
        except sr.RequestError as e:
            logger.error(f"SpeechRecognition request error: {e}")
            return None
        except Exception as e:
            logger.error(f"SpeechRecognition error: {e}")
            return None
    
    def _transcribe_large_audio_groq(self, audio_file_path: str, language: str) -> Optional[Dict]:
        """
        Transcribe large audio files by splitting into chunks
        """
        try:
            # Load audio file
            audio = AudioSegment.from_file(audio_file_path)
            
            # Split into 10-minute chunks (Whisper can handle up to 25MB)
            chunk_length_ms = 10 * 60 * 1000  # 10 minutes in milliseconds
            chunks = [audio[i:i + chunk_length_ms] for i in range(0, len(audio), chunk_length_ms)]
            
            logger.info(f"Splitting audio into {len(chunks)} chunks")
            
            all_sentences = []
            current_time = 0
            
            # Create temp directory for chunks
            temp_dir = tempfile.mkdtemp(dir=config.TEMP_DIR)
            
            try:
                for i, chunk in enumerate(chunks):
                    chunk_file = os.path.join(temp_dir, f"chunk_{i}.mp3")
                    
                    # Export chunk
                    chunk.export(chunk_file, format="mp3")
                    
                    # Transcribe chunk
                    chunk_data = self.transcribe_with_groq(chunk_file, language)
                    
                    if chunk_data and chunk_data.get('sentences'):
                        # Adjust timestamps for chunk position
                        for sentence in chunk_data['sentences']:
                            sentence['start'] += current_time
                            sentence['end'] += current_time
                            
                            # Adjust word timestamps
                            for word in sentence.get('words', []):
                                word['start'] += current_time
                                word['end'] += current_time
                        
                        all_sentences.extend(chunk_data['sentences'])
                    
                    # Update current time
                    current_time += len(chunk) / 1000  # Convert ms to seconds
                    
                    # Cleanup chunk file
                    if os.path.exists(chunk_file):
                        os.remove(chunk_file)
                
                # Cleanup temp directory
                cleanup_temp_files(temp_dir)
                
                if all_sentences:
                    transcript_data = {
                        'language': language,
                        'sentences': all_sentences,
                        'total_duration': current_time,
                        'word_count': sum(len(s['text'].split()) for s in all_sentences),
                        'sentence_count': len(all_sentences),
                        'api_used': 'groq_whisper_chunked',
                        'chunks_processed': len(chunks)
                    }
                    
                    logger.info(f"Large audio transcription complete: {len(all_sentences)} sentences from {len(chunks)} chunks")
                    return transcript_data
                else:
                    return None
                    
            except Exception as e:
                logger.error(f"Error in chunked transcription: {e}")
                cleanup_temp_files(temp_dir)
                return None
                
        except Exception as e:
            logger.error(f"Error splitting audio: {e}")
            return None
    
    def _process_whisper_response(self, response: Any, language: str) -> Dict:
        """
        Process Whisper API response into structured format
        """
        try:
            sentences = []
            
            # Extract segments from response
            if hasattr(response, 'segments'):
                segments = response.segments
            elif isinstance(response, dict) and 'segments' in response:
                segments = response['segments']
            elif isinstance(response, dict) and 'text' in response:
                # Simple text response
                sentences.append({
                    'text': response['text'],
                    'start': 0,
                    'end': 0,
                    'words': []
                })
                
                return {
                    'language': language,
                    'sentences': sentences,
                    'total_duration': 0,
                    'word_count': len(response['text'].split()),
                    'sentence_count': 1
                }
            else:
                # Fallback for different response formats
                text = str(response)
                sentences.append({
                    'text': text,
                    'start': 0,
                    'end': 0,
                    'words': []
                })
                
                return {
                    'language': language,
                    'sentences': sentences,
                    'total_duration': 0,
                    'word_count': len(text.split()),
                    'sentence_count': 1
                }
            
            # Process each segment
            for segment in segments:
                text = segment.get('text', '').strip()
                start = segment.get('start', 0)
                end = segment.get('end', 0)
                
                if not text:
                    continue
                
                # Extract words with timestamps if available
                words = []
                if 'words' in segment and segment['words']:
                    for word_info in segment['words']:
                        word_text = word_info.get('word', '').strip()
                        word_start = word_info.get('start', start)
                        word_end = word_info.get('end', end)
                        
                        if word_text:
                            words.append({
                                'text': word_text,
                                'start': word_start,
                                'end': word_end
                            })
                
                # If no word-level timestamps, estimate them
                if not words:
                    word_list = text.split()
                    if word_list and end > start:
                        word_duration = (end - start) / len(word_list)
                        
                        for i, word in enumerate(word_list):
                            word_start = start + (i * word_duration)
                            word_end = word_start + word_duration
                            
                            words.append({
                                'text': word,
                                'start': word_start,
                                'end': word_end
                            })
                
                sentences.append({
                    'text': text,
                    'start': start,
                    'end': end,
                    'words': words
                })
            
            # Calculate total duration
            total_duration = sentences[-1]['end'] if sentences else 0
            
            return {
                'language': language,
                'sentences': sentences,
                'total_duration': total_duration,
                'word_count': sum(len(s['text'].split()) for s in sentences),
                'sentence_count': len(sentences)
            }
            
        except Exception as e:
            logger.error(f"Error processing Whisper response: {e}")
            return {
                'language': language,
                'sentences': [],
                'total_duration': 0,
                'word_count': 0,
                'sentence_count': 0,
                'error': str(e)
            }
    
    def _convert_audio_format(self, input_path: str, output_format: str = "wav") -> Optional[str]:
        """
        Convert audio file to required format
        """
        try:
            # Get file extension
            input_ext = os.path.splitext(input_path)[1].lower().replace('.', '')
            
            if input_ext == output_format:
                return input_path
            
            # Create output path
            output_path = os.path.join(
                os.path.dirname(input_path),
                f"{os.path.splitext(os.path.basename(input_path))[0]}.{output_format}"
            )
            
            # Convert using pydub
            audio = AudioSegment.from_file(input_path, format=input_ext)
            audio.export(output_path, format=output_format)
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error converting audio format: {e}")
            return None
    
    def format_transcript_for_display(self, transcript_data: Dict) -> Dict:
        """
        Format transcript data for frontend display
        """
        if not transcript_data or 'sentences' not in transcript_data:
            return transcript_data
        
        formatted_sentences = []
        
        for sentence in transcript_data['sentences']:
            formatted_sentence = {
                'text': sentence['text'],
                'start': sentence['start'],
                'end': sentence['end'],
                'start_formatted': format_timestamp(sentence['start']),
                'end_formatted': format_timestamp(sentence['end']),
                'word_count': len(sentence['text'].split())
            }
            
            # Add words if available
            if 'words' in sentence and sentence['words']:
                formatted_words = []
                for word in sentence['words']:
                    formatted_words.append({
                        'text': word['text'],
                        'start': word['start'],
                        'end': word['end'],
                        'start_formatted': format_timestamp(word['start'])
                    })
                
                formatted_sentence['words'] = formatted_words
            
            formatted_sentences.append(formatted_sentence)
        
        # Create formatted transcript
        formatted_transcript = transcript_data.copy()
        formatted_transcript['sentences'] = formatted_sentences
        
        # Add summary statistics
        formatted_transcript['summary'] = {
            'total_sentences': len(formatted_sentences),
            'total_words': sum(s['word_count'] for s in formatted_sentences),
            'total_duration_formatted': format_timestamp(transcript_data.get('total_duration', 0)),
            'avg_words_per_sentence': sum(s['word_count'] for s in formatted_sentences) / max(len(formatted_sentences), 1)
        }
        
        return formatted_transcript
    
    def extract_key_phrases(self, transcript_data: Dict, max_phrases: int = 10) -> List[Dict]:
        """
        Extract key phrases from transcript (simple implementation)
        """
        try:
            if not transcript_data or 'sentences' not in transcript_data:
                return []
            
            # Combine all text
            full_text = ' '.join(s['text'] for s in transcript_data['sentences'])
            
            # Simple keyword extraction (can be enhanced with NLP)
            words = full_text.lower().split()
            
            # Remove common stop words
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 'of', 'with', 'by'}
            filtered_words = [w for w in words if w not in stop_words and len(w) > 3]
            
            # Count word frequencies
            word_freq = {}
            for word in filtered_words:
                word_freq[word] = word_freq.get(word, 0) + 1
            
            # Get top phrases
            sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
            top_phrases = []
            
            for word, freq in sorted_words[:max_phrases]:
                # Find sentence where word appears
                for sentence in transcript_data['sentences']:
                    if word in sentence['text'].lower():
                        top_phrases.append({
                            'phrase': word,
                            'frequency': freq,
                            'example_sentence': sentence['text'][:100] + '...',
                            'timestamp': sentence['start']
                        })
                        break
            
            return top_phrases
            
        except Exception as e:
            logger.error(f"Error extracting key phrases: {e}")
            return []
    
    def create_transcript_summary(self, transcript_data: Dict) -> str:
        """
        Create a simple summary of the transcript
        """
        if not transcript_data or 'sentences' not in transcript_data:
            return "No transcript available for summary."
        
        sentences = transcript_data['sentences']
        
        if not sentences:
            return "Transcript is empty."
        
        # Take first few sentences as summary (simple approach)
        summary_sentences = sentences[:3]
        summary_text = ' '.join(s['text'] for s in summary_sentences)
        
        # Add metadata
        duration = transcript_data.get('total_duration', 0)
        word_count = sum(len(s['text'].split()) for s in sentences)
        
        summary = f"Summary: {summary_text[:200]}..."
        summary += f"\n\nDuration: {format_timestamp(duration)}"
        summary += f"\nTotal Sentences: {len(sentences)}"
        summary += f"\nTotal Words: {word_count}"
        
        return summary


# Singleton instance for easy access
transcript_processor = TranscriptProcessor()
