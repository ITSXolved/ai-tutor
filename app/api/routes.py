from flask import Blueprint, request, jsonify
from flask import request, jsonify
from werkzeug.utils import secure_filename
from services.pdf_service import PDFService
from services.teaching_service import TeachingService
from services.session_service import SessionService
from models.schemas import ChatRequest, SessionRequest, UserExperienceRequest
import loggings
api_bp = Blueprint('api', __name__)

teaching_service = TeachingService()
session_service = SessionService()


# Add this to your existing routes.py file

pdf_service = PDFService()


@api_bp.route('/upload/pdf', methods=['POST'])
def upload_pdf():
    """Upload and process PDF file for vector storage"""
    try:
        # Check if file is in request
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        
        # Get optional parameters
        subject = request.form.get('subject', 'english')
        difficulty_level = request.form.get('difficulty_level', 'auto')
        
        # Validate subject
        valid_subjects = ['english', 'math', 'science', 'history', 'general']
        if subject not in valid_subjects:
            subject = 'general'
        
        # Validate difficulty level
        valid_difficulties = ['beginner', 'intermediate', 'advanced', 'auto']
        if difficulty_level not in valid_difficulties:
            difficulty_level = 'auto'
        
        # Process the PDF
        result = pdf_service.process_uploaded_pdf(
            file=file,
            subject=subject,
            difficulty_level=difficulty_level
        )
        
        if result['success']:
            return jsonify({
                'message': 'PDF processed and stored successfully',
                'data': result
            }), 200
        else:
            return jsonify({
                'error': result.get('error', 'Unknown error'),
                'data': result
            }), 400
            
    except Exception as e:
        logging.error(f"PDF upload endpoint error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/upload/status', methods=['GET'])
def upload_status():
    """Get upload capabilities and supported formats"""
    
    # Check available PDF libraries
    capabilities = {
        'supported_formats': ['.pdf', '.txt'],
        'max_file_size_mb': 10,
        'available_extractors': [],
        'supported_subjects': ['english', 'math', 'science', 'history', 'general'],
        'supported_difficulties': ['beginner', 'intermediate', 'advanced', 'auto']
    }
    
    # Check which PDF libraries are available
    try:
        import PyPDF2
        capabilities['available_extractors'].append('PyPDF2')
    except ImportError:
        pass
    
    try:
        import pdfplumber
        capabilities['available_extractors'].append('pdfplumber')
    except ImportError:
        pass
    
    try:
        import fitz
        capabilities['available_extractors'].append('PyMuPDF')
    except ImportError:
        pass
    
    if not capabilities['available_extractors']:
        return jsonify({
            'error': 'No PDF extraction libraries available',
            'install_command': 'pip install PyPDF2 pdfplumber pymupdf',
            'capabilities': capabilities
        }), 503
    
    return jsonify({
        'message': 'PDF upload service available',
        'capabilities': capabilities
    }), 200

@api_bp.route('/documents/search', methods=['POST'])
def search_documents():
    """Search uploaded documents"""
    try:
        data = request.get_json()
        if not data or 'query' not in data:
            return jsonify({'error': 'Query is required'}), 400
        
        query = data['query']
        subject = data.get('subject')
        difficulty_level = data.get('difficulty_level')
        limit = data.get('limit', 5)
        
        # Build metadata filters
        metadata_filters = {}
        if subject:
            metadata_filters['subject'] = subject
        if difficulty_level:
            metadata_filters['difficulty_level'] = difficulty_level
        
        # Perform search
        results = pdf_service.vector_service.hybrid_search(
            query=query,
            metadata_filters=metadata_filters,
            limit=limit
        )
        
        return jsonify({
            'query': query,
            'results_count': len(results),
            'results': results
        }), 200
        
    except Exception as e:
        logging.error(f"Document search error: {e}")
        return jsonify({'error': str(e)}), 500

@api_bp.route('/documents/stats', methods=['GET'])
def document_stats():
    """Get statistics about stored documents"""
    try:
        # This would require additional database queries
        # For now, return basic info
        return jsonify({
            'message': 'Document statistics',
            'note': 'Implement statistics queries based on your Supabase schema'
        }), 200
        
    except Exception as e:
        logging.error(f"Document stats error: {e}")
        return jsonify({'error': str(e)}), 500
@api_bp.route('/session/create', methods=['POST'])
def create_session():
    """Create a new teaching session"""
    try:
        data = request.get_json() or {}
        session_id = session_service.create_session(data.get('user_data', {}))
        return jsonify({
            'session_id': session_id,
            'message': 'Session created successfully'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """Get session information"""
    try:
        session_data = session_service.get_session(session_id)
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'difficulty_level': session_data['difficulty_level'],
            'proficiency_score': session_data['proficiency_score'],
            'subject': session_data['subject'],
            'interaction_count': session_data['interaction_count'],
            'session_status': session_data.get('session_status', 'active')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/session/<session_id>/end', methods=['POST'])
def end_session(session_id):
    """End a session and store conversation in Supabase"""
    try:
        data = request.get_json() or {}
        user_experience = data.get('user_experience')
        
        success = session_service.end_session(session_id, user_experience)
        
        if not success:
            return jsonify({'error': 'Failed to end session or session not found'}), 404
        
        return jsonify({
            'message': 'Session ended successfully',
            'session_id': session_id
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/chat', methods=['POST'])
def chat():
    """Main chat endpoint for student-teacher interaction"""
    try:
        data = request.get_json()
        if not data or 'message' not in data or 'session_id' not in data:
            return jsonify({'error': 'Missing required fields'}), 400
        
        # Check if session exists and is active
        session_data = session_service.get_session(data['session_id'])
        if not session_data:
            return jsonify({'error': 'Session not found or expired'}), 404
        
        if session_data.get('session_status') != 'active':
            return jsonify({'error': 'Session is not active'}), 400
        
        response = teaching_service.process_student_message(
            session_id=data['session_id'],
            message=data['message']
        )
        
        if 'error' in response:
            return jsonify(response), 400
        
        return jsonify(response)
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/session/<session_id>/history', methods=['GET'])
def get_conversation_history(session_id):
    """Get conversation history for a session (active sessions only)"""
    try:
        session_data = session_service.get_session(session_id)
        if not session_data:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({
            'session_id': session_id,
            'conversation_history': session_data.get('conversation_history', []),
            'total_interactions': session_data.get('interaction_count', 0),
            'session_status': session_data.get('session_status', 'active')
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/user/<user_id>/sessions', methods=['GET'])
def get_user_session_history(user_id):
    """Get user's historical sessions from Supabase"""
    try:
        limit = request.args.get('limit', 10, type=int)
        sessions = session_service.get_user_session_history(user_id, limit)
        
        return jsonify({
            'user_id': user_id,
            'sessions': sessions,
            'total_sessions': len(sessions)
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/experience', methods=['POST'])
def store_user_experience():
    """Store user experience feedback"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'No data provided'}), 400
        
        required_fields = ['session_id', 'user_id']
        if not all(field in data for field in required_fields):
            return jsonify({'error': 'Missing required fields: session_id, user_id'}), 400
        
        experience_data = {
            'rating': data.get('rating'),
            'feedback': data.get('feedback'),
            'usefulness_rating': data.get('usefulness_rating'),
            'difficulty_appropriate': data.get('difficulty_appropriate'),
            'would_recommend': data.get('would_recommend'),
            'improvement_suggestions': data.get('improvement_suggestions'),
            'favorite_features': data.get('favorite_features')
        }
        
        success = session_service._store_user_experience(
            data['session_id'],
            data['user_id'],
            experience_data
        )
        
        if not success:
            return jsonify({'error': 'Failed to store user experience'}), 500
        
        return jsonify({'message': 'User experience stored successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/session/<session_id>/subject', methods=['PUT'])
def change_subject(session_id):
    """Change the subject for future extensibility"""
    try:
        data = request.get_json()
        if not data or 'subject' not in data:
            return jsonify({'error': 'Subject is required'}), 400
        
        success = session_service.update_session(session_id, {
            'subject': data['subject']
        })
        
        if not success:
            return jsonify({'error': 'Session not found'}), 404
        
        return jsonify({'message': 'Subject updated successfully'})
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@api_bp.route('/analytics/user/<user_id>', methods=['GET'])
def get_user_analytics(user_id):
    """Get user learning analytics"""
    try:
        sessions = session_service.get_user_session_history(user_id, limit=50)
        
        if not sessions:
            return jsonify({
                'user_id': user_id,
                'analytics': {
                    'total_sessions': 0,
                    'total_interactions': 0,
                    'average_proficiency_improvement': 0,
                    'favorite_subjects': [],
                    'learning_progress': []
                }
            })
        
        # Calculate analytics
        total_sessions = len(sessions)
        total_interactions = sum(session.get('total_interactions', 0) for session in sessions)
        
        proficiency_improvements = [
            session.get('proficiency_improvement', 0) 
            for session in sessions 
            if session.get('proficiency_improvement') is not None
        ]
        avg_improvement = sum(proficiency_improvements) / len(proficiency_improvements) if proficiency_improvements else 0
        
        # Subject frequency
        subjects = [session.get('subject') for session in sessions if session.get('subject')]
        subject_counts = {}
        for subject in subjects:
            subject_counts[subject] = subject_counts.get(subject, 0) + 1
        favorite_subjects = sorted(subject_counts.items(), key=lambda x: x[1], reverse=True)
        
        return jsonify({
            'user_id': user_id,
            'analytics': {
                'total_sessions': total_sessions,
                'total_interactions': total_interactions,
                'average_proficiency_improvement': round(avg_improvement, 2),
                'favorite_subjects': favorite_subjects,
                'recent_sessions': sessions[:5],
                'learning_trend': proficiency_improvements[-10:] if proficiency_improvements else []
            }
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500