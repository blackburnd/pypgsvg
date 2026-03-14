"""Tests for ERDService."""
import pytest
import os
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
from pypgsvg.erd_service import ERDService
from pypgsvg.database_service import DatabaseService


@pytest.fixture
def erd_service():
    """Create ERDService instance with mocked database service."""
    db_service = DatabaseService()
    return ERDService(db_service)


class TestGenerateFromDatabase:
    """Tests for generate_from_database method."""

    def test_generate_from_database_success(self, erd_service, tmp_path):
        """Test successful ERD generation from database."""
        output_file = str(tmp_path / "test_erd")

        with patch.object(erd_service.database_service, 'fetch_schema') as mock_fetch_schema, \
             patch.object(erd_service.database_service, 'fetch_view_columns') as mock_fetch_views, \
             patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_fetch_schema.return_value = "CREATE TABLE users (id INT);"
            mock_fetch_views.return_value = {}
            mock_parse.return_value = (
                {'users': {'columns': []}},  # tables
                [],  # foreign_keys
                {},  # triggers
                [],  # errors
                {},  # views
                {},  # functions
                {}   # settings
            )
            mock_extract.return_value = {}

            generation_params = {
                'packmode': 'array',
                'rankdir': 'TB',
                'show_standalone': True
            }

            svg_file, success = erd_service.generate_from_database(
                'localhost', '5432', 'testdb', 'testuser', 'password',
                output_file, generation_params
            )

            assert success is True
            assert svg_file == output_file + '.svg'
            mock_gen.assert_called_once()

    def test_generate_from_database_with_errors(self, erd_service, tmp_path):
        """Test ERD generation with parsing errors."""
        output_file = str(tmp_path / "test_erd")

        with patch.object(erd_service.database_service, 'fetch_schema') as mock_fetch_schema, \
             patch.object(erd_service.database_service, 'fetch_view_columns') as mock_fetch_views, \
             patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_fetch_schema.return_value = "CREATE TABLE users (id INT);"
            mock_fetch_views.return_value = {}
            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                ['Error 1', 'Error 2'],  # parsing errors
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            generation_params = {'packmode': 'array'}

            svg_file, success = erd_service.generate_from_database(
                'localhost', '5432', 'testdb', 'testuser', 'password',
                output_file, generation_params
            )

            assert success is True
            assert svg_file == output_file + '.svg'

    def test_generate_from_database_with_view_columns(self, erd_service, tmp_path):
        """Test ERD generation with view columns from database."""
        output_file = str(tmp_path / "test_erd")

        with patch.object(erd_service.database_service, 'fetch_schema') as mock_fetch_schema, \
             patch.object(erd_service.database_service, 'fetch_view_columns') as mock_fetch_views, \
             patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_fetch_schema.return_value = "CREATE VIEW user_view AS SELECT * FROM users;"
            mock_fetch_views.return_value = {
                'user_view': [{'name': 'id', 'type': 'integer'}]
            }
            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {'user_view': {'columns': []}},  # views
                {},
                {}
            )
            mock_extract.return_value = {}

            generation_params = {'packmode': 'array'}

            svg_file, success = erd_service.generate_from_database(
                'localhost', '5432', 'testdb', 'testuser', 'password',
                output_file, generation_params
            )

            assert success is True

    def test_generate_from_database_view_columns_in_tables(self, erd_service, tmp_path):
        """Test ERD generation with view columns matching table names."""
        output_file = str(tmp_path / "test_erd")

        with patch.object(erd_service.database_service, 'fetch_schema') as mock_fetch_schema, \
             patch.object(erd_service.database_service, 'fetch_view_columns') as mock_fetch_views, \
             patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_fetch_schema.return_value = "CREATE TABLE users (id INT);"
            # View columns with a name that matches a table
            mock_fetch_views.return_value = {
                'users': [{'name': 'id', 'type': 'integer'}]
            }
            mock_parse.return_value = (
                {'users': {'columns': []}},  # tables with 'users'
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            generation_params = {'packmode': 'array'}

            svg_file, success = erd_service.generate_from_database(
                'localhost', '5432', 'testdb', 'testuser', 'password',
                output_file, generation_params
            )

            assert success is True


class TestGenerateFromFile:
    """Tests for generate_from_file method."""

    def test_generate_from_file_success(self, erd_service, tmp_path):
        """Test successful ERD generation from file."""
        # Create a temp SQL file
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        output_file = str(tmp_path / "test_erd")

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            generation_params = {'packmode': 'array'}

            svg_file, success = erd_service.generate_from_file(
                str(sql_file), output_file, generation_params
            )

            assert success is True
            assert svg_file == output_file + '.svg'
            mock_gen.assert_called_once()

    def test_generate_from_file_not_found(self, erd_service, tmp_path):
        """Test ERD generation with non-existent file."""
        output_file = str(tmp_path / "test_erd")

        with pytest.raises(FileNotFoundError) as exc_info:
            erd_service.generate_from_file(
                '/nonexistent/file.sql', output_file, {}
            )

        assert "File not found" in str(exc_info.value)

    def test_generate_from_file_with_errors(self, erd_service, tmp_path):
        """Test ERD generation from file with parsing errors."""
        sql_file = tmp_path / "schema.sql"
        sql_file.write_text("CREATE TABLE users (id INT);")
        output_file = str(tmp_path / "test_erd")

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                ['Parse error'],  # errors
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            svg_file, success = erd_service.generate_from_file(
                str(sql_file), output_file, {}
            )

            assert success is True


class TestGenerateFocusedErd:
    """Tests for generate_focused_erd method."""

    def test_generate_focused_erd_success(self, erd_service, tmp_path):
        """Test successful focused ERD generation."""
        sql_dump = "CREATE TABLE users (id INT); CREATE TABLE posts (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)
        input_source = "test.sql"
        graphviz_settings = {'packmode': 'array'}

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = (
                {'users': {'columns': []}, 'posts': {'columns': []}},
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            svg_file = erd_service.generate_focused_erd(
                sql_dump, table_ids, output_dir, input_source, graphviz_settings
            )

            assert svg_file.endswith('.svg')
            # Verify include_tables was passed correctly
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs['include_tables'] == ['users']
            assert call_kwargs['show_standalone'] is False

    def test_generate_focused_erd_with_view_columns(self, erd_service, tmp_path):
        """Test focused ERD generation with view columns."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)
        view_columns = {'user_view': [{'name': 'id', 'type': 'integer'}]}

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {'user_view': {'columns': []}},
                {},
                {}
            )
            mock_extract.return_value = {}

            svg_file = erd_service.generate_focused_erd(
                sql_dump, table_ids, output_dir, 'test.sql',
                {'packmode': 'array'}, view_columns
            )

            assert svg_file.endswith('.svg')

    def test_generate_focused_erd_view_columns_in_tables(self, erd_service, tmp_path):
        """Test focused ERD with view columns matching table names."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)
        # View column name matches table name
        view_columns = {'users': [{'name': 'id', 'type': 'integer'}]}

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen:

            mock_parse.return_value = (
                {'users': {'columns': []}},  # table named 'users'
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            svg_file = erd_service.generate_focused_erd(
                sql_dump, table_ids, output_dir, 'test.sql',
                {'packmode': 'array'}, view_columns
            )

            assert svg_file.endswith('.svg')


class TestGenerateSelectedSvg:
    """Tests for generate_selected_svg method."""

    def test_generate_selected_svg_success(self, erd_service, tmp_path):
        """Test successful standalone SVG generation."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)

        # Mock the SVG file creation
        svg_content = '<?xml version="1.0"?><svg>Test SVG</svg>'

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen, \
             patch('builtins.open', mock_open(read_data=svg_content)), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            result = erd_service.generate_selected_svg(
                sql_dump, table_ids, output_dir, 'test.sql', {'packmode': 'array'}
            )

            assert result == svg_content
            # Verify show_standalone was True
            call_kwargs = mock_gen.call_args[1]
            assert call_kwargs['show_standalone'] is True

    def test_generate_selected_svg_with_view_columns(self, erd_service, tmp_path):
        """Test standalone SVG generation with view columns."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)
        view_columns = {'user_view': [{'name': 'id', 'type': 'integer'}]}
        svg_content = '<svg>Test</svg>'

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen, \
             patch('builtins.open', mock_open(read_data=svg_content)), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {'user_view': {'columns': []}},
                {},
                {}
            )
            mock_extract.return_value = {}

            result = erd_service.generate_selected_svg(
                sql_dump, table_ids, output_dir, 'test.sql',
                {'packmode': 'array'}, view_columns
            )

            assert result == svg_content

    def test_generate_selected_svg_view_columns_in_tables(self, erd_service, tmp_path):
        """Test standalone SVG with view columns matching table names."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)
        # View column name matches table name
        view_columns = {'users': [{'name': 'id', 'type': 'integer'}]}
        svg_content = '<svg>Test</svg>'

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen, \
             patch('builtins.open', mock_open(read_data=svg_content)), \
             patch('os.path.exists', return_value=True), \
             patch('os.remove'):

            mock_parse.return_value = (
                {'users': {'columns': []}},  # table named 'users'
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            result = erd_service.generate_selected_svg(
                sql_dump, table_ids, output_dir, 'test.sql',
                {'packmode': 'array'}, view_columns
            )

            assert result == svg_content

    def test_generate_selected_svg_file_not_created(self, erd_service, tmp_path):
        """Test standalone SVG generation when file creation fails."""
        sql_dump = "CREATE TABLE users (id INT);"
        table_ids = ['users']
        output_dir = str(tmp_path)

        with patch('pypgsvg.erd_service.parse_sql_dump') as mock_parse, \
             patch('pypgsvg.erd_service.extract_constraint_info') as mock_extract, \
             patch('pypgsvg.erd_service.generate_erd_with_graphviz') as mock_gen, \
             patch('os.path.exists', return_value=False):

            mock_parse.return_value = (
                {'users': {'columns': []}},
                [],
                {},
                [],
                {},
                {},
                {}
            )
            mock_extract.return_value = {}

            with pytest.raises(Exception) as exc_info:
                erd_service.generate_selected_svg(
                    sql_dump, table_ids, output_dir, 'test.sql', {}
                )

            assert "Failed to generate SVG file" in str(exc_info.value)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])
