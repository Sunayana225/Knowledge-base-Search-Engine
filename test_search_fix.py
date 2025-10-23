#!/usr/bin/env python3
"""
Test script to verify the search fix for queries with apostrophes.
"""
import requests
import json

def test_search_queries():
    """Test various queries that were previously failing."""
    
    test_queries = [
        "what is sunayana's experience",  # Contains apostrophe
        "don't show me this",  # Contains apostrophe
        "what's the formula",  # Contains apostrophe
        "quadratic formula",  # Normal query
        "speed distance time",  # Normal query
    ]
    
    for query in test_queries:
        try:
            print(f"\n🔍 Testing query: '{query}'")
            
            response = requests.post(
                'http://localhost:8000/search',
                json={"query": query},
                headers={'Content-Type': 'application/json'}
            )
            
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Success! Answer length: {len(result.get('answer', ''))}")
                print(f"Sources: {len(result.get('sources', []))}")
            else:
                print(f"❌ Error: {response.text}")
                
        except Exception as e:
            print(f"❌ Exception: {e}")

if __name__ == "__main__":
    test_search_queries()