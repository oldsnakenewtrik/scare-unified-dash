"""
This is a targeted fix for SQLAlchemy Row conversion in the main.py file.
Run this script to update all instances of dict(row) to dict(row._mapping) for SQLAlchemy 2.0 compatibility.
"""

import re
import os

def fix_sqlalchemy_row_conversion(file_path):
    """Fix the SQLAlchemy Row conversion in the given file."""
    print(f"Fixing SQLAlchemy Row conversion in {file_path}")
    
    # Read the file content
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regular expression to match dict(row) but not dict(row._mapping)
    pattern = r'dict\(row\)'
    replacement = 'dict(row._mapping)'
    
    # Count original occurrences
    original_count = len(re.findall(pattern, content))
    
    if original_count == 0:
        print("No instances found to fix.")
        return False
    
    # Replace all occurrences
    new_content = re.sub(pattern, replacement, content)
    
    # Count new occurrences to verify changes
    new_count = len(re.findall(r'dict\(row\._mapping\)', new_content))
    
    # Write the updated content back to the file
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"Fixed {new_count} occurrences. Previously had {original_count} instances of dict(row).")
    return True

if __name__ == "__main__":
    main_py_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "main.py")
    if os.path.exists(main_py_path):
        fixed = fix_sqlalchemy_row_conversion(main_py_path)
        if fixed:
            print("✅ Successfully fixed SQLAlchemy Row conversion in main.py")
        else:
            print("⚠️ No changes needed or file couldn't be processed")
    else:
        print(f"❌ File not found: {main_py_path}")
