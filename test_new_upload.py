#!/usr/bin/env python3
"""
Test script to upload a new document and watch the logs.
"""
import requests
import os

def test_new_upload():
    # Upload the test document
    with open('test_document2.txt', 'rb') as f:
        files = {'file': ('test_document2.txt', f, 'text/plain')}
        
        try:
            print("Uploading test_document2.txt...")
            response = requests.post('http://localhost:8000/documents', files=files)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Response text: {response.text if 'response' in locals() else 'No response'}")

if __name__ == "__main__":
    test_new_upload()