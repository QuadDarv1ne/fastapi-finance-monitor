# Test script to check if the get_dashboard function works correctly

import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the function
from app.main import get_dashboard

# Test the function
import asyncio

async def test_dashboard():
    try:
        result = await get_dashboard()
        print(f"Type of result: {type(result)}")
        print(f"Result: {result}")
        if hasattr(result, 'body'):
            print(f"Body length: {len(result.body)}")
            print(f"Body content (first 500 chars): {result.body[:500]}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

# Run the test
asyncio.run(test_dashboard())