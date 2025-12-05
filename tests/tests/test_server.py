"""Tests for server endpoints and Graphviz settings functionality."""
import sys
import os
import pytest
import json
import tempfile
from unittest.mock import patch, MagicMock, mock_open
from pathlib import Path

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../src'))

from pypgsvg.server import ERDServer


@pytest.fixture
def mock_svg_file(tmp_path):
    """Create a temporary SVG file for testing."""
    svg_file = tmp_path / "test_erd.svg"
    svg_file.write_text("""<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100">
    <rect width="100" height="100" fill="blue"/>
</svg>""")
    return str(svg_file)


@pytest.fixture
def file_server(mock_svg_file):
    """Create ERDServer instance with file source."""
    source_params = {
        'filepath': '/path/to/schema.sql'
    }
    generation_params = {
        'packmode': 'array',
        'rankdir': 'TB',
        'esep': '8',
        'fontname': 'Arial',
        'fontsize': 18,
        'node_fontsize': 14,
        'edge_fontsize': 12,
        'node_style': 'rounded,filled',
        'node_shape': 'rect',
        'node_sep': '0.5',
        'rank_sep': '1.2'
    }
    server = ERDServer(
        svg_file=mock_svg_file,
        source_type='file',
        source_params=source_params,
        generation_params=generation_params
    )
    return server


@pytest.fixture
def database_server(mock_svg_file):
    """Create ERDServer instance with database source."""
    source_params = {
        'host': 'localhost',
        'port': '5432',
        'database': 'testdb',
        'user': 'testuser'
    }
    generation_params = {
        'packmode': 'array',
        'rankdir': 'TB',
        'esep': '8',
        'fontname': 'Arial',
        'fontsize': 18,
        'node_fontsize': 14,
        'edge_fontsize': 12,
        'node_style': 'rounded,filled',
        'node_shape': 'rect',
        'node_sep': '0.5',
        'rank_sep': '1.2'
    }
    server = ERDServer(
        svg_file=mock_svg_file,
        source_type='database',
        source_params=source_params,
        generation_params=generation_params
    )
    # Set cached password to empty string (passwordless connection)
    server.cached_password = ''
    return server


class TestGraphvizSettingsEndpoint:
    """Tests for /api/apply_graphviz_settings endpoint."""

    def test_apply_settings_file_source_success(self, file_server, tmp_path):
        """Test applying Graphviz settings with file source."""
        new_settings = {
            'packmode': 'cluster',
            'rankdir': 'LR',
            'fontsize': 24
        }

        # Mock the reload_from_file method
        with patch.object(file_server, 'reload_from_file') as mock_reload:
            mock_reload.return_value = {
                'success': True,
                'message': 'ERD reloaded successfully',
                'reload': True
            }

            # Create request handler
            handler_class = file_server.create_request_handler()
            handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

            # Mock request data
            data = {'graphviz_settings': new_settings}

            # Call the handler
            with patch.object(handler, 'send_json_response') as mock_response:
                handler.handle_apply_graphviz_settings(data)

                # Verify generation_params were updated
                assert file_server.generation_params['packmode'] == 'cluster'
                assert file_server.generation_params['rankdir'] == 'LR'
                assert file_server.generation_params['fontsize'] == 24

                # Verify reload_from_file was called
                mock_reload.assert_called_once_with('/path/to/schema.sql')

                # Verify response was sent
                mock_response.assert_called_once()
                args = mock_response.call_args[0]
                assert args[0]['success'] is True

    def test_apply_settings_database_source_success(self, database_server):
        """Test applying Graphviz settings with database source."""
        new_settings = {
            'packmode': 'graph',
            'node_shape': 'ellipse',
            'esep': '10'
        }

        # Mock the reload_from_database method
        with patch.object(database_server, 'reload_from_database') as mock_reload:
            mock_reload.return_value = {
                'success': True,
                'message': 'ERD reloaded successfully',
                'reload': True,
                'new_file': 'testdb_erd.svg'
            }

            # Create request handler
            handler_class = database_server.create_request_handler()
            handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

            # Mock request data
            data = {'graphviz_settings': new_settings}

            # Call the handler
            with patch.object(handler, 'send_json_response') as mock_response:
                handler.handle_apply_graphviz_settings(data)

                # Verify generation_params were updated
                assert database_server.generation_params['packmode'] == 'graph'
                assert database_server.generation_params['node_shape'] == 'ellipse'
                assert database_server.generation_params['esep'] == '10'

                # Verify reload_from_database was called with empty password
                mock_reload.assert_called_once_with(
                    'localhost', '5432', 'testdb', 'testuser', ''
                )

                # Verify response was sent
                mock_response.assert_called_once()
                args = mock_response.call_args[0]
                assert args[0]['success'] is True

    def test_apply_settings_missing_parameters(self, file_server):
        """Test applying settings with missing graphviz_settings."""
        handler_class = file_server.create_request_handler()
        handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

        data = {}  # Missing graphviz_settings

        with patch.object(handler, 'send_json_response') as mock_response:
            handler.handle_apply_graphviz_settings(data)

            # Verify error response
            mock_response.assert_called_once()
            args = mock_response.call_args[0]
            assert args[0]['success'] is False
            assert 'Missing graphviz_settings' in args[0]['message']
            assert args[1] == 400  # Bad request status code

    def test_apply_settings_preserves_other_params(self, file_server):
        """Test that applying settings preserves unchanged parameters."""
        original_fontname = file_server.generation_params['fontname']
        original_fontsize = file_server.generation_params['fontsize']

        new_settings = {
            'packmode': 'cluster'  # Only change one setting
        }

        with patch.object(file_server, 'reload_from_file') as mock_reload:
            mock_reload.return_value = {'success': True, 'reload': True}

            handler_class = file_server.create_request_handler()
            handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

            data = {'graphviz_settings': new_settings}

            with patch.object(handler, 'send_json_response'):
                handler.handle_apply_graphviz_settings(data)

                # Verify new setting was applied
                assert file_server.generation_params['packmode'] == 'cluster'

                # Verify other settings were preserved
                assert file_server.generation_params['fontname'] == original_fontname
                assert file_server.generation_params['fontsize'] == original_fontsize


class TestGenerateSelectedSVGEndpoint:
    """Tests for /api/generate_selected_svg endpoint."""

    def test_generate_selected_svg_file_source(self, file_server, tmp_path):
        """Test generating selected SVG from file source."""
        # Mock file content
        sql_dump = "CREATE TABLE users (id SERIAL PRIMARY KEY);"

        with patch('builtins.open', mock_open(read_data=sql_dump)), \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.server.generate_erd_with_graphviz') as mock_gen, \
             patch('os.path.exists', return_value=True):

            # Mock parse_sql_dump return value
            mock_parse.return_value = (
                {'users': {'columns': []}},  # tables
                [],  # foreign_keys
                {},  # triggers
                [],  # errors
                {}   # views
            )
            mock_extract.return_value = {}

            # Mock generated SVG
            generated_svg = '<svg>Selected ERD</svg>'
            with patch('builtins.open', mock_open(read_data=generated_svg)):
                handler_class = file_server.create_request_handler()
                handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

                data = {
                    'table_ids': ['users'],
                    'edge_ids': [],
                    'graphviz_settings': {'packmode': 'array'}
                }

                # Mock response methods
                handler.send_response = MagicMock()
                handler.send_header = MagicMock()
                handler.end_headers = MagicMock()
                handler.wfile = MagicMock()

                handler.handle_generate_selected_svg(data)

                # Verify generate_erd_with_graphviz was called with show_standalone=False
                assert mock_gen.called
                call_kwargs = mock_gen.call_args[1]
                assert call_kwargs['show_standalone'] is False

    def test_generate_selected_svg_no_tables_selected(self, file_server):
        """Test generating SVG with no tables selected."""
        handler_class = file_server.create_request_handler()
        handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

        data = {
            'table_ids': [],  # No tables selected
            'edge_ids': [],
            'graphviz_settings': {}
        }

        with patch.object(handler, 'send_json_response') as mock_response:
            handler.handle_generate_selected_svg(data)

            # Verify error response
            mock_response.assert_called_once()
            args = mock_response.call_args[0]
            assert args[0]['success'] is False
            assert 'No tables selected' in args[0]['message']
            assert args[1] == 400

    def test_generate_selected_svg_filters_tables(self, file_server):
        """Test that only selected tables are included."""
        sql_dump = """
        CREATE TABLE users (id SERIAL PRIMARY KEY);
        CREATE TABLE posts (id SERIAL PRIMARY KEY);
        CREATE TABLE comments (id SERIAL PRIMARY KEY);
        """

        with patch('builtins.open', mock_open(read_data=sql_dump)), \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.server.generate_erd_with_graphviz') as mock_gen, \
             patch('os.path.exists', return_value=True):

            # Mock parse_sql_dump with 3 tables
            mock_parse.return_value = (
                {
                    'users': {'columns': []},
                    'posts': {'columns': []},
                    'comments': {'columns': []}
                },
                [],
                {},
                [],
                {}
            )
            mock_extract.return_value = {}

            with patch('builtins.open', mock_open(read_data='<svg></svg>')):
                handler_class = file_server.create_request_handler()
                handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

                # Select only 2 tables
                data = {
                    'table_ids': ['users', 'posts'],
                    'edge_ids': [],
                    'graphviz_settings': {}
                }

                handler.send_response = MagicMock()
                handler.send_header = MagicMock()
                handler.end_headers = MagicMock()
                handler.wfile = MagicMock()

                handler.handle_generate_selected_svg(data)

                # Verify only selected tables were passed to generate_erd_with_graphviz
                assert mock_gen.called
                filtered_tables = mock_gen.call_args[0][0]
                assert 'users' in filtered_tables
                assert 'posts' in filtered_tables
                assert 'comments' not in filtered_tables


class TestPasswordlessConnections:
    """Tests for passwordless database connections."""

    def test_fetch_schema_with_empty_password(self, database_server):
        """Test fetching schema with empty password."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema dump')

            result = database_server.fetch_schema_from_database(
                'localhost', '5432', 'testdb', 'testuser', ''
            )

            assert result == '-- Schema dump'

            # Verify PGPASSWORD was not set in environment
            call_env = mock_run.call_args[1]['env']
            assert 'PGPASSWORD' not in call_env or call_env.get('PGPASSWORD') == ''

    def test_fetch_schema_with_none_password(self, database_server):
        """Test fetching schema with None password defaults to empty."""
        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout='-- Schema dump')

            result = database_server.fetch_schema_from_database(
                'localhost', '5432', 'testdb', 'testuser', None
            )

            assert result == '-- Schema dump'

            # Verify password was converted to empty string
            assert database_server.cached_password == ''

    def test_apply_settings_with_passwordless_db(self, database_server):
        """Test applying settings with passwordless database connection."""
        database_server.cached_password = ''  # Explicitly set to empty

        new_settings = {'packmode': 'cluster'}

        with patch.object(database_server, 'reload_from_database') as mock_reload:
            mock_reload.return_value = {'success': True, 'reload': True}

            handler_class = database_server.create_request_handler()
            handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

            data = {'graphviz_settings': new_settings}

            with patch.object(handler, 'send_json_response') as mock_response:
                handler.handle_apply_graphviz_settings(data)

                # Verify reload was called with empty password
                mock_reload.assert_called_once()
                call_args = mock_reload.call_args[0]
                assert call_args[4] == ''  # password parameter

                # Verify success response
                args = mock_response.call_args[0]
                assert args[0]['success'] is True


class TestSettingsPersistence:
    """Tests for Graphviz settings persistence across reloads."""

    def test_settings_persist_in_generation_params(self, file_server):
        """Test that updated settings persist in generation_params."""
        original_settings = file_server.generation_params.copy()

        new_settings = {
            'packmode': 'cluster',
            'rankdir': 'LR',
            'fontsize': 24,
            'node_shape': 'ellipse'
        }

        # Update settings
        file_server.generation_params.update(new_settings)

        # Verify all new settings are present
        for key, value in new_settings.items():
            assert file_server.generation_params[key] == value

        # Verify other settings are still present
        for key in original_settings:
            if key not in new_settings:
                assert key in file_server.generation_params

    def test_reload_uses_updated_settings(self, file_server, tmp_path):
        """Test that reload methods use updated generation_params."""
        # Update settings
        file_server.generation_params.update({
            'packmode': 'cluster',
            'rankdir': 'LR'
        })

        with patch('builtins.open', mock_open(read_data='CREATE TABLE test (id INT);')), \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.server.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = ({'test': {}}, [], {}, [], {})
            mock_extract.return_value = {}

            # Mock the SVG file creation
            with patch('os.path.splitext', return_value=(str(tmp_path / 'test'), '.svg')):
                file_server.reload_from_file('/path/to/schema.sql')

                # Verify generate_erd_with_graphviz was called with updated settings
                assert mock_gen.called
                call_kwargs = mock_gen.call_args[1]
                assert call_kwargs['packmode'] == 'cluster'
                assert call_kwargs['rankdir'] == 'LR'


class TestIncludeTablesParameter:
    """Tests for --include tables filtering functionality."""

    def test_generate_focused_erd_with_include_parameter(self, file_server):
        """Test that generate_focused_erd uses include_tables parameter correctly."""
        sql_dump = """
        CREATE TABLE users (id SERIAL PRIMARY KEY);
        CREATE TABLE posts (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id));
        CREATE TABLE comments (id SERIAL PRIMARY KEY, post_id INT REFERENCES posts(id));
        CREATE TABLE tags (id SERIAL PRIMARY KEY);
        """

        with patch('builtins.open', mock_open(read_data=sql_dump)), \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.server.generate_erd_with_graphviz') as mock_gen, \
             patch('os.path.exists', return_value=True):

            # Mock parse_sql_dump with 4 tables
            mock_parse.return_value = (
                {
                    'users': {'columns': []},
                    'posts': {'columns': []},
                    'comments': {'columns': []},
                    'tags': {'columns': []}
                },
                [
                    ('posts', 'user_id', 'users', 'id', 1, {}, None),
                    ('comments', 'post_id', 'posts', 'id', 2, {}, None),
                ],
                {},
                [],
                {}
            )
            mock_extract.return_value = {}

            handler_class = file_server.create_request_handler()
            handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

            # Select only 2 tables
            data = {
                'table_ids': ['users', 'posts'],
                'edge_ids': [],
                'graphviz_settings': {}
            }

            with patch.object(handler, 'send_json_response') as mock_response:
                handler.handle_generate_focused_erd(data)

                # Verify generate_erd_with_graphviz was called with include_tables
                assert mock_gen.called
                call_kwargs = mock_gen.call_args[1]

                # CRITICAL: include_tables should contain only selected tables
                assert call_kwargs['include_tables'] == ['users', 'posts']

                # Verify all tables were passed (not pre-filtered)
                all_tables = mock_gen.call_args[0][0]
                assert 'users' in all_tables
                assert 'posts' in all_tables
                assert 'comments' in all_tables
                assert 'tags' in all_tables

                # Verify show_standalone is False for focused ERD
                assert call_kwargs['show_standalone'] is False

    def test_generate_standalone_svg_with_include_parameter(self, file_server):
        """Test that generate_selected_svg uses include_tables parameter correctly."""
        sql_dump = """
        CREATE TABLE users (id SERIAL PRIMARY KEY);
        CREATE TABLE posts (id SERIAL PRIMARY KEY, user_id INT REFERENCES users(id));
        CREATE TABLE comments (id SERIAL PRIMARY KEY);
        """

        with patch('builtins.open', mock_open(read_data=sql_dump)), \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.server.generate_erd_with_graphviz') as mock_gen, \
             patch('os.path.exists', return_value=True):

            # Mock parse_sql_dump with 3 tables
            mock_parse.return_value = (
                {
                    'users': {'columns': []},
                    'posts': {'columns': []},
                    'comments': {'columns': []}
                },
                [('posts', 'user_id', 'users', 'id', 1, {}, None)],
                {},
                [],
                {}
            )
            mock_extract.return_value = {}

            # Mock generated SVG
            generated_svg = '<svg>Selected ERD</svg>'
            with patch('builtins.open', mock_open(read_data=generated_svg)):
                handler_class = file_server.create_request_handler()
                handler = handler_class(MagicMock(), ('127.0.0.1', 12345), MagicMock())

                # Select only 2 tables
                data = {
                    'table_ids': ['users', 'posts'],
                    'edge_ids': [],
                    'graphviz_settings': {}
                }

                handler.send_response = MagicMock()
                handler.send_header = MagicMock()
                handler.end_headers = MagicMock()
                handler.wfile = MagicMock()

                handler.handle_generate_selected_svg(data)

                # Verify generate_erd_with_graphviz was called with include_tables
                assert mock_gen.called
                call_kwargs = mock_gen.call_args[1]

                # CRITICAL: include_tables should contain only selected tables
                assert call_kwargs['include_tables'] == ['users', 'posts']

                # Verify all tables were passed (not pre-filtered)
                all_tables = mock_gen.call_args[0][0]
                assert 'users' in all_tables
                assert 'posts' in all_tables
                assert 'comments' in all_tables

                # Verify show_standalone is True for standalone SVG
                assert call_kwargs['show_standalone'] is True

    def test_include_tables_filters_correctly(self, file_server):
        """Test that ERD generator properly filters using include_tables."""
        from pypgsvg.erd_generator import generate_erd_with_graphviz
        import tempfile

        tables = {
            'users': {'columns': [{'name': 'id', 'type': 'INT'}]},
            'posts': {'columns': [{'name': 'id', 'type': 'INT'}]},
            'comments': {'columns': [{'name': 'id', 'type': 'INT'}]},
        }
        foreign_keys = [
            ('posts', 'user_id', 'users', 'id', 1, {}, None),
            ('comments', 'post_id', 'posts', 'id', 2, {}, None),
        ]

        # Create temporary output file
        with tempfile.NamedTemporaryFile(mode='w', suffix='_test', delete=False) as tmp_file:
            output_file = tmp_file.name.replace('.svg', '')

        try:
            # Generate ERD with include_tables parameter
            generate_erd_with_graphviz(
                tables,
                foreign_keys,
                output_file,
                include_tables=['users', 'posts'],
                show_standalone=False
            )

            # Read generated SVG
            svg_file = output_file + '.svg'
            if os.path.exists(svg_file):
                with open(svg_file, 'r') as f:
                    svg_content = f.read()

                # Verify only included tables are in the SVG
                assert 'users' in svg_content
                assert 'posts' in svg_content
                # Comments table should NOT be in the SVG
                assert 'comments' not in svg_content or svg_content.count('comments') == 0

                # Clean up
                os.remove(svg_file)
        finally:
            # Clean up temp file
            if os.path.exists(output_file):
                os.remove(output_file)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
