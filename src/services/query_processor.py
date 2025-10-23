"""
Query processing service for handling natural language queries.
"""
import re
import time
from typing import List, Optional
from src.services.interfaces import QueryProcessorInterface
from src.services.document_storage import DocumentStorageService
from src.services.llm_service import GeminiLLMService
from src.models.query import QueryResult, Citation
from src.models.document import DocumentMetadata, DocumentChunk
from src.utils.exceptions import QueryProcessingError, ValidationError, AnswerSynthesisError


class QueryProcessor(QueryProcessorInterface):
    """Service for processing natural language queries."""
    
    def __init__(self):
        """Initialize query processor."""
        self.storage_service = DocumentStorageService()
        self.llm_service = GeminiLLMService()
        self.min_query_length = 3
        self.max_query_length = 1000
    
    def process_query(self, query: str, top_k: int = 5, 
                     document_ids: Optional[List[str]] = None) -> QueryResult:
        """
        Process a natural language query and return results.
        
        Args:
            query: Natural language query
            top_k: Number of top results to retrieve
            document_ids: Optional list of document IDs to search within
            
        Returns:
            QueryResult: Query results with retrieved chunks
            
        Raises:
            QueryProcessingError: If query processing fails
        """
        start_time = time.time()
        
        try:
            # Validate query
            self.validate_query(query)
            
            # Preprocess query
            processed_query = self._preprocess_query(query)
            
            # Search for similar chunks
            similar_chunks = self.storage_service.search_similar_chunks(
                processed_query, top_k, document_ids
            )
            
            # Get document metadata for the chunks
            document_metadata = self._get_document_metadata(similar_chunks)
            
            # Prepare context for LLM
            context = self._prepare_context_for_llm(similar_chunks)
            
            # Generate synthesized answer using LLM
            try:
                synthesized_answer = self.llm_service.synthesize_answer(
                    query=processed_query,
                    context=context,
                    sources=document_metadata
                )
                answer = synthesized_answer.content
                citations = synthesized_answer.citations
            except AnswerSynthesisError as e:
                # Fallback to basic answer if LLM fails
                print(f"LLM synthesis failed: {e}, using fallback")
                answer = self._create_basic_answer(similar_chunks)
                citations = self._create_citations(similar_chunks)
            
            # Calculate processing time
            processing_time = time.time() - start_time
            
            return QueryResult.create_new(
                query=query,
                answer=answer,
                sources=document_metadata,
                citations=citations,
                processing_time=processing_time
            )
            
        except (ValidationError, QueryProcessingError):
            raise
        except Exception as e:
            raise QueryProcessingError(f"Query processing failed: {str(e)}")
    
    def validate_query(self, query: str) -> bool:
        """
        Validate query format and content.
        
        Args:
            query: Query string to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If query is invalid
        """
        if not query:
            raise ValidationError("Query cannot be empty")
        
        if not query.strip():
            raise ValidationError("Query cannot be only whitespace")
        
        if len(query.strip()) < self.min_query_length:
            raise ValidationError(
                f"Query too short (minimum {self.min_query_length} characters)"
            )
        
        if len(query) > self.max_query_length:
            raise ValidationError(
                f"Query too long (maximum {self.max_query_length} characters)"
            )
        
        # Check for potentially malicious content
        if self._contains_suspicious_content(query):
            raise ValidationError("Query contains suspicious content")
        
        return True
    
    def _preprocess_query(self, query: str) -> str:
        """
        Preprocess and normalize the query.
        
        Args:
            query: Raw query string
            
        Returns:
            str: Preprocessed query
        """
        # Strip whitespace
        processed = query.strip()
        
        # Normalize whitespace
        processed = re.sub(r'\s+', ' ', processed)
        
        # Remove excessive punctuation
        processed = re.sub(r'[!?]{2,}', '!', processed)
        processed = re.sub(r'\.{2,}', '.', processed)
        
        # Basic normalization (could be enhanced with more NLP)
        processed = processed.lower()
        
        return processed
    
    def _contains_suspicious_content(self, query: str) -> bool:
        """
        Check if query contains suspicious or potentially harmful content.
        
        Args:
            query: Query to check
            
        Returns:
            bool: True if suspicious content is found
        """
        # More reasonable checks for actual malicious patterns
        # Allow normal punctuation like apostrophes and quotes in search queries
        sql_patterns = [
            r'\b(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE)\s+(TABLE|DATABASE|INDEX)',  # More specific SQL commands
            r';\s*(DROP|DELETE|INSERT|UPDATE|ALTER|CREATE)',  # SQL injection attempts
            r'--\s*[^\s]',  # SQL comments (but allow normal dashes)
            r'/\*.*\*/',  # SQL block comments
            r'\bUNION\s+SELECT\b',  # SQL injection pattern
            r'\bOR\s+1\s*=\s*1\b',  # SQL injection pattern
        ]
        
        query_upper = query.upper()
        
        for pattern in sql_patterns:
            if re.search(pattern, query_upper):
                return True
        
        # Check for excessively long repeated characters (potential DoS)
        if re.search(r'(.)\1{100,}', query):  # Increased threshold
            return True
        
        # Check for extremely long queries (potential DoS)
        if len(query) > 10000:  # Very generous limit
            return True
        
        return False
    
    def _get_document_metadata(self, chunks: List[DocumentChunk]) -> List[DocumentMetadata]:
        """
        Get document metadata for the given chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List[DocumentMetadata]: Unique document metadata
        """
        document_ids = list(set(chunk.document_id for chunk in chunks))
        metadata_list = []
        
        for doc_id in document_ids:
            metadata = self.storage_service.get_document(doc_id)
            if metadata:
                metadata_list.append(metadata)
        
        return metadata_list
    
    def _create_citations(self, chunks: List[DocumentChunk]) -> List[Citation]:
        """
        Create citations from document chunks.
        
        Args:
            chunks: List of document chunks
            
        Returns:
            List[Citation]: Citations with relevance scores
        """
        citations = []
        
        for chunk in chunks:
            try:
                # Get document metadata for filename
                doc_metadata = self.storage_service.get_document(chunk.document_id)
                filename = doc_metadata.filename if doc_metadata else f"Document {chunk.document_id[:8]}"
                
                # Get similarity score if available
                relevance_score = getattr(chunk, 'similarity_score', 0.0)
                
                # Clean up chunk content for citation
                chunk_content = chunk.content.strip()
                if len(chunk_content) > 200:
                    # Try to break at sentence boundary
                    sentences = chunk_content.split('. ')
                    if len(sentences) > 1:
                        chunk_content = sentences[0] + "..."
                    else:
                        chunk_content = chunk_content[:200] + "..."
                
                citation = Citation(
                    document_id=chunk.document_id,
                    filename=filename,
                    chunk_content=chunk_content,
                    relevance_score=relevance_score
                )
                
                citations.append(citation)
                
            except Exception as e:
                print(f"Error creating citation for chunk {chunk.id}: {e}")
                continue
        
        return citations
    
    def _create_basic_answer(self, chunks: List[DocumentChunk]) -> str:
        """
        Create a basic answer from retrieved chunks.
        This is a placeholder until LLM integration is added.
        
        Args:
            chunks: Retrieved document chunks
            
        Returns:
            str: Basic answer
        """
        if not chunks:
            return "No relevant information found in the document collection."
        
        # Get unique content and combine intelligently
        seen_content = set()
        relevant_content = []
        
        for chunk in chunks[:5]:  # Use top 5 chunks
            # Clean and deduplicate content
            content = chunk.content.strip()
            if content and content not in seen_content:
                seen_content.add(content)
                relevant_content.append(content)
        
        if not relevant_content:
            return "No relevant information found in the document collection."
        
        # Create a more coherent answer by combining the content
        if len(relevant_content) == 1:
            return relevant_content[0]
        
        # For multiple chunks, create a structured answer
        answer = "Based on the documents:\n\n"
        
        # Combine content intelligently
        combined_text = " ".join(relevant_content)
        
        # If the combined text is too long, summarize key points
        if len(combined_text) > 800:
            # Take the most relevant chunks and create bullet points
            answer += "Key information found:\n\n"
            for i, content in enumerate(relevant_content[:3]):
                # Extract key sentences (simple approach)
                sentences = content.split('. ')
                key_sentence = sentences[0] if sentences else content[:200]
                if not key_sentence.endswith('.'):
                    key_sentence += "..."
                answer += f"• {key_sentence}\n"
        else:
            # If short enough, include the full content
            answer += combined_text
        
        return answer
    
    def get_query_suggestions(self, partial_query: str, limit: int = 5) -> List[str]:
        """
        Get query suggestions based on partial input.
        
        Args:
            partial_query: Partial query string
            limit: Maximum number of suggestions
            
        Returns:
            List[str]: Query suggestions
        """
        # This is a basic implementation
        # In a production system, this could use query logs, popular searches, etc.
        
        if len(partial_query) < 2:
            return []
        
        # Basic suggestions based on common query patterns
        suggestions = []
        
        # Add "what is" pattern
        if not partial_query.lower().startswith(('what', 'how', 'why', 'when', 'where')):
            suggestions.append(f"What is {partial_query}?")
            suggestions.append(f"How does {partial_query} work?")
        
        # Add the partial query as-is if it's reasonable length
        if len(partial_query) >= 3:
            suggestions.append(partial_query)
        
        return suggestions[:limit]
    
    def analyze_query_complexity(self, query: str) -> dict:
        """
        Analyze query complexity and characteristics.
        
        Args:
            query: Query to analyze
            
        Returns:
            dict: Query analysis results
        """
        analysis = {
            "length": len(query),
            "word_count": len(query.split()),
            "has_question_words": bool(re.search(r'\b(what|how|why|when|where|who)\b', query.lower())),
            "has_question_mark": "?" in query,
            "complexity": "simple"
        }
        
        # Determine complexity
        if analysis["word_count"] > 10:
            analysis["complexity"] = "complex"
        elif analysis["word_count"] > 5:
            analysis["complexity"] = "medium"
        
        # Check for specific patterns
        analysis["is_question"] = analysis["has_question_words"] or analysis["has_question_mark"]
        analysis["is_keyword_search"] = analysis["word_count"] <= 3 and not analysis["is_question"]
        
        return analysis   
 
    def _prepare_context_for_llm(self, chunks: List[DocumentChunk]) -> str:
        """
        Prepare context from retrieved chunks for LLM processing.
        
        Args:
            chunks: Retrieved document chunks
            
        Returns:
            str: Formatted context for LLM
        """
        if not chunks:
            return ""
        
        context_parts = []
        
        for i, chunk in enumerate(chunks):
            # Get document metadata for context
            doc_metadata = self.storage_service.get_document(chunk.document_id)
            filename = doc_metadata.filename if doc_metadata else "Unknown document"
            
            # Add chunk with source information
            context_part = f"[Source: {filename}]\n{chunk.content.strip()}"
            context_parts.append(context_part)
        
        # Join all context parts
        full_context = "\n\n---\n\n".join(context_parts)
        
        # Limit context length to avoid token limits
        max_context_length = 4000  # Conservative limit for most LLMs
        if len(full_context) > max_context_length:
            full_context = full_context[:max_context_length] + "\n\n[Context truncated due to length...]"
        
        return full_context