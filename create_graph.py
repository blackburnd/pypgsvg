#!/usr/bin/env python3
"""
Main entry point for pypgsvg ERD generator.
Re-exports functions from src.pypgsvg for backward compatibility with tests.
"""

from src.pypgsvg import *
from src.pypgsvg import (
    parse_sql_dump,
    generate_erd_with_graphviz,
    get_contrasting_text_color,
    sanitize_label,
    should_exclude_table,
    is_standalone_table,
    extract_constraint_info,
    color_palette,
    saturate_color,
    desaturate_color,
    convert_svg_to_png,
    generate_miniature_erd,
    inject_metadata_into_svg,
    wrap_main_erd_content,
    get_svg_dimensions,
    extract_svg_dimensions_from_content
)

# For compatibility with existing code
if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='Generate ERD from PostgreSQL dump file')
    parser.add_argument('dump_file', help='Path to the PostgreSQL dump file')
    parser.add_argument('-o', '--output', default='schema_erd', help='Output file name (without extension)')
    parser.add_argument('--no-standalone', action='store_true', help='Exclude standalone tables')
    
    args = parser.parse_args()
    
    try:
        with open(args.dump_file, 'r', encoding='utf-8') as f:
            sql_content = f.read()
        
        tables, foreign_keys, errors = parse_sql_dump(sql_content)
        
        if errors:
            print("Parsing errors detected:")
            for error in errors:
                print(f"  {error}")
        
        generate_erd_with_graphviz(
            tables, 
            foreign_keys, 
            args.output,
            input_file_path=args.dump_file,
            show_standalone=not args.no_standalone
        )
        
    except FileNotFoundError:
        print(f"Error: File '{args.dump_file}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)