import requests
import json
import traceback

# Test user registration with detailed error handling
try:
    response = requests.post(
        'http://localhost:8000/api/users/register',
        json={
            'username': 'testuser',
            'email': 'test@example.com',
            'password': 'Test123!'
        }
    )
    
    print(f"Status Code: {response.status_code}")
    print(f"Response: {response.json()}")
except Exception as e:
    print(f"Exception occurred: {str(e)}")
    print(f"Traceback: {traceback.format_exc()}")