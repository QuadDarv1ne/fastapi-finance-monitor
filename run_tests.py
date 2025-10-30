#!/usr/bin/env python3
"""
Test runner script for FastAPI Finance Monitor
"""

import sys
import os
import subprocess
import argparse

def run_pytest_tests():
    """Run pytest tests"""
    print("Running pytest tests...")
    try:
        # Run pytest on the tests directory
        result = subprocess.run([
            sys.executable, "-m", "pytest", 
            "app/tests/", 
            "-v", 
            "--tb=short"
        ], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running pytest tests: {e}")
        return False

def run_functionality_tests():
    """Run functionality tests"""
    print("Running functionality tests...")
    try:
        result = subprocess.run([
            sys.executable, "test_functionality.py"
        ], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running functionality tests: {e}")
        return False

def run_indicators_demo():
    """Run indicators demonstration"""
    print("Running technical indicators demonstration...")
    try:
        result = subprocess.run([
            sys.executable, "demonstrate_indicators.py"
        ], check=False)
        return result.returncode == 0
    except Exception as e:
        print(f"Error running indicators demo: {e}")
        return False

def main():
    """Main test runner"""
    parser = argparse.ArgumentParser(description="Run tests for FastAPI Finance Monitor")
    parser.add_argument(
        "test_type",
        nargs="?",
        default="all",
        choices=["all", "unit", "functionality", "indicators"],
        help="Type of tests to run"
    )
    
    args = parser.parse_args()
    
    print("FastAPI Finance Monitor - Test Runner")
    print("=" * 40)
    
    success = True
    
    if args.test_type in ["all", "unit"]:
        print("\n1. Running unit tests...")
        if not run_pytest_tests():
            success = False
    
    if args.test_type in ["all", "functionality"]:
        print("\n2. Running functionality tests...")
        if not run_functionality_tests():
            success = False
    
    if args.test_type in ["all", "indicators"]:
        print("\n3. Running indicators demonstration...")
        if not run_indicators_demo():
            success = False
    
    print("\n" + "=" * 40)
    if success:
        print("🎉 All tests completed successfully!")
        return 0
    else:
        print("❌ Some tests failed. Please check the output above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())