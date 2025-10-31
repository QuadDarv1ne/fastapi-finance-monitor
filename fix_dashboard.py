# Script to fix the get_dashboard function by adding the missing return statement

# Read the file
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find the get_dashboard function
import re

# Pattern to find the end of the html_content definition
pattern = r'(html_content = """\s*</html>\s*"""\s*)'

# Add the return statement
replacement = r'\1\n    return HTMLResponse(content=html_content, status_code=200)'

# Replace the content
fixed_content = re.sub(pattern, replacement, content, count=1)

# Write the file back
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.write(fixed_content)

print("Fixed the get_dashboard function")