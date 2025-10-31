# Script to fix the get_dashboard function by adding the missing return statement

# Read the file
with open('app/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with the closing html tag
for i, line in enumerate(lines):
    if '</html>' in line:
        # Add the return statement after the html_content definition
        lines.insert(i + 2, '    return HTMLResponse(content=html_content, status_code=200)\n')
        break

# Write the file back
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed the get_dashboard function")