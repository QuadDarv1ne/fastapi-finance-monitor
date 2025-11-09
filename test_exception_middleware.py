"""Test script to verify exception handling middleware is working properly"""

import requests
import time

def test_exception_handling():
    """Test various exception scenarios"""
    base_url = "http://localhost:8000"
    
    print("Testing exception handling middleware...")
    
    # Test 1: Health check endpoint (should work)
    print("\n1. Testing health check endpoint:")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Non-existent endpoint (should return 404)
    print("\n2. Testing non-existent endpoint:")
    try:
        response = requests.get(f"{base_url}/non-existent")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: API endpoint (should work)
    print("\n3. Testing API health endpoint:")
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_exception_handling()