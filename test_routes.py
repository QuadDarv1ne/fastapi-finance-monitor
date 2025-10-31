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
    # Check if route has the attributes we need
    if hasattr(route, 'methods') and hasattr(route, 'path') and hasattr(route, 'endpoint'):
        endpoint_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(route.endpoint)
        print(f"  {route.methods} {route.path} -> {endpoint_name}")
    else:
        print(f"  {route}")

# Check if the root route exists
root_routes = [route for route in app.routes if hasattr(route, 'path') and route.path == "/"]
print(f"\nRoot routes: {len(root_routes)}")
for route in root_routes:
    if hasattr(route, 'methods') and hasattr(route, 'endpoint'):
        endpoint_name = route.endpoint.__name__ if hasattr(route.endpoint, '__name__') else str(route.endpoint)
        print(f"  {route.methods} {route.path} -> {endpoint_name}")