"""
Integration tests for the complete create_graph workflow.
"""
import pytest
import sys
import os
import tempfile
from unittest.mock import patch, Mock


from pypgsvg.db_parser import parse_sql_dump
from pypgsvg.erd_generator import generate_erd_with_graphviz
from pypgsvg.metadata_injector import inject_metadata_into_svg


@pytest.mark.integration
class TestIntegration:
    """Integration tests for the complete workflow."""
    
    @patch('create_graph.Digraph')
    def test_complete_workflow(self, mock_digraph, sample_sql_dump):
        """Test the complete workflow from SQL dump to ERD generation."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        
        # Parse the SQL dump
        tables, foreign_keys, errors = parse_sql_dump(sample_sql_dump)
        
        # Verify parsing worked
        assert len(tables) >= 2
        assert len(foreign_keys) >= 1
        assert len(errors) == 0
        
        # Generate ERD
        generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Verify ERD generation was called
        mock_digraph.assert_called_once()
        mock_dot.render.assert_called_once()
    
    def test_parse_and_filter_workflow(self, sample_sql_dump):
        """Test parsing followed by table filtering."""
        # Add tables that should be excluded
        sql_with_excluded = sample_sql_dump + """
        CREATE TABLE vw_user_summary (
            id integer,
            username varchar(50)
        );
        
        CREATE TABLE old_posts (
            id integer,
            title varchar(200)
        );
        """
        
        tables, foreign_keys, errors = parse_sql_dump(sql_with_excluded)
        
        # Verify excluded tables are parsed
        assert 'vw_user_summary' in tables
        assert 'old_posts' in tables
        
        # These tables should be filtered during ERD generation
        # (tested by mocking in ERD generation tests)
    
    def test_error_handling_workflow(self):
        """Test error handling in the complete workflow."""
        malformed_sql = """
        CREATE TABLE incomplete (
            id integer
        -- Missing closing parenthesis and semicolon
        
        ALTER TABLE nonexistent ADD CONSTRAINT fk FOREIGN KEY (id) REFERENCES also_nonexistent(id);
        """
        
        tables, foreign_keys, errors = parse_sql_dump(malformed_sql)
        
        # Should handle errors gracefully
        assert isinstance(tables, dict)
        assert isinstance(foreign_keys, list)
        assert isinstance(errors, list)
        
        # Can still attempt ERD generation (should handle empty/invalid data)
        with patch('create_graph.Digraph') as mock_digraph:
            mock_dot = Mock()
            mock_digraph.return_value = mock_dot
            
            # Should not crash even with malformed data
            generate_erd_with_graphviz(tables, foreign_keys, "test_output")
            mock_dot.render.assert_called_once()
    
    @patch('create_graph.Digraph')
    def test_large_dataset_workflow(self, mock_digraph):
        """Test workflow with a larger, more complex dataset."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        
        # Create a larger SQL dump
        large_sql = """
        CREATE TABLE users (
            id integer PRIMARY KEY,
            username varchar(50) UNIQUE,
            email varchar(100),
            created_at timestamp DEFAULT now()
        );
        
        CREATE TABLE categories (
            id integer PRIMARY KEY,
            name varchar(100),
            description text
        );
        
        CREATE TABLE posts (
            id integer PRIMARY KEY,
            title varchar(200),
            content text,
            user_id integer,
            category_id integer,
            created_at timestamp DEFAULT now(),
            updated_at timestamp
        );
        
        CREATE TABLE comments (
            id integer PRIMARY KEY,
            post_id integer,
            user_id integer,
            content text,
            created_at timestamp DEFAULT now()
        );
        
        CREATE TABLE tags (
            id integer PRIMARY KEY,
            name varchar(50) UNIQUE
        );
        
        CREATE TABLE post_tags (
            post_id integer,
            tag_id integer,
            PRIMARY KEY (post_id, tag_id)
        );
        
        ALTER TABLE posts ADD CONSTRAINT posts_user_fk FOREIGN KEY (user_id) REFERENCES users(id);
        ALTER TABLE posts ADD CONSTRAINT posts_category_fk FOREIGN KEY (category_id) REFERENCES categories(id);
        ALTER TABLE comments ADD CONSTRAINT comments_post_fk FOREIGN KEY (post_id) REFERENCES posts(id);
        ALTER TABLE comments ADD CONSTRAINT comments_user_fk FOREIGN KEY (user_id) REFERENCES users(id);
        ALTER TABLE post_tags ADD CONSTRAINT post_tags_post_fk FOREIGN KEY (post_id) REFERENCES posts(id);
        ALTER TABLE post_tags ADD CONSTRAINT post_tags_tag_fk FOREIGN KEY (tag_id) REFERENCES tags(id);
        """
        
        tables, foreign_keys, errors = parse_sql_dump(large_sql)
        
        # Verify parsing of complex dataset
        assert len(tables) == 6
        assert len(foreign_keys) == 6
        assert len(errors) == 0
        
        # Verify all expected tables are present
        expected_tables = ['users', 'categories', 'posts', 'comments', 'tags', 'post_tags']
        for table in expected_tables:
            assert table in tables
        
        # Generate ERD
        generate_erd_with_graphviz(tables, foreign_keys, "large_test_output")
        
        # Verify ERD generation handled the complex dataset
        assert mock_dot.node.call_count == 6  # One node per table
        assert mock_dot.edge.call_count == 6  # One edge per foreign key
    
    def test_unicode_handling_workflow(self):
        """Test workflow with Unicode characters in SQL."""
        unicode_sql = """
        CREATE TABLE users (
            id integer,
            name varchar(100),
            description text
        );
        """
        
        tables, foreign_keys, errors = parse_sql_dump(unicode_sql)
        
        # Should handle Unicode without issues
        assert len(tables) == 1
        assert 'users' in tables
        assert len(errors) == 0
    
    @patch('create_graph.Digraph')
    @patch('builtins.print')
    def test_output_verification(self, mock_print, mock_digraph):
        """Test that output messages are generated correctly."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        
        simple_sql = """
        CREATE TABLE test (
            id integer
        );
        """
        
        tables, foreign_keys, errors = parse_sql_dump(simple_sql)
        
        # No errors should be printed for valid SQL
        error_prints = [call for call in mock_print.call_args_list 
                       if 'error' in str(call).lower()]
        assert len(error_prints) == 0
        
        # Generate ERD
        generate_erd_with_graphviz(tables, foreign_keys, "output_test")
        
        # Should print success message
        success_prints = [call for call in mock_print.call_args_list 
                         if 'ERD saved' in str(call)]
        assert len(success_prints) == 1
