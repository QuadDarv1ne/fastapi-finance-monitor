import requests
import json

# Test user registration
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