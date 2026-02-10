"""
Sync Manager
Handles video-AI response synchronization
"""

import re
from typing import Dict, List, Optional, Tuple


class SyncManager:
    """Manages synchronization between video playback and AI responses"""
    
    def __init__(self):
        self.timestamp_pattern = r'\[(\d{1,2}):(\d{2})(?::(\d{2}))?\]'
    
    def extract_timestamps(self, text: str) -> List[Dict]:
        """Extract all timestamps from text"""
        matches = re.finditer(self.timestamp_pattern, text)
        
        timestamps = []
        for match in matches:
            hours = int(match.group(1)) if match.group(3) else 0
            minutes = int(match.group(1)) if not match.group(3) else int(match.group(2))
            seconds = int(match.group(2)) if not match.group(3) else int(match.group(3))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            
            timestamps.append({
                'original': match.group(0),
                'seconds': total_seconds,
                'start_pos': match.start(),
                'end_pos': match.end()
            })
        
        return timestamps
    
    def add_clickable_timestamps(self, text: str) -> str:
        """Convert timestamps to clickable HTML spans"""
        def replace_timestamp(match):
            hours = int(match.group(1)) if match.group(3) else 0
            minutes = int(match.group(1)) if not match.group(3) else int(match.group(2))
            seconds = int(match.group(2)) if not match.group(3) else int(match.group(3))
            
            total_seconds = hours * 3600 + minutes * 60 + seconds
            original = match.group(0)
            
            return f'<span class="timestamp" data-time="{total_seconds}" onclick="jumpToTime({total_seconds})">{original}</span>'
        
        return re.sub(self.timestamp_pattern, replace_timestamp, text)
    
    def find_active_segment(self, current_time: float, segments: List[Dict]) -> Optional[int]:
        """Find which segment is active at current time"""
        for i, segment in enumerate(segments):
            start = segment.get('start', 0)
            end = segment.get('end', start + 10)
            
            if start <= current_time < end:
                return i
        
        return None
    
    def get_context_window(self, current_time: float, segments: List[Dict], 
                          window_seconds: int = 30) -> List[int]:
        """Get segment indices within time window"""
        active_indices = []
        
        for i, segment in enumerate(segments):
            start = segment.get('start', 0)
            end = segment.get('end', start)
            
            # Check if segment overlaps with window
            if (start <= current_time + window_seconds and 
                end >= current_time - window_seconds):
                active_indices.append(i)
        
        return active_indices
    
    def format_timestamp(self, seconds: float) -> str:
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
    
    def parse_timestamp(self, timestamp_str: str) -> float:
        """Parse timestamp string to seconds"""
        try:
            parts = timestamp_str.replace('[', '').replace(']', '').split(':')
            
            if len(parts) == 3:
                hours, minutes, seconds = parts
                return int(hours) * 3600 + int(minutes) * 60 + float(seconds)
            elif len(parts) == 2:
                minutes, seconds = parts
                return int(minutes) * 60 + float(seconds)
            else:
                return float(parts[0])
        except:
            return 0.0
    
    def create_sync_metadata(self, transcript_data: Dict) -> Dict:
        """Create sync metadata for frontend"""
        segments = transcript_data.get('segments', [])
        
        sync_data = {
            'total_segments': len(segments),
            'duration': transcript_data.get('duration', 0),
            'segments': []
        }
        
        for i, segment in enumerate(segments):
            sync_data['segments'].append({
                'index': i,
                'start': segment.get('start', 0),
                'end': segment.get('end', 0),
                'text': segment.get('text', ''),
                'has_words': len(segment.get('words', [])) > 0
            })
        
        return sync_data
    
    def generate_word_level_sync(self, segment: Dict) -> List[Dict]:
        """Generate word-level sync data"""
        words = segment.get('words', [])
        
        if not words:
            # Estimate word timings
            text = segment.get('text', '')
            word_list = text.split()
            start = segment.get('start', 0)
            end = segment.get('end', start + len(word_list))
            duration = (end - start) / max(len(word_list), 1)
            
            words = []
            for i, word in enumerate(word_list):
                words.append({
                    'text': word,
                    'start': start + i * duration,
                    'end': start + (i + 1) * duration
                })
        
        return words
    
    def calculate_sync_score(self, ai_response: str, transcript: Dict) -> float:
        """Calculate how well AI response syncs with transcript"""
        timestamps_in_response = self.extract_timestamps(ai_response)
        total_segments = len(transcript.get('segments', []))
        
        if total_segments == 0:
            return 0.0
        
        # Score based on timestamp coverage
        covered_segments = set()
        for ts in timestamps_in_response:
            segment_idx = self.find_active_segment(
                ts['seconds'],
                transcript.get('segments', [])
            )
            if segment_idx is not None:
                covered_segments.add(segment_idx)
        
        coverage = len(covered_segments) / total_segments
        return coverage * 100


# Global instance
sync_manager = SyncManager()
