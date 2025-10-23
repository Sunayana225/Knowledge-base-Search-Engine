"""
Document chunking service with sentence boundary preservation.
"""
import re
from typing import List
from src.models.document import DocumentChunk
from src.utils.exceptions import ChunkingError
from src.config.settings import config


class DocumentChunker:
    """Service for splitting documents into chunks with overlap."""
    
    def __init__(self, chunk_size: int = None, overlap: int = None):
        """
        Initialize document chunker.
        
        Args:
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
        """
        self.chunk_size = chunk_size or config.document_processing.chunk_size
        self.overlap = overlap or config.document_processing.chunk_overlap
        
        # Sentence boundary patterns
        self.sentence_endings = re.compile(r'[.!?]+\s+')
        self.paragraph_breaks = re.compile(r'\n\s*\n')
    
    def chunk_document(self, text: str, document_id: str, 
                      chunk_size: int = None, overlap: int = None) -> List[DocumentChunk]:
        """
        Split document text into overlapping chunks with sentence boundary preservation.
        
        Args:
            text: Document text to chunk
            document_id: ID of the source document
            chunk_size: Override default chunk size
            overlap: Override default overlap size
            
        Returns:
            List[DocumentChunk]: List of document chunks
            
        Raises:
            ChunkingError: If chunking fails
        """
        if not text or not text.strip():
            raise ChunkingError("Cannot chunk empty text")
        
        chunk_size = chunk_size or self.chunk_size
        overlap = overlap or self.overlap
        
        if overlap >= chunk_size:
            raise ChunkingError("Overlap size must be less than chunk size")
        
        try:
            # Normalize text
            normalized_text = self._normalize_text(text)
            
            # Create chunks using sliding window with sentence boundaries
            chunks = self._create_chunks_with_sentences(
                normalized_text, document_id, chunk_size, overlap
            )
            
            if not chunks:
                raise ChunkingError("No chunks were created from the text")
            
            return chunks
            
        except ChunkingError:
            raise
        except Exception as e:
            raise ChunkingError(f"Failed to chunk document: {str(e)}")
    
    def _normalize_text(self, text: str) -> str:
        """
        Normalize text for consistent chunking.
        
        Args:
            text: Raw text
            
        Returns:
            str: Normalized text
        """
        # Remove excessive whitespace while preserving paragraph structure
        text = re.sub(r' +', ' ', text)  # Multiple spaces to single space
        text = re.sub(r'\n +', '\n', text)  # Remove spaces after newlines
        text = re.sub(r' +\n', '\n', text)  # Remove spaces before newlines
        text = re.sub(r'\n{3,}', '\n\n', text)  # Max 2 consecutive newlines
        
        return text.strip()
    
    def _create_chunks_with_sentences(self, text: str, document_id: str, 
                                    chunk_size: int, overlap: int) -> List[DocumentChunk]:
        """
        Create chunks while trying to preserve sentence boundaries.
        
        Args:
            text: Normalized text
            document_id: Document ID
            chunk_size: Maximum chunk size
            overlap: Overlap size
            
        Returns:
            List[DocumentChunk]: List of chunks
        """
        chunks = []
        text_length = len(text)
        start_pos = 0
        chunk_index = 0
        
        while start_pos < text_length:
            # Calculate end position for this chunk
            end_pos = min(start_pos + chunk_size, text_length)
            
            # If this isn't the last chunk, try to find a good break point
            if end_pos < text_length:
                end_pos = self._find_optimal_break_point(text, start_pos, end_pos)
            
            # Extract chunk content
            chunk_content = text[start_pos:end_pos].strip()
            
            if chunk_content:  # Only create non-empty chunks
                chunk = DocumentChunk.create_new(
                    document_id=document_id,
                    content=chunk_content,
                    chunk_index=chunk_index,
                    start_position=start_pos,
                    end_position=end_pos
                )
                chunks.append(chunk)
                chunk_index += 1
            
            # Calculate next start position with overlap
            if end_pos >= text_length:
                break
            
            # Move start position forward, accounting for overlap
            next_start = end_pos - overlap
            
            # Ensure we make progress (avoid infinite loops)
            if next_start <= start_pos:
                next_start = start_pos + max(1, chunk_size // 2)
            
            start_pos = next_start
        
        return chunks
    
    def _find_optimal_break_point(self, text: str, start_pos: int, max_end_pos: int) -> int:
        """
        Find the best position to break a chunk, preferring sentence boundaries.
        
        Args:
            text: Full text
            start_pos: Start position of chunk
            max_end_pos: Maximum end position
            
        Returns:
            int: Optimal break position
        """
        # Look for sentence endings within the last 20% of the chunk
        search_start = max(start_pos, max_end_pos - (max_end_pos - start_pos) // 5)
        search_text = text[search_start:max_end_pos]
        
        # Find sentence endings in reverse order (prefer later breaks)
        sentence_matches = list(self.sentence_endings.finditer(search_text))
        if sentence_matches:
            # Use the last sentence ending found
            last_match = sentence_matches[-1]
            return search_start + last_match.end()
        
        # Look for paragraph breaks
        paragraph_matches = list(self.paragraph_breaks.finditer(search_text))
        if paragraph_matches:
            last_match = paragraph_matches[-1]
            return search_start + last_match.start()
        
        # Look for any whitespace as a fallback
        for i in range(max_end_pos - 1, search_start - 1, -1):
            if text[i].isspace():
                return i
        
        # If no good break point found, use the maximum position
        return max_end_pos
    
    def get_chunk_context(self, chunk: DocumentChunk, full_text: str, 
                         context_size: int = 200) -> dict:
        """
        Get surrounding context for a chunk.
        
        Args:
            chunk: Document chunk
            full_text: Full document text
            context_size: Number of characters of context on each side
            
        Returns:
            dict: Chunk content with surrounding context
        """
        start_context = max(0, chunk.start_position - context_size)
        end_context = min(len(full_text), chunk.end_position + context_size)
        
        context_text = full_text[start_context:end_context]
        
        # Mark the actual chunk boundaries
        chunk_start_in_context = chunk.start_position - start_context
        chunk_end_in_context = chunk.end_position - start_context
        
        return {
            'full_context': context_text,
            'chunk_start': chunk_start_in_context,
            'chunk_end': chunk_end_in_context,
            'chunk_content': chunk.content
        }
    
    def validate_chunks(self, chunks: List[DocumentChunk], original_text: str) -> bool:
        """
        Validate that chunks properly cover the original text.
        
        Args:
            chunks: List of chunks to validate
            original_text: Original document text
            
        Returns:
            bool: True if validation passes
            
        Raises:
            ChunkingError: If validation fails
        """
        if not chunks:
            raise ChunkingError("No chunks to validate")
        
        # Check chunk ordering
        for i in range(len(chunks) - 1):
            if chunks[i].chunk_index >= chunks[i + 1].chunk_index:
                raise ChunkingError("Chunks are not properly ordered")
        
        # Check position consistency
        for chunk in chunks:
            if chunk.start_position >= chunk.end_position:
                raise ChunkingError(f"Invalid chunk positions: {chunk.start_position} >= {chunk.end_position}")
            
            if chunk.end_position > len(original_text):
                raise ChunkingError(f"Chunk end position exceeds text length: {chunk.end_position} > {len(original_text)}")
            
            # Verify chunk content matches positions
            expected_content = original_text[chunk.start_position:chunk.end_position].strip()
            if chunk.content != expected_content:
                # Allow for minor whitespace differences
                if chunk.content.replace(' ', '').replace('\n', '') != expected_content.replace(' ', '').replace('\n', ''):
                    raise ChunkingError(f"Chunk content doesn't match expected content at positions {chunk.start_position}-{chunk.end_position}")
        
        return True