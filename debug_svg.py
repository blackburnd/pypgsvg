#!/usr/bin/env python3
import sys
import os
sys.path.insert(0, 'src')

from pypgsvg.erd_generator import generate_erd_with_graphviz
import tempfile

# Simple test schema
tables = {
    "users": {
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "username", "type": "varchar(50)"},
            {"name": "email", "type": "varchar(100)"}
        ]
    },
    "posts": {
        "columns": [
            {"name": "id", "type": "integer"},
            {"name": "user_id", "type": "integer"},
            {"name": "title", "type": "varchar(200)"},
            {"name": "content", "type": "text"}
        ]
    }
}
foreign_keys = [
    ("posts", "user_id", "users", "id", 
     "FOREIGN KEY (user_id) REFERENCES users(id)", "CASCADE", "CASCADE")
]

with tempfile.TemporaryDirectory() as tmpdir:
    output_file = os.path.join(tmpdir, "test_erd")
    generate_erd_with_graphviz(tables, foreign_keys, output_file)
    svg_path = output_file + ".svg"
    
    with open(svg_path, "r", encoding="utf-8") as f:
        svg_content = f.read()
    
    print("Looking for selection-container...")
    if 'id="selection-container"' in svg_content:
        print("✓ Found id=\"selection-container\"")
        # Find the div and print the surrounding context
        pos = svg_content.find('id="selection-container"')
        start = max(0, pos - 100)
        end = min(len(svg_content), pos + 300)
        print(f"Context around selection-container:")
        print(svg_content[start:end])
        print("\n" + "="*80 + "\n")
        
        if 'class="selection-container"' in svg_content:
            print("✓ Found class=\"selection-container\"")
        else:
            print("✗ class=\"selection-container\" NOT FOUND")
            # Check for partial matches
            if 'class="selection-container container"' in svg_content:
                print("✓ Found class=\"selection-container container\"")
            if 'selection-container container' in svg_content:
                print("✓ Found 'selection-container container' (without quotes)")
            if 'selection-container' in svg_content:
                print("✓ Found 'selection-container' somewhere")
            # Let's search for what class it actually has
            lines = svg_content.split('\n')
            for i, line in enumerate(lines):
                if 'selection-container' in line and 'class=' in line:
                    print(f"Line {i}: {line.strip()}")
    else:
        print("✗ id=\"selection-container\" NOT FOUND")
    
    print("\nLooking for miniature-container...")
    if 'id="miniature-container"' in svg_content:
        print("✓ Found id=\"miniature-container\"")
        if 'class="miniature-container"' in svg_content:
            print("✓ Found class=\"miniature-container\"")
        else:
            print("✗ class=\"miniature-container\" NOT FOUND")
            # Check for partial matches
            if 'class="miniature-container container"' in svg_content:
                print("✓ Found class=\"miniature-container container\"")
            if 'miniature-container container' in svg_content:
                print("✓ Found 'miniature-container container' (without quotes)")
            # Let's search for what class it actually has
            lines = svg_content.split('\n')
            for i, line in enumerate(lines):
                if 'miniature-container' in line and 'class=' in line:
                    print(f"Line {i}: {line.strip()}")
    else:
        print("✗ id=\"miniature-container\" NOT FOUND")
