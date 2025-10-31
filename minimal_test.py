import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the app
from app.main import app
from fastapi.testclient import TestClient

# Create a test client
client = TestClient(app)

# Make a request to the root endpoint
print("Making request to root endpoint...")
response = client.get("/")

print(f"Status code: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Content length: {len(response.content)}")

if response.content:
    print("Response has content")
    # Check if it contains expected elements
    content_str = response.content.decode('utf-8')
    if "<title>FastAPI Finance Monitor</title>" in content_str:
        print("✓ Title found")
    else:
        print("✗ Title not found")
else:
    print("Response is empty")