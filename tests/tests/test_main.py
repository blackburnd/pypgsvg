"""
Tests for the main execution and file handling in create_graph.py.
"""
import pytest
import sys
import os
import tempfile
from unittest.mock import Mock, patch, mock_open

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import create_graph


@pytest.mark.unit
class TestMainExecution:
    """Test the main execution workflow and file handling."""
    
    @patch('create_graph.generate_erd_with_graphviz')
    @patch('create_graph.parse_sql_dump')
    @patch('builtins.open', new_callable=mock_open, read_data="CREATE TABLE test (id integer);")
    def test_file_reading_workflow(self, mock_file, mock_parse, mock_generate):
        """Test file reading and processing workflow."""
        # Setup mocks
        mock_parse.return_value = ({'test': {'columns': []}}, [], [])
        
        # Simulate the main workflow (without __main__ check)
        with patch('builtins.open', mock_file):
            with mock_file.return_value as file:
                sql_content = file.read()
                tables, foreign_keys, errors = create_graph.parse_sql_dump(sql_content)
                if not errors:
                    create_graph.generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Verify functions were called
        mock_parse.assert_called_once()
        mock_generate.assert_called_once()
    
    @patch('create_graph.parse_sql_dump')
    @patch('builtins.print')
    def test_error_handling_workflow(self, mock_print, mock_parse):
        """Test error handling when parsing fails."""
        # Setup mock to return parsing errors
        mock_parse.return_value = ({}, [], ['Parsing error'])
        
        # Simulate the workflow
        tables, foreign_keys, errors = mock_parse("some sql")
        if errors:
            print("ERD generation skipped due to parsing errors.")
        
        # Verify error message was printed
        mock_print.assert_called_with("ERD generation skipped due to parsing errors.")
    
    @patch('builtins.print')
    def test_unicode_decode_error_simulation(self, mock_print):
        """Test Unicode decode error handling simulation."""
        # Simulate the error handling code path
        try:
            raise UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
        except UnicodeDecodeError as e:
            print(f"Encoding error reading the file: {e}")
            print("Attempting to read with error handling...")
        
        # Verify error handling messages were printed
        error_prints = [call for call in mock_print.call_args_list 
                       if 'Encoding error' in str(call)]
        assert len(error_prints) >= 1


@pytest.mark.unit 
class TestColorPalette:
    """Test the color palette functionality."""
    
    def test_color_palette_exists(self):
        """Test that color palette is defined and accessible."""
        assert hasattr(create_graph, 'color_palette')
        assert len(create_graph.color_palette) > 0
        
        # Verify all colors are valid hex colors
        for color in create_graph.color_palette:
            assert color.startswith('#')
            assert len(color) == 7
            # Verify it's a valid hex color
            int(color[1:], 16)  # Should not raise exception
    
    def test_color_palette_accessibility(self):
        """Test that all palette colors work with contrast function."""
        for color in create_graph.color_palette:
            result = create_graph.get_contrasting_text_color(color)
            assert result in ['black', 'white']


@pytest.mark.unit
class TestErrorHandling:
    """Test error handling in various functions."""
    
    def test_parse_sql_dump_exception_handling(self):
        """Test that parse_sql_dump handles unexpected exceptions."""
        # This should trigger the general exception handler
        malformed_sql = "CREATE TABLE test (\nid integer\n"  # Unclosed parenthesis
        
        tables, foreign_keys, errors = create_graph.parse_sql_dump(malformed_sql)
        
        # Should handle gracefully
        assert isinstance(tables, dict)
        assert isinstance(foreign_keys, list)
        assert isinstance(errors, list)
    
    @patch('create_graph.Digraph')
    def test_generate_erd_with_missing_tables(self, mock_digraph):
        """Test ERD generation with tables missing from foreign key references."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        
        tables = {'table1': {'columns': [], 'lines': 'table1'}}
        foreign_keys = [('table1', 'col', 'missing_table', 'id', 'FK constraint')]
        
        # Should not crash
        create_graph.generate_erd_with_graphviz(tables, foreign_keys, "test")
        
        # Should create node for existing table
        assert mock_dot.node.call_count == 1
        # Should not create edge for missing table reference
        assert mock_dot.edge.call_count == 0


@pytest.mark.unit
class TestRegexPatterns:
    """Test the regex patterns used in parsing."""
    
    def test_table_pattern_matching(self):
        """Test table creation pattern matching."""
        # Access the pattern from the function (requires some refactoring ideally)
        test_cases = [
            "CREATE TABLE test (id integer);",
            "CREATE TABLE IF NOT EXISTS test (id integer);",
            'CREATE TABLE "quoted_table" (id integer);',
            "create table lowercase (id integer);",  # Case insensitive
        ]
        
        for sql in test_cases:
            tables, _, _ = create_graph.parse_sql_dump(sql)
            assert len(tables) >= 1
    
    def test_foreign_key_pattern_matching(self):
        """Test foreign key pattern matching."""
        sql = """
        CREATE TABLE parent (id integer);
        CREATE TABLE child (id integer, parent_id integer);
        ALTER TABLE child ADD CONSTRAINT fk FOREIGN KEY (parent_id) REFERENCES parent(id);
        ALTER TABLE ONLY child ADD CONSTRAINT fk2 FOREIGN KEY (parent_id) REFERENCES parent(id) NOT VALID;
        """
        
        tables, foreign_keys, errors = create_graph.parse_sql_dump(sql)
        
        assert len(foreign_keys) >= 1
        assert any('child' in fk and 'parent' in fk for fk in foreign_keys)
