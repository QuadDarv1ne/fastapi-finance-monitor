# Script to fix the indentation of the return statement in get_dashboard function

# Read the file
with open('app/main.py', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Find the line with the return statement and fix indentation
for i, line in enumerate(lines):
    if 'return HTMLResponse(content=html_content, status_code=200)' in line:
        # Fix indentation (should be at function level, not inside the string)
        lines[i] = '    return HTMLResponse(content=html_content, status_code=200)\n'
        break

# Write the file back
with open('app/main.py', 'w', encoding='utf-8') as f:
    f.writelines(lines)

print("Fixed the indentation of the return statement")