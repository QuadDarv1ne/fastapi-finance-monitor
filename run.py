#!/usr/bin/env python3
"""
Run script for the FastAPI Finance Monitor
"""

import sys
import os
import argparse
import subprocess
import time

def run_direct():
    """Run the application directly"""
    print("Starting FastAPI Finance Monitor...")
    print("Visit http://localhost:8000 in your browser")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        # Run the main application
        subprocess.run([sys.executable, "app/main.py"], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped.")
    except Exception as e:
        print(f"Error running application: {e}")

def run_uvicorn():
    """Run the application with uvicorn"""
    print("Starting FastAPI Finance Monitor with Uvicorn...")
    print("Visit http://localhost:8000 in your browser")
    print("Press Ctrl+C to stop")
    print()
    
    try:
        subprocess.run([
            sys.executable, "-m", "uvicorn", 
            "app.main:app", 
            "--host", "0.0.0.0", 
            "--port", "8000"
        ], check=True)
    except KeyboardInterrupt:
        print("\nApplication stopped.")
    except Exception as e:
        print(f"Error running application: {e}")

def run_docker():
    """Run the application with Docker"""
    print("Starting FastAPI Finance Monitor with Docker...")
    print("Make sure Docker is installed and running")
    print()
    
    try:
        subprocess.run(["docker-compose", "up"], check=True)
    except FileNotFoundError:
        print("Docker Compose not found. Please install Docker Desktop.")
    except KeyboardInterrupt:
        print("\nStopping Docker containers...")
        subprocess.run(["docker-compose", "down"])
    except Exception as e:
        print(f"Error running Docker: {e}")

def test_application():
    """Run basic tests"""
    print("Running basic tests...")
    print()
    
    try:
        subprocess.run([sys.executable, "test_functionality.py"], check=True)
    except Exception as e:
        print(f"Error running tests: {e}")

def show_info():
    """Show application information"""
    print("FastAPI Finance Monitor")
    print("=" * 30)
    print("A real-time financial dashboard for stocks, crypto, and commodities")
    print()
    print("Features:")
    print("  • Real-time data updates via WebSocket")
    print("  • Technical indicators (RSI, MACD, Bollinger Bands, etc.)")
    print("  • Personalized watchlists")
    print("  • Interactive charts")
    print("  • Responsive dark theme UI")
    print()
    print("Usage:")
    print("  python run.py                # Show this help")
    print("  python run.py start          # Run directly")
    print("  python run.py uvicorn        # Run with Uvicorn")
    print("  python run.py docker         # Run with Docker")
    print("  python run.py test           # Run basic tests")
    print("  python run.py info           # Show this information")
    print()

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="FastAPI Finance Monitor Runner")
    parser.add_argument(
        "command", 
        nargs="?", 
        default="info",
        choices=["start", "uvicorn", "docker", "test", "info"],
        help="Command to run"
    )
    
    args = parser.parse_args()
    
    if args.command == "start":
        run_direct()
    elif args.command == "uvicorn":
        run_uvicorn()
    elif args.command == "docker":
        run_docker()
    elif args.command == "test":
        test_application()
    else:
        show_info()

if __name__ == "__main__":
    main()