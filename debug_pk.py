#!/usr/bin/env python3
"""
Debug script to understand why inline composite primary key detection isn't working
"""

from src.pypgsvg.db_parser import parse_sql_dump
import re

def debug_composite_primary_key():
    """Debug the parsing of composite primary keys"""
    
    sql_inline = """
    CREATE TABLE test_table (
        col1 integer NOT NULL,
        col2 integer NOT NULL,
        col3 varchar(50),
        PRIMARY KEY (col1, col2)
    );
    """
    
    print("=== Debug Inline Composite Primary Key ===")
    tables, foreign_keys, triggers, errors = parse_sql_dump(sql_inline)
    
    if 'test_table' in tables:
        table_data = tables['test_table']
        print(f"Table lines: {repr(table_data['lines'])}")
        
        # Test the pattern manually
        inline_pk_pattern = re.compile(r'PRIMARY\s+KEY\s*\(([^)]+)\)', re.I)
        pk_match = inline_pk_pattern.search(table_data['lines'])
        
        if pk_match:
            print(f"Pattern matched: {pk_match.group(0)}")
            print(f"Captured group: {pk_match.group(1)}")
            pk_columns = [col.strip().strip('"') 
                         for col in pk_match.group(1).split(',')]
            print(f"Parsed columns: {pk_columns}")
        else:
            print("Pattern did not match")
            print("Trying different patterns...")
            
            # Try a more relaxed pattern
            patterns = [
                r'PRIMARY\s+KEY\s*\(([^)]+)\)',
                r'PRIMARY KEY\s*\(([^)]+)\)',
                r'primary\s+key\s*\(([^)]+)\)',
            ]
            
            for i, pattern_str in enumerate(patterns):
                pattern = re.compile(pattern_str, re.I)
                match = pattern.search(table_data['lines'])
                if match:
                    print(f"Pattern {i+1} matched: {match.group(0)}")
                    break
                else:
                    print(f"Pattern {i+1} failed: {pattern_str}")

if __name__ == "__main__":
    debug_composite_primary_key()
