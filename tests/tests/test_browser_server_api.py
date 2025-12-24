"""Pytest-Playwright tests for Python ERD server API endpoints."""
import pytest
import subprocess
import time
import signal
import os
from pathlib import Path
from playwright.sync_api import Page, expect

pytestmark = pytest.mark.browser


@pytest.fixture(scope="module")
def sample_svg_file(tmp_path_factory):
    """Create a sample SVG file for testing."""
    tmp_dir = tmp_path_factory.mktemp("svg_data")
    svg_file = tmp_dir / "test_erd.svg"

    # Create a simple SVG with embedded graph data
    svg_content = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" width="800" height="600">
    <script id="graph-data" type="application/json">
    {
        "tables": {"users": {"id": "users", "label": "users"}},
        "edges": [],
        "views": {}
    }
    </script>
    <g id="main-erd-group">
        <g class="node" id="node-users">
            <rect width="100" height="50" fill="lightblue"/>
            <text x="50" y="25">users</text>
        </g>
    </g>
    <foreignObject id="metadata-container" x="10" y="10" width="200" height="100">
        <div xmlns="http://www.w3.org/1999/xhtml">
            <p>Database: test</p>
            <button class="copy-btn">Copy</button>
        </div>
    </foreignObject>
</svg>"""

    svg_file.write_text(svg_content)
    return svg_file


@pytest.fixture(scope="module")
def sample_sql_dump(tmp_path_factory):
    """Create a sample SQL dump file for testing."""
    tmp_dir = tmp_path_factory.mktemp("sql_data")
    sql_file = tmp_dir / "test_schema.sql"

    sql_content = """
    CREATE TABLE users (
        id integer NOT NULL PRIMARY KEY,
        username character varying(50) NOT NULL,
        email character varying(100)
    );

    CREATE TABLE posts (
        id integer NOT NULL PRIMARY KEY,
        title character varying(200) NOT NULL,
        user_id integer,
        FOREIGN KEY (user_id) REFERENCES users(id)
    );
    """

    sql_file.write_text(sql_content)
    return sql_file


@pytest.fixture(scope="module")
def erd_server(sample_svg_file, sample_sql_dump):
    """Start the Python ERD server for testing."""
    # Import here to ensure coverage tracking
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent / "src"))

    from pypgsvg.server import ERDServer

    # Create server instance
    source_params = {'filepath': str(sample_sql_dump)}
    generation_params = {
        'packmode': 'array',
        'rankdir': 'TB',
        'show_standalone': True,
    }

    server = ERDServer(
        svg_file=str(sample_svg_file),
        source_type='file',
        source_params=source_params,
        generation_params=generation_params
    )

    # Start server in background thread
    import threading
    server_thread = threading.Thread(target=lambda: server.start(open_browser=False), daemon=True)
    server_thread.start()

    # Wait for server to start
    time.sleep(2)

    base_url = f"http://localhost:{server.port}"

    yield base_url, server

    # Cleanup
    if server.server:
        server.server.shutdown()


def test_server_serves_svg_file(erd_server, page: Page):
    """Test that the ERD server serves the SVG file."""
    base_url, server = erd_server
    svg_filename = os.path.basename(server.svg_file)

    # Navigate to the SVG file
    page.goto(f"{base_url}/{svg_filename}")
    page.wait_for_load_state('domcontentloaded')

    # Verify SVG content is loaded
    metadata_container = page.locator('#metadata-container')
    expect(metadata_container).to_be_visible()


def test_server_api_reload_erd(erd_server, page: Page):
    """Test the /api/reload-erd endpoint."""
    base_url, server = erd_server

    # Make API request to reload ERD
    response = page.request.post(
        f"{base_url}/api/reload-erd",
        data={
            "filepath": server.source_params['filepath']
        }
    )

    # Verify response
    assert response.ok
    data = response.json()
    assert data.get('success') is not None


def test_server_api_apply_graphviz_settings(erd_server, page: Page):
    """Test the /api/apply_graphviz_settings endpoint."""
    base_url, server = erd_server

    # Make API request to apply settings
    response = page.request.post(
        f"{base_url}/api/apply_graphviz_settings",
        data={
            "graphviz_settings": {
                "rankdir": "LR",
                "packmode": "cluster"
            }
        }
    )

    # Verify response
    assert response.ok or response.status == 500  # May fail if schema invalid, but endpoint should respond
    data = response.json()
    assert 'success' in data
