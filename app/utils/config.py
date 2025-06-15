import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Flask config
    SECRET_KEY = os.getenv('SECRET_KEY', 'dev-secret-key')
    
    # Model configurations
    OPENROUTER_API_KEY = os.getenv('OPENROUTER_API_KEY')
    GOOGLE_API_KEY = os.getenv('GOOGLE_API_KEY')
    LEARNLM_MODEL = "learnlm-2.0-flash-experimental"
    OPENROUTER_MODEL = os.getenv('OPEN_ROUTER_MODEL')

    
    # Database configurations
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    SUPABASE_KEY = os.getenv('SUPABASE_KEY')
    
    # Redis configuration
    REDIS_URL = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
    
    # RAG configurations
    VECTOR_DIMENSION = 1536
    CHUNK_SIZE = 500
    CHUNK_OVERLAP = 50
    TOP_K_RESULTS = 5
    
    # Teaching configurations
    DIFFICULTY_LEVELS = ['beginner', 'intermediate', 'advanced']
    DEFAULT_DIFFICULTY = 'intermediate'
    PREFER_LEARNLM=os.getenv('PREFER_LEARNLM')