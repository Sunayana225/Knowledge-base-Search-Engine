#!/usr/bin/env python3
"""
Fixed HTTP server to serve the frontend files properly
"""
import http.server
import socketserver
import os
from pathlib import Path

PORT = 3000

class CORSHTTPRequestHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory="frontend", **kwargs)
    
    def end_headers(self):
        # Add CORS headers
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, PUT, DELETE, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization')
        super().end_headers()
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

# Check if frontend directory exists
frontend_dir = Path("frontend")
if not frontend_dir.exists():
    print("Frontend directory not found!")
    exit(1)

print(f"Serving files from: {frontend_dir.absolute()}")

with socketserver.TCPServer(("", PORT), CORSHTTPRequestHandler) as httpd:
    print(f"Frontend server running at: http://localhost:{PORT}")
    print("Open this URL in your browser to access the Knowledge-base Search Engine")
    print("Press Ctrl+C to stop the server")
    
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down frontend server...")
        httpd.shutdown()