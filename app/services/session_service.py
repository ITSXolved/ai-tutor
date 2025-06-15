import redis
import json
import uuid
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from supabase import create_client, Client
from utils.config import Config
import logging

class SessionService:
    def __init__(self):
        self.config = Config()
        self.redis_client = redis.from_url(self.config.REDIS_URL, decode_responses=True)
        self.supabase: Client = create_client(
            self.config.SUPABASE_URL,
            self.config.SUPABASE_KEY
        )
        self.session_ttl = 3600  # 1 hour
    
    def create_session(self, user_data: Dict[str, Any] = None) -> str:
        """Create a new session"""
        session_id = str(uuid.uuid4())
        user_id = user_data.get('user_id', f"anonymous_{uuid.uuid4()}")
        
        session_data = {
            'session_id': session_id,
            'user_id': user_id,
            'created_at': datetime.now().isoformat(),
            'user_data': user_data or {},
            'conversation_history': [],
            'difficulty_level': self.config.DEFAULT_DIFFICULTY,
            'subject': 'english',
            'proficiency_score': 50,  # Initial proficiency (0-100)
            'interaction_count': 0,
            'initial_proficiency': 50,
            'session_status': 'active'
        }
        
        self.redis_client.setex(
            f"session:{session_id}",
            self.session_ttl,
            json.dumps(session_data)
        )
        
        return session_id
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve session data"""
        session_data = self.redis_client.get(f"session:{session_id}")
        if session_data:
            return json.loads(session_data)
        return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> bool:
        """Update session data"""
        session_data = self.get_session(session_id)
        if session_data:
            session_data.update(updates)
            self.redis_client.setex(
                f"session:{session_id}",
                self.session_ttl,
                json.dumps(session_data)
            )
            return True
        return False
    
    def add_to_conversation(self, session_id: str, message: Dict[str, Any]) -> bool:
        """Add message to conversation history"""
        session_data = self.get_session(session_id)
        if session_data:
            session_data['conversation_history'].append(message)
            session_data['interaction_count'] += 1
            return self.update_session(session_id, session_data)
        return False
    
    def update_proficiency(self, session_id: str, score_change: int) -> bool:
        """Update user's proficiency score"""
        session_data = self.get_session(session_id)
        if session_data:
            current_score = session_data.get('proficiency_score', 50)
            new_score = max(0, min(100, current_score + score_change))
            session_data['proficiency_score'] = new_score
            
            # Adjust difficulty based on proficiency
            if new_score >= 75:
                session_data['difficulty_level'] = 'advanced'
            elif new_score >= 40:
                session_data['difficulty_level'] = 'intermediate'
            else:
                session_data['difficulty_level'] = 'beginner'
            
            return self.update_session(session_id, session_data)
        return False
    
    def end_session(self, session_id: str, user_experience: Dict[str, Any] = None) -> bool:
        """End session, store conversation in Supabase, and clear from Redis"""
        try:
            # Get session data before deletion
            session_data = self.get_session(session_id)
            if not session_data:
                return False
            
            # Mark session as ended
            session_data['ended_at'] = datetime.now().isoformat()
            session_data['session_status'] = 'ended'
            session_data['session_duration'] = self._calculate_session_duration(session_data)
            
            # Store conversation history in Supabase
            conversation_stored = self._store_conversation_history(session_data)
            
            # Store user experience if provided
            if user_experience:
                self._store_user_experience(session_id, session_data['user_id'], user_experience)
            
            # Store session summary in Supabase
            session_summary_stored = self._store_session_summary(session_data)
            
            # Clear session from Redis
            self.redis_client.delete(f"session:{session_id}")
            
            logging.info(f"Session {session_id} ended and stored successfully")
            return conversation_stored and session_summary_stored
            
        except Exception as e:
            logging.error(f"Error ending session {session_id}: {e}")
            return False
    
    def _store_conversation_history(self, session_data: Dict[str, Any]) -> bool:
        """Store conversation history in Supabase"""
        try:
            conversation_record = {
                'session_id': session_data['session_id'],
                'user_id': session_data['user_id'],
                'conversation_data': json.dumps(session_data['conversation_history']),
                'message_count': len(session_data['conversation_history']),
                'subject': session_data['subject'],
                'final_difficulty_level': session_data['difficulty_level'],
                'final_proficiency_score': session_data['proficiency_score'],
                'created_at': session_data['created_at'],
                'ended_at': session_data.get('ended_at'),
                'session_duration_minutes': session_data.get('session_duration', 0)
            }
            
            result = self.supabase.table('conversation_history').insert(conversation_record).execute()
            return bool(result.data)
            
        except Exception as e:
            logging.error(f"Error storing conversation history: {e}")
            return False
    
    def _store_session_summary(self, session_data: Dict[str, Any]) -> bool:
        """Store session summary in Supabase"""
        try:
            summary_record = {
                'session_id': session_data['session_id'],
                'user_id': session_data['user_id'],
                'subject': session_data['subject'],
                'initial_proficiency_score': session_data.get('initial_proficiency', 50),
                'final_proficiency_score': session_data['proficiency_score'],
                'proficiency_improvement': session_data['proficiency_score'] - session_data.get('initial_proficiency', 50),
                'initial_difficulty_level': self.config.DEFAULT_DIFFICULTY,
                'final_difficulty_level': session_data['difficulty_level'],
                'total_interactions': session_data['interaction_count'],
                'session_duration_minutes': session_data.get('session_duration', 0),
                'created_at': session_data['created_at'],
                'ended_at': session_data.get('ended_at'),
                'session_status': session_data['session_status']
            }
            
            result = self.supabase.table('session_summaries').insert(summary_record).execute()
            return bool(result.data)
            
        except Exception as e:
            logging.error(f"Error storing session summary: {e}")
            return False
    
    def _store_user_experience(self, session_id: str, user_id: str, experience_data: Dict[str, Any]) -> bool:
        """Store user experience feedback in Supabase"""
        try:
            experience_record = {
                'session_id': session_id,
                'user_id': user_id,
                'rating': experience_data.get('rating'),
                'feedback_text': experience_data.get('feedback'),
                'usefulness_rating': experience_data.get('usefulness_rating'),
                'difficulty_appropriate': experience_data.get('difficulty_appropriate'),
                'would_recommend': experience_data.get('would_recommend'),
                'improvement_suggestions': experience_data.get('improvement_suggestions'),
                'favorite_features': experience_data.get('favorite_features'),
                'created_at': datetime.now().isoformat()
            }
            
            result = self.supabase.table('user_experiences').insert(experience_record).execute()
            return bool(result.data)
            
        except Exception as e:
            logging.error(f"Error storing user experience: {e}")
            return False
    
    def _calculate_session_duration(self, session_data: Dict[str, Any]) -> int:
        """Calculate session duration in minutes"""
        try:
            start_time = datetime.fromisoformat(session_data['created_at'])
            end_time = datetime.fromisoformat(session_data['ended_at'])
            duration = (end_time - start_time).total_seconds() / 60
            return round(duration, 2)
        except Exception:
            return 0
    
    def get_user_session_history(self, user_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get user's session history from Supabase"""
        try:
            result = self.supabase.table('session_summaries')\
                .select('*')\
                .eq('user_id', user_id)\
                .order('created_at', desc=True)\
                .limit(limit)\
                .execute()
            
            return result.data if result.data else []
            
        except Exception as e:
            logging.error(f"Error fetching user session history: {e}")
            return []