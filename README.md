
# Hybrid RAG Teaching Agent

An intelligent English language teaching agent that adapts to student proficiency levels using hybrid vector search and conversational AI.

## Features

- **Adaptive Difficulty**: Automatically adjusts teaching level based on student interactions
- **Hybrid Search**: Combines vector similarity search with metadata filtering
- **Persistent Session Management**: 
  - Active sessions stored in Redis for fast access
  - Completed sessions archived in Supabase with full conversation history
  - Automatic session cleanup and data persistence
- **User Experience Tracking**: Comprehensive feedback collection and analytics
- **Multiple Model Support**: LearnLM (primary) and OpenRouter models (fallback)
- **Subject Extensibility**: Framework supports multiple subjects (currently English)
- **Learning Analytics**: Progress tracking, proficiency improvement, and usage patterns
- **Conversation Archival**: Complete conversation history stored permanently in Supabase

## Quick Start

1. **Clone and setup**:
   ```bash
   git clone <repository>
   cd teaching-rag-agent
   cp .env.example .env
   # Edit .env with your API keys
   ```

2. **Run with Docker**:
   ```bash
   docker-compose up --build
   ```

3. **Access the API**:
   - Health check: `GET http://localhost:5000/health`
   - Create session: `POST http://localhost:5000/api/v1/session/create`
   - Chat: `POST http://localhost:5000/api/v1/chat`

## API Usage

### Create Session
```bash
curl -X POST http://localhost:5000/api/v1/session/create \
  -H "Content-Type: application/json" \
  -d '{"user_data": {"user_id": "student123", "name": "John"}}'
```

### Chat
```bash
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "message": "Hello, I want to learn English"
  }'
```

### End Session and Store Experience
```bash
curl -X POST http://localhost:5000/api/v1/session/your-session-id/end \
  -H "Content-Type: application/json" \
  -d '{
    "user_experience": {
      "rating": 5,
      "feedback": "Great learning experience!",
      "usefulness_rating": 4,
      "difficulty_appropriate": true,
      "would_recommend": true
    }
  }'
```

### Get User Session History
```bash
curl -X GET http://localhost:5000/api/v1/user/student123/sessions?limit=5
```

### Store User Experience (Standalone)
```bash
curl -X POST http://localhost:5000/api/v1/experience \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "your-session-id",
    "user_id": "student123",
    "rating": 4,
    "feedback": "Very helpful session",
    "usefulness_rating": 5,
    "difficulty_appropriate": true,
    "would_recommend": true,
    "improvement_suggestions": "More practice exercises",
    "favorite_features": ["adaptive difficulty", "instant feedback"]
  }'
```

### Get User Analytics
```bash
curl -X GET http://localhost:5000/api/v1/analytics/user/student123
```

## Architecture

- **Flask API**: RESTful endpoints for chat and session management
- **LangChain**: RAG pipeline and model management
- **Supabase**: Vector database for hybrid search + conversation archival
- **Redis**: Active session and conversation history storage
- **LearnLM/OpenRouter**: Adaptive language models for teaching

## Session Lifecycle

1. **Session Creation**: New session created in Redis with user data and initial proficiency
2. **Active Learning**: Real-time chat with adaptive responses, stored in Redis for fast access
3. **Progress Tracking**: Continuous proficiency analysis and difficulty adjustment
4. **Session End**: 
   - Full conversation history moved to Supabase for permanent storage
   - User experience feedback collected and stored
   - Session analytics calculated and archived
   - Redis session data cleared to free memory
5. **Historical Access**: Past sessions and analytics available via Supabase queries

## Data Storage Strategy

- **Redis (Active Sessions)**: Fast access for ongoing conversations, temporary storage
- **Supabase (Permanent Archive)**: 
  - Complete conversation histories
  - Session summaries and analytics
  - User experience feedback
  - Learning content and embeddings

## Sample Workflow

```bash
# 1. Create a new learning session
curl -X POST http://localhost:5000/api/v1/session/create \
  -H "Content-Type: application/json" \
  -d '{"user_data": {"user_id": "alice123", "name": "Alice"}}'

# Response: {"session_id": "uuid-here", "message": "Session created successfully"}

# 2. Start learning conversation
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "message": "Hi, I want to practice English conversation"
  }'

# 3. Continue chatting (system adapts difficulty automatically)
curl -X POST http://localhost:5000/api/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "uuid-here",
    "message": "Can you help me with grammar?"
  }'

# 4. End session and provide feedback
curl -X POST http://localhost:5000/api/v1/session/uuid-here/end \
  -H "Content-Type: application/json" \
  -d '{
    "user_experience": {
      "rating": 5,
      "feedback": "Very helpful session!",
      "usefulness_rating": 4,
      "difficulty_appropriate": true,
      "would_recommend": true
    }
  }'

# 5. View learning history and analytics
curl -X GET http://localhost:5000/api/v1/user/alice123/sessions
curl -X GET http://localhost:5000/api/v1/analytics/user/alice123
```

## Development

Run locally without Docker:
```bash
pip install -r requirements.txt
python data/scripts/populate_db.py  # Setup database
python app/main.py
```
```

This complete implementation provides:

✅ **Hybrid Vector Search**: Combines vector similarity with metadata filtering
✅ **Adaptive Difficulty**: Automatically adjusts based on student proficiency
✅ **Session Management**: Redis-based conversation tracking
✅ **Multiple Model Support**: LearnLM primary, OpenRouter fallback
✅ **Extensible Architecture**: Easy to add new subjects
✅ **Production Ready**: Docker configuration for deployment
✅ **Clean Structure**: Modular design with separation of concerns

The system automatically analyzes student responses, adjusts difficulty levels, and provides contextually relevant teaching content through the hybrid RAG approach.