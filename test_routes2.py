import sys
import os

# Add the current directory and parent directory to the path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the app
from app.main import app

# Print all registered routes
print("Registered routes:")
for route in app.routes:
    print(f"  Route: {route}")

# Check if the root route exists by looking at the app's openapi spec
print("\nChecking routes via OpenAPI spec:")
try:
    openapi_spec = app.openapi()
    paths = openapi_spec.get('paths', {})
    for path, methods in paths.items():
        print(f"  {path}: {list(methods.keys())}")
        
        # Check if we have a root path
        if path == "/":
            print(f"  ✓ Found root path with methods: {list(methods.keys())}")
            
except Exception as e:
    print(f"Error getting OpenAPI spec: {e}")