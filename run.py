#!/usr/bin/env python3
"""
Run script for the FastAPI Finance Monitor
"""

import sys
import os

# Add the app directory to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'app'))

def main():
    """Main entry point"""
    print("FastAPI Finance Monitor")
    print("======================")
    print("To run the application, use one of the following commands:")
    print()
    print("1. Direct execution:")
    print("   python app/main.py")
    print()
    print("2. Using uvicorn:")
    print("   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000")
    print()
    print("3. Using Docker:")
    print("   docker-compose up -d")
    print()
    print("Visit http://localhost:8000 in your browser to access the dashboard.")

if __name__ == "__main__":
    main()