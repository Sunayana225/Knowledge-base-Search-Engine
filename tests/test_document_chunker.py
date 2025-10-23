"""
Tests for document chunking service.
"""
import pytest
from src.services.document_chunker import DocumentChunker
from src.utils.exceptions import ChunkingError


class TestDocumentChunker:
    """Test cases for DocumentChunker."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.chunker = DocumentChunker(chunk_size=100, overlap=20)
    
    def test_chunk_document_basic(self):
        """Test basic document chunking."""
        text = "This is a test document. It has multiple sentences. Each sentence should be preserved in chunks. The chunking algorithm should respect sentence boundaries when possible."
        document_id = "test-doc-1"
        
        chunks = self.chunker.chunk_document(text, document_id)
        
        assert len(chunks) > 0
        assert all(chunk.document_id == document_id for chunk in chunks)
        assert all(chunk.chunk_index == i for i, chunk in enumerate(chunks))
        assert all(len(chunk.content) <= 100 for chunk in chunks)
    
    def test_chunk_document_with_paragraphs(self):
        """Test chunking document with paragraph breaks."""
        text = """This is the first paragraph. It contains multiple sentences.

This is the second paragraph. It also has several sentences for testing.

This is the third paragraph. The chunker should handle paragraph breaks properly."""
        
        document_id = "test-doc-2"
        chunks = self.chunker.chunk_document(text, document_id, chunk_size=80, overlap=15)
        
        assert len(chunks) > 1
        # Verify chunks are properly ordered
        for i in range(len(chunks) - 1):
            assert chunks[i].chunk_index < chunks[i + 1].chunk_index
    
    def test_chunk_document_empty_text(self):
        """Test chunking empty text."""
        with pytest.raises(ChunkingError, match="Cannot chunk empty text"):
            self.chunker.chunk_document("", "test-doc")
    
    def test_chunk_document_whitespace_only(self):
        """Test chunking whitespace-only text."""
        with pytest.raises(ChunkingError, match="Cannot chunk empty text"):
            self.chunker.chunk_document("   \n\t   ", "test-doc")
    
    def test_chunk_document_invalid_overlap(self):
        """Test chunking with invalid overlap size."""
        text = "This is a test document."
        
        with pytest.raises(ChunkingError, match="Overlap size must be less than chunk size"):
            self.chunker.chunk_document(text, "test-doc", chunk_size=50, overlap=60)
    
    def test_chunk_positions_consistency(self):
        """Test that chunk positions are consistent."""
        text = "First sentence. Second sentence. Third sentence. Fourth sentence. Fifth sentence."
        document_id = "test-doc-3"
        
        chunks = self.chunker.chunk_document(text, document_id, chunk_size=30, overlap=10)
        
        # Verify positions are valid
        for chunk in chunks:
            assert chunk.start_position >= 0
            assert chunk.end_position > chunk.start_position
            assert chunk.end_position <= len(text)
            
            # Verify content matches positions
            expected_content = text[chunk.start_position:chunk.end_position].strip()
            assert chunk.content == expected_content
    
    def test_chunk_overlap_functionality(self):
        """Test that overlap between chunks works correctly."""
        text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."
        document_id = "test-doc-4"
        
        chunks = self.chunker.chunk_document(text, document_id, chunk_size=25, overlap=10)
        
        if len(chunks) > 1:
            # Check that there's some overlap between consecutive chunks
            for i in range(len(chunks) - 1):
                current_chunk = chunks[i]
                next_chunk = chunks[i + 1]
                
                # There should be some overlap in positions
                overlap_start = max(current_chunk.start_position, next_chunk.start_position - 10)
                overlap_end = min(current_chunk.end_position, next_chunk.start_position + 10)
                
                # Verify overlap exists (within reasonable bounds)
                assert overlap_start < overlap_end or abs(current_chunk.end_position - next_chunk.start_position) <= 15
    
    def test_find_optimal_break_point_sentence_boundary(self):
        """Test finding optimal break points at sentence boundaries."""
        text = "This is sentence one. This is sentence two. This is sentence three."
        start_pos = 0
        max_end_pos = 30  # Should break after first sentence
        
        break_point = self.chunker._find_optimal_break_point(text, start_pos, max_end_pos)
        
        # Should break after the first sentence
        assert break_point <= max_end_pos
        assert text[break_point - 2:break_point] == ". " or text[break_point - 1] == "."
    
    def test_normalize_text(self):
        """Test text normalization."""
        messy_text = "This  has   multiple    spaces.\n\n\n\nAnd many newlines.\n \n  \nAnd mixed whitespace."
        
        normalized = self.chunker._normalize_text(messy_text)
        
        assert "  " not in normalized  # No double spaces
        assert "\n\n\n" not in normalized  # Max 2 newlines
        assert not normalized.startswith(" ")  # No leading whitespace
        assert not normalized.endswith(" ")  # No trailing whitespace
    
    def test_validate_chunks_success(self):
        """Test successful chunk validation."""
        text = "This is a test document for validation."
        document_id = "test-doc-5"
        
        chunks = self.chunker.chunk_document(text, document_id)
        
        # Should not raise an exception
        result = self.chunker.validate_chunks(chunks, text)
        assert result is True
    
    def test_validate_chunks_empty_list(self):
        """Test validation with empty chunk list."""
        with pytest.raises(ChunkingError, match="No chunks to validate"):
            self.chunker.validate_chunks([], "some text")
    
    def test_get_chunk_context(self):
        """Test getting context around a chunk."""
        text = "This is the beginning. This is the middle part. This is the end."
        document_id = "test-doc-6"
        
        chunks = self.chunker.chunk_document(text, document_id, chunk_size=20, overlap=5)
        
        if chunks:
            context = self.chunker.get_chunk_context(chunks[0], text, context_size=10)
            
            assert 'full_context' in context
            assert 'chunk_start' in context
            assert 'chunk_end' in context
            assert 'chunk_content' in context
            assert context['chunk_content'] == chunks[0].content
    
    def test_chunk_very_long_text(self):
        """Test chunking very long text."""
        # Create a long text
        long_text = "This is a sentence. " * 1000  # 20,000 characters
        document_id = "test-doc-long"
        
        chunks = self.chunker.chunk_document(long_text, document_id, chunk_size=500, overlap=50)
        
        assert len(chunks) > 10  # Should create many chunks
        assert all(len(chunk.content) <= 500 for chunk in chunks)
        
        # Verify all chunks together cover the original text reasonably
        total_content_length = sum(len(chunk.content) for chunk in chunks)
        # Should be at least as long as original (due to overlap)
        assert total_content_length >= len(long_text.strip())
    
    def test_chunk_short_text(self):
        """Test chunking text shorter than chunk size."""
        short_text = "Short text."
        document_id = "test-doc-short"
        
        chunks = self.chunker.chunk_document(short_text, document_id, chunk_size=100, overlap=20)
        
        assert len(chunks) == 1
        assert chunks[0].content == short_text
        assert chunks[0].start_position == 0
        assert chunks[0].end_position == len(short_text)