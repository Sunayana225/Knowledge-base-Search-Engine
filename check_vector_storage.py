#!/usr/bin/env python3
"""
Script to check what's actually stored in the vector storage.
"""
import sys
import os
import pickle
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.vector_storage import VectorStorageFactory

def check_vector_storage():
    """Check what's in the vector storage."""
    try:
        vector_storage = VectorStorageFactory.create_storage()
        
        # Get stats
        stats = vector_storage.get_storage_stats()
        print(f"Vector storage stats: {stats}")
        
        # Check metadata directly
        metadata_file = "data/vector_index/metadata.pkl"
        if os.path.exists(metadata_file):
            with open(metadata_file, 'rb') as f:
                data = pickle.load(f)
                
            print(f"\nMetadata file contents:")
            print(f"chunk_metadata keys: {list(data.get('chunk_metadata', {}).keys())}")
            print(f"id_to_vector_id: {data.get('id_to_vector_id', {})}")
            print(f"next_vector_id: {data.get('next_vector_id', 0)}")
            
            # Check chunks from both documents
            chunk_metadata = data.get('chunk_metadata', {})
            
            # Find chunks from each document
            relative_speed_chunks = []
            averages_chunks = []
            
            test_doc_chunks = []
            
            for vector_id, chunk in chunk_metadata.items():
                if chunk.document_id == "416b004b-c3ac-492b-8c3a-412ed5c1ae63":  # RELATIVE SPEED
                    relative_speed_chunks.append((vector_id, chunk))
                elif chunk.document_id == "7bed1027-710b-428d-bacc-f4373d039869":  # AVERAGES
                    averages_chunks.append((vector_id, chunk))
                elif chunk.document_id == "7be062eb-c795-478f-970c-774ac8c44f4d":  # TEST DOCUMENT
                    test_doc_chunks.append((vector_id, chunk))
                else:
                    print(f"Unknown document: {chunk.document_id} at vector_id {vector_id}")
            
            print(f"\nRELATIVE SPEED chunks: {len(relative_speed_chunks)}")
            for i, (vector_id, chunk) in enumerate(relative_speed_chunks[:3]):
                print(f"  Chunk {i+1} (vector_id={vector_id}): {chunk.content[:80]}...")
            
            print(f"\nAVERAGES chunks: {len(averages_chunks)}")
            for i, (vector_id, chunk) in enumerate(averages_chunks[:3]):
                print(f"  Chunk {i+1} (vector_id={vector_id}): {chunk.content[:80]}...")
            
            print(f"\nTEST DOCUMENT chunks: {len(test_doc_chunks)}")
            for i, (vector_id, chunk) in enumerate(test_doc_chunks):
                print(f"  Chunk {i+1} (vector_id={vector_id}): {chunk.content[:80]}...")
        
        # Test a search
        from src.services.embedding_service import EmbeddingService
        embedding_service = EmbeddingService()
        
        query = "speed distance time formula"
        query_embedding = embedding_service.generate_query_embedding(query)
        
        similar_chunks = vector_storage.similarity_search(query_embedding, top_k=10)
        print(f"\nSearch results for '{query}':")
        print(f"Found {len(similar_chunks)} chunks")
        
        for i, chunk in enumerate(similar_chunks):
            similarity_score = getattr(chunk, 'similarity_score', 'N/A')
            print(f"Chunk {i+1}: similarity={similarity_score}, doc_id={chunk.document_id}, content={chunk.content[:50]}...")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    check_vector_storage()