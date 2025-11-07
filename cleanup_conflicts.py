#!/usr/bin/env python3
"""
Script to remove merge conflict markers from all files in the repository.
Keeps the HEAD version (first part) of each conflict.
"""

import os
import re

def remove_conflict_markers(filepath):
    """Remove merge conflict markers from a file, keeping HEAD version."""
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        
        # Check if file has conflict markers
        if '<<<<<<< HEAD' not in content:
            return False
        
        # Pattern to match conflict blocks
        # Keeps the HEAD version (between <<<<<<< HEAD and =======)
        pattern = r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]+\n'
        
        def replace_conflict(match):
            head_version = match.group(1)
            return head_version + '\n'
        
        # Replace all conflicts
        cleaned_content = re.sub(pattern, replace_conflict, content, flags=re.DOTALL)
        
        # Write back
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(cleaned_content)
        
        print(f"✓ Cleaned: {filepath}")
        return True
    except Exception as e:
        print(f"✗ Error in {filepath}: {e}")
        return False

# Find all files with conflict markers
app_dir = os.path.dirname(os.path.abspath(__file__))
files_with_conflicts = []

for root, dirs, files in os.walk(app_dir):
    # Skip git folder
    if '.git' in dirs:
        dirs.remove('.git')
    if '__pycache__' in dirs:
        dirs.remove('__pycache__')
    
    for file in files:
        filepath = os.path.join(root, file)
        try:
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                if '<<<<<<< HEAD' in f.read():
                    files_with_conflicts.append(filepath)
        except:
            pass

print(f"Found {len(files_with_conflicts)} files with conflict markers\n")

# Clean each file
cleaned_count = 0
for filepath in files_with_conflicts:
    if remove_conflict_markers(filepath):
        cleaned_count += 1

print(f"\nCleaned {cleaned_count} files successfully!")
