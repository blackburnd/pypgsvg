#!/usr/bin/env python3
"""
Test script to check composite primary key support in pypgsvg
"""

from src.pypgsvg.db_parser import parse_sql_dump

def test_composite_primary_key():
    """Test parsing of composite primary keys"""
    
    # Test 1: Inline composite primary key
    sql_inline = """
    CREATE TABLE test_table (
        col1 integer NOT NULL,
        col2 integer NOT NULL,
        col3 varchar(50),
        PRIMARY KEY (col1, col2)
    );
    """
    
    print("=== Testing Inline Composite Primary Key ===")
    tables, foreign_keys, triggers, errors = parse_sql_dump(sql_inline)
    
    if 'test_table' in tables:
        print("✓ Table found")
        columns = tables['test_table']['columns']
        pk_columns = [col['name'] for col in columns if col.get('is_primary_key', False)]
        print(f"Primary key columns: {pk_columns}")
        
        if sorted(pk_columns) == sorted(['col1', 'col2']):
            print("✓ Composite primary key correctly identified")
        else:
            print("✗ Composite primary key not correctly identified")
            print(f"Expected: ['col1', 'col2'], Got: {pk_columns}")
    else:
        print("✗ Table not found")
    
    if errors:
        print(f"Parsing errors: {errors}")
    
    print()
    
    # Test 2: ALTER TABLE composite primary key
    sql_alter = """
    CREATE TABLE test_table2 (
        col1 integer NOT NULL,
        col2 integer NOT NULL,
        col3 varchar(50)
    );
    
    ALTER TABLE test_table2 ADD CONSTRAINT test_pk PRIMARY KEY (col1, col2);
    """
    
    print("=== Testing ALTER TABLE Composite Primary Key ===")
    tables, foreign_keys, triggers, errors = parse_sql_dump(sql_alter)
    
    if 'test_table2' in tables:
        print("✓ Table found")
        columns = tables['test_table2']['columns']
        pk_columns = [col['name'] for col in columns if col.get('is_primary_key', False)]
        print(f"Primary key columns: {pk_columns}")
        
        if sorted(pk_columns) == sorted(['col1', 'col2']):
            print("✓ Composite primary key correctly identified")
        else:
            print("✗ Composite primary key not correctly identified")
            print(f"Expected: ['col1', 'col2'], Got: {pk_columns}")
    else:
        print("✗ Table not found")
    
    if errors:
        print(f"Parsing errors: {errors}")
    
    print()
    
    # Test 3: Complex example with foreign keys referencing composite primary key
    sql_complex = """
    CREATE TABLE parent_table (
        id1 integer NOT NULL,
        id2 integer NOT NULL,
        name varchar(100),
        PRIMARY KEY (id1, id2)
    );
    
    CREATE TABLE child_table (
        child_id serial PRIMARY KEY,
        parent_id1 integer NOT NULL,
        parent_id2 integer NOT NULL,
        data text
    );
    
    ALTER TABLE child_table ADD CONSTRAINT fk_parent 
        FOREIGN KEY (parent_id1, parent_id2) REFERENCES parent_table(id1, id2);
    """
    
    print("=== Testing Composite PK with Composite FK ===")
    tables, foreign_keys, triggers, errors = parse_sql_dump(sql_complex)
    
    print(f"Tables found: {list(tables.keys())}")
    print(f"Foreign keys found: {len(foreign_keys)}")
    
    if 'parent_table' in tables:
        columns = tables['parent_table']['columns']
        pk_columns = [col['name'] for col in columns if col.get('is_primary_key', False)]
        print(f"Parent table primary key columns: {pk_columns}")
    
    if foreign_keys:
        print(f"Foreign key details: {foreign_keys}")
    
    if errors:
        print(f"Parsing errors: {errors}")

if __name__ == "__main__":
    test_composite_primary_key()
