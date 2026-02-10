"""
Chunking Manager
Handles chunking of large videos for processing
"""

from typing import Dict, List, Tuple
from backend.config import config


class ChunkingManager:
    """Manages video chunking for large file processing"""
    
    def __init__(self, max_chunk_duration: int = None):
        self.max_chunk_duration = max_chunk_duration or config.MAX_CHUNK_DURATION
    
    def calculate_chunks(self, total_duration: float) -> List[Dict]:
        """Calculate chunk boundaries for a video"""
        if total_duration <= self.max_chunk_duration:
            return [{
                'chunk_id': 0,
                'start': 0,
                'end': total_duration,
                'duration': total_duration
            }]
        
        chunks = []
        num_chunks = int(total_duration / self.max_chunk_duration) + 1
        
        for i in range(num_chunks):
            start = i * self.max_chunk_duration
            end = min((i + 1) * self.max_chunk_duration, total_duration)
            
            chunks.append({
                'chunk_id': i,
                'start': start,
                'end': end,
                'duration': end - start
            })
        
        return chunks
    
    def get_chunk_for_timestamp(self, timestamp: float, chunks: List[Dict]) -> int:
        """Get chunk ID for a given timestamp"""
        for chunk in chunks:
            if chunk['start'] <= timestamp < chunk['end']:
                return chunk['chunk_id']
        
        # Return last chunk if timestamp is beyond
        return chunks[-1]['chunk_id'] if chunks else 0
    
    def get_priority_chunks(self, current_time: float, chunks: List[Dict], 
                          lookahead: int = 2) -> List[int]:
        """Get priority chunks to load (current + lookahead)"""
        current_chunk = self.get_chunk_for_timestamp(current_time, chunks)
        
        priority_chunks = [current_chunk]
        
        # Add lookahead chunks
        for i in range(1, lookahead + 1):
            next_chunk = current_chunk + i
            if next_chunk < len(chunks):
                priority_chunks.append(next_chunk)
        
        # Add previous chunk if exists
        if current_chunk > 0:
            priority_chunks.insert(0, current_chunk - 1)
        
        return priority_chunks
    
    def filter_segments_by_chunk(self, segments: List[Dict], chunk: Dict) -> List[Dict]:
        """Filter segments that belong to a chunk"""
        filtered = []
        
        for segment in segments:
            seg_start = segment.get('start', 0)
            seg_end = segment.get('end', seg_start)
            
            # Check if segment overlaps with chunk
            if (seg_start < chunk['end'] and seg_end > chunk['start']):
                filtered.append(segment)
        
        return filtered
    
    def estimate_processing_time(self, duration: float, has_transcript: bool = False) -> float:
        """Estimate processing time for a video"""
        base_time = 5.0
        duration_factor = 0.1
        
        estimated = base_time + (duration * duration_factor)
        
        if not has_transcript:
            estimated *= 1.5
        
        return min(estimated, 300)
    
    def create_chunk_manifest(self, video_id: str, total_duration: float) -> Dict:
        """Create a manifest for chunked processing"""
        chunks = self.calculate_chunks(total_duration)
        
        manifest = {
            'video_id': video_id,
            'total_duration': total_duration,
            'chunk_size': self.max_chunk_duration,
            'total_chunks': len(chunks),
            'chunks': chunks,
            'estimated_time': self.estimate_processing_time(total_duration),
            'strategy': 'on_demand' if len(chunks) > 10 else 'preload_all'
        }
        
        return manifest
    
    def get_load_strategy(self, total_chunks: int) -> str:
        """Determine loading strategy based on video size"""
        if total_chunks <= 3:
            return 'preload_all'
        elif total_chunks <= 10:
            return 'preload_adjacent'
        else:
            return 'on_demand'


# Global instance
chunking_manager = ChunkingManager()
