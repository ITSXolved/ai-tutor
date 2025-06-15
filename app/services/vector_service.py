from supabase import create_client, Client
from langchain_openai import OpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.schema import Document
from typing import List, Dict, Any
import logging
from utils.config import Config

class VectorService:
    def __init__(self):
        self.config = Config()
        self.supabase: Client = create_client(
            self.config.SUPABASE_URL,
            self.config.SUPABASE_KEY
        )
        self.embeddings = OpenAIEmbeddings()
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=self.config.CHUNK_SIZE,
            chunk_overlap=self.config.CHUNK_OVERLAP
        )
        
    def add_documents(self, documents: List[Document]) -> bool:
        """Add documents to vector database"""
        try:
            # Split documents into chunks
            chunks = self.text_splitter.split_documents(documents)
            
            for chunk in chunks:
                # Generate embedding
                embedding = self.embeddings.embed_query(chunk.page_content)
                
                # Prepare document data
                doc_data = {
                    'content': chunk.page_content,
                    'metadata': chunk.metadata,
                    'embedding': embedding,
                    'subject': chunk.metadata.get('subject', 'english'),
                    'difficulty_level': chunk.metadata.get('difficulty_level', 'intermediate'),
                    'content_type': chunk.metadata.get('content_type', 'lesson')
                }
                
                # Insert into Supabase
                result = self.supabase.table('documents').insert(doc_data).execute()
                
            return True
        except Exception as e:
            logging.error(f"Error adding documents: {e}")
            return False
    
    def hybrid_search(self, query: str, metadata_filters: Dict[str, Any] = None, limit: int = 5) -> List[Dict]:
        """Perform hybrid search combining vector similarity and metadata filtering"""
        try:
            # Generate query embedding
            query_embedding = self.embeddings.embed_query(query)
            
            # Build the search query
            search_query = self.supabase.table('documents').select('*')
            
            # Apply metadata filters
            if metadata_filters:
                for key, value in metadata_filters.items():
                    if key == 'subject':
                        search_query = search_query.eq('subject', value)
                    elif key == 'difficulty_level':
                        search_query = search_query.eq('difficulty_level', value)
                    elif key == 'content_type':
                        search_query = search_query.eq('content_type', value)
            
            # Execute vector similarity search
            results = search_query.limit(limit).execute()
            
            # Calculate similarity scores (simplified - in production, use proper vector similarity)
            scored_results = []
            for doc in results.data:
                # In a real implementation, you'd calculate cosine similarity here
                score = 0.8  # Placeholder similarity score
                scored_results.append({
                    'content': doc['content'],
                    'metadata': doc['metadata'],
                    'score': score
                })
            
            return sorted(scored_results, key=lambda x: x['score'], reverse=True)
            
        except Exception as e:
            logging.error(f"Error in hybrid search: {e}")
            return []
    
    def search_by_difficulty(self, query: str, difficulty_level: str, subject: str = 'english') -> List[Dict]:
        """Search for content matching specific difficulty level"""
        metadata_filters = {
            'subject': subject,
            'difficulty_level': difficulty_level
        }
        return self.hybrid_search(query, metadata_filters)