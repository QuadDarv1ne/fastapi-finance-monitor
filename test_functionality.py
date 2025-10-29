#!/usr/bin/env python3
"""
Test script to verify all functionality of the FastAPI Finance Monitor
"""

import requests
import time
import sys
import os

# Add the app directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), 'app'))

def test_health_check():
    """Test the health check endpoint"""
    try:
        response = requests.get('http://localhost:8000/api/health', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Health check: {data['message']}")
            return True
        else:
            print(f"✗ Health check failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False

def test_watchlist():
    """Test the watchlist endpoints"""
    try:
        # Get current watchlist
        response = requests.get('http://localhost:8000/api/watchlist', timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Watchlist retrieval: {len(data['watchlist'])} assets")
            
            # Try to add an asset
            add_response = requests.post(
                'http://localhost:8000/api/watchlist/add',
                params={'symbol': 'NVDA'},
                timeout=5
            )
            if add_response.status_code == 200:
                print("✓ Asset added to watchlist")
                
                # Verify it was added
                verify_response = requests.get('http://localhost:8000/api/watchlist', timeout=5)
                if verify_response.status_code == 200:
                    verify_data = verify_response.json()
                    if 'NVDA' in verify_data['watchlist']:
                        print("✓ Asset verification successful")
                        return True
                    else:
                        print("✗ Asset not found in watchlist after addition")
                        return False
                else:
                    print("✗ Failed to verify watchlist after addition")
                    return False
            else:
                print("✗ Failed to add asset to watchlist")
                return False
        else:
            print(f"✗ Watchlist retrieval failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Watchlist test failed: {e}")
        return False

def test_search():
    """Test the search endpoint"""
    try:
        response = requests.get(
            'http://localhost:8000/api/search',
            params={'query': 'Apple'},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            print(f"✓ Search functionality: Found {len(data['results'])} results")
            return True
        else:
            print(f"✗ Search failed with status {response.status_code}")
            return False
    except Exception as e:
        print(f"✗ Search test failed: {e}")
        return False

def main():
    """Main test function"""
    print("Testing FastAPI Finance Monitor functionality...")
    print("=" * 50)
    
    # Wait a moment for the server to fully start
    time.sleep(2)
    
    tests = [
        test_health_check,
        test_watchlist,
        test_search
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the application.")
        return 1

if __name__ == "__main__":
    sys.exit(main())