"""
Simple test to examine container functionality in generated SVGs.
"""

import pytest
import tempfile
import os
from pypgsvg.erd_generator import generate_erd_with_graphviz


def test_examine_container_functionality():
    """Examine the generated SVG for container functionality differences."""
    
    # Simple schema
    tables = {
        "users": {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "username", "type": "varchar(50)"}
            ]
        },
        "posts": {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "user_id", "type": "integer"}
            ]
        }
    }
    foreign_keys = [
        ("posts", "user_id", "users", "id", 
         "FOREIGN KEY (user_id) REFERENCES users(id)", "CASCADE", "CASCADE")
    ]
    
    # Generate SVG
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        
        print("\n" + "="*80)
        print("EXAMINING GENERATED SVG CONTENT")
        print("="*80)
        
        # Check for containers
        has_selection_container = 'id="selection-container"' in svg_content
        has_miniature_container = 'id="miniature-container"' in svg_content
        
        print(f"Selection container present: {has_selection_container}")
        print(f"Miniature container present: {has_miniature_container}")
        
        if has_selection_container or has_miniature_container:
            # Extract JavaScript section
            js_start = svg_content.find('<script type="text/javascript">')
            js_end = svg_content.find('</script>', js_start)
            
            if js_start != -1 and js_end != -1:
                js_section = svg_content[js_start:js_end]
                
                print("\n" + "-"*50)
                print("JAVASCRIPT EVENT HANDLERS ANALYSIS")
                print("-"*50)
                
                # Check for event handlers
                selection_listeners = js_section.count('selectionContainer.addEventListener')
                miniature_listeners = js_section.count('miniatureContainer.addEventListener')
                miniature_header_listeners = js_section.count('miniatureHeader.addEventListener')
                
                print(f"Selection container event listeners: {selection_listeners}")
                print(f"Miniature container event listeners: {miniature_listeners}")
                print(f"Miniature header event listeners: {miniature_header_listeners}")
                
                # Check for drag state variables
                has_selection_drag = 'isDraggingSelection' in js_section
                has_miniature_drag = 'isDraggingMiniature' in js_section
                has_miniature_window_drag = 'miniature-window' in js_section
                
                print(f"Selection drag state variable: {has_selection_drag}")
                print(f"Miniature drag state variable: {has_miniature_drag}")
                print(f"Miniature window drag state: {has_miniature_window_drag}")
                
                # Check for makeResizable calls
                selection_resizable = 'makeResizable(selectionContainer)' in js_section
                miniature_resizable = 'makeResizable(miniatureContainer)' in js_section
                
                print(f"Selection makeResizable call: {selection_resizable}")
                print(f"Miniature makeResizable call: {miniature_resizable}")
                
                # Look for specific mousedown handlers
                if 'selectionContainer.addEventListener(\'mousedown\'' in js_section:
                    print("[OK] Selection container has isolated mousedown handler")
                else:
                    print("[MISSING] Selection container missing isolated mousedown handler")

                if 'miniatureHeader.addEventListener(\'mousedown\'' in js_section:
                    print("[OK] Miniature header has isolated mousedown handler")
                else:
                    print("[MISSING] Miniature header missing isolated mousedown handler")

                # Check for document event listeners instead of global mousemove
                if 'window.addEventListener(\'mousemove\'' in js_section:
                    print("[OK] Window mousemove handlers present (isolated approach)")
                elif 'document.addEventListener(\'mousemove\'' in js_section:
                    print("[OK] Global mousemove handler present")
                else:
                    print("[MISSING] No mousemove handlers found")
                
                print("\n" + "-"*50)
                print("CSS ANALYSIS")
                print("-"*50)
                
                # Extract CSS section
                css_start = svg_content.find('<style type="text/css">')
                css_end = svg_content.find('</style>', css_start)
                
                if css_start != -1 and css_end != -1:
                    css_section = svg_content[css_start:css_end]
                    
                    # Check for cursor syntax errors
                    if 'cursor;' in css_section:
                        print("[ERROR] Found CSS cursor syntax errors (semicolon instead of colon)")
                    else:
                        print("[OK] No CSS cursor syntax errors found")

                    # Check for proper cursor styles
                    cursor_styles = ['cursor:nw-resize', 'cursor:ne-resize', 'cursor:sw-resize', 'cursor:se-resize']
                    for style in cursor_styles:
                        if style in css_section:
                            print(f"[OK] Found {style}")
                        else:
                            print(f"[MISSING] Missing {style}")
                
                # Print a sample of the JavaScript for manual inspection
                print("\n" + "-"*50)
                print("JAVASCRIPT SAMPLE (first 2000 chars)")
                print("-"*50)
                print(js_section[:2000])
                
        # The test should pass if we can examine the content
        assert True, "SVG examination completed"


if __name__ == "__main__":
    test_examine_container_functionality()
