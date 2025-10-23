#!/usr/bin/env python3
"""
Test script to manually upload the PDF file that's already in uploads directory.
"""
import requests
import os

def test_upload():
    # Path to the PDF file
    pdf_path = "data/uploads/6db1eb82-59a9-47cf-a2a7-981dd75c06e6_RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf"
    
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return
    
    # Upload the file
    with open(pdf_path, 'rb') as f:
        files = {'file': ('RELATIVE SPEED(TIME SPEED DISTANCE) (2).pdf', f, 'application/pdf')}
        
        try:
            response = requests.post('http://localhost:8000/documents', files=files)
            print(f"Status Code: {response.status_code}")
            print(f"Response: {response.json()}")
        except Exception as e:
            print(f"Error: {e}")
            print(f"Response text: {response.text if 'response' in locals() else 'No response'}")

if __name__ == "__main__":
    test_upload()