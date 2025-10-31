import requests

# Make a request to the main page
response = requests.get("http://127.0.0.1:8000/")

print(f"Status Code: {response.status_code}")
print(f"Content Length: {len(response.text)}")
print(f"Content Type: {response.headers.get('content-type')}")

# Print first 500 characters of the response
print("\nFirst 500 characters of response:")
print(response.text[:500])

# Check if the response contains expected HTML elements
if "<title>FastAPI Finance Monitor</title>" in response.text:
    print("\n✓ Title found")
else:
    print("\n✗ Title not found")

if "<body>" in response.text:
    print("✓ Body tag found")
else:
    print("✗ Body tag not found")

if "</html>" in response.text:
    print("✓ HTML closing tag found")
else:
    print("✗ HTML closing tag not found")