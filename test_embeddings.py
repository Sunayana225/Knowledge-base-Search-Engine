#!/usr/bin/env python3
"""
Test script to check embedding generation and similarity search.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.embedding_service import EmbeddingService
from src.services.vector_storage import VectorStorageFactory
from src.database.repository import DocumentChunkRepository
import numpy as np

def test_embeddings():
    """Test embedding generation and similarity search."""
    try:
        # Initialize services
        embedding_service = EmbeddingService()
        vector_storage = VectorStorageFactory.create_storage()
        chunk_repo = DocumentChunkRepository()
        
        print("Testing embedding generation...")
        
        # Test query embedding
        query = "speed distance time formula"
        query_embedding = embedding_service.generate_query_embedding(query)
        print(f"Query embedding generated: {len(query_embedding)} dimensions")
        print(f"Query embedding sample: {query_embedding[:5]}")
        
        # Get stored chunks for the document
        document_id = "416b004b-c3ac-492b-8c3a-412ed5c1ae63"  # The uploaded document ID
        chunks = chunk_repo.get_chunks_by_document(document_id)
        print(f"\nFound {len(chunks)} chunks in database for document {document_id}")
        
        if chunks:
            # Check first chunk
            first_chunk = chunks[0]
            print(f"First chunk content preview: {first_chunk.content[:100]}...")
            print(f"First chunk has embedding: {first_chunk.embedding is not None}")
            
            if first_chunk.embedding:
                print(f"First chunk embedding length: {len(first_chunk.embedding)}")
                print(f"First chunk embedding sample: {first_chunk.embedding[:5]}")
                
                # Test similarity manually
                chunk_embedding = np.array(first_chunk.embedding)
                query_embedding_np = np.array(query_embedding)
                
                # Normalize vectors
                chunk_norm = chunk_embedding / np.linalg.norm(chunk_embedding)
                query_norm = query_embedding_np / np.linalg.norm(query_embedding_np)
                
                # Calculate cosine similarity
                similarity = np.dot(chunk_norm, query_norm)
                print(f"Manual cosine similarity: {similarity}")
        
        # Test vector storage search
        print(f"\nTesting vector storage search...")
        vector_stats = vector_storage.get_storage_stats()
        print(f"Vector storage stats: {vector_stats}")
        
        if vector_stats['total_vectors'] > 0:
            similar_chunks = vector_storage.similarity_search(query_embedding, top_k=5)
            print(f"Vector search returned {len(similar_chunks)} chunks")
            
            for i, chunk in enumerate(similar_chunks):
                similarity_score = getattr(chunk, 'similarity_score', 'N/A')
                print(f"Chunk {i+1}: similarity={similarity_score}, content={chunk.content[:50]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_embeddings()