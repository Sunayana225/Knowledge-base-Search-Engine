"""
Text extraction service for multiple file formats.
"""
import PyPDF2
import pdfplumber
from pathlib import Path
from typing import Union
try:
    import chardet
    CHARDET_AVAILABLE = True
except ImportError:
    CHARDET_AVAILABLE = False
from src.models.document import FileType
from src.utils.exceptions import TextExtractionError, FileFormatError


class TextExtractionService:
    """Service for extracting text from various file formats."""
    
    def __init__(self):
        """Initialize text extraction service."""
        self.encoding_fallbacks = ['utf-8', 'utf-16', 'latin-1', 'cp1252']
    
    def extract_text(self, file_path: Union[str, Path], file_type: FileType) -> str:
        """
        Extract text from a file based on its type.
        
        Args:
            file_path: Path to the file
            file_type: Type of the file (PDF or TXT)
            
        Returns:
            str: Extracted text content
            
        Raises:
            TextExtractionError: If text extraction fails
            FileFormatError: If file format is not supported
        """
        file_path = Path(file_path)
        
        if not file_path.exists():
            raise TextExtractionError(f"File not found: {file_path}")
        
        try:
            if file_type == FileType.PDF:
                return self._extract_pdf_text(file_path)
            elif file_type == FileType.TXT:
                return self._extract_txt_text(file_path)
            else:
                raise FileFormatError(f"Unsupported file type: {file_type}")
                
        except (TextExtractionError, FileFormatError):
            raise
        except Exception as e:
            raise TextExtractionError(f"Failed to extract text from {file_path}: {str(e)}")
    
    def _extract_pdf_text(self, file_path: Path) -> str:
        """
        Extract text from PDF file using multiple methods.
        
        Args:
            file_path: Path to PDF file
            
        Returns:
            str: Extracted text
            
        Raises:
            TextExtractionError: If PDF text extraction fails
        """
        text_content = ""
        
        # Try pdfplumber first (better for complex layouts)
        try:
            text_content = self._extract_with_pdfplumber(file_path)
            if text_content.strip():
                return text_content
        except Exception as e:
            print(f"pdfplumber extraction failed: {e}")
        
        # Fallback to PyPDF2
        try:
            text_content = self._extract_with_pypdf2(file_path)
            if text_content.strip():
                return text_content
        except Exception as e:
            print(f"PyPDF2 extraction failed: {e}")
        
        # If both methods fail or return empty content
        if not text_content.strip():
            raise TextExtractionError(
                "Could not extract text from PDF. The file may be image-based, "
                "password-protected, or corrupted."
            )
        
        return text_content
    
    def _extract_with_pdfplumber(self, file_path: Path) -> str:
        """Extract text using pdfplumber library."""
        text_parts = []
        
        with pdfplumber.open(file_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    print(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
        
        return "\n\n".join(text_parts)
    
    def _extract_with_pypdf2(self, file_path: Path) -> str:
        """Extract text using PyPDF2 library."""
        text_parts = []
        
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            
            # Check if PDF is encrypted
            if pdf_reader.is_encrypted:
                raise TextExtractionError("PDF is password-protected")
            
            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text:
                        text_parts.append(page_text)
                except Exception as e:
                    print(f"Failed to extract text from page {page_num + 1}: {e}")
                    continue
        
        return "\n\n".join(text_parts)
    
    def _extract_txt_text(self, file_path: Path) -> str:
        """
        Extract text from plain text file with encoding detection.
        
        Args:
            file_path: Path to text file
            
        Returns:
            str: File content as text
            
        Raises:
            TextExtractionError: If text extraction fails
        """
        # First, try to detect encoding
        encoding = self._detect_encoding(file_path)
        
        if encoding:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    return content
            except UnicodeDecodeError:
                pass  # Fall through to try other encodings
        
        # Try fallback encodings
        for encoding in self.encoding_fallbacks:
            try:
                with open(file_path, 'r', encoding=encoding) as file:
                    content = file.read()
                    return content
            except UnicodeDecodeError:
                continue
        
        # Last resort: read as binary and decode with error handling
        try:
            with open(file_path, 'rb') as file:
                raw_content = file.read()
                content = raw_content.decode('utf-8', errors='replace')
                return content
        except Exception as e:
            raise TextExtractionError(f"Could not decode text file: {str(e)}")
    
    def _detect_encoding(self, file_path: Path) -> str:
        """
        Detect file encoding using chardet.
        
        Args:
            file_path: Path to file
            
        Returns:
            str: Detected encoding or None
        """
        if not CHARDET_AVAILABLE:
            return None
            
        try:
            with open(file_path, 'rb') as file:
                # Read a sample of the file for encoding detection
                sample = file.read(10000)  # Read first 10KB
                result = chardet.detect(sample)
                
                if result and result['confidence'] > 0.7:
                    return result['encoding']
        except Exception:
            pass
        
        return None
    
    def validate_extracted_text(self, text: str, min_length: int = 10) -> bool:
        """
        Validate extracted text content.
        
        Args:
            text: Extracted text
            min_length: Minimum required text length
            
        Returns:
            bool: True if text is valid
            
        Raises:
            TextExtractionError: If text validation fails
        """
        if not text:
            raise TextExtractionError("No text content extracted")
        
        if not text.strip():
            raise TextExtractionError("Extracted text contains only whitespace")
        
        if len(text.strip()) < min_length:
            raise TextExtractionError(
                f"Extracted text is too short (minimum {min_length} characters required)"
            )
        
        return True
    
    def clean_extracted_text(self, text: str) -> str:
        """
        Clean and normalize extracted text.
        
        Args:
            text: Raw extracted text
            
        Returns:
            str: Cleaned text
        """
        if not text:
            return ""
        
        # Remove excessive whitespace
        lines = text.split('\n')
        cleaned_lines = []
        
        for line in lines:
            # Strip whitespace from each line
            cleaned_line = line.strip()
            if cleaned_line:  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)
        
        # Join lines with single newlines
        cleaned_text = '\n'.join(cleaned_lines)
        
        # Remove excessive spaces within lines
        import re
        cleaned_text = re.sub(r' +', ' ', cleaned_text)
        
        return cleaned_text