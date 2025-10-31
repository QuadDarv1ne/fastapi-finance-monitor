import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the app and function
from app.main import app, get_dashboard
import asyncio

async def simulate_request():
    print("Simulating a request to the root endpoint...")
    
    # Call the function directly
    try:
        result = await get_dashboard()
        print(f"Direct function call result: {type(result)}")
        print(f"Status code: {result.status_code}")
        print(f"Content length: {len(result.body)}")
        
        # Try to make a test client request
        from fastapi.testclient import TestClient
        client = TestClient(app)
        response = client.get("/")
        print(f"\nTest client response status: {response.status_code}")
        print(f"Test client response headers: {response.headers}")
        print(f"Test client response content length: {len(response.content)}")
        if response.content:
            print(f"First 500 characters: {response.content[:500]}")
        else:
            print("Response content is empty")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Run the simulation
asyncio.run(simulate_request())