"""
Unit tests for ERD generation functionality in create_graph.py.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from create_graph import generate_erd_with_graphviz


@pytest.mark.unit
class TestGenerateErdWithGraphviz:
    """Test ERD generation with Graphviz."""
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    def test_generate_erd_basic(self, mock_choice, mock_digraph, sample_tables, sample_foreign_keys):
        """Test basic ERD generation."""
        # Setup mocks
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"  # Return consistent color
        
        # Call function
        generate_erd_with_graphviz(sample_tables, sample_foreign_keys, "test_output")
        
        # Verify Digraph was created
        mock_digraph.assert_called_once_with(comment='Database ERD', format='svg')
        
        # Verify attributes were set
        mock_dot.attr.assert_called_once()
        
        # Verify nodes were created (one for each table)
        assert mock_dot.node.call_count == len(sample_tables)
        
        # Verify edges were created for foreign keys
        expected_edges = len([fk for fk in sample_foreign_keys 
                             if fk[0] in sample_tables and fk[2] in sample_tables])
        assert mock_dot.edge.call_count == expected_edges
        
        # Verify render was called
        mock_dot.render.assert_called_once_with("test_output", view=True)
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    def test_generate_erd_with_excluded_tables(self, mock_choice, mock_digraph):
        """Test ERD generation with excluded tables."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"
        
        # Create test data with tables that should be excluded
        tables = {
            'users': {
                'lines': 'users\nid integer',
                'columns': [{'name': 'id', 'type': 'integer', 'line': 'id integer'}]
            },
            'vw_users': {  # Should be excluded
                'lines': 'vw_users\nid integer',
                'columns': [{'name': 'id', 'type': 'integer', 'line': 'id integer'}]
            }
        }
        foreign_keys = []
        
        generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Should only create node for 'users', not 'vw_users'
        assert mock_dot.node.call_count == 1
        
        # Verify the call was for 'users' table
        call_args = mock_dot.node.call_args_list[0]
        assert call_args[0][0] == 'users'  # First argument should be table name
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    def test_generate_erd_with_foreign_keys(self, mock_choice, mock_digraph):
        """Test ERD generation with foreign key relationships."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"
        
        tables = {
            'users': {
                'lines': 'users\nid integer',
                'columns': [{'name': 'id', 'type': 'integer', 'line': 'id integer'}]
            },
            'posts': {
                'lines': 'posts\nid integer\nuser_id integer',
                'columns': [
                    {'name': 'id', 'type': 'integer', 'line': 'id integer'},
                    {'name': 'user_id', 'type': 'integer', 'line': 'user_id integer'}
                ]
            }
        }
        foreign_keys = [
            ('posts', 'user_id', 'users', 'id', 'ALTER TABLE posts ADD CONSTRAINT fk FOREIGN KEY (user_id) REFERENCES users(id);')
        ]
        
        generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Verify edge was created for the foreign key
        assert mock_dot.edge.call_count == 1
        
        # Verify edge parameters
        edge_call = mock_dot.edge.call_args
        assert 'dir' in edge_call[1]
        assert 'weight' in edge_call[1]
        assert 'head_name' in edge_call[1]
        assert 'tail_name' in edge_call[1]
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    @patch('create_graph.get_contrasting_text_color')
    def test_generate_erd_color_assignment(self, mock_contrast, mock_choice, mock_digraph):
        """Test that colors are assigned correctly."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"
        mock_contrast.return_value = "white"
        
        tables = {
            'users': {
                'lines': 'users\nid integer',
                'columns': [{'name': 'id', 'type': 'integer', 'line': 'id integer'}]
            }
        }
        foreign_keys = []
        
        generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Verify contrast function was called
        mock_contrast.assert_called_with("#F94144")
        
        # Verify node was created with correct colors
        node_call = mock_dot.node.call_args
        assert 'fillcolor' in node_call[1]
        assert 'fontcolor' in node_call[1]
        assert node_call[1]['fillcolor'] == "#F94144"
        assert node_call[1]['fontcolor'] == "white"
    
    @patch('create_graph.Digraph')
    def test_generate_erd_empty_tables(self, mock_digraph):
        """Test ERD generation with empty tables dict."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        
        generate_erd_with_graphviz({}, [], "test_output")
        
        # Should create Digraph and set attributes but no nodes or edges
        mock_digraph.assert_called_once()
        mock_dot.attr.assert_called_once()
        assert mock_dot.node.call_count == 0
        assert mock_dot.edge.call_count == 0
        mock_dot.render.assert_called_once_with("test_output", view=True)
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    def test_generate_erd_foreign_key_filtering(self, mock_choice, mock_digraph):
        """Test that foreign keys are filtered correctly."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"
        
        tables = {
            'users': {
                'lines': 'users\nid integer',
                'columns': [{'name': 'id', 'type': 'integer', 'line': 'id integer'}]
            }
        }
        
        # Foreign key references table that doesn't exist in filtered tables
        foreign_keys = [
            ('posts', 'user_id', 'users', 'id', 'FK constraint'),
            ('users', 'role_id', 'roles', 'id', 'FK constraint')  # 'roles' table not in tables
        ]
        
        generate_erd_with_graphviz(tables, foreign_keys, "test_output")
        
        # Should not create any edges since foreign keys don't have both tables
        assert mock_dot.edge.call_count == 0
    
    @patch('create_graph.Digraph')
    @patch('create_graph.choice')
    @patch('builtins.print')
    def test_generate_erd_print_output(self, mock_print, mock_choice, mock_digraph):
        """Test that success message is printed."""
        mock_dot = Mock()
        mock_digraph.return_value = mock_dot
        mock_choice.return_value = "#F94144"
        
        generate_erd_with_graphviz({}, [], "test_output")
        
        # Verify success message was printed
        mock_print.assert_called_with("ERD saved to test_output.svg")
