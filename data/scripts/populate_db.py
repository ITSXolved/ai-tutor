from supabase import create_client
import os
from dotenv import load_dotenv

load_dotenv()

def setup_supabase_tables():
    """Setup Supabase tables for vector storage and conversation history"""
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    # SQL to create all required tables
    create_tables_sql = """
    -- Enable the vector extension
    CREATE EXTENSION IF NOT EXISTS vector;
    
    -- Documents table for RAG content
    CREATE TABLE IF NOT EXISTS documents (
        id SERIAL PRIMARY KEY,
        content TEXT NOT NULL,
        metadata JSONB,
        embedding vector(1536),
        subject TEXT DEFAULT 'english',
        difficulty_level TEXT DEFAULT 'intermediate',
        content_type TEXT DEFAULT 'lesson',
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Conversation history table
    CREATE TABLE IF NOT EXISTS conversation_history (
        id SERIAL PRIMARY KEY,
        session_id UUID NOT NULL,
        user_id TEXT NOT NULL,
        conversation_data JSONB NOT NULL,
        message_count INTEGER DEFAULT 0,
        subject TEXT DEFAULT 'english',
        final_difficulty_level TEXT,
        final_proficiency_score INTEGER,
        created_at TIMESTAMP,
        ended_at TIMESTAMP,
        session_duration_minutes DECIMAL(10,2) DEFAULT 0
    );
    
    -- Session summaries table
    CREATE TABLE IF NOT EXISTS session_summaries (
        id SERIAL PRIMARY KEY,
        session_id UUID NOT NULL UNIQUE,
        user_id TEXT NOT NULL,
        subject TEXT DEFAULT 'english',
        initial_proficiency_score INTEGER DEFAULT 50,
        final_proficiency_score INTEGER DEFAULT 50,
        proficiency_improvement INTEGER DEFAULT 0,
        initial_difficulty_level TEXT DEFAULT 'intermediate',
        final_difficulty_level TEXT DEFAULT 'intermediate',
        total_interactions INTEGER DEFAULT 0,
        session_duration_minutes DECIMAL(10,2) DEFAULT 0,
        created_at TIMESTAMP,
        ended_at TIMESTAMP,
        session_status TEXT DEFAULT 'active'
    );
    
    -- User experiences table
    CREATE TABLE IF NOT EXISTS user_experiences (
        id SERIAL PRIMARY KEY,
        session_id UUID NOT NULL,
        user_id TEXT NOT NULL,
        rating INTEGER CHECK (rating >= 1 AND rating <= 5),
        feedback_text TEXT,
        usefulness_rating INTEGER CHECK (usefulness_rating >= 1 AND usefulness_rating <= 5),
        difficulty_appropriate BOOLEAN,
        would_recommend BOOLEAN,
        improvement_suggestions TEXT,
        favorite_features JSONB,
        created_at TIMESTAMP DEFAULT NOW()
    );
    
    -- Create indexes for documents table
    CREATE INDEX IF NOT EXISTS documents_embedding_idx 
    ON documents USING ivfflat (embedding vector_cosine_ops);
    
    CREATE INDEX IF NOT EXISTS documents_subject_idx ON documents(subject);
    CREATE INDEX IF NOT EXISTS documents_difficulty_idx ON documents(difficulty_level);
    CREATE INDEX IF NOT EXISTS documents_content_type_idx ON documents(content_type);
    
    -- Create indexes for conversation_history table
    CREATE INDEX IF NOT EXISTS conversation_history_session_idx ON conversation_history(session_id);
    CREATE INDEX IF NOT EXISTS conversation_history_user_idx ON conversation_history(user_id);
    CREATE INDEX IF NOT EXISTS conversation_history_created_idx ON conversation_history(created_at);
    
    -- Create indexes for session_summaries table
    CREATE INDEX IF NOT EXISTS session_summaries_session_idx ON session_summaries(session_id);
    CREATE INDEX IF NOT EXISTS session_summaries_user_idx ON session_summaries(user_id);
    CREATE INDEX IF NOT EXISTS session_summaries_created_idx ON session_summaries(created_at);
    CREATE INDEX IF NOT EXISTS session_summaries_status_idx ON session_summaries(session_status);
    
    -- Create indexes for user_experiences table
    CREATE INDEX IF NOT EXISTS user_experiences_session_idx ON user_experiences(session_id);
    CREATE INDEX IF NOT EXISTS user_experiences_user_idx ON user_experiences(user_id);
    CREATE INDEX IF NOT EXISTS user_experiences_created_idx ON user_experiences(created_at);
    """
    
    try:
        supabase.query(create_tables_sql).execute()
        print("✅ All Supabase tables created successfully!")
    except Exception as e:
        print(f"❌ Error creating tables: {e}")

def populate_sample_content():
    """Populate sample teaching content"""
    supabase = create_client(
        os.getenv('SUPABASE_URL'),
        os.getenv('SUPABASE_KEY')
    )
    
    sample_content = [
        {
            'content': 'Basic English greetings include: Hello, Hi, Good morning, Good afternoon, Good evening, How are you?',
            'metadata': {'topic': 'greetings', 'lesson_type': 'vocabulary'},
            'subject': 'english',
            'difficulty_level': 'beginner',
            'content_type': 'lesson'
        },
        {
            'content': 'Present tense formation: Subject + base verb (for I, you, we, they) or Subject + verb+s (for he, she, it). Example: I eat, She eats.',
            'metadata': {'topic': 'grammar', 'lesson_type': 'grammar_rule'},
            'subject': 'english',
            'difficulty_level': 'beginner',
            'content_type': 'lesson'
        },
        {
            'content': 'Advanced vocabulary for business: negotiate, collaborate, strategize, implement, optimize, analyze, synthesize.',
            'metadata': {'topic': 'business_vocabulary', 'lesson_type': 'vocabulary'},
            'subject': 'english',
            'difficulty_level': 'advanced',
            'content_type': 'lesson'
        },
        {
            'content': 'Conditional sentences: First conditional (If + present simple, will + base verb), Second conditional (If + past simple, would + base verb).',
            'metadata': {'topic': 'conditionals', 'lesson_type': 'grammar_rule'},
            'subject': 'english',
            'difficulty_level': 'intermediate',
            'content_type': 'lesson'
        },
        {
            'content': 'Test question: Choose the correct form: "She _____ to school every day." a) go b) goes c) going d) gone',
            'metadata': {'topic': 'present_tense', 'correct_answer': 'b'},
            'subject': 'english',
            'difficulty_level': 'beginner',
            'content_type': 'test_question'
        }
    ]
    
    try:
        for content in sample_content:
            result = supabase.table('documents').insert(content).execute()
        print("✅ Sample content populated successfully!")
    except Exception as e:
        print(f"❌ Error populating sample content: {e}")

if __name__ == "__main__":
    print("🚀 Setting up Supabase database...")
    setup_supabase_tables()
    print("\n📚 Populating sample content...")
    populate_sample_content()
    print("\n✨ Database setup complete!")