#!/usr/bin/env python3
"""
Debug script to check what the query processor is doing.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.query_processor import QueryProcessor

def debug_query_processor():
    """Debug the query processor step by step."""
    try:
        # Initialize query processor
        query_processor = QueryProcessor()
        
        query = "speed distance time formula"
        print(f"Testing query: '{query}'")
        
        # Step 1: Search for similar chunks
        print("\n1. Searching for similar chunks...")
        similar_chunks = query_processor.storage_service.search_similar_chunks(query, top_k=5)
        print(f"Found {len(similar_chunks)} chunks")
        
        for i, chunk in enumerate(similar_chunks):
            similarity_score = getattr(chunk, 'similarity_score', 'N/A')
            print(f"Chunk {i+1}: similarity={similarity_score}, doc_id={chunk.document_id}")
            print(f"  Content: {chunk.content[:100]}...")
        
        # Step 2: Get document metadata
        print("\n2. Getting document metadata...")
        document_metadata = query_processor._get_document_metadata(similar_chunks)
        print(f"Found metadata for {len(document_metadata)} documents")
        
        for doc in document_metadata:
            print(f"  Document: {doc.filename} (ID: {doc.id})")
        
        # Step 3: Prepare context for LLM
        print("\n3. Preparing context for LLM...")
        context = query_processor._prepare_context_for_llm(similar_chunks)
        print(f"Context length: {len(context)} characters")
        print(f"Context preview:\n{context[:500]}...")
        
        # Step 4: Test full query processing
        print("\n4. Testing full query processing...")
        result = query_processor.process_query(query, top_k=5)
        
        print(f"Final result:")
        print(f"  Query: {result.query}")
        print(f"  Answer: {result.answer}")
        print(f"  Sources: {len(result.sources)}")
        print(f"  Citations: {len(result.citations)}")
        print(f"  Processing time: {result.processing_time}")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_query_processor()