from typing import Dict, Any, List
from datetime import datetime
from langchain.schema import HumanMessage, SystemMessage
from models.llm_models import ModelManager
from services.vector_service import VectorService
from services.session_service import SessionService
from prompts.teaching_prompts import TeachingPrompts
import logging

class TeachingService:
    def __init__(self):
        self.model_manager = ModelManager()
        self.vector_service = VectorService()
        self.session_service = SessionService()
        self.prompts = TeachingPrompts()
    
    def process_student_message(self, session_id: str, message: str) -> Dict[str, Any]:
        """Process student message and generate adaptive response"""
        try:
            # Get session data
            session_data = self.session_service.get_session(session_id)
            if not session_data:
                return {"error": "Invalid session"}
            
            # Check if session is active
            if session_data.get('session_status') != 'active':
                return {"error": "Session is not active"}
            
            # Analyze student proficiency from message
            proficiency_analysis = self._analyze_proficiency(message, session_data)
            
            # Update proficiency score
            if proficiency_analysis['score_change'] != 0:
                self.session_service.update_proficiency(
                    session_id, 
                    proficiency_analysis['score_change']
                )
                session_data = self.session_service.get_session(session_id)  # Refresh data
            
            # Perform RAG search for relevant content
            search_results = self.vector_service.search_by_difficulty(
                query=message,
                difficulty_level=session_data['difficulty_level'],
                subject=session_data['subject']
            )
            
            # Generate context-aware response
            response = self._generate_adaptive_response(
                message, 
                session_data, 
                search_results
            )
            
            # Update conversation history
            self.session_service.add_to_conversation(session_id, {
                'type': 'student',
                'message': message,
                'timestamp': datetime.now().isoformat(),
                'proficiency_level': session_data['difficulty_level'],
                'proficiency_score': session_data['proficiency_score']
            })
            
            self.session_service.add_to_conversation(session_id, {
                'type': 'teacher',
                'message': response['content'],
                'timestamp': datetime.now().isoformat(),
                'teaching_strategy': response['strategy'],
                'search_results_used': len(search_results)
            })
            
            return {
                'response': response['content'],
                'difficulty_level': session_data['difficulty_level'],
                'proficiency_score': session_data['proficiency_score'],
                'teaching_strategy': response['strategy'],
                'session_id': session_id,
                'interaction_count': session_data['interaction_count']
            }
            
        except Exception as e:
            logging.error(f"Error processing student message: {e}")
            return {"error": "Failed to process message"}
    
    def _analyze_proficiency(self, message: str, session_data: Dict) -> Dict[str, Any]:
        """Analyze student's English proficiency from their message"""
        # Enhanced proficiency analysis
        words = message.split()
        unique_words = set(word.lower().strip('.,!?') for word in words)
        
        complexity_indicators = {
            'vocabulary_diversity': len(unique_words) / len(words) if words else 0,
            'average_word_length': sum(len(word) for word in words) / len(words) if words else 0,
            'sentence_count': message.count('.') + message.count('!') + message.count('?') + 1,
            'sentence_length': len(words) / max(1, message.count('.') + message.count('!') + message.count('?') + 1),
            'grammar_complexity': message.count(',') + message.count(';') + message.count(':'),
            'question_complexity': message.count('?')
        }
        
        score_change = 0
        current_level = session_data['difficulty_level']
        current_score = session_data['proficiency_score']
        
        # Scoring logic
        if complexity_indicators['vocabulary_diversity'] > 0.8 and complexity_indicators['average_word_length'] > 5:
            if current_level == 'beginner':
                score_change = 5
            elif current_level == 'intermediate':
                score_change = 3
        elif complexity_indicators['sentence_length'] > 10 and current_level == 'beginner':
            score_change = 3
        elif complexity_indicators['sentence_length'] < 3 and current_level == 'advanced':
            score_change = -2
        elif len(words) < 3 and current_level in ['intermediate', 'advanced']:
            score_change = -1
        
        return {
            'score_change': score_change,
            'complexity_indicators': complexity_indicators
        }
    
    def _generate_adaptive_response(self, message: str, session_data: Dict, search_results: List[Dict]) -> Dict[str, Any]:
        """Generate adaptive teaching response based on student level and context"""
        difficulty_level = session_data['difficulty_level']
        conversation_history = session_data.get('conversation_history', [])
        
        # Select appropriate system instruction based on context
        if session_data['interaction_count'] < 3:
            system_instruction = self.prompts.get_assessment_prompt(difficulty_level)
            strategy = 'assessment'
        elif any(word in message.lower() for word in ['test', 'quiz', 'exam', 'practice']):
            system_instruction = self.prompts.get_test_prep_prompt(difficulty_level)
            strategy = 'test_prep'
        elif '?' in message or any(word in message.lower() for word in ['what', 'how', 'why', 'when', 'where']):
            system_instruction = self.prompts.get_concept_teaching_prompt(difficulty_level)
            strategy = 'concept_teaching'
        elif any(word in message.lower() for word in ['bye', 'goodbye', 'end', 'finish', 'stop', 'done']):
            system_instruction = self.prompts.get_session_ending_prompt(difficulty_level)
            strategy = 'session_ending'
        else:
            system_instruction = self.prompts.get_general_teaching_prompt(difficulty_level)
            strategy = 'general_teaching'
        
        # Build context from search results
        context = self._build_context(search_results)
        
        # Build conversation context
        recent_conversation = self._build_conversation_context(conversation_history[-6:] if conversation_history else [])
        
        # Create messages for the model
        messages = [
            SystemMessage(content=system_instruction),
            HumanMessage(content=f"""
            Context from knowledge base: {context}
            
            Recent conversation: {recent_conversation}
            
            Student's current level: {difficulty_level}
            Student's proficiency score: {session_data['proficiency_score']}/100
            Total interactions in session: {session_data['interaction_count']}
            Student's message: {message}
            
            Provide an appropriate response that matches their proficiency level and learning needs.
            """)
        ]
        
        # Get model response
        model = self.model_manager.get_active_model()
        response = model(messages)
        
        return {
            'content': response.content,
            'strategy': strategy
        }
    
    def _build_context(self, search_results: List[Dict]) -> str:
        """Build context string from search results"""
        if not search_results:
            return "No specific context found."
        
        context_parts = []
        for result in search_results[:3]:  # Use top 3 results
            context_parts.append(f"- {result['content'][:200]}...")
        
        return "\n".join(context_parts)
    
    def _build_conversation_context(self, recent_messages: List[Dict]) -> str:
        """Build conversation context from recent messages"""
        if not recent_messages:
            return "This is the beginning of the conversation."
        
        context_parts = []
        for msg in recent_messages:
            role = "Student" if msg['type'] == 'student' else "Teacher"
            context_parts.append(f"{role}: {msg['message'][:100]}...")
        
        return "\n".join(context_parts)