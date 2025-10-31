import requests
import json

# Test user registration with a simpler password
response = requests.post(
    'http://localhost:8000/api/users/register',
    json={
        'username': 'testuser2',
        'email': 'test2@example.com',
        'password': 'Test123!'
    }
)

print(f"Status Code: {response.status_code}")
print(f"Response: {response.json()}")