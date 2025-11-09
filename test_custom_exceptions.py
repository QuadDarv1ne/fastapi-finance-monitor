"""Test script to verify custom exception handling"""

import requests
import time

def test_custom_exceptions():
    """Test custom exception handling scenarios"""
    base_url = "http://localhost:8000"
    
    print("Testing custom exception handling...")
    
    # Test 1: Health check endpoint (should work)
    print("\n1. Testing health check endpoint:")
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 2: Detailed health check endpoint (should work)
    print("\n2. Testing detailed health check endpoint:")
    try:
        response = requests.get(f"{base_url}/api/health/detailed")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 3: User registration endpoint with invalid data
    print("\n3. Testing user registration with invalid data:")
    try:
        response = requests.post(f"{base_url}/api/users/register", json={})
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    # Test 4: User registration endpoint with valid data (but will fail due to missing auth)
    print("\n4. Testing user registration with valid format:")
    try:
        response = requests.post(f"{base_url}/api/users/register", json={
            "username": "testuser",
            "email": "test@example.com",
            "password": "testpassword123"
        })
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\nTest completed!")

if __name__ == "__main__":
    test_custom_exceptions()