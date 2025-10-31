import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the function
from app.main import get_dashboard
import asyncio

async def debug_dashboard():
    try:
        print("Calling get_dashboard function...")
        result = await get_dashboard()
        print(f"Function returned: {type(result)}")
        print(f"Result status code: {result.status_code}")
        print(f"Result headers: {result.headers}")
        
        # Get the content
        content = result.body
        print(f"Content type: {type(content)}")
        print(f"Content length: {len(content)}")
        
        # Convert to string if it's bytes
        if isinstance(content, bytes):
            content_str = content.decode('utf-8')
            print(f"Content string length: {len(content_str)}")
            print("First 500 characters:")
            print(content_str[:500])
        else:
            print(f"Content: {content}")
            
    except Exception as e:
        print(f"Error occurred: {e}")
        import traceback
        traceback.print_exc()

# Run the debug
asyncio.run(debug_dashboard())