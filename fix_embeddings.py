#!/usr/bin/env python3
"""
Script to manually fix embeddings for the uploaded document.
"""
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.services.document_storage import DocumentStorageService
from src.database.repository import DocumentRepository

def fix_embeddings():
    """Fix embeddings for all documents that don't have them in vector storage."""
    try:
        # Initialize services
        storage_service = DocumentStorageService()
        doc_repo = DocumentRepository()
        
        # Get all documents
        documents = doc_repo.list_documents(limit=100)
        print(f"Found {len(documents)} documents")
        
        for doc in documents:
            print(f"\nProcessing document: {doc.filename} (ID: {doc.id})")
            
            # Get chunks for this document
            chunks = storage_service.get_document_chunks(doc.id)
            print(f"Found {len(chunks)} chunks")
            
            if chunks:
                # Check if chunks have embeddings
                chunks_without_embeddings = [chunk for chunk in chunks if not chunk.embedding]
                print(f"Chunks without embeddings: {len(chunks_without_embeddings)}")
                
                if chunks_without_embeddings:
                    print("Generating embeddings...")
                    # Update embeddings for this document
                    success = storage_service.update_document_embeddings(doc.id)
                    if success:
                        print("✅ Embeddings updated successfully")
                    else:
                        print("❌ Failed to update embeddings")
                else:
                    print("All chunks already have embeddings")
                    
                    # Check if they're in vector storage
                    vector_stats = storage_service.vector_storage.get_storage_stats()
                    print(f"Vector storage has {vector_stats['total_vectors']} vectors")
                    
                    if vector_stats['total_vectors'] == 0:
                        print("Vectors not in storage, adding them...")
                        storage_service.vector_storage.store_embeddings(chunks)
                        print("✅ Vectors added to storage")
            else:
                print("No chunks found for this document")
        
        # Print final statistics
        print("\n" + "="*50)
        stats = storage_service.get_storage_statistics()
        print("Final Statistics:")
        print(f"Documents: {stats['documents']['total']}")
        print(f"Vector storage: {stats['vector_storage']['total_vectors']} vectors")
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    fix_embeddings()