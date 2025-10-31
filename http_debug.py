import socket
import time

# Create a socket connection to the server
host = '127.0.0.1'
port = 8000

try:
    # Create socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(10)  # 10 second timeout
    
    # Connect to server
    print(f"Connecting to {host}:{port}...")
    sock.connect((host, port))
    
    # Send HTTP GET request
    request = f"GET / HTTP/1.1\r\nHost: {host}:{port}\r\nConnection: close\r\n\r\n"
    print("Sending request...")
    sock.send(request.encode())
    
    # Receive response
    print("Receiving response...")
    response = b""
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                break
            response += data
        except socket.timeout:
            break
    
    # Close socket
    sock.close()
    
    # Parse response
    response_str = response.decode('utf-8', errors='ignore')
    print(f"Response length: {len(response)}")
    print(f"Response (first 1000 chars):\n{response_str[:1000]}")
    
    # Check if we have headers and body
    if '\r\n\r\n' in response_str:
        headers, body = response_str.split('\r\n\r\n', 1)
        print(f"\nHeaders:\n{headers}")
        print(f"\nBody length: {len(body)}")
        print(f"Body (first 500 chars):\n{body[:500]}")
    else:
        print("No headers/body separation found")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()