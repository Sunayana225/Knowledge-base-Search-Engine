#!/usr/bin/env python3
"""
Simple server starter script
"""
import uvicorn
from src.api.main import app

if __name__ == "__main__":
    print("Starting Knowledge-base Search Engine API...")
    print("Server will be available at: http://localhost:8000")
    print("API docs will be available at: http://localhost:8000/docs")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )