#!/usr/bin/env python3
"""
Simple startup script for the Knowledge-base Search Engine
"""
import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def main():
    """Start both backend and frontend servers"""
    print("🚀 Starting Knowledge-base Search Engine...")
    
    # Check if .env file exists
    if not Path('.env').exists():
        print("⚠️  No .env file found. Please copy .env.example to .env and configure your API keys.")
        print("   cp .env.example .env")
        return
    
    try:
        # Start backend server
        print("📡 Starting API server on http://localhost:8000")
        backend = subprocess.Popen([
            sys.executable, "start_server.py"
        ])
        
        # Wait a moment for backend to start
        time.sleep(3)
        
        # Start frontend server
        print("🌐 Starting frontend server on http://localhost:3000")
        frontend = subprocess.Popen([
            sys.executable, "serve_frontend_fixed.py"
        ])
        
        # Wait a moment for frontend to start
        time.sleep(2)
        
        print("\n✅ Knowledge-base Search Engine is running!")
        print("   Frontend: http://localhost:3000")
        print("   API Docs: http://localhost:8000/docs")
        print("   Health:   http://localhost:8000/health")
        print("\n🌐 Opening browser...")
        
        # Open browser
        webbrowser.open("http://localhost:3000")
        
        print("\n⏹️  Press Ctrl+C to stop both servers")
        
        # Wait for user to stop
        try:
            backend.wait()
        except KeyboardInterrupt:
            print("\n🛑 Stopping servers...")
            backend.terminate()
            frontend.terminate()
            print("✅ Servers stopped successfully!")
            
    except Exception as e:
        print(f"❌ Error starting servers: {e}")
        return 1

if __name__ == "__main__":
    main()