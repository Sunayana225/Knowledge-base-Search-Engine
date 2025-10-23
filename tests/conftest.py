"""
Pytest configuration and fixtures.
"""
import pytest
import tempfile
import os
from pathlib import Path
from src.database.connection import DatabaseManager
from src.database.models import Base


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test files."""
    with tempfile.TemporaryDirectory() as temp_dir:
        yield Path(temp_dir)


@pytest.fixture
def sample_text_content():
    """Sample text content for testing."""
    return """This is a sample document for testing purposes.
    
It contains multiple paragraphs with different content. The first paragraph introduces the document.

The second paragraph provides more details about the testing scenario. It includes various sentence structures and punctuation marks! This helps test the text processing capabilities.

The third paragraph concludes the sample document. It ensures we have enough content for chunking tests and other processing operations."""


@pytest.fixture
def sample_pdf_content():
    """Sample PDF content (as bytes) for testing."""
    # This is a minimal PDF structure for testing
    return b"""%PDF-1.4
1 0 obj
<<
/Type /Catalog
/Pages 2 0 R
>>
endobj
2 0 obj
<<
/Type /Pages
/Kids [3 0 R]
/Count 1
>>
endobj
3 0 obj
<<
/Type /Page
/Parent 2 0 R
/MediaBox [0 0 612 792]
/Contents 4 0 R
>>
endobj
4 0 obj
<<
/Length 44
>>
stream
BT
/F1 12 Tf
72 720 Td
(Sample PDF content) Tj
ET
endstream
endobj
xref
0 5
0000000000 65535 f 
0000000009 00000 n 
0000000058 00000 n 
0000000115 00000 n 
0000000204 00000 n 
trailer
<<
/Size 5
/Root 1 0 R
>>
startxref
297
%%EOF"""


@pytest.fixture
def test_database():
    """Create a test database."""
    # Use in-memory SQLite for testing
    db_manager = DatabaseManager()
    db_manager.engine = db_manager.engine.execution_options(
        isolation_level="AUTOCOMMIT"
    )
    
    # Create tables
    Base.metadata.create_all(bind=db_manager.engine)
    
    yield db_manager
    
    # Clean up
    Base.metadata.drop_all(bind=db_manager.engine)


@pytest.fixture
def sample_files(temp_dir, sample_text_content, sample_pdf_content):
    """Create sample files for testing."""
    # Create text file
    text_file = temp_dir / "sample.txt"
    text_file.write_text(sample_text_content, encoding='utf-8')
    
    # Create PDF file
    pdf_file = temp_dir / "sample.pdf"
    pdf_file.write_bytes(sample_pdf_content)
    
    # Create empty file
    empty_file = temp_dir / "empty.txt"
    empty_file.write_text("", encoding='utf-8')
    
    # Create large file
    large_content = "Large file content. " * 1000
    large_file = temp_dir / "large.txt"
    large_file.write_text(large_content, encoding='utf-8')
    
    return {
        'text_file': text_file,
        'pdf_file': pdf_file,
        'empty_file': empty_file,
        'large_file': large_file,
        'temp_dir': temp_dir
    }