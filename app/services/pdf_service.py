
import os
import uuid
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import tempfile
import mimetypes

# PDF parsing libraries
try:
    import PyPDF2
    PYPDF2_AVAILABLE = True
except ImportError:
    PYPDF2_AVAILABLE = False

try:
    import pdfplumber
    PDFPLUMBER_AVAILABLE = True
except ImportError:
    PDFPLUMBER_AVAILABLE = False

try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from services.vector_service import VectorService
from utils.config import Config

class PDFService:
    def __init__(self):
        self.config = Config()
        self.vector_service = VectorService()
        self.upload_dir = Path("data/uploads")
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Text splitter for large documents
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,  # Larger chunks for PDFs
            chunk_overlap=100,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Supported file types
        self.supported_types = {
            'application/pdf': '.pdf',
            'text/plain': '.txt'
        }
        
    def validate_file(self, file) -> Tuple[bool, str]:
        """Validate uploaded file"""
        if not file:
            return False, "No file provided"
        
        if not file.filename:
            return False, "No filename provided"
        
        # Check file extension
        if not file.filename.lower().endswith(('.pdf', '.txt')):
            return False, "Only PDF and TXT files are supported"
        
        # Check file size (10MB limit)
        file.seek(0, 2)  # Seek to end
        size = file.tell()
        file.seek(0)     # Reset to beginning
        
        max_size = 10 * 1024 * 1024  # 10MB
        if size > max_size:
            return False, f"File too large. Maximum size is {max_size // (1024*1024)}MB"
        
        if size == 0:
            return False, "Empty file"
        
        return True, "Valid file"
    
    def save_uploaded_file(self, file) -> str:
        """Save uploaded file temporarily"""
        # Generate unique filename
        file_id = str(uuid.uuid4())
        original_name = file.filename
        extension = Path(original_name).suffix
        
        temp_filename = f"{file_id}_{original_name}"
        temp_path = self.upload_dir / temp_filename
        
        # Save file
        file.save(str(temp_path))
        
        logging.info(f"File saved: {temp_path}")
        return str(temp_path)
    
    def extract_pdf_metadata(self, file_path: str) -> Dict[str, Any]:
        """Extract metadata from PDF"""
        metadata = {
            'filename': Path(file_path).name,
            'file_size': os.path.getsize(file_path),
            'file_type': 'pdf',
            'total_pages': 0,
            'title': '',
            'author': '',
            'subject': '',
            'creator': '',
            'creation_date': '',
            'extraction_method': 'unknown'
        }
        
        # Try different PDF libraries for metadata
        if PYPDF2_AVAILABLE:
            try:
                with open(file_path, 'rb') as file:
                    pdf_reader = PyPDF2.PdfReader(file)
                    metadata['total_pages'] = len(pdf_reader.pages)
                    metadata['extraction_method'] = 'PyPDF2'
                    
                    # Extract document info
                    if pdf_reader.metadata:
                        metadata['title'] = pdf_reader.metadata.get('/Title', '')
                        metadata['author'] = pdf_reader.metadata.get('/Author', '')
                        metadata['subject'] = pdf_reader.metadata.get('/Subject', '')
                        metadata['creator'] = pdf_reader.metadata.get('/Creator', '')
                        
            except Exception as e:
                logging.warning(f"PyPDF2 metadata extraction failed: {e}")
        
        elif PYMUPDF_AVAILABLE:
            try:
                doc = fitz.open(file_path)
                metadata['total_pages'] = doc.page_count
                metadata['extraction_method'] = 'PyMuPDF'
                
                doc_metadata = doc.metadata
                metadata['title'] = doc_metadata.get('title', '')
                metadata['author'] = doc_metadata.get('author', '')
                metadata['subject'] = doc_metadata.get('subject', '')
                metadata['creator'] = doc_metadata.get('creator', '')
                
                doc.close()
            except Exception as e:
                logging.warning(f"PyMuPDF metadata extraction failed: {e}")
        
        return metadata
    
    def extract_text_pypdf2(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text using PyPDF2"""
        pages_content = []
        
        try:
            with open(file_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                
                for page_num, page in enumerate(pdf_reader.pages, 1):
                    try:
                        text = page.extract_text()
                        if text.strip():
                            pages_content.append({
                                'page_number': page_num,
                                'content': text.strip(),
                                'word_count': len(text.split()),
                                'extraction_method': 'PyPDF2'
                            })
                    except Exception as e:
                        logging.warning(f"Error extracting page {page_num}: {e}")
                        continue
                        
        except Exception as e:
            logging.error(f"PyPDF2 extraction failed: {e}")
            
        return pages_content
    
    def extract_text_pdfplumber(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text using pdfplumber (better for complex layouts)"""
        pages_content = []
        
        try:
            with pdfplumber.open(file_path) as pdf:
                for page_num, page in enumerate(pdf.pages, 1):
                    try:
                        text = page.extract_text()
                        if text and text.strip():
                            pages_content.append({
                                'page_number': page_num,
                                'content': text.strip(),
                                'word_count': len(text.split()),
                                'extraction_method': 'pdfplumber',
                                'page_width': page.width,
                                'page_height': page.height
                            })
                    except Exception as e:
                        logging.warning(f"Error extracting page {page_num}: {e}")
                        continue
                        
        except Exception as e:
            logging.error(f"pdfplumber extraction failed: {e}")
            
        return pages_content
    
    def extract_text_pymupdf(self, file_path: str) -> List[Dict[str, Any]]:
        """Extract text using PyMuPDF (fastest, good for simple layouts)"""
        pages_content = []
        
        try:
            doc = fitz.open(file_path)
            
            for page_num in range(doc.page_count):
                try:
                    page = doc[page_num]
                    text = page.get_text()
                    
                    if text.strip():
                        pages_content.append({
                            'page_number': page_num + 1,
                            'content': text.strip(),
                            'word_count': len(text.split()),
                            'extraction_method': 'PyMuPDF',
                            'page_rect': page.rect
                        })
                except Exception as e:
                    logging.warning(f"Error extracting page {page_num + 1}: {e}")
                    continue
            
            doc.close()
            
        except Exception as e:
            logging.error(f"PyMuPDF extraction failed: {e}")
            
        return pages_content
    
    def extract_text_from_pdf(self, file_path: str) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """Extract text using the best available method"""
        
        # Extract metadata first
        metadata = self.extract_pdf_metadata(file_path)
        
        # Try extraction methods in order of preference
        pages_content = []
        
        # 1. Try pdfplumber (best for complex layouts)
        if PDFPLUMBER_AVAILABLE and not pages_content:
            logging.info("Trying pdfplumber extraction...")
            pages_content = self.extract_text_pdfplumber(file_path)
            if pages_content:
                logging.info(f"pdfplumber extracted {len(pages_content)} pages")
        
        # 2. Try PyMuPDF (fastest)
        if PYMUPDF_AVAILABLE and not pages_content:
            logging.info("Trying PyMuPDF extraction...")
            pages_content = self.extract_text_pymupdf(file_path)
            if pages_content:
                logging.info(f"PyMuPDF extracted {len(pages_content)} pages")
        
        # 3. Fallback to PyPDF2
        if PYPDF2_AVAILABLE and not pages_content:
            logging.info("Trying PyPDF2 extraction...")
            pages_content = self.extract_text_pypdf2(file_path)
            if pages_content:
                logging.info(f"PyPDF2 extracted {len(pages_content)} pages")
        
        if not pages_content:
            raise ValueError("Could not extract text from PDF using any available method")
        
        return pages_content, metadata
    
    def process_extracted_content(self, pages_content: List[Dict], metadata: Dict, 
                                subject: str = 'english', difficulty_level: str = 'intermediate') -> List[Document]:
        """Process extracted content into documents for vector storage"""
        
        documents = []
        
        # Combine all text for analysis
        full_text = " ".join([page['content'] for page in pages_content])
        
        # Auto-detect difficulty level based on content complexity
        detected_difficulty = self._detect_difficulty_level(full_text)
        if detected_difficulty:
            difficulty_level = detected_difficulty
        
        # Create documents for each page
        for page_data in pages_content:
            page_content = page_data['content']
            
            # Skip very short pages
            if len(page_content.split()) < 10:
                continue
            
            # Create document metadata
            doc_metadata = {
                'source': metadata['filename'],
                'page_number': page_data['page_number'],
                'total_pages': metadata['total_pages'],
                'word_count': page_data['word_count'],
                'extraction_method': page_data['extraction_method'],
                'file_size': metadata['file_size'],
                'upload_timestamp': metadata.get('upload_timestamp'),
                'content_type': 'pdf_page',
                'subject': subject,
                'difficulty_level': difficulty_level,
                'pdf_title': metadata.get('title', ''),
                'pdf_author': metadata.get('author', ''),
            }
            
            # Create document
            document = Document(
                page_content=page_content,
                metadata=doc_metadata
            )
            
            documents.append(document)
        
        # Split large documents if needed
        if documents:
            documents = self.text_splitter.split_documents(documents)
            
        return documents
    
    def _detect_difficulty_level(self, text: str) -> Optional[str]:
        """Auto-detect difficulty level based on text complexity"""
        words = text.split()
        
        if len(words) < 50:
            return None
        
        # Simple heuristics for difficulty detection
        avg_word_length = sum(len(word) for word in words) / len(words)
        sentence_count = text.count('.') + text.count('!') + text.count('?')
        avg_sentence_length = len(words) / max(sentence_count, 1)
        
        # Complex vocabulary indicators
        complex_words = sum(1 for word in words if len(word) > 8)
        complex_ratio = complex_words / len(words)
        
        # Difficulty scoring
        if avg_word_length <= 4.5 and avg_sentence_length <= 12 and complex_ratio <= 0.1:
            return 'beginner'
        elif avg_word_length >= 6 and avg_sentence_length >= 20 and complex_ratio >= 0.2:
            return 'advanced'
        else:
            return 'intermediate'
    
    def store_in_vector_database(self, documents: List[Document]) -> Dict[str, Any]:
        """Store processed documents in vector database"""
        
        try:
            success = self.vector_service.add_documents(documents)
            
            if success:
                result = {
                    'success': True,
                    'documents_stored': len(documents),
                    'total_chunks': len(documents),
                    'subjects': list(set(doc.metadata.get('subject', 'unknown') for doc in documents)),
                    'difficulty_levels': list(set(doc.metadata.get('difficulty_level', 'unknown') for doc in documents)),
                    'source_files': list(set(doc.metadata.get('source', 'unknown') for doc in documents))
                }
                
                logging.info(f"Successfully stored {len(documents)} document chunks")
                return result
            else:
                return {
                    'success': False,
                    'error': 'Failed to store documents in vector database'
                }
                
        except Exception as e:
            logging.error(f"Error storing documents: {e}")
            return {
                'success': False,
                'error': str(e)
            }
    
    def cleanup_temp_file(self, file_path: str):
        """Clean up temporary uploaded file"""
        try:
            if os.path.exists(file_path):
                os.remove(file_path)
                logging.info(f"Cleaned up temp file: {file_path}")
        except Exception as e:
            logging.warning(f"Failed to cleanup temp file {file_path}: {e}")
    
    def process_uploaded_pdf(self, file, subject: str = 'english', 
                           difficulty_level: str = 'auto') -> Dict[str, Any]:
        """Complete PDF processing pipeline"""
        
        temp_file_path = None
        
        try:
            # Step 1: Validate file
            valid, message = self.validate_file(file)
            if not valid:
                return {'success': False, 'error': message}
            
            # Step 2: Save file temporarily
            temp_file_path = self.save_uploaded_file(file)
            
            # Step 3: Extract text and metadata
            if file.filename.lower().endswith('.pdf'):
                pages_content, metadata = self.extract_text_from_pdf(temp_file_path)
            else:  # .txt file
                with open(temp_file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                pages_content = [{
                    'page_number': 1,
                    'content': content,
                    'word_count': len(content.split()),
                    'extraction_method': 'text_file'
                }]
                metadata = {
                    'filename': file.filename,
                    'file_size': os.path.getsize(temp_file_path),
                    'file_type': 'txt',
                    'total_pages': 1
                }
            
            # Add upload timestamp
            from datetime import datetime
            metadata['upload_timestamp'] = datetime.now().isoformat()
            
            # Step 4: Process content into documents
            if difficulty_level == 'auto':
                difficulty_level = 'intermediate'  # Default
            
            documents = self.process_extracted_content(
                pages_content, metadata, subject, difficulty_level
            )
            
            # Step 5: Store in vector database
            storage_result = self.store_in_vector_database(documents)
            
            # Step 6: Prepare result
            result = {
                'success': storage_result['success'],
                'filename': metadata['filename'],
                'file_size': metadata['file_size'],
                'total_pages': metadata['total_pages'],
                'extraction_method': pages_content[0]['extraction_method'] if pages_content else 'unknown',
                'documents_created': len(documents),
                'subject': subject,
                'difficulty_level': documents[0].metadata.get('difficulty_level') if documents else difficulty_level,
                'storage_result': storage_result
            }
            
            if not storage_result['success']:
                result['error'] = storage_result.get('error', 'Unknown storage error')
            
            return result
            
        except Exception as e:
            logging.error(f"Error processing PDF: {e}")
            return {
                'success': False,
                'error': str(e),
                'filename': file.filename if file else 'unknown'
            }
        
        finally:
            # Always cleanup temp file
            if temp_file_path:
                self.cleanup_temp_file(temp_file_path)