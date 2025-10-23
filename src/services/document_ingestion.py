"""
Document ingestion service implementation.
"""
import os
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
from typing import BinaryIO, List
from pathlib import Path
from src.models.document import DocumentMetadata, FileType, ProcessingStatus, DocumentChunk
from src.services.interfaces import DocumentIngestionInterface
from src.services.text_extraction import TextExtractionService
from src.services.document_chunker import DocumentChunker
from src.utils.exceptions import (
    FileFormatError, FileSizeError, DocumentProcessingError, ValidationError, TextExtractionError, ChunkingError
)
from src.models.document import ProcessedDocument, ProcessingStatus
from src.config.settings import config


class DocumentIngestionService(DocumentIngestionInterface):
    """Service for handling document upload and validation."""
    
    def __init__(self, upload_dir: str = "data/uploads"):
        """Initialize the document ingestion service."""
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.max_file_size = config.document_processing.max_file_size
        self.supported_formats = config.document_processing.supported_formats
        self.text_extractor = TextExtractionService()
        self.chunker = DocumentChunker()
    
    def upload_document(self, file_content: BinaryIO, filename: str) -> DocumentMetadata:
        """
        Upload and validate a document file.
        
        Args:
            file_content: Binary file content
            filename: Original filename
            
        Returns:
            DocumentMetadata: Metadata for the uploaded document
            
        Raises:
            ValidationError: If filename is invalid
            FileFormatError: If file format is not supported
            FileSizeError: If file size exceeds limits
            DocumentProcessingError: If upload fails
        """
        try:
            # Validate filename
            if not filename or not filename.strip():
                raise ValidationError("Filename cannot be empty")
            
            # Read file content to check size and format
            file_content.seek(0)
            content = file_content.read()
            file_size = len(content)
            
            # Validate file size
            if file_size > self.max_file_size:
                raise FileSizeError(
                    f"File size {file_size} bytes exceeds maximum allowed size "
                    f"{self.max_file_size} bytes"
                )
            
            if file_size == 0:
                raise ValidationError("File is empty")
            
            # Detect file type
            file_type = self._detect_file_type(content, filename)
            
            # Create document metadata
            metadata = DocumentMetadata.create_new(
                filename=filename,
                file_type=file_type,
                file_size=file_size
            )
            
            # Save file to upload directory
            file_path = self.upload_dir / f"{metadata.id}_{filename}"
            with open(file_path, "wb") as f:
                f.write(content)
            
            return metadata
            
        except (FileFormatError, FileSizeError, ValidationError):
            raise
        except Exception as e:
            raise DocumentProcessingError(f"Failed to upload document: {str(e)}")
    
    def _detect_file_type(self, content: bytes, filename: str) -> FileType:
        """
        Detect file type from content and filename.
        
        Args:
            content: File content bytes
            filename: Original filename
            
        Returns:
            FileType: Detected file type
            
        Raises:
            FileFormatError: If file format is not supported
        """
        # Get file extension
        extension = Path(filename).suffix.lower().lstrip('.')
        
        # Check if extension is supported
        if extension not in self.supported_formats:
            raise FileFormatError(
                f"File format '{extension}' is not supported. "
                f"Supported formats: {', '.join(self.supported_formats)}"
            )
        
        # Use python-magic for more accurate detection if available
        mime_type = None
        if MAGIC_AVAILABLE:
            try:
                mime_type = magic.from_buffer(content, mime=True)
            except Exception:
                # Fallback to extension-based detection
                mime_type = None
        
        # Validate file type based on content and extension
        if extension == "pdf":
            if mime_type and not mime_type.startswith("application/pdf"):
                raise FileFormatError("File extension is PDF but content is not PDF format")
            return FileType.PDF
        
        elif extension == "txt":
            if mime_type and not (mime_type.startswith("text/") or mime_type == "application/octet-stream"):
                # Allow octet-stream as some text files are detected as binary
                try:
                    # Try to decode as text to verify it's actually text
                    content.decode('utf-8')
                except UnicodeDecodeError:
                    raise FileFormatError("File extension is TXT but content is not valid text")
            return FileType.TXT
        
        else:
            raise FileFormatError(f"Unsupported file format: {extension}")
    
    def validate_file_metadata(self, metadata: DocumentMetadata) -> bool:
        """
        Validate document metadata.
        
        Args:
            metadata: Document metadata to validate
            
        Returns:
            bool: True if valid
            
        Raises:
            ValidationError: If metadata is invalid
        """
        if not metadata.id:
            raise ValidationError("Document ID is required")
        
        if not metadata.filename:
            raise ValidationError("Filename is required")
        
        if metadata.file_size <= 0:
            raise ValidationError("File size must be positive")
        
        if metadata.file_type not in FileType:
            raise ValidationError(f"Invalid file type: {metadata.file_type}")
        
        return True
    
    def get_file_path(self, document_id: str, filename: str) -> Path:
        """
        Get the file path for a stored document.
        
        Args:
            document_id: Document ID
            filename: Original filename
            
        Returns:
            Path: Path to the stored file
        """
        return self.upload_dir / f"{document_id}_{filename}"
    
    def delete_uploaded_file(self, document_id: str, filename: str) -> bool:
        """
        Delete an uploaded file from storage.
        
        Args:
            document_id: Document ID
            filename: Original filename
            
        Returns:
            bool: True if file was deleted successfully
        """
        try:
            file_path = self.get_file_path(document_id, filename)
            if file_path.exists():
                file_path.unlink()
                return True
            return False
        except Exception:
            return False 
   
    def extract_text(self, file_path: str, file_type: FileType) -> str:
        """
        Extract text from a file using the text extraction service.
        
        Args:
            file_path: Path to the file
            file_type: Type of the file
            
        Returns:
            str: Extracted and cleaned text content
            
        Raises:
            TextExtractionError: If text extraction fails
            DocumentProcessingError: If processing fails
        """
        try:
            # Extract raw text
            raw_text = self.text_extractor.extract_text(file_path, file_type)
            
            # Validate extracted text
            self.text_extractor.validate_extracted_text(raw_text)
            
            # Clean and normalize text
            cleaned_text = self.text_extractor.clean_extracted_text(raw_text)
            
            return cleaned_text
            
        except TextExtractionError:
            raise
        except Exception as e:
            raise DocumentProcessingError(f"Failed to extract text: {str(e)}")
    
    def process_document(self, file_content: BinaryIO, filename: str) -> tuple[DocumentMetadata, str]:
        """
        Complete document processing: upload, validate, and extract text.
        
        Args:
            file_content: Binary file content
            filename: Original filename
            
        Returns:
            tuple: (DocumentMetadata, extracted_text)
            
        Raises:
            DocumentProcessingError: If any step fails
        """
        try:
            # Upload and validate document
            metadata = self.upload_document(file_content, filename)
            
            # Get file path for text extraction
            file_path = self.get_file_path(metadata.id, filename)
            
            # Extract text content
            extracted_text = self.extract_text(str(file_path), metadata.file_type)
            
            return metadata, extracted_text
            
        except Exception as e:
            # Clean up uploaded file if processing fails
            if 'metadata' in locals():
                self.delete_uploaded_file(metadata.id, filename)
            raise DocumentProcessingError(f"Document processing failed: {str(e)}")
    
    def chunk_document(self, text: str, document_id: str, chunk_size: int = 1000, overlap: int = 200) -> List[DocumentChunk]:
        """
        Split document text into chunks using the chunking service.
        
        Args:
            text: Document text to chunk
            document_id: ID of the source document
            chunk_size: Maximum characters per chunk
            overlap: Number of characters to overlap between chunks
            
        Returns:
            List[DocumentChunk]: List of document chunks
            
        Raises:
            ChunkingError: If chunking fails
            DocumentProcessingError: If processing fails
        """
        try:
            chunks = self.chunker.chunk_document(text, document_id, chunk_size, overlap)
            
            # Validate chunks
            self.chunker.validate_chunks(chunks, text)
            
            return chunks
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to chunk document: {str(e)}")
    
    def store_document(self, document: ProcessedDocument) -> str:
        """
        Store processed document with metadata and chunks.
        
        Args:
            document: Processed document with metadata and chunks
            
        Returns:
            str: Document ID
            
        Raises:
            DocumentProcessingError: If storage fails
        """
        try:
            from src.services.document_storage import DocumentStorageService
            
            storage_service = DocumentStorageService()
            return storage_service.store_processed_document(document)
            
        except Exception as e:
            raise DocumentProcessingError(f"Failed to store document: {str(e)}")
    
    def process_and_store_document(self, file_content: BinaryIO, filename: str) -> ProcessedDocument:
        """
        Complete document processing pipeline: upload, extract, chunk, and store.
        
        Args:
            file_content: Binary file content
            filename: Original filename
            
        Returns:
            ProcessedDocument: Fully processed document
            
        Raises:
            DocumentProcessingError: If any step fails
        """
        try:
            # Process document (upload and extract text)
            metadata, extracted_text = self.process_document(file_content, filename)
            
            # Chunk the document
            chunks = self.chunk_document(extracted_text, metadata.id)
            
            # Create processed document
            processed_doc = ProcessedDocument(
                metadata=metadata,
                chunks=chunks
            )
            
            # Store in database
            self.store_document(processed_doc)
            
            return processed_doc
            
        except Exception as e:
            # Clean up uploaded file if processing fails
            if 'metadata' in locals():
                self.delete_uploaded_file(metadata.id, filename)
            raise DocumentProcessingError(f"Complete document processing failed: {str(e)}")