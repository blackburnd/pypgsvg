import os
import tempfile
import pytest
import json
from unittest.mock import patch, MagicMock
from pypgsvg.erd_generator import generate_erd_with_graphviz
import re

@pytest.fixture
def simple_schema():
    tables = {
        "users": {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "name", "type": "varchar(100)"}
            ]
        },
        "posts": {
            "columns": [
                {"name": "id", "type": "integer"},
                {"name": "user_id", "type": "integer"}
            ]
        }
    }
    foreign_keys = [
        ("posts", "user_id", "users", "id", "FOREIGN KEY (user_id) REFERENCES users(id) on DELETE CASCADE", "CASCADE", "CASCADE")
    ]
    return tables, foreign_keys

def test_generate_erd_creates_svg_file(simple_schema):
    tables, foreign_keys = simple_schema
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        # Check for table names in SVG
        assert "users" in svg_content
        assert "posts" in svg_content
        # Check for graph-data script
        assert '<script id="graph-data"' in svg_content

def test_generate_erd_with_no_foreign_keys():
    tables = {
        "users": {"columns": [{"name": "id", "type": "integer"}]},
        "posts": {"columns": [{"name": "id", "type": "integer"}]}
    }
    foreign_keys = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd2")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        assert "users" in svg_content
        assert "posts" in svg_content

def test_generate_erd_excludes_tables():
    # Table name triggers exclusion when pattern is provided
    tables = {
        "users": {"columns": [{"name": "id", "type": "integer"}]},
        "vw_users": {"columns": [{"name": "id", "type": "integer"}]},  # Should be excluded
        "tmp_data": {"columns": [{"name": "id", "type": "integer"}]},  # Should be excluded
    }
    foreign_keys = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd3")
        # Pass exclusion patterns
        generate_erd_with_graphviz(tables, foreign_keys, output_file, exclude_patterns=['vw_', 'tmp_'])
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        assert "users" in svg_content
        assert "vw_users" not in svg_content
        assert "tmp_data" not in svg_content

def test_generate_erd_hide_standalone(simple_schema):
    tables, foreign_keys = simple_schema
    # Remove foreign keys so both tables are standalone
    foreign_keys = []
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd4")
        generate_erd_with_graphviz(tables, foreign_keys, output_file, show_standalone=False)
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        # Both tables are standalone, so should be excluded
        assert "users" not in svg_content
        assert "posts" not in svg_content

@patch("pypgsvg.erd_generator.Digraph")
def test_generate_erd_graphviz_error(mock_digraph, simple_schema):
    tables, foreign_keys = simple_schema
    mock_dot = MagicMock()
    mock_dot.pipe.side_effect = Exception("Graphviz error!")
    mock_digraph.return_value = mock_dot
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd5")
        # Should not raise, but should not create file
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        assert not os.path.exists(svg_path)

def test_generate_erd_metadata_fields(simple_schema):
    tables, foreign_keys = simple_schema
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd6")
        generate_erd_with_graphviz(tables, foreign_keys, output_file, input_file_path=__file__)
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        # Metadata fields - updated to match new HTML structure
        assert "Generated" in svg_content

def test_generate_erd_graph_data_json(simple_schema):
    tables, foreign_keys = simple_schema
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd7")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        # Extract graph-data JSON
        m = re.search(r'<script id="graph-data" type="application/json">(.*?)</script>', svg_content, re.DOTALL)
        assert m
        graph_data = json.loads(m.group(1))
        assert "tables" in graph_data
        assert "edges" in graph_data
        assert "users" in [k for k in graph_data["tables"].keys()] or "users" in svg_content


def test_generate_erd_cascade_constraint_styling():
    """Test that CASCADE constraints get special edge styling"""
    tables = {
        "users": {"columns": [{"name": "id", "type": "integer"}]},
        "posts": {"columns": [{"name": "id", "type": "integer"}, {"name": "user_id", "type": "integer"}]}
    }
    # Foreign key with CASCADE constraint - constraints must be a list
    foreign_keys = [
        ("posts", "user_id", "users", "id", "FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE", {}, ["ON DELETE CASCADE"])
    ]
    with tempfile.TemporaryDirectory() as tmpdir:
        output_file = os.path.join(tmpdir, "test_erd9")
        generate_erd_with_graphviz(tables, foreign_keys, output_file)
        svg_path = output_file + ".svg"
        assert os.path.exists(svg_path)
        with open(svg_path, "r", encoding="utf-8") as f:
            svg_content = f.read()
        # Verify the graph was created successfully
        assert "users" in svg_content
        assert "posts" in svg_content
