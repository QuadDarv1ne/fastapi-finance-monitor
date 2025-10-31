# Script to fix the main.py file
with open('app/main.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find and replace the problematic line
if 'alert_type: type' in content:
    # Replace from the problematic line to the end with correct HTML closing
    pos = content.rfind('alert_type: type')
    fixed_content = content[:pos] + '        </script>\n    </body>\n</html>\n""";'
    
    # Write the fixed content back
    with open('app/main.py', 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    
    print("File fixed successfully!")
else:
    print("No issues found in the file.")