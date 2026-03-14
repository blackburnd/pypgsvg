"""Tests for pypgsvg.__init__ module."""
import pytest
from unittest.mock import patch, MagicMock, call
import subprocess
import sys


class TestFetchSchemaFromDatabase:
    """Tests for fetch_schema_from_database function."""

    def test_fetch_schema_success(self):
        """Test successful schema fetch from database."""
        from pypgsvg import fetch_schema_from_database

        with patch('getpass.getpass') as mock_getpass, \
             patch('subprocess.run') as mock_run, \
             patch('pypgsvg.fetch_view_columns') as mock_fetch_views:

            mock_getpass.return_value = 'testpass'
            mock_run.return_value = MagicMock(stdout='-- Schema dump')
            mock_fetch_views.return_value = {'view1': [{'name': 'col1', 'type': 'text'}]}

            sql_dump, view_columns = fetch_schema_from_database('localhost', '5432', 'testdb', 'testuser')

            assert sql_dump == '-- Schema dump'
            assert view_columns == {'view1': [{'name': 'col1', 'type': 'text'}]}

            # Verify pg_dump was called with correct arguments
            call_args = mock_run.call_args
            assert call_args[0][0][0] == 'pg_dump'
            assert '-h' in call_args[0][0]
            assert 'localhost' in call_args[0][0]
            assert '-p' in call_args[0][0]
            assert '5432' in call_args[0][0]

    def test_fetch_schema_subprocess_error(self):
        """Test schema fetch with subprocess error."""
        from pypgsvg import fetch_schema_from_database

        with patch('getpass.getpass') as mock_getpass, \
             patch('subprocess.run') as mock_run:

            mock_getpass.return_value = 'testpass'
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd='pg_dump', stderr="Connection failed"
            )

            with pytest.raises(subprocess.CalledProcessError):
                fetch_schema_from_database('localhost', '5432', 'testdb', 'testuser')

    def test_fetch_schema_pg_dump_not_found(self):
        """Test schema fetch when pg_dump not found."""
        from pypgsvg import fetch_schema_from_database

        with patch('getpass.getpass') as mock_getpass, \
             patch('subprocess.run') as mock_run, \
             patch('sys.exit') as mock_exit:

            mock_getpass.return_value = 'testpass'
            mock_run.side_effect = FileNotFoundError("pg_dump not found")

            fetch_schema_from_database('localhost', '5432', 'testdb', 'testuser')

            # Verify sys.exit(1) was called
            mock_exit.assert_called_once_with(1)


class TestFetchViewColumns:
    """Tests for fetch_view_columns function."""

    def test_fetch_view_columns_success(self):
        """Test successful view columns fetch."""
        from pypgsvg import fetch_view_columns

        psql_output = "view1|col1|integer|1\nview1|col2|text|2\nview2|col1|text|1\n"

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout=psql_output)

            result = fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            assert 'view1' in result
            assert 'view2' in result
            assert len(result['view1']) == 2
            assert result['view1'][0]['name'] == 'col1'
            assert result['view1'][0]['type'] == 'integer'
            assert result['view1'][1]['name'] == 'col2'

    def test_fetch_view_columns_subprocess_error(self):
        """Test fetch view columns with subprocess error."""
        from pypgsvg import fetch_view_columns

        with patch('subprocess.run') as mock_run:
            mock_run.side_effect = subprocess.CalledProcessError(
                returncode=1, cmd='psql', stderr="Auth failed"
            )

            result = fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on error
            assert result == {}

    def test_fetch_view_columns_parse_error(self):
        """Test fetch view columns with parse error."""
        from pypgsvg import fetch_view_columns

        with patch('subprocess.run') as mock_run:
            # Return invalid data that will cause parsing exception
            mock_run.return_value = MagicMock(stdout="invalid|data\n")

            result = fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on parse error
            assert result == {}

    def test_fetch_view_columns_empty_output(self):
        """Test fetch view columns with empty output."""
        from pypgsvg import fetch_view_columns

        with patch('subprocess.run') as mock_run:
            mock_run.return_value = MagicMock(stdout="")

            result = fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            assert result == {}

    def test_fetch_view_columns_general_exception(self):
        """Test fetch view columns with general exception during parsing."""
        from pypgsvg import fetch_view_columns

        with patch('subprocess.run') as mock_run:
            # Make stdout.strip().split() raise an exception
            mock_result = MagicMock()
            mock_result.stdout.strip.side_effect = RuntimeError("Unexpected error")
            mock_run.return_value = mock_result

            result = fetch_view_columns('localhost', '5432', 'testdb', 'testuser', 'password')

            # Should return empty dict on general exception
            assert result == {}


class TestMainFunction:
    """Tests for main() function."""

    def test_main_with_file_input(self, tmp_path):
        """Test main function with file input."""
        from pypgsvg import main

        # Create temp SQL file
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        output_file = tmp_path / "output"

        with patch('sys.argv', ['pypgsvg', str(sql_file), '-o', str(output_file)]), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            mock_parse.return_value = (
                {'users': {}},  # tables
                [],  # foreign_keys
                [],  # triggers
                [],  # errors
                {},  # views
                [],  # functions
                {}   # settings
            )
            mock_extract.return_value = []

            main()

            # Verify ERD generation was called
            mock_generate.assert_called_once()

    def test_main_with_database_connection(self):
        """Test main function with database connection."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '--host', 'localhost', '--port', '5432',
                                '--database', 'testdb', '--user', 'testuser']), \
             patch('pypgsvg.fetch_schema_from_database') as mock_fetch, \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            mock_fetch.return_value = ('-- Schema', {})
            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            mock_fetch.assert_called_once_with('localhost', '5432', 'testdb', 'testuser')
            mock_generate.assert_called_once()

    def test_main_file_not_found(self):
        """Test main with non-existent file."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '/nonexistent/file.sql']), \
             patch('sys.exit') as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_both_file_and_db_params(self, tmp_path):
        """Test main with both file and database params (should error)."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file), '--host', 'localhost',
                                '--port', '5432', '--database', 'testdb', '--user', 'testuser']), \
             patch('sys.exit') as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_partial_db_params(self):
        """Test main with partial database params (should error)."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '--host', 'localhost', '--port', '5432']), \
             patch('sys.exit') as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_no_input(self):
        """Test main with no input (should error)."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg']), \
             patch('sys.exit') as mock_exit:

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_with_parsing_errors(self, tmp_path):
        """Test main function with parsing errors."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file)]), \
             patch('pypgsvg.parse_sql_dump') as mock_parse:

            mock_parse.return_value = (
                {},  # tables
                [],  # foreign_keys
                [],  # triggers
                ['Error 1', 'Error 2'],  # errors
                {},  # views
                [],  # functions
                {}   # settings
            )

            main()

            # Should print errors but not generate ERD
            # Just verify it doesn't crash

    def test_main_with_view_flag(self, tmp_path):
        """Test main function with --view flag to start server."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        output_file = tmp_path / "output"

        with patch('sys.argv', ['pypgsvg', str(sql_file), '-o', str(output_file), '--view']), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate, \
             patch('pypgsvg.server.start_server') as mock_start_server:

            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            # Verify server was started
            mock_start_server.assert_called_once()
            call_args = mock_start_server.call_args
            assert call_args[0][1] == 'file'  # source_type

    def test_main_with_view_flag_database_source(self):
        """Test main function with --view flag and database source."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '--host', 'localhost', '--port', '5432',
                                '--database', 'testdb', '--user', 'testuser', '--view']), \
             patch('pypgsvg.fetch_schema_from_database') as mock_fetch, \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate, \
             patch('pypgsvg.server.start_server') as mock_start_server:

            mock_fetch.return_value = ('-- Schema', {})
            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            # Verify server was started with database source
            mock_start_server.assert_called_once()
            call_args = mock_start_server.call_args
            assert call_args[0][1] == 'database'  # source_type

    def test_main_with_exclude_patterns(self, tmp_path):
        """Test main function with --exclude patterns."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file), '--exclude', 'tmp_', 'vw_']), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            # Verify exclude patterns were passed
            call_args = mock_generate.call_args
            assert call_args[1]['exclude_patterns'] == ['tmp_', 'vw_']

    def test_main_with_include_tables(self, tmp_path):
        """Test main function with --include tables."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file), '--include', 'users', 'posts']), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            # Verify include tables were passed
            call_args = mock_generate.call_args
            assert call_args[1]['include_tables'] == ['users', 'posts']

    def test_main_with_custom_graphviz_settings(self, tmp_path):
        """Test main function with custom Graphviz settings."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file),
                                '--packmode', 'cluster', '--rankdir', 'LR',
                                '--node-fontsize', '16', '--edge-fontsize', '14']), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []

            main()

            # Verify custom settings were passed
            call_args = mock_generate.call_args
            assert call_args[1]['packmode'] == 'cluster'
            assert call_args[1]['rankdir'] == 'LR'
            assert call_args[1]['node_fontsize'] == 16
            assert call_args[1]['edge_fontsize'] == 14

    def test_main_generation_exception(self, tmp_path):
        """Test main function with generation exception."""
        from pypgsvg import main

        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")

        with patch('sys.argv', ['pypgsvg', str(sql_file)]), \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate, \
             patch('sys.exit') as mock_exit:

            mock_parse.return_value = ({'users': {}}, [], [], [], {}, [], {})
            mock_extract.return_value = []
            mock_generate.side_effect = Exception("Generation failed")

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_database_fetch_exception(self):
        """Test main function with database fetch exception."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '--host', 'localhost', '--port', '5432',
                                '--database', 'testdb', '--user', 'testuser']), \
             patch('pypgsvg.fetch_schema_from_database') as mock_fetch, \
             patch('sys.exit') as mock_exit:

            mock_fetch.side_effect = Exception("Connection failed")

            main()

            mock_exit.assert_called_once_with(1)

    def test_main_view_columns_enhancement(self, tmp_path):
        """Test main function with view columns enhancement from database."""
        from pypgsvg import main

        with patch('sys.argv', ['pypgsvg', '--host', 'localhost', '--port', '5432',
                                '--database', 'testdb', '--user', 'testuser']), \
             patch('pypgsvg.fetch_schema_from_database') as mock_fetch, \
             patch('pypgsvg.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.generate_erd_with_graphviz') as mock_generate:

            # Return view columns from database
            mock_fetch.return_value = ('-- Schema', {
                'users': [{'name': 'id', 'type': 'integer'}],
                'user_view': [{'name': 'name', 'type': 'text'}]
            })
            mock_parse.return_value = (
                {'users': {'columns': []}},  # tables
                [],  # foreign_keys
                [],  # triggers
                [],  # errors
                {'user_view': {'columns': []}},  # views
                [],  # functions
                {}   # settings
            )
            mock_extract.return_value = []

            main()

            # Verify generation was called
            mock_generate.assert_called_once()


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
