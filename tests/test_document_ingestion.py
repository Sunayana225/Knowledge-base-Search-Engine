"""
Tests for document ingestion service.
"""
import pytest
import io
from pathlib import Path
from src.services.document_ingestion import DocumentIngestionService
from src.models.document import FileType, ProcessingStatus
from src.utils.exceptions import (
    FileFormatError, FileSizeError, DocumentProcessingError, ValidationError
)


class TestDocumentIngestionService:
    """Test cases for DocumentIngestionService."""
    
    def setup_method(self, temp_dir):
        """Set up test fixtures."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
    
    def test_upload_document_txt_success(self, temp_dir, sample_text_content):
        """Test successful text document upload."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(sample_text_content.encode('utf-8'))
        filename = "test_document.txt"
        
        metadata = self.service.upload_document(file_content, filename)
        
        assert metadata is not None
        assert metadata.filename == filename
        assert metadata.file_type == FileType.TXT
        assert metadata.processing_status == ProcessingStatus.PENDING
        assert metadata.file_size > 0
        assert metadata.id is not None
    
    def test_upload_document_pdf_success(self, temp_dir, sample_pdf_content):
        """Test successful PDF document upload."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(sample_pdf_content)
        filename = "test_document.pdf"
        
        metadata = self.service.upload_document(file_content, filename)
        
        assert metadata is not None
        assert metadata.filename == filename
        assert metadata.file_type == FileType.PDF
        assert metadata.processing_status == ProcessingStatus.PENDING
        assert metadata.file_size > 0
    
    def test_upload_document_empty_filename(self, temp_dir):
        """Test upload with empty filename."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(b"test content")
        
        with pytest.raises(ValidationError, match="Filename cannot be empty"):
            self.service.upload_document(file_content, "")
    
    def test_upload_document_empty_file(self, temp_dir):
        """Test upload of empty file."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(b"")
        filename = "empty.txt"
        
        with pytest.raises(ValidationError, match="File is empty"):
            self.service.upload_document(file_content, filename)
    
    def test_upload_document_unsupported_format(self, temp_dir):
        """Test upload of unsupported file format."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(b"test content")
        filename = "test.docx"  # Unsupported format
        
        with pytest.raises(FileFormatError, match="not supported"):
            self.service.upload_document(file_content, filename)
    
    def test_upload_document_file_too_large(self, temp_dir):
        """Test upload of file that's too large."""
        # Create service with very small max file size
        service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        service.max_file_size = 10  # 10 bytes max
        
        large_content = b"This content is definitely longer than 10 bytes"
        file_content = io.BytesIO(large_content)
        filename = "large.txt"
        
        with pytest.raises(FileSizeError, match="exceeds maximum allowed size"):
            service.upload_document(file_content, filename)
    
    def test_detect_file_type_txt(self, temp_dir):
        """Test file type detection for text files."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        content = b"This is plain text content"
        filename = "test.txt"
        
        file_type = self.service._detect_file_type(content, filename)
        assert file_type == FileType.TXT
    
    def test_detect_file_type_pdf(self, temp_dir, sample_pdf_content):
        """Test file type detection for PDF files."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        filename = "test.pdf"
        
        file_type = self.service._detect_file_type(sample_pdf_content, filename)
        assert file_type == FileType.PDF
    
    def test_detect_file_type_mismatch(self, temp_dir):
        """Test file type detection with content/extension mismatch."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        # Text content with PDF extension
        content = b"This is actually text content"
        filename = "fake.pdf"
        
        with pytest.raises(FileFormatError, match="PDF but content is not PDF"):
            self.service._detect_file_type(content, filename)
    
    def test_validate_file_metadata_success(self, temp_dir):
        """Test successful metadata validation."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        from src.models.document import DocumentMetadata
        metadata = DocumentMetadata.create_new("test.txt", FileType.TXT, 100)
        
        result = self.service.validate_file_metadata(metadata)
        assert result is True
    
    def test_validate_file_metadata_missing_id(self, temp_dir):
        """Test metadata validation with missing ID."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        from src.models.document import DocumentMetadata
        metadata = DocumentMetadata(
            id="",  # Empty ID
            filename="test.txt",
            file_type=FileType.TXT,
            upload_date=None,
            processing_status=ProcessingStatus.PENDING,
            chunk_count=0,
            file_size=100
        )
        
        with pytest.raises(ValidationError, match="Document ID is required"):
            self.service.validate_file_metadata(metadata)
    
    def test_validate_file_metadata_invalid_size(self, temp_dir):
        """Test metadata validation with invalid file size."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        from src.models.document import DocumentMetadata
        metadata = DocumentMetadata.create_new("test.txt", FileType.TXT, -1)  # Invalid size
        
        with pytest.raises(ValidationError, match="File size must be positive"):
            self.service.validate_file_metadata(metadata)
    
    def test_get_file_path(self, temp_dir):
        """Test file path generation."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        document_id = "test-id-123"
        filename = "test.txt"
        
        file_path = self.service.get_file_path(document_id, filename)
        
        expected_path = temp_dir / "uploads" / f"{document_id}_{filename}"
        assert file_path == expected_path
    
    def test_delete_uploaded_file(self, temp_dir, sample_text_content):
        """Test deletion of uploaded file."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        # First upload a file
        file_content = io.BytesIO(sample_text_content.encode('utf-8'))
        filename = "test_delete.txt"
        metadata = self.service.upload_document(file_content, filename)
        
        # Verify file exists
        file_path = self.service.get_file_path(metadata.id, filename)
        assert file_path.exists()
        
        # Delete the file
        result = self.service.delete_uploaded_file(metadata.id, filename)
        assert result is True
        assert not file_path.exists()
    
    def test_delete_nonexistent_file(self, temp_dir):
        """Test deletion of non-existent file."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        result = self.service.delete_uploaded_file("nonexistent-id", "nonexistent.txt")
        assert result is False
    
    def test_extract_text_integration(self, temp_dir, sample_text_content):
        """Test text extraction integration."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        # Create a test file
        test_file = temp_dir / "test_extract.txt"
        test_file.write_text(sample_text_content, encoding='utf-8')
        
        extracted_text = self.service.extract_text(str(test_file), FileType.TXT)
        
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "sample document" in extracted_text.lower()
    
    def test_chunk_document_integration(self, temp_dir):
        """Test document chunking integration."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        text = "This is a test document. " * 50  # Create longer text
        document_id = "test-chunk-doc"
        
        chunks = self.service.chunk_document(text, document_id, chunk_size=100, overlap=20)
        
        assert len(chunks) > 0
        assert all(chunk.document_id == document_id for chunk in chunks)
        assert all(len(chunk.content) <= 100 for chunk in chunks)
    
    def test_process_document_complete(self, temp_dir, sample_text_content):
        """Test complete document processing pipeline."""
        self.service = DocumentIngestionService(upload_dir=str(temp_dir / "uploads"))
        
        file_content = io.BytesIO(sample_text_content.encode('utf-8'))
        filename = "test_process.txt"
        
        metadata, extracted_text = self.service.process_document(file_content, filename)
        
        assert metadata is not None
        assert metadata.filename == filename
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "sample document" in extracted_text.lower()