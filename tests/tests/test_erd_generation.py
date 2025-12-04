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
import re, json


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
    tables, foreign_keys, triggers,  errors = parse_sql_dump(sample_sql)
    assert not errors
    return tables, foreign_keys


def test_parse_sql_dump(sample_sql):

    tables, foreign_keys, triggers, errors = parse_sql_dump(sample_sql)
    assert 'users' in tables
    def test_generate_erd_creates_svg_file(parsed_schema):
        """
        Test that generate_erd_with_graphviz creates an SVG file on disk.
        """
        tables, foreign_keys = parsed_schema
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_output")
            generate_erd_with_graphviz(tables, foreign_keys, output_file)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            assert "users" in svg_content
            assert "posts" in svg_content
            assert "<svg" in svg_content

    def test_generate_erd_with_no_foreign_keys(parsed_schema):
        """
        Test ERD generation when there are no foreign keys.
        """
        tables, _ = parsed_schema
        foreign_keys = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_no_fk")
            generate_erd_with_graphviz(tables, foreign_keys, output_file)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            assert "users" in svg_content
            assert "posts" in svg_content

    def test_generate_erd_hide_standalone(parsed_schema):
        """
        Test ERD generation with show_standalone=False (should hide tables with no FKs).
        """
        tables, _ = parsed_schema
        foreign_keys = []
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_hide_standalone")
            generate_erd_with_graphviz(tables, foreign_keys, output_file, show_standalone=False)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            # Both tables are standalone, so should not appear
            assert "users" not in svg_content
            assert "posts" not in svg_content

    def test_generate_erd_metadata_in_svg(parsed_schema):
        """
        Test that metadata is injected into the SVG.
        """
        tables, foreign_keys = parsed_schema
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_metadata")
            generate_erd_with_graphviz(tables, foreign_keys, output_file, input_file_path=__file__)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            assert "Source:" in svg_content or "filename" in svg_content
            assert "generated" in svg_content

    def test_generate_erd_graph_data_json(parsed_schema):
        """
        Test that the SVG contains a <script id="graph-data"> JSON block.
        """
        tables, foreign_keys = parsed_schema
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_graph_data")
            generate_erd_with_graphviz(tables, foreign_keys, output_file)
            svg_path = output_file + ".svg"
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            m = re.search(r'<script id="graph-data" type="application/json">(.*?)</script>', svg_content, re.DOTALL)
            assert m
            graph_data = json.loads(m.group(1))
            assert "tables" in graph_data
            assert "edges" in graph_data

    def test_generate_erd_excludes_tables(parsed_schema):
        """
        Test that tables matching exclusion patterns are not included in the SVG.
        """
        tables, foreign_keys = parsed_schema
        tables["vw_hidden"] = {"columns": [{"name": "id", "type": "integer"}]}
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_exclude")
            # Pass exclusion patterns
            generate_erd_with_graphviz(tables, foreign_keys, output_file, exclude_patterns=['vw_'])
            svg_path = output_file + ".svg"
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            assert "vw_hidden" not in svg_content

    def test_generate_erd_with_graphviz_mocked(parsed_schema):
        """
        Test that Digraph.render is called (mocked test).
        """
        tables, foreign_keys = parsed_schema
        with patch('pypgsvg.erd_generator.Digraph') as mock_digraph:
            mock_dot = MagicMock()
            mock_digraph.return_value = mock_dot
            with tempfile.TemporaryDirectory() as tmpdir:
                output_file = os.path.join(tmpdir, "test_erd")
                generate_erd_with_graphviz(tables, foreign_keys, output_file)
                mock_dot.render.assert_called()

    def test_generate_erd_with_graphviz_real(parsed_schema):
        """
        Test that generate_erd_with_graphviz creates an SVG file and it contains expected content.
        """
        tables, foreign_keys = parsed_schema
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_erd")
            generate_erd_with_graphviz(tables, foreign_keys, output_file)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            assert "users" in svg_content
            assert "posts" in svg_content
            assert "<svg" in svg_content

            
    def test_generate_erd_with_real_schema_dump():

        """
        Integration test: Parse a real PostgreSQL schema dump and generate an ERD SVG.
        This exercises the parser and ERD generator on a large, realistic schema.
        """
        schema_path = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../Samples/schema.dump")
        )
        assert os.path.exists(schema_path), f"Schema dump not found: {schema_path}"
    
        with open(schema_path, "r", encoding="utf-8", errors="replace") as f:
            sql_content = f.read()
    
        from pypgsvg.db_parser import parse_sql_dump
        from pypgsvg.erd_generator import generate_erd_with_graphviz
    
        tables, foreign_keys, triggers, errors = parse_sql_dump(sql_content)
        # Should parse some tables and not fail
        assert isinstance(tables, dict)
        assert len(tables) > 10  # Should find many tables
        assert isinstance(foreign_keys, list)
        # Accept errors, but should not be catastrophic
    
        import tempfile
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "erd_schema_dump")
            generate_erd_with_graphviz(tables, foreign_keys, output_file, input_file_path=schema_path)
            svg_path = output_file + ".svg"
            assert os.path.exists(svg_path)
            with open(svg_path, "r", encoding="utf-8") as svgf:
                svg_content = svgf.read()
            # Spot check for some known tables and SVG structure
            assert "<svg" in svg_content
            assert "players" in svg_content or "users" in svg_content or "products" in svg_content
            # Should contain metadata
            assert "schema.dump" in svg_content or "filename" in svg_content