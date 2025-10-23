#!/usr/bin/env python3
"""
Test script to check LLM service directly.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.llm_service import GeminiLLMService
from src.models.document import DocumentMetadata, FileType, ProcessingStatus
from datetime import datetime

def test_llm():
    """Test LLM service directly."""
    try:
        # Initialize LLM service
        llm_service = GeminiLLMService()
        
        print(f"LLM Service Info: {llm_service.get_model_info()}")
        print(f"Using mock: {llm_service.use_mock}")
        
        # Test context from the PDF
        context = """[Source: RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf]
1
RelTaotpivice/C Soupreseed
Sub-Topic (Example: name of college)
2
Relative Speed:
The Speed of one object with respect to another object is called relative speed.

---

[Source: RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf]
Distance traveled by First Car = 240 - 80 = 160 km
Time taken = 160/40 = 4 hours
Speed = Distance/Time
Formula: Speed = Distance / Time

---

[Source: RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf]
m/hr= 25/60 km/minutes
And distance from village to town = 15 km
Time taken to cover this distance at a speed of 10 km/hr:
=10/15 = 1.5 hr"""
        
        # Create mock document metadata
        doc_metadata = DocumentMetadata(
            id="416b004b-c3ac-492b-8c3a-412ed5c1ae63",
            filename="RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf",
            file_type=FileType.PDF,
            file_size=875141,
            upload_date=datetime.now(),
            processing_status=ProcessingStatus.COMPLETED,
            chunk_count=18
        )
        
        # Test query
        query = "speed distance time formula"
        
        print(f"\nTesting query: '{query}'")
        print(f"Context length: {len(context)} characters")
        print(f"Context preview: {context[:200]}...")
        
        # Generate answer
        result = llm_service.synthesize_answer(query, context, [doc_metadata])
        
        print(f"\nGenerated Answer:")
        print(f"Content: {result.content}")
        print(f"Sources used: {result.sources_used}")
        print(f"Citations: {len(result.citations)}")
        print(f"Confidence: {result.confidence_score}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_llm()