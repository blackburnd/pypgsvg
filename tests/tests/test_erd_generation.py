"""
Unit tests for ERD generation functionality in create_graph.py.
"""
import pytest
import sys
import os
from unittest.mock import Mock, patch, MagicMock

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))
import tempfile
from pypgsvg.db_parser import parse_sql_dump
from pypgsvg.erd_generator import generate_erd_with_graphviz
from pypgsvg.metadata_injector import inject_metadata_into_svg


@pytest.fixture
def sample_sql():
    return """
    CREATE TABLE users (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100)
    );
    CREATE TABLE posts (
        id SERIAL PRIMARY KEY,
        user_id INTEGER REFERENCES users(id)
    );
    """


@pytest.fixture
def parsed_schema(sample_sql):
    tables, foreign_keys, errors = parse_sql_dump(sample_sql)
    assert not errors
    return tables, foreign_keys


def test_parse_sql_dump(sample_sql):

    tables, foreign_keys, errors = parse_sql_dump(sample_sql)
    assert 'users' in tables
    assert 'posts' in tables
    assert len(foreign_keys) == 1
    assert not errors


@patch('pypgsvg.erd_generator.Digraph')
def test_generate_erd_with_graphviz(mock_digraph, parsed_schema):
    tables, foreign_keys = parsed_schema
    mock_dot = MagicMock()
    mock_digraph.return_value = mock_dot

    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        mock_dot.render.assert_called()


def test_metadata_injection(parsed_schema):
    tables, foreign_keys = parsed_schema
    # Generate a minimal SVG for testing
    svg_content = "<svg><g id='main-erd-group'></g></svg>"
    file_info = {'filename': 'test.sql', 'filesize': '123', 'generated': 'now'}
    svg_with_metadata = inject_metadata_into_svg(
        svg_content, file_info, total_tables=len(tables), total_columns=2,
        total_foreign_keys=len(foreign_keys), total_edges=len(foreign_keys),
        tables=tables, foreign_keys=foreign_keys, show_standalone=True,
        generate_miniature_erd=None  # Or mock if needed
    )
    assert "Source: test.sql" in svg_with_metadata
    assert "<svg" in svg_with_metadata

