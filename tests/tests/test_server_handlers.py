"""Tests for server.py HTTP handlers and error paths."""
import pytest
from unittest.mock import patch, MagicMock
from pypgsvg.server import ERDServer


@pytest.fixture
def mock_svg_file(tmp_path):
    """Create a temporary SVG file for testing."""
    svg_file = tmp_path / "test_erd.svg"
    svg_file.write_text('<svg></svg>')
    return str(svg_file)


@pytest.fixture
def file_server(mock_svg_file):
    """Create ERDServer instance with file source."""
    source_params = {'filepath': '/path/to/schema.sql'}
    generation_params = {'packmode': 'array', 'rankdir': 'TB'}
    return ERDServer(mock_svg_file, 'file', source_params, generation_params)


@pytest.fixture
def database_server(mock_svg_file):
    """Create ERDServer instance with database source."""
    source_params = {
        'host': 'localhost',
        'port': '5432',
        'database': 'testdb',
        'user': 'testuser'
    }
    generation_params = {'packmode': 'array', 'rankdir': 'TB'}
    server = ERDServer(mock_svg_file, 'database', source_params, generation_params)
    server.cached_password = ''
    return server


class TestReloadMethods:
    """Tests for reload_from_database and reload_from_file error handling."""

    def test_reload_from_database_exception(self, database_server):
        """Test reload_from_database with exception."""
        with patch.object(database_server.erd_service, 'generate_from_database') as mock_gen:
            mock_gen.side_effect = Exception("Generation failed")

            result = database_server.reload_from_database(
                'localhost', '5432', 'testdb', 'testuser', 'password'
            )

            assert result['success'] is False
            assert 'Generation failed' in result['message']

    def test_reload_from_file_exception(self, file_server):
        """Test reload_from_file with exception."""
        with patch.object(file_server.erd_service, 'generate_from_file') as mock_gen:
            mock_gen.side_effect = Exception("File generation failed")

            result = file_server.reload_from_file('/path/to/schema.sql')

            assert result['success'] is False
            assert 'File generation failed' in result['message']


class TestRequestHandler:
    """Tests for HTTP request handler methods."""

    def test_do_options(self, file_server):
        """Test OPTIONS request handling (CORS preflight)."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)

        handler.send_response = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_OPTIONS()

        handler.send_response.assert_called_once_with(200)
        handler.end_headers.assert_called_once()

    def test_do_post_invalid_json(self, file_server):
        """Test POST with invalid JSON body."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)

        handler.path = '/api/test'
        handler.headers = {'Content-Length': '10'}
        handler.rfile = MagicMock()
        handler.rfile.read = MagicMock(return_value=b'invalid json')
        handler.send_error = MagicMock()

        handler.do_POST()

        handler.send_error.assert_called_once_with(400, "Invalid JSON")

    def test_do_post_unknown_endpoint(self, file_server):
        """Test POST to unknown endpoint."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)

        handler.path = '/api/unknown'
        handler.headers = {'Content-Length': '2'}
        handler.rfile = MagicMock()
        handler.rfile.read = MagicMock(return_value=b'{}')
        handler.send_error = MagicMock()

        handler.do_POST()

        handler.send_error.assert_called_once_with(404, "Endpoint not found")

    def test_handle_test_connection_not_database_source(self, file_server):
        """Test test-db-connection with non-database source."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'host': 'localhost', 'port': '5432', 'database': 'test', 'user': 'user'}
        handler.handle_test_connection(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'only available for database sources' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_test_connection_missing_params(self, database_server):
        """Test test-db-connection with missing parameters."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'host': 'localhost'}  # Missing port, database, user
        handler.handle_test_connection(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Missing required parameters' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_reload_erd_missing_params_file(self, file_server):
        """Test reload-erd with missing filepath for file source."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {}  # Missing filepath
        handler.handle_reload_erd(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Missing required parameter: filepath' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_reload_erd_missing_params_database(self, database_server):
        """Test reload-erd with missing parameters for database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'host': 'localhost'}  # Missing port, database, user
        handler.handle_reload_erd(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Missing required parameters' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_graphviz_settings_missing_params_file(self, file_server):
        """Test apply-graphviz-settings with missing filepath for file source."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        # Temporarily clear filepath to trigger error
        file_server.source_params = {}

        data = {'graphviz_settings': {'packmode': 'cluster'}}
        handler.handle_apply_graphviz_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Missing filepath' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_graphviz_settings_missing_params_database(self, database_server):
        """Test apply-graphviz-settings with missing database params."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        # Clear database params to trigger error
        database_server.source_params = {}

        data = {'graphviz_settings': {'packmode': 'cluster'}}
        handler.handle_apply_graphviz_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Missing database connection parameters' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_graphviz_settings_unknown_source(self, file_server):
        """Test apply-graphviz-settings with unknown source type."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        # Set unknown source type
        file_server.source_type = 'unknown'

        data = {'graphviz_settings': {'packmode': 'cluster'}}
        handler.handle_apply_graphviz_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Unknown source type' in args[0][0]['message']


class TestFocusedHandlers:
    """Tests for focused ERD generation handlers."""

    def test_handle_apply_focused_settings_no_tables(self, file_server):
        """Test apply-focused-settings with no tables provided."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': [], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'No tables provided' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_focused_settings_missing_db_params(self, database_server):
        """Test apply-focused-settings with missing database parameters."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        # Clear params
        database_server.source_params = {}

        data = {'table_ids': ['users'], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Database connection parameters not available' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_focused_settings_file_not_found(self, file_server):
        """Test apply-focused-settings with non-existent file."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_params = {'filepath': '/nonexistent/file.sql'}

        with patch('os.path.exists', return_value=False):
            data = {'table_ids': ['users'], 'graphviz_settings': {}}
            handler.handle_apply_focused_settings(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Source file not available' in args[0][0]['message']
            assert args[0][1] == 400

    def test_handle_apply_focused_settings_unknown_source(self, file_server):
        """Test apply-focused-settings with unknown source type."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_type = 'unknown'

        data = {'table_ids': ['users'], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Unknown source type' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_apply_focused_settings_exception(self, file_server, tmp_path):
        """Test apply-focused-settings with exception during generation."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        file_server.source_params = {'filepath': str(sql_file)}

        with patch.object(file_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_gen.side_effect = Exception("Generation error")

            data = {'table_ids': ['users'], 'graphviz_settings': {}}
            handler.handle_apply_focused_settings(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Generation error' in args[0][0]['message']
            assert args[0][1] == 500


class TestGenerateSelectedSvgHandler:
    """Tests for generate_selected_svg handler."""

    def test_handle_generate_selected_svg_no_tables(self, file_server):
        """Test generate-selected-svg with no tables."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': [], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'No tables selected' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_generate_selected_svg_missing_db_params(self, database_server):
        """Test generate-selected-svg with missing database parameters."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        database_server.source_params = {}

        data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Database connection parameters not available' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_generate_selected_svg_file_not_found(self, file_server):
        """Test generate-selected-svg with non-existent file."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_params = {'filepath': '/nonexistent/file.sql'}

        with patch('os.path.exists', return_value=False):
            data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
            handler.handle_generate_selected_svg(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Source file not available' in args[0][0]['message']
            assert args[0][1] == 400

    def test_handle_generate_selected_svg_unknown_source(self, file_server):
        """Test generate-selected-svg with unknown source type."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_type = 'unknown'

        data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Unknown source type' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_generate_selected_svg_exception(self, file_server, tmp_path):
        """Test generate-selected-svg with exception during generation."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        file_server.source_params = {'filepath': str(sql_file)}

        with patch.object(file_server.erd_service, 'generate_selected_svg') as mock_gen:
            mock_gen.side_effect = Exception("SVG generation error")

            data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
            handler.handle_generate_selected_svg(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'SVG generation error' in args[0][0]['message']
            assert args[0][1] == 500


class TestGenerateFocusedErdHandler:
    """Tests for generate_focused_erd handler."""

    def test_handle_generate_focused_erd_no_tables(self, file_server):
        """Test generate-focused-erd with no tables."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': [], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_focused_erd(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'No tables selected' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_generate_focused_erd_exception(self, file_server, tmp_path):
        """Test generate-focused-erd with exception during generation."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        file_server.source_params = {'filepath': str(sql_file)}

        with patch.object(file_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_gen.side_effect = Exception("Focused ERD error")

            data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
            handler.handle_generate_focused_erd(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Focused ERD error' in args[0][0]['message']
            assert args[0][1] == 500


class TestOptimizeLayoutHandler:
    """Tests for optimize_layout handler."""

    def test_handle_optimize_layout_missing_settings(self, file_server):
        """Test optimize-layout with missing current_settings."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {}  # Missing current_settings
        handler.handle_optimize_layout(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Current settings not provided' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_optimize_layout_success_file(self, file_server, tmp_path):
        """Test optimize-layout with file source."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        file_server.source_params = {'filepath': str(sql_file)}

        with patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.optimize_layout') as mock_optimize:
            mock_parse.return_value = ({'users': {}}, [], {}, [], {}, {}, {})
            mock_optimize.return_value = ({'packmode': 'cluster'}, 'Optimized for small schema')

            data = {'current_settings': {'packmode': 'array'}}
            handler.handle_optimize_layout(data)

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True
            assert 'optimized_settings' in args
            assert 'explanation' in args

    def test_handle_optimize_layout_missing_db_params(self, database_server):
        """Test optimize-layout with missing database parameters."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        database_server.source_params = {}

        data = {'current_settings': {'packmode': 'array'}}
        handler.handle_optimize_layout(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Database connection parameters not available' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_optimize_layout_file_not_found(self, file_server):
        """Test optimize-layout with non-existent file."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_params = {'filepath': '/nonexistent/file.sql'}

        with patch('os.path.exists', return_value=False):
            data = {'current_settings': {'packmode': 'array'}}
            handler.handle_optimize_layout(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Source file not available' in args[0][0]['message']
            assert args[0][1] == 400

    def test_handle_optimize_layout_unknown_source(self, file_server):
        """Test optimize-layout with unknown source type."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        file_server.source_type = 'unknown'

        data = {'current_settings': {'packmode': 'array'}}
        handler.handle_optimize_layout(data)

        args = handler.send_json_response.call_args
        assert args[0][0]['success'] is False
        assert 'Unknown source type' in args[0][0]['message']
        assert args[0][1] == 400

    def test_handle_optimize_layout_exception(self, file_server, tmp_path):
        """Test optimize-layout with exception during optimization."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        sql_file = tmp_path / "test.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        file_server.source_params = {'filepath': str(sql_file)}

        with patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.optimize_layout') as mock_optimize:
            mock_parse.return_value = ({'users': {}}, [], {}, [], {}, {}, {})
            mock_optimize.side_effect = Exception("Optimization failed")

            data = {'current_settings': {'packmode': 'array'}}
            handler.handle_optimize_layout(data)

            args = handler.send_json_response.call_args
            assert args[0][0]['success'] is False
            assert 'Optimization failed' in args[0][0]['message']
            assert args[0][1] == 500


class TestShutdownHandler:
    """Tests for shutdown handler."""

    def test_handle_shutdown(self, file_server):
        """Test server shutdown handler."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch('threading.Thread'):
            handler.handle_shutdown()

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True
            assert 'shutting down' in args['message']


class TestDatabaseSourceHandlers:
    """Tests for handlers with database source."""

    def test_handle_list_databases_success(self, database_server):
        """Test list-databases handler with database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server.database_service, 'list_databases') as mock_list:
            mock_list.return_value = [
                {'name': 'db1', 'table_count': 5},
                {'name': 'db2', 'table_count': 10}
            ]

            data = {'host': 'localhost', 'port': '5432', 'user': 'testuser', 'password': 'pass'}
            handler.handle_list_databases(data)

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True
            assert len(args['databases']) == 2

    def test_handle_apply_focused_settings_database_success(self, database_server, tmp_path):
        """Test apply-focused-settings with database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch.object(database_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            mock_views.return_value = {}
            mock_gen.return_value = str(tmp_path / "focused_erd.svg")

            data = {'table_ids': ['users'], 'graphviz_settings': {}}
            handler.handle_apply_focused_settings(data)

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True

    def test_handle_generate_selected_svg_database_success(self, database_server, tmp_path):
        """Test generate-selected-svg with database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()
        handler.wfile = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch.object(database_server.erd_service, 'generate_selected_svg') as mock_gen:
            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            mock_views.return_value = {}
            mock_gen.return_value = '<svg>Test</svg>'

            data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
            handler.handle_generate_selected_svg(data)

            handler.send_response.assert_called_with(200)

    def test_handle_generate_focused_erd_database_success(self, database_server, tmp_path):
        """Test generate-focused-erd with database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch.object(database_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            mock_views.return_value = {}
            mock_gen.return_value = str(tmp_path / "focused_erd.svg")

            data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
            handler.handle_generate_focused_erd(data)

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True

    def test_handle_optimize_layout_database_success(self, database_server):
        """Test optimize-layout with database source."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.optimize_layout') as mock_optimize:
            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            mock_views.return_value = {}
            mock_parse.return_value = ({'users': {}}, [], {}, [], {}, {}, {})
            mock_optimize.return_value = ({'packmode': 'cluster'}, 'Optimized')

            data = {'current_settings': {'packmode': 'array'}}
            handler.handle_optimize_layout(data)

            args = handler.send_json_response.call_args[0][0]
            assert args['success'] is True


class TestViewColumnEnhancement:
    """Tests for view column enhancement in handlers."""

    def test_handler_with_view_columns_in_views(self, database_server, tmp_path):
        """Test handler with view columns that match views."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch.object(database_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_fetch.return_value = "CREATE VIEW user_view AS SELECT * FROM users;"
            mock_views.return_value = {'user_view': [{'name': 'id', 'type': 'integer'}]}
            mock_gen.return_value = str(tmp_path / "focused_erd.svg")

            data = {'table_ids': ['user_view'], 'graphviz_settings': {}}
            handler.handle_apply_focused_settings(data)

            # Check that view columns were passed
            assert mock_gen.called

    def test_handler_with_view_columns_in_tables(self, database_server, tmp_path):
        """Test handler with view columns that match tables."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_views, \
             patch.object(database_server.erd_service, 'generate_focused_erd') as mock_gen:
            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            # View column name matches table name
            mock_views.return_value = {'users': [{'name': 'id', 'type': 'integer'}]}
            mock_gen.return_value = str(tmp_path / "focused_erd.svg")

            data = {'table_ids': ['users'], 'graphviz_settings': {}}
            handler.handle_apply_focused_settings(data)

            assert mock_gen.called


class TestServerStartup:
    """Tests for server startup and error handling."""

    def test_server_start_port_already_in_use(self, file_server):
        """Test server startup when port is already in use."""
        with patch('socketserver.TCPServer') as mock_tcp:
            # First 9 attempts fail, 10th succeeds
            mock_tcp.side_effect = [OSError("Port in use")] * 9 + [MagicMock()]

            with patch('threading.Timer'), \
                 patch.object(file_server, 'server', MagicMock()):
                # This should increment port and eventually succeed
                file_server.start(open_browser=False)

                # Verify port was incremented
                assert file_server.port == 8765 + 9

    def test_server_start_all_ports_in_use(self, file_server):
        """Test server startup when all ports are in use."""
        with patch('socketserver.TCPServer') as mock_tcp:
            # All attempts fail
            mock_tcp.side_effect = OSError("Port in use")

            with pytest.raises(Exception) as exc_info:
                file_server.start(open_browser=False)

            assert "Could not bind to any port" in str(exc_info.value)

    def test_server_start_with_browser(self, file_server):
        """Test server startup with browser opening."""
        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        with patch('socketserver.TCPServer', return_value=mock_server), \
             patch('threading.Timer') as mock_timer, \
             patch('webbrowser.open'):
            try:
                file_server.start(open_browser=True)
            except KeyboardInterrupt:
                pass

            # Verify Timer was created for browser opening
            assert mock_timer.called


class TestDelegationMethods:
    """Tests for direct delegation methods."""

    def test_fetch_view_columns(self, database_server):
        """Test fetch_view_columns delegation."""
        with patch.object(database_server.database_service, 'fetch_view_columns') as mock_fetch:
            mock_fetch.return_value = {'view1': [{'name': 'col1', 'type': 'text'}]}

            result = database_server.fetch_view_columns('localhost', '5432', 'testdb', 'user', 'pass')

            assert result == {'view1': [{'name': 'col1', 'type': 'text'}]}
            mock_fetch.assert_called_once_with('localhost', '5432', 'testdb', 'user', 'pass')

    def test_test_database_connection(self, database_server):
        """Test test_database_connection delegation."""
        with patch.object(database_server.database_service, 'test_connection') as mock_test:
            mock_test.return_value = {'success': True, 'message': 'Connected'}

            result = database_server.test_database_connection('localhost', '5432', 'testdb', 'user', 'pass')

            assert result == {'success': True, 'message': 'Connected'}
            mock_test.assert_called_once_with('localhost', '5432', 'testdb', 'user', 'pass')


class TestReloadFromDatabaseSuccess:
    """Tests for reload_from_database success path."""

    def test_reload_from_database_updates_svg_file(self, database_server):
        """Test that reload_from_database updates svg_file and source_params."""
        original_svg = database_server.svg_file

        with patch.object(database_server.erd_service, 'generate_from_database') as mock_gen:
            mock_gen.return_value = ('/path/to/new_erd.svg', True)

            result = database_server.reload_from_database('localhost', '5432', 'newdb', 'user', 'pass')

            assert result['success'] is True
            assert database_server.svg_file == '/path/to/new_erd.svg'
            assert database_server.source_params['database'] == 'newdb'


class TestHandleTestConnectionSuccess:
    """Tests for handle_test_connection success path."""

    def test_handle_test_connection_success(self, database_server):
        """Test handle_test_connection with successful connection."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'test_database_connection') as mock_test:
            mock_test.return_value = {'success': True, 'message': 'Connected'}

            data = {'host': 'localhost', 'port': '5432', 'database': 'testdb', 'user': 'user', 'password': 'pass'}
            handler.handle_test_connection(data)

            handler.send_json_response.assert_called_once_with({'success': True, 'message': 'Connected'}, 200)


class TestHandleReloadErdDatabaseSuccess:
    """Tests for handle_reload_erd database success path."""

    def test_handle_reload_erd_database_success(self, database_server):
        """Test handle_reload_erd with successful database reload."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'reload_from_database') as mock_reload:
            mock_reload.return_value = {'success': True, 'message': 'Reloaded'}

            data = {'host': 'localhost', 'port': '5432', 'database': 'testdb', 'user': 'user', 'password': 'pass'}
            handler.handle_reload_erd(data)

            handler.send_json_response.assert_called_once_with({'success': True, 'message': 'Reloaded'}, 200)

    def test_handle_reload_erd_unknown_source(self, file_server):
        """Test handle_reload_erd with unknown source type."""
        file_server.source_type = 'unknown'
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        handler.handle_reload_erd({})

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args[0][0]
        assert call_args['success'] is False
        assert 'Unknown source type' in call_args['message']


class TestHandleListDatabasesValidation:
    """Tests for handle_list_databases validation and exception."""

    def test_handle_list_databases_missing_params(self, database_server):
        """Test handle_list_databases with missing parameters."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'host': 'localhost', 'port': '5432'}  # Missing 'user'
        handler.handle_list_databases(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Missing required parameters' in call_args[0][0]['message']
        assert call_args[0][1] == 400

    def test_handle_list_databases_exception(self, database_server):
        """Test handle_list_databases with exception."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server.database_service, 'list_databases') as mock_list:
            mock_list.side_effect = Exception('Database error')

            data = {'host': 'localhost', 'port': '5432', 'user': 'user', 'password': 'pass'}
            handler.handle_list_databases(data)

            handler.send_json_response.assert_called_once()
            call_args = handler.send_json_response.call_args
            assert call_args[0][0]['success'] is False
            assert 'Database error' in call_args[0][0]['message']
            assert call_args[0][1] == 500


class TestHandleApplyFocusedSettingsValidation:
    """Tests for handle_apply_focused_settings validation errors."""

    def test_handle_apply_focused_settings_db_missing_params(self, database_server):
        """Test handle_apply_focused_settings with database and missing connection params."""
        # Simulate missing connection parameters
        database_server.source_params = {}
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': ['users'], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Database connection parameters not available' in call_args[0][0]['message']
        assert call_args[0][1] == 400

    def test_handle_apply_focused_settings_file_missing(self, file_server):
        """Test handle_apply_focused_settings with missing file."""
        file_server.source_params['filepath'] = '/nonexistent/file.sql'
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': ['users'], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Source file not available' in call_args[0][0]['message']
        assert call_args[0][1] == 400

    def test_handle_apply_focused_settings_unknown_source(self, file_server):
        """Test handle_apply_focused_settings with unknown source type."""
        file_server.source_type = 'unknown'
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': ['users'], 'graphviz_settings': {}}
        handler.handle_apply_focused_settings(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Unknown source type' in call_args[0][0]['message']
        assert call_args[0][1] == 400


class TestMissingLines:
    """Tests to cover remaining missing lines in server.py."""

    def test_handle_generate_selected_svg_db_missing_params(self, database_server):
        """Test handle_generate_selected_svg with database and missing params."""
        database_server.source_params = {}  # Missing required params
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        # Include table_ids to pass the first validation
        data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Database connection parameters not available' in call_args[0][0]['message']

    def test_handle_generate_selected_svg_file_missing(self, file_server):
        """Test handle_generate_selected_svg with missing file."""
        file_server.source_params['filepath'] = '/nonexistent/file.sql'
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Source file not available' in call_args[0][0]['message']

    def test_handle_generate_selected_svg_unknown_source(self, file_server):
        """Test handle_generate_selected_svg with unknown source."""
        file_server.source_type = 'unknown'
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        data = {'table_ids': ['users'], 'edge_ids': [], 'graphviz_settings': {}}
        handler.handle_generate_selected_svg(data)

        handler.send_json_response.assert_called_once()
        call_args = handler.send_json_response.call_args
        assert call_args[0][0]['success'] is False
        assert 'Unknown source type' in call_args[0][0]['message']

    def test_handle_optimize_layout_view_columns_enhancement(self, database_server, tmp_path):
        """Test handle_optimize_layout with view columns enhancement."""
        # Create a temporary SQL file
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        # Use database source to test view_columns_from_db
        database_server.source_type = 'database'
        database_server.source_params = {
            'host': 'localhost',
            'port': '5432',
            'database': 'testdb',
            'user': 'testuser'
        }
        database_server.cached_password = 'testpass'

        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch.object(database_server, 'fetch_schema_from_database') as mock_fetch, \
             patch.object(database_server, 'fetch_view_columns') as mock_fetch_views, \
             patch('pypgsvg.server.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.server.optimize_layout') as mock_optimize:

            mock_fetch.return_value = "CREATE TABLE users (id INT);"
            # Return view_columns that match both a view and a table name
            mock_fetch_views.return_value = {
                'users': [{'name': 'id', 'type': 'integer'}],  # Matches table
                'user_view': [{'name': 'name', 'type': 'text'}]  # Matches view
            }
            mock_parse.return_value = (
                {'users': {'columns': []}},  # tables - will be enhanced
                [],  # foreign_keys
                [],  # triggers
                [],  # errors
                {'user_view': {'columns': []}},  # views - will be enhanced
                [],  # functions
                {}   # settings
            )
            mock_optimize.return_value = ({'rankdir': 'TB'}, 'Optimized')

            data = {'graphviz_settings': {'rankdir': 'LR'}}
            handler.handle_optimize_layout(data)

            # Verify the handler responded
            assert handler.send_json_response.called

    def test_handle_shutdown_threading_and_shutdown(self, database_server):
        """Test handle_shutdown creates thread and calls shutdown (lines 685-687)."""
        database_server.server = MagicMock()
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.send_json_response = MagicMock()

        with patch('threading.Thread') as mock_thread, \
             patch('time.sleep'):  # Mock sleep to speed up test
            handler.handle_shutdown()

            # Verify thread was created and started
            mock_thread.assert_called_once()
            assert mock_thread.return_value.start.called




class TestUnknownEndpoint:
    """Test for unknown API endpoint (line 157)."""

    def test_do_post_unknown_api_endpoint(self, file_server):
        """Test POST to completely unknown API endpoint."""
        handler_class = file_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{}'
        handler.headers = {'Content-Length': '2'}
        handler.path = '/api/completely_unknown_endpoint'
        handler.send_error = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        # Verify 404 error was sent
        handler.send_error.assert_called_once_with(404, "Endpoint not found")


class TestStartServerFunction:
    """Tests for start_server function."""

    def test_start_server_function(self):
        """Test start_server function creates and starts server."""
        from pypgsvg.server import start_server

        with patch('pypgsvg.server.ERDServer') as mock_server_class:
            mock_server = MagicMock()
            mock_server_class.return_value = mock_server

            start_server(
                '/path/to/file.svg',
                'file',
                {'filepath': '/path/to/dump.sql'},
                {'graphviz_settings': {}},
                open_browser=False
            )

            # Verify server was created and started
            mock_server_class.assert_called_once_with(
                '/path/to/file.svg',
                'file',
                {'filepath': '/path/to/dump.sql'},
                {'graphviz_settings': {}}
            )
            mock_server.start.assert_called_once_with(open_browser=False)


class TestRoutingPaths:
    """Tests for API routing paths in do_POST."""

    def test_route_test_connection(self, database_server):
        """Test routing to handle_test_connection."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"host":"localhost","port":"5432","database":"testdb","user":"user"}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/test-db-connection'
        handler.handle_test_connection = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_test_connection.called

    def test_route_reload_erd(self, database_server):
        """Test routing to handle_reload_erd."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"host":"localhost","port":"5432","database":"testdb","user":"user"}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/reload-erd'
        handler.handle_reload_erd = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_reload_erd.called

    def test_route_apply_focused_settings(self, database_server):
        """Test routing to handle_apply_focused_settings."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"table_ids":[],"graphviz_settings":{}}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/apply_focused_settings'
        handler.handle_apply_focused_settings = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_apply_focused_settings.called

    def test_route_generate_selected_svg(self, database_server):
        """Test routing to handle_generate_selected_svg."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"table_ids":[],"graphviz_settings":{}}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/generate_selected_svg'
        handler.handle_generate_selected_svg = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_generate_selected_svg.called

    def test_route_generate_focused_erd(self, database_server):
        """Test routing to handle_generate_focused_erd."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"table_ids":[],"graphviz_settings":{}}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/generate_focused_erd'
        handler.handle_generate_focused_erd = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_generate_focused_erd.called

    def test_route_optimize_layout(self, database_server):
        """Test routing to handle_optimize_layout."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"graphviz_settings":{}}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/optimize_layout'
        handler.handle_optimize_layout = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_optimize_layout.called

    def test_route_shutdown(self, database_server):
        """Test routing to handle_shutdown."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/shutdown'
        handler.handle_shutdown = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_shutdown.called

    def test_route_list_databases(self, database_server):
        """Test routing to handle_list_databases."""
        handler_class = database_server.create_request_handler()
        handler = handler_class.__new__(handler_class)
        handler.rfile = MagicMock()
        handler.rfile.read.return_value = b'{"host":"localhost","port":"5432","user":"user"}'
        handler.headers = {'Content-Length': '100'}
        handler.path = '/api/list-databases'
        handler.handle_list_databases = MagicMock()
        handler.send_response = MagicMock()
        handler.send_header = MagicMock()
        handler.end_headers = MagicMock()

        handler.do_POST()

        assert handler.handle_list_databases.called


class TestServerStartupPrintStatements:
    """Tests to trigger print statements during server startup."""

    def test_server_start_database_source_prints(self, database_server):
        """Test server startup with database source triggers connection print."""
        mock_server = MagicMock()
        mock_server.serve_forever.side_effect = KeyboardInterrupt()

        with patch('socketserver.TCPServer', return_value=mock_server):
            try:
                database_server.start(open_browser=False)
            except KeyboardInterrupt:
                pass

            # Just verify it runs without error - prints are side effects


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
