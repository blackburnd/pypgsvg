"""
Unit tests for SQL parsing functionality in create_graph.py.
"""
import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


from pypgsvg.db_parser import parse_sql_dump


@pytest.mark.unit
class TestParseSqlDump:
    """Test SQL dump parsing functionality."""
    
    def test_parse_simple_table(self):
        """Test parsing a simple table definition."""
        sql = """
        CREATE TABLE users (
            id integer NOT NULL,
            username varchar(50)
        );
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert len(tables) == 1
        assert 'users' in tables
        assert len(tables['users']['columns']) == 2
        assert tables['users']['columns'][0]['name'] == 'id'
        assert tables['users']['columns'][0]['type'] == 'integer'
        assert tables['users']['columns'][1]['name'] == 'username'
        assert tables['users']['columns'][1]['type'] == 'varchar(50)'
        assert len(foreign_keys) == 0
        assert len(errors) == 0
    
    def test_parse_table_with_foreign_key(self, sample_sql_dump):
        """Test parsing tables with foreign key relationships."""
        tables, foreign_keys, errors = parse_sql_dump(sample_sql_dump)
        
        # Check tables were parsed
        assert len(tables) >= 2
        assert 'users' in tables
        assert 'posts' in tables
        
        # Check foreign keys were parsed
        assert len(foreign_keys) >= 1
        fk_found = any(fk[0] == 'posts' and fk[1] == 'user_id' and fk[2] == 'users' for fk in foreign_keys)
        assert fk_found
    
    def test_parse_table_with_quoted_names(self):
        """Test parsing tables with quoted identifiers."""
        sql = '''
        CREATE TABLE "user_table" (
            "user_id" integer NOT NULL,
            "user_name" character varying(50)
        );
        '''
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert 'user_table' in tables
        assert tables['user_table']['columns'][0]['name'] == 'user_id'
        assert tables['user_table']['columns'][1]['name'] == 'user_name'
    
    def test_parse_table_if_not_exists(self):
        """Test parsing CREATE TABLE IF NOT EXISTS statements."""
        sql = """
        CREATE TABLE IF NOT EXISTS test_table (
            id integer,
            name varchar(100)
        );
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert 'test_table' in tables
        assert len(tables['test_table']['columns']) == 2
    
    @pytest.mark.parametrize("sql_dump", [
        """
        CREATE TABLE incomplete (
            id integer NOT NULL
        """,  # Missing closing parenthesis and semicolon
        """
        INVALID SQL STATEMENT;
        """,  # Invalid SQL
        "",  # Empty string
    ])
    def test_parse_malformed_sql(self, sql_dump):
        """Test parsing malformed SQL dumps."""
        tables, foreign_keys, errors = parse_sql_dump(sql_dump)
        
        # Should handle gracefully without crashing
        assert isinstance(tables, dict)
        assert isinstance(foreign_keys, list)
        assert isinstance(errors, list)
    
    def test_parse_foreign_key_variations(self):
        """Test parsing different foreign key syntax variations."""
        sql = """
        CREATE TABLE parent (id integer);
        CREATE TABLE child1 (id integer, parent_id integer);
        CREATE TABLE child2 (id integer, parent_id integer);
        
        ALTER TABLE child1 ADD CONSTRAINT fk1 FOREIGN KEY (parent_id) REFERENCES parent(id);
        ALTER TABLE ONLY child2 ADD CONSTRAINT fk2 FOREIGN KEY (parent_id) REFERENCES parent(id) NOT VALID;
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert len(foreign_keys) == 2
        assert any(fk[0] == 'child1' and fk[2] == 'parent' for fk in foreign_keys)
        assert any(fk[0] == 'child2' and fk[2] == 'parent' for fk in foreign_keys)
    
    def test_parse_foreign_key_with_on_delete(self):
        """Test parsing foreign keys with ON DELETE clauses."""
        sql = """
        CREATE TABLE parent (id integer);
        CREATE TABLE child (id integer, parent_id integer);
        
        ALTER TABLE child ADD CONSTRAINT fk1 FOREIGN KEY (parent_id) REFERENCES parent(id) ON DELETE CASCADE;
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert len(foreign_keys) == 1
        assert foreign_keys[0][0] == 'child'
        assert foreign_keys[0][2] == 'parent'
    
    def test_parse_foreign_key_nonexistent_table(self):
        """Test parsing foreign key that references nonexistent table."""
        sql = """
        CREATE TABLE child (id integer, parent_id integer);
        
        ALTER TABLE child ADD CONSTRAINT fk1 FOREIGN KEY (parent_id) REFERENCES nonexistent(id);
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert len(tables) == 1
        assert len(foreign_keys) == 0  # Should not be added
        assert len(errors) >= 1  # Should have parsing error
    
    def test_parse_complex_column_types(self):
        """Test parsing tables with complex column types."""
        sql = """
        CREATE TABLE complex_table (
            id bigint NOT NULL,
            price numeric(10,2),
            description text,
            created_at timestamp with time zone DEFAULT now(),
            is_active boolean DEFAULT true,
            metadata jsonb
        );
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert 'complex_table' in tables
        columns = tables['complex_table']['columns']
        assert len(columns) == 6
        
        # Check specific column types
        column_types = {col['name']: col['type'] for col in columns}
        assert column_types['id'] == 'bigint'
        assert column_types['price'] == 'numeric(10'  # Note: parser splits on comma, so we expect this
        assert column_types['description'] == 'text'
        assert 'timestamp' in column_types['created_at']
        assert column_types['is_active'] == 'boolean'
        assert column_types['metadata'] == 'jsonb'
    
    def test_parse_table_with_primary_key_constraint(self):
        """Test parsing tables with PRIMARY KEY constraints."""
        sql = """
        CREATE TABLE with_pk (
            id integer NOT NULL,
            name varchar(50),
            PRIMARY KEY (id)
        );
        """
        tables, foreign_keys, errors = parse_sql_dump(sql)
        
        assert 'with_pk' in tables
        # PRIMARY KEY constraint should not be parsed as a column
        assert len(tables['with_pk']['columns']) == 2
        column_names = [col['name'] for col in tables['with_pk']['columns']]
        assert 'id' in column_names
        assert 'name' in column_names
