"""
Firebase Manager
Handles all Firebase Firestore operations
"""

import os
import json
import hashlib
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

try:
    import firebase_admin
    from firebase_admin import credentials, firestore
    FIREBASE_AVAILABLE = True
except ImportError:
    FIREBASE_AVAILABLE = False
    print("⚠️ Firebase Admin SDK not installed")

from backend.config import config


class FirebaseManager:
    """Manages Firebase Firestore operations with local JSON fallback"""
    
    def __init__(self):
        self.db = None
        self.storage_type = None
        self._initialize_database()
    
    def _initialize_database(self):
        """Initialize Firebase or fallback to local JSON"""
        try:
            # Try Firebase first
            if FIREBASE_AVAILABLE and all(config.FIREBASE_CONFIG.values()):
                self._init_firebase()
            else:
                self._init_local_storage()
        except Exception as e:
            print(f"❌ Firebase init failed: {e}")
            self._init_local_storage()
    
    def _init_firebase(self):
        """Initialize Firebase Firestore"""
        try:
            if not firebase_admin._apps:
                # Check for service account file
                if os.path.exists(config.FIREBASE_SERVICE_ACCOUNT_PATH):
                    cred = credentials.Certificate(config.FIREBASE_SERVICE_ACCOUNT_PATH)
                else:
                    # Use config dict
                    cred = credentials.Certificate({
                        "type": "service_account",
                        "project_id": config.FIREBASE_CONFIG['projectId'],
                        "private_key_id": os.getenv('FIREBASE_PRIVATE_KEY_ID', ''),
                        "private_key": os.getenv('FIREBASE_PRIVATE_KEY', '').replace('\\n', '\n'),
                        "client_email": os.getenv('FIREBASE_CLIENT_EMAIL', ''),
                        "client_id": os.getenv('FIREBASE_CLIENT_ID', ''),
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs"
                    })
                
                firebase_admin.initialize_app(cred)
            
            self.db = firestore.client()
            self.storage_type = 'firebase'
            print("✅ Firebase Firestore initialized")
            
        except Exception as e:
            print(f"❌ Firebase initialization failed: {e}")
            raise
    
    def _init_local_storage(self):
        """Initialize local JSON storage as fallback"""
        self.local_storage_path = "local_data"
        os.makedirs(self.local_storage_path, exist_ok=True)
        
        self.collections = {
            'video_sessions': os.path.join(self.local_storage_path, 'video_sessions.json'),
            'transcripts': os.path.join(self.local_storage_path, 'transcripts.json'),
            'chat_history': os.path.join(self.local_storage_path, 'chat_history.json'),
            'ai_responses': os.path.join(self.local_storage_path, 'ai_responses.json')
        }
        
        # Create empty files if they don't exist
        for collection_path in self.collections.values():
            if not os.path.exists(collection_path):
                with open(collection_path, 'w', encoding='utf-8') as f:
                    json.dump([], f)
        
        self.storage_type = 'local_json'
        print("⚠️ Using local JSON storage (Firebase not configured)")
    
    # ============================================
    # VIDEO SESSION OPERATIONS
    # ============================================
    
    def save_video_session(self, session_id: str, video_url: str, video_data: Dict) -> bool:
        """Save video session"""
        try:
            session_doc = {
                'session_id': session_id,
                'video_url': video_url,
                'video_data': video_data,
                'platform': video_data.get('platform', 'unknown'),
                'status': 'created',
                'transcript_available': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            if self.storage_type == 'firebase':
                self.db.collection('video_sessions').document(session_id).set(session_doc)
            else:
                self._save_to_local('video_sessions', session_id, session_doc)
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving video session: {e}")
            return False
    
    def get_video_session(self, session_id: str) -> Optional[Dict]:
        """Get video session by ID"""
        try:
            if self.storage_type == 'firebase':
                doc = self.db.collection('video_sessions').document(session_id).get()
                return doc.to_dict() if doc.exists else None
            else:
                return self._get_from_local('video_sessions', session_id)
                
        except Exception as e:
            print(f"❌ Error getting video session: {e}")
            return None
    
    def update_video_session(self, session_id: str, updates: Dict) -> bool:
        """Update video session"""
        try:
            updates['updated_at'] = datetime.now().isoformat()
            
            if self.storage_type == 'firebase':
                self.db.collection('video_sessions').document(session_id).update(updates)
            else:
                self._update_local('video_sessions', session_id, updates)
            
            return True
            
        except Exception as e:
            print(f"❌ Error updating video session: {e}")
            return False
    
    # ============================================
    # TRANSCRIPT OPERATIONS
    # ============================================
    
    def save_transcript(self, session_id: str, video_id: str, transcript_data: Dict, source: str) -> bool:
        """Save transcript"""
        try:
            transcript_id = f"{session_id}_transcript"
            
            transcript_doc = {
                'transcript_id': transcript_id,
                'session_id': session_id,
                'video_id': video_id,
                'data': transcript_data,
                'source': source,
                'segments_count': len(transcript_data.get('segments', [])),
                'duration': transcript_data.get('duration', 0),
                'created_at': datetime.now().isoformat()
            }
            
            if self.storage_type == 'firebase':
                self.db.collection('transcripts').document(transcript_id).set(transcript_doc)
            else:
                self._save_to_local('transcripts', transcript_id, transcript_doc)
            
            # Update session to mark transcript available
            self.update_video_session(session_id, {'transcript_available': True})
            
            return True
            
        except Exception as e:
            print(f"❌ Error saving transcript: {e}")
            return False
    
    def get_transcript(self, session_id: str, video_id: str = None) -> Optional[Dict]:
        """Get transcript for session"""
        try:
            transcript_id = f"{session_id}_transcript"
            
            if self.storage_type == 'firebase':
                doc = self.db.collection('transcripts').document(transcript_id).get()
                return doc.to_dict() if doc.exists else None
            else:
                return self._get_from_local('transcripts', transcript_id)
                
        except Exception as e:
            print(f"❌ Error getting transcript: {e}")
            return None
    
    # ============================================
    # CHAT HISTORY OPERATIONS
    # ============================================
    
    def save_chat_message(self, session_id: str, role: str, content: str, 
                         model: str, metadata: Dict = None) -> str:
        """Save chat message"""
        try:
            message_id = f"{session_id}_{int(datetime.now().timestamp() * 1000)}"
            
            message_doc = {
                'message_id': message_id,
                'session_id': session_id,
                'role': role,
                'content': content,
                'model': model,
                'metadata': metadata or {},
                'timestamp': datetime.now().isoformat()
            }
            
            if self.storage_type == 'firebase':
                self.db.collection('chat_history').document(message_id).set(message_doc)
            else:
                self._save_to_local('chat_history', message_id, message_doc)
            
            return message_id
            
        except Exception as e:
            print(f"❌ Error saving chat message: {e}")
            return ""
    
    def get_chat_history(self, session_id: str, limit: int = 50) -> List[Dict]:
        """Get chat history for session"""
        try:
            if self.storage_type == 'firebase':
                query = (self.db.collection('chat_history')
                        .where('session_id', '==', session_id)
                        .order_by('timestamp')
                        .limit(limit))
                docs = query.stream()
                return [doc.to_dict() for doc in docs]
            else:
                return self._query_local('chat_history', 
                                       lambda x: x.get('session_id') == session_id,
                                       limit)
                
        except Exception as e:
            print(f"❌ Error getting chat history: {e}")
            return []
    
    def clear_chat_history(self, session_id: str) -> bool:
        """Clear chat history for session"""
        try:
            if self.storage_type == 'firebase':
                query = self.db.collection('chat_history').where('session_id', '==', session_id)
                docs = query.stream()
                for doc in docs:
                    doc.reference.delete()
            else:
                self._delete_from_local('chat_history', 
                                      lambda x: x.get('session_id') == session_id)
            
            return True
            
        except Exception as e:
            print(f"❌ Error clearing chat history: {e}")
            return False
    
    # ============================================
    # AI RESPONSE CACHING
    # ============================================
    
    def save_ai_response(self, session_id: str, query: str, response: Dict, model: str) -> str:
        """Save AI response for caching"""
        try:
            cache_key = hashlib.md5(f"{session_id}:{model}:{query}".encode()).hexdigest()
            
            response_doc = {
                'cache_key': cache_key,
                'session_id': session_id,
                'query': query,
                'response': response,
                'model': model,
                'timestamp': datetime.now().isoformat(),
                'expires_at': (datetime.now() + timedelta(hours=24)).isoformat()
            }
            
            if self.storage_type == 'firebase':
                self.db.collection('ai_responses').document(cache_key).set(response_doc)
            else:
                self._save_to_local('ai_responses', cache_key, response_doc)
            
            return cache_key
            
        except Exception as e:
            print(f"❌ Error saving AI response: {e}")
            return ""
    
    def get_cached_response(self, session_id: str, query: str, model: str = None) -> Optional[Dict]:
        """Get cached AI response"""
        try:
            cache_key = hashlib.md5(f"{session_id}:{model}:{query}".encode()).hexdigest()
            
            if self.storage_type == 'firebase':
                doc = self.db.collection('ai_responses').document(cache_key).get()
                if doc.exists:
                    data = doc.to_dict()
                    # Check expiration
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if datetime.now() < expires_at:
                        return data['response']
            else:
                data = self._get_from_local('ai_responses', cache_key)
                if data:
                    expires_at = datetime.fromisoformat(data['expires_at'])
                    if datetime.now() < expires_at:
                        return data['response']
            
            return None
            
        except Exception as e:
            print(f"❌ Error getting cached response: {e}")
            return None
    
    # ============================================
    # LOCAL JSON HELPERS
    # ============================================
    
    def _save_to_local(self, collection: str, doc_id: str, data: Dict):
        """Save to local JSON file"""
        file_path = self.collections[collection]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        # Remove existing
        all_data = [item for item in all_data 
                   if item.get(list(data.keys())[0]) != doc_id]
        
        # Add new
        all_data.append(data)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def _get_from_local(self, collection: str, doc_id: str) -> Optional[Dict]:
        """Get from local JSON file"""
        file_path = self.collections[collection]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        for item in all_data:
            if any(item.get(key) == doc_id for key in item.keys()):
                return item
        
        return None
    
    def _update_local(self, collection: str, doc_id: str, updates: Dict):
        """Update local JSON file"""
        file_path = self.collections[collection]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        for item in all_data:
            if any(item.get(key) == doc_id for key in item.keys()):
                item.update(updates)
                break
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(all_data, f, ensure_ascii=False, indent=2)
    
    def _delete_from_local(self, collection: str, filter_func):
        """Delete from local JSON file"""
        file_path = self.collections[collection]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        new_data = [item for item in all_data if not filter_func(item)]
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(new_data, f, ensure_ascii=False, indent=2)
    
    def _query_local(self, collection: str, filter_func, limit: int = 50) -> List[Dict]:
        """Query local JSON file"""
        file_path = self.collections[collection]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            all_data = json.load(f)
        
        filtered = [item for item in all_data if filter_func(item)]
        return filtered[:limit]
    
    # ============================================
    # UTILITY METHODS
    # ============================================
    
    def export_session_data(self, session_id: str) -> Optional[Dict]:
        """Export all data for a session"""
        try:
            session = self.get_video_session(session_id)
            if not session:
                return None
            
            transcript = self.get_transcript(session_id)
            chat_history = self.get_chat_history(session_id, 1000)
            
            return {
                'session': session,
                'transcript': transcript,
                'chat_history': chat_history,
                'exported_at': datetime.now().isoformat()
            }
            
        except Exception as e:
            print(f"❌ Error exporting session: {e}")
            return None
    
    def get_stats(self) -> Dict:
        """Get database statistics"""
        try:
            stats = {
                'storage_type': self.storage_type,
                'timestamp': datetime.now().isoformat()
            }
            
            if self.storage_type == 'firebase':
                # Count documents in each collection
                for collection in ['video_sessions', 'transcripts', 'chat_history', 'ai_responses']:
                    try:
                        count = len(list(self.db.collection(collection).limit(1000).stream()))
                        stats[collection] = count
                    except:
                        stats[collection] = 0
            else:
                # Count items in local files
                for collection, file_path in self.collections.items():
                    try:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        stats[collection] = len(data)
                    except:
                        stats[collection] = 0
            
            return stats
            
        except Exception as e:
            print(f"❌ Error getting stats: {e}")
            return {'error': str(e)}


# Global instance
db_manager = FirebaseManager()
