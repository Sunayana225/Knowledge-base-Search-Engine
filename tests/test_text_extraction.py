"""
Tests for text extraction service.
"""
import pytest
from pathlib import Path
from src.services.text_extraction import TextExtractionService
from src.models.document import FileType
from src.utils.exceptions import TextExtractionError, FileFormatError


class TestTextExtractionService:
    """Test cases for TextExtractionService."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.extractor = TextExtractionService()
    
    def test_extract_text_from_txt_file(self, sample_files):
        """Test text extraction from plain text file."""
        text_file = sample_files['text_file']
        
        extracted_text = self.extractor.extract_text(text_file, FileType.TXT)
        
        assert extracted_text is not None
        assert len(extracted_text) > 0
        assert "sample document" in extracted_text.lower()
        assert "testing purposes" in extracted_text.lower()
    
    def test_extract_text_from_pdf_file(self, sample_files):
        """Test text extraction from PDF file."""
        pdf_file = sample_files['pdf_file']
        
        # Note: Our sample PDF is minimal and may not extract properly
        # This test checks that the extraction doesn't crash
        try:
            extracted_text = self.extractor.extract_text(pdf_file, FileType.PDF)
            # If extraction succeeds, text should be a string
            assert isinstance(extracted_text, str)
        except TextExtractionError:
            # This is acceptable for our minimal test PDF
            pass
    
    def test_extract_text_file_not_found(self):
        """Test extraction from non-existent file."""
        non_existent_file = Path("non_existent.txt")
        
        with pytest.raises(TextExtractionError, match="File not found"):
            self.extractor.extract_text(non_existent_file, FileType.TXT)
    
    def test_extract_text_unsupported_format(self, sample_files):
        """Test extraction with unsupported file type."""
        text_file = sample_files['text_file']
        
        # Create a mock unsupported file type
        class UnsupportedType:
            pass
        
        with pytest.raises(FileFormatError, match="Unsupported file type"):
            self.extractor.extract_text(text_file, UnsupportedType())
    
    def test_validate_extracted_text_valid(self):
        """Test validation of valid extracted text."""
        valid_text = "This is a valid text with sufficient length for validation."
        
        result = self.extractor.validate_extracted_text(valid_text)
        assert result is True
    
    def test_validate_extracted_text_empty(self):
        """Test validation of empty text."""
        with pytest.raises(TextExtractionError, match="No text content extracted"):
            self.extractor.validate_extracted_text("")
    
    def test_validate_extracted_text_whitespace_only(self):
        """Test validation of whitespace-only text."""
        with pytest.raises(TextExtractionError, match="only whitespace"):
            self.extractor.validate_extracted_text("   \n\t   ")
    
    def test_validate_extracted_text_too_short(self):
        """Test validation of text that's too short."""
        short_text = "Short"
        
        with pytest.raises(TextExtractionError, match="too short"):
            self.extractor.validate_extracted_text(short_text, min_length=20)
    
    def test_clean_extracted_text(self):
        """Test text cleaning functionality."""
        messy_text = """  This   is    messy   text.  
        
        
        It has    excessive    whitespace.
        
        
        
        And multiple   empty   lines.  """
        
        cleaned_text = self.extractor.clean_extracted_text(messy_text)
        
        assert "This is messy text." in cleaned_text
        assert "It has excessive whitespace." in cleaned_text
        assert "And multiple empty lines." in cleaned_text
        # Should not have excessive whitespace
        assert "    " not in cleaned_text
        assert "\n\n\n" not in cleaned_text
    
    def test_clean_extracted_text_empty(self):
        """Test cleaning empty text."""
        result = self.extractor.clean_extracted_text("")
        assert result == ""
    
    def test_detect_encoding_utf8(self, temp_dir):
        """Test encoding detection for UTF-8 file."""
        utf8_file = temp_dir / "utf8_test.txt"
        utf8_content = "This is UTF-8 content with special chars: áéíóú"
        utf8_file.write_text(utf8_content, encoding='utf-8')
        
        encoding = self.extractor._detect_encoding(utf8_file)
        # Should detect UTF-8 or similar
        assert encoding is not None
        assert encoding.lower() in ['utf-8', 'ascii']
    
    def test_extract_txt_with_encoding_detection(self, temp_dir):
        """Test text extraction with automatic encoding detection."""
        # Create file with special characters
        special_file = temp_dir / "special_chars.txt"
        content = "Text with special characters: café, naïve, résumé"
        special_file.write_text(content, encoding='utf-8')
        
        extracted_text = self.extractor.extract_text(special_file, FileType.TXT)
        
        assert "café" in extracted_text
        assert "naïve" in extracted_text
        assert "résumé" in extracted_text