#!/usr/bin/env python3
"""
Web server for pypgsvg to handle interactive ERD viewing with reload capabilities.
"""
import http.server
import socketserver
import json
import os
import threading
import webbrowser
import time
from urllib.parse import urlparse
from typing import Optional, Dict, Any

from .database_service import DatabaseService
from .erd_service import ERDService
from .db_parser import parse_sql_dump, extract_constraint_info
from .layout_optimizer import optimize_layout


class ERDServer:
    """Server to host ERD SVG files with reload capabilities."""

    def __init__(self, svg_file: str, source_type: str, source_params: Dict[str, Any],
                 generation_params: Dict[str, Any]):
        """
        Initialize ERD server.

        Args:
            svg_file: Path to the SVG file to serve
            source_type: 'database' or 'file'
            source_params: Parameters for the data source (host, port, etc. for database; filepath for file)
            generation_params: Parameters for ERD generation (packmode, rankdir, etc.)
        """
        self.svg_file = svg_file
        self.source_type = source_type
        self.source_params = source_params
        self.generation_params = generation_params
        self.port = 8765
        self.server = None

        # Initialize service layer
        self.database_service = DatabaseService()
        self.erd_service = ERDService(self.database_service)

    @property
    def cached_password(self) -> str:
        """Get cached password from database service."""
        return self.database_service.cached_password

    @cached_password.setter
    def cached_password(self, value: str):
        """Set cached password in database service."""
        self.database_service.cached_password = value

    def fetch_schema_from_database(self, host: str, port: str, database: str,
                                   user: str, password: str = None) -> str:
        """Fetch schema from PostgreSQL database using pg_dump."""
        return self.database_service.fetch_schema(host, port, database, user, password)

    def fetch_view_columns(self, host: str, port: str, database: str,
                          user: str, password: str) -> Dict[str, Any]:
        """
        Fetch column information for all views in the database.

        Returns:
            Dict mapping view names to their column lists
        """
        return self.database_service.fetch_view_columns(host, port, database, user, password)
    
    def test_database_connection(self, host: str, port: str, database: str,
                                user: str, password: str) -> Dict[str, Any]:
        """Test database connection."""
        return self.database_service.test_connection(host, port, database, user, password)
    
    def reload_from_database(self, host: str, port: str, database: str,
                           user: str, password: str) -> Dict[str, Any]:
        """Reload ERD from database connection."""
        try:
            # Generate new filename with database name
            svg_dir = os.path.dirname(os.path.abspath(self.svg_file))
            new_filename = f"{database}_erd"
            output_file = os.path.join(svg_dir, new_filename)

            # Delegate to ERD service
            new_svg_file, success = self.erd_service.generate_from_database(
                host, port, database, user, password,
                output_file,
                self.generation_params
            )

            # Update the server's SVG file reference and source params
            self.svg_file = new_svg_file
            self.source_params['database'] = database

            print(f"ERD reloaded successfully! New file: {new_svg_file}")
            return {
                "success": True,
                "message": "ERD reloaded successfully",
                "reload": True,  # Signal browser to reload
                "new_file": os.path.basename(new_svg_file)  # Return new filename
            }
        except Exception as e:
            print(f"Reload failed: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def reload_from_file(self, filepath: str) -> Dict[str, Any]:
        """Reload ERD from dump file."""
        try:
            # Extract base filename without extension
            output_file = os.path.splitext(self.svg_file)[0]

            # Delegate to ERD service
            new_svg_file, success = self.erd_service.generate_from_file(
                filepath,
                output_file,
                self.generation_params
            )

            # Update source params with new filepath
            self.source_params['filepath'] = filepath

            print("ERD reloaded successfully!")
            return {
                "success": True,
                "message": "ERD reloaded successfully",
                "reload": True  # Signal browser to reload
            }
        except Exception as e:
            print(f"Reload failed: {e}")
            return {
                "success": False,
                "message": str(e)
            }
    
    def create_request_handler(self):
        """Create a custom request handler with access to server instance."""
        server_instance = self
        
        class ERDRequestHandler(http.server.SimpleHTTPRequestHandler):
            def __init__(self, *args, **kwargs):
                # Serve files from the directory containing the SVG
                svg_dir = os.path.dirname(os.path.abspath(server_instance.svg_file))
                super().__init__(*args, directory=svg_dir, **kwargs)
            
            def log_message(self, format, *args):
                """Suppress default logging or customize it."""
                # Only log non-GET requests or errors
                # Check if args[0] is a string (HTTP method) and not an HTTPStatus object
                if args and isinstance(args[0], str) and not args[0].startswith('GET'):
                    print(f"{self.address_string()} - {format % args}")
                elif args and not isinstance(args[0], str):
                    # This is an error log (args[0] is HTTPStatus), always print
                    print(f"{self.address_string()} - {format % args}")
            
            def end_headers(self):
                """Add CORS headers to allow cross-origin requests."""
                self.send_header('Access-Control-Allow-Origin', '*')
                self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
                self.send_header('Access-Control-Allow-Headers', 'Content-Type')
                super().end_headers()
            
            def do_OPTIONS(self):
                """Handle preflight requests."""
                self.send_response(200)
                self.end_headers()
            
            def do_POST(self):
                """Handle POST requests for API endpoints."""
                parsed_path = urlparse(self.path)
                
                # Read request body
                content_length = int(self.headers.get('Content-Length', 0))
                body = self.rfile.read(content_length).decode('utf-8') if content_length > 0 else '{}'
                
                try:
                    data = json.loads(body) if body else {}
                except json.JSONDecodeError:
                    self.send_error(400, "Invalid JSON")
                    return
                
                # Route API requests
                if parsed_path.path == '/api/test-db-connection':
                    self.handle_test_connection(data)
                elif parsed_path.path == '/api/reload-erd':
                    self.handle_reload_erd(data)
                elif parsed_path.path == '/api/apply_graphviz_settings':
                    self.handle_apply_graphviz_settings(data)
                elif parsed_path.path == '/api/apply_focused_settings':
                    self.handle_apply_focused_settings(data)
                elif parsed_path.path == '/api/generate_selected_svg':
                    self.handle_generate_selected_svg(data)
                elif parsed_path.path == '/api/generate_focused_erd':
                    self.handle_generate_focused_erd(data)
                elif parsed_path.path == '/api/optimize_layout':
                    self.handle_optimize_layout(data)
                elif parsed_path.path == '/api/shutdown':
                    self.handle_shutdown()
                elif parsed_path.path == '/api/list-databases':
                    self.handle_list_databases(data)
                else:
                    self.send_error(404, "Endpoint not found")
            
            def handle_test_connection(self, data):
                """Handle connection test request."""
                if server_instance.source_type != 'database':
                    self.send_json_response({
                        "success": False,
                        "message": "Connection testing only available for database sources"
                    }, 400)
                    return
                
                host = data.get('host')
                port = data.get('port')
                database = data.get('database')
                user = data.get('user')
                password = data.get('password', '')
                
                if not all([host, port, database, user]):
                    self.send_json_response({
                        "success": False,
                        "message": "Missing required parameters: host, port, database, user"
                    }, 400)
                    return
                
                result = server_instance.test_database_connection(host, port, database, user, password)
                status_code = 200 if result['success'] else 500
                self.send_json_response(result, status_code)
            
            def handle_reload_erd(self, data):
                """Handle ERD reload request."""
                if server_instance.source_type == 'database':
                    host = data.get('host')
                    port = data.get('port')
                    database = data.get('database')
                    user = data.get('user')
                    password = data.get('password', '')
                    
                    if not all([host, port, database, user]):
                        self.send_json_response({
                            "success": False,
                            "message": "Missing required parameters: host, port, database, user"
                        }, 400)
                        return
                    
                    result = server_instance.reload_from_database(host, port, database, user, password)
                elif server_instance.source_type == 'file':
                    filepath = data.get('filepath')
                    
                    if not filepath:
                        self.send_json_response({
                            "success": False,
                            "message": "Missing required parameter: filepath"
                        }, 400)
                        return
                    
                    result = server_instance.reload_from_file(filepath)
                else:
                    result = {
                        "success": False,
                        "message": "Unknown source type"
                    }
                
                status_code = 200 if result.get('success') else 500
                self.send_json_response(result, status_code)
            
            def handle_list_databases(self, data):
                """Handle list databases request."""
                host = data.get('host')
                port = data.get('port')
                user = data.get('user')
                password = data.get('password', '')

                if not all([host, port, user]):
                    self.send_json_response({
                        "success": False,
                        "message": "Missing required parameters: host, port, user"
                    }, 400)
                    return

                try:
                    databases = server_instance.database_service.list_databases(
                        host, port, user, password
                    )
                    self.send_json_response({
                        "success": True,
                        "databases": databases
                    })
                except Exception as e:
                    self.send_json_response({
                        "success": False,
                        "message": str(e)
                    }, 500)

            def handle_apply_graphviz_settings(self, data):
                """Handle apply Graphviz settings request - regenerate ERD with new settings."""
                graphviz_settings = data.get('graphviz_settings', {})

                if not graphviz_settings:
                    self.send_json_response({
                        "success": False,
                        "message": "Missing graphviz_settings parameter"
                    }, 400)
                    return

                # Update generation params with new Graphviz settings
                server_instance.generation_params.update(graphviz_settings)

                # Regenerate ERD based on source type
                if server_instance.source_type == 'database':
                    # Get database connection parameters from source_params
                    host = server_instance.source_params.get('host')
                    port = server_instance.source_params.get('port')
                    database = server_instance.source_params.get('database')
                    user = server_instance.source_params.get('user')
                    password = server_instance.cached_password or ''  # Allow empty password

                    if not all([host, port, database, user]):
                        self.send_json_response({
                            "success": False,
                            "message": "Missing database connection parameters in server configuration"
                        }, 400)
                        return

                    result = server_instance.reload_from_database(host, port, database, user, password)
                elif server_instance.source_type == 'file':
                    filepath = server_instance.source_params.get('filepath')

                    if not filepath:
                        self.send_json_response({
                            "success": False,
                            "message": "Missing filepath in server configuration"
                        }, 400)
                        return

                    result = server_instance.reload_from_file(filepath)
                else:
                    result = {
                        "success": False,
                        "message": "Unknown source type"
                    }

                status_code = 200 if result.get('success') else 500
                self.send_json_response(result, status_code)

            def handle_apply_focused_settings(self, data):
                """Handle apply focused settings request - regenerate focused ERD with new settings and same tables."""
                table_ids = data.get('table_ids', [])
                graphviz_settings = data.get('graphviz_settings', {})

                if not table_ids:
                    self.send_json_response({
                        "success": False,
                        "message": "No tables provided. Cannot regenerate focused ERD."
                    }, 400)
                    return

                try:
                    # Fetch the current schema
                    if server_instance.source_type == 'database':
                        host = server_instance.source_params.get('host')
                        port = server_instance.source_params.get('port')
                        database = server_instance.source_params.get('database')
                        user = server_instance.source_params.get('user')
                        password = server_instance.cached_password or ''

                        if not all([host, port, database, user]):
                            self.send_json_response({
                                "success": False,
                                "message": "Database connection parameters not available"
                            }, 400)
                            return

                        sql_dump = server_instance.fetch_schema_from_database(host, port, database, user, password)
                        view_columns_from_db = server_instance.fetch_view_columns(host, port, database, user, password)
                        input_source = f"{user}@{host}:{port}/{database}"
                    elif server_instance.source_type == 'file':
                        filepath = server_instance.source_params.get('filepath')

                        if not filepath or not os.path.exists(filepath):
                            self.send_json_response({
                                "success": False,
                                "message": "Source file not available"
                            }, 400)
                            return

                        with open(filepath, 'r', encoding='utf-8') as f:
                            sql_dump = f.read()
                        view_columns_from_db = {}
                        input_source = filepath
                    else:
                        self.send_json_response({
                            "success": False,
                            "message": "Unknown source type"
                        }, 400)
                        return

                    # Delegate to ERD service
                    svg_dir = os.path.dirname(os.path.abspath(server_instance.svg_file))
                    new_svg_file = server_instance.erd_service.generate_focused_erd(
                        sql_dump,
                        table_ids,
                        svg_dir,
                        input_source,
                        graphviz_settings,
                        view_columns_from_db
                    )

                    # Update server instance to use the new focused ERD
                    server_instance.svg_file = new_svg_file

                    # Return success with filename
                    self.send_json_response({
                        "success": True,
                        "new_file": os.path.basename(new_svg_file),
                        "message": f"Focused ERD regenerated with {len(table_ids)} tables"
                    })

                except Exception as e:
                    print(f"Apply focused settings failed: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_json_response({
                        "success": False,
                        "message": str(e)
                    }, 500)

            def handle_generate_selected_svg(self, data):
                """Handle generate selected SVG request - create standalone SVG from selected elements."""
                table_ids = data.get('table_ids', [])
                edge_ids = data.get('edge_ids', [])
                graphviz_settings = data.get('graphviz_settings', {})

                if not table_ids:
                    self.send_json_response({
                        "success": False,
                        "message": "No tables selected. Please select at least one table."
                    }, 400)
                    return

                try:
                    # Fetch the current schema
                    if server_instance.source_type == 'database':
                        host = server_instance.source_params.get('host')
                        port = server_instance.source_params.get('port')
                        database = server_instance.source_params.get('database')
                        user = server_instance.source_params.get('user')
                        password = server_instance.cached_password or ''

                        if not all([host, port, database, user]):
                            self.send_json_response({
                                "success": False,
                                "message": "Database connection parameters not available"
                            }, 400)
                            return

                        sql_dump = server_instance.fetch_schema_from_database(host, port, database, user, password)
                        view_columns_from_db = server_instance.fetch_view_columns(host, port, database, user, password)
                        input_source = f"{user}@{host}:{port}/{database}"
                    elif server_instance.source_type == 'file':
                        filepath = server_instance.source_params.get('filepath')

                        if not filepath or not os.path.exists(filepath):
                            self.send_json_response({
                                "success": False,
                                "message": "Source file not available"
                            }, 400)
                            return

                        with open(filepath, 'r', encoding='utf-8') as f:
                            sql_dump = f.read()
                        view_columns_from_db = {}
                        input_source = filepath
                    else:
                        self.send_json_response({
                            "success": False,
                            "message": "Unknown source type"
                        }, 400)
                        return

                    # Merge settings
                    settings = server_instance.generation_params.copy()
                    settings.update(graphviz_settings)

                    # Delegate to ERD service
                    svg_dir = os.path.dirname(server_instance.svg_file)
                    svg_content = server_instance.erd_service.generate_selected_svg(
                        sql_dump,
                        table_ids,
                        svg_dir,
                        input_source,
                        settings,
                        view_columns_from_db
                    )

                    # Send SVG content as response
                    self.send_response(200)
                    self.send_header('Content-Type', 'image/svg+xml')
                    self.send_header('Content-Disposition', 'attachment; filename="selected_erd.svg"')
                    self.end_headers()
                    self.wfile.write(svg_content.encode('utf-8'))

                except Exception as e:
                    print(f"Generate selected SVG failed: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_json_response({
                        "success": False,
                        "message": str(e)
                    }, 500)

            def handle_generate_focused_erd(self, data):
                """Handle generate focused ERD request - create interactive ERD from selected elements."""
                table_ids = data.get('table_ids', [])
                edge_ids = data.get('edge_ids', [])
                graphviz_settings = data.get('graphviz_settings', {})

                if not table_ids:
                    self.send_json_response({
                        "success": False,
                        "message": "No tables selected. Please select at least one table."
                    }, 400)
                    return

                try:
                    # Fetch the current schema
                    if server_instance.source_type == 'database':
                        host = server_instance.source_params.get('host')
                        port = server_instance.source_params.get('port')
                        database = server_instance.source_params.get('database')
                        user = server_instance.source_params.get('user')
                        password = server_instance.cached_password or ''

                        if not all([host, port, database, user]):
                            self.send_json_response({
                                "success": False,
                                "message": "Database connection parameters not available"
                            }, 400)
                            return

                        sql_dump = server_instance.fetch_schema_from_database(host, port, database, user, password)
                        view_columns_from_db = server_instance.fetch_view_columns(host, port, database, user, password)
                        input_source = f"{user}@{host}:{port}/{database}"
                    elif server_instance.source_type == 'file':
                        filepath = server_instance.source_params.get('filepath')

                        if not filepath or not os.path.exists(filepath):
                            self.send_json_response({
                                "success": False,
                                "message": "Source file not available"
                            }, 400)
                            return

                        with open(filepath, 'r', encoding='utf-8') as f:
                            sql_dump = f.read()
                        view_columns_from_db = {}
                        input_source = filepath
                    else:
                        self.send_json_response({
                            "success": False,
                            "message": "Unknown source type"
                        }, 400)
                        return

                    # Delegate to ERD service
                    svg_dir = os.path.dirname(os.path.abspath(server_instance.svg_file))
                    new_svg_file = server_instance.erd_service.generate_focused_erd(
                        sql_dump,
                        table_ids,
                        svg_dir,
                        input_source,
                        graphviz_settings,
                        view_columns_from_db
                    )

                    # Update server instance to use the new focused ERD
                    server_instance.svg_file = new_svg_file

                    # Return success with filename
                    self.send_json_response({
                        "success": True,
                        "new_file": os.path.basename(new_svg_file),
                        "message": f"Focused ERD generated with {len(table_ids)} tables"
                    })

                except Exception as e:
                    print(f"Generate focused ERD failed: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_json_response({
                        "success": False,
                        "message": str(e)
                    }, 500)

            def handle_optimize_layout(self, data):
                """Handle layout optimization request - analyze schema and recommend optimal settings."""
                # Get user's CURRENT settings from the request (their defaults)
                current_settings = data.get('current_settings', {})

                if not current_settings:
                    self.send_json_response({
                        "success": False,
                        "message": "Current settings not provided"
                    }, 400)
                    return

                try:
                    # Fetch the current schema
                    if server_instance.source_type == 'database':
                        host = server_instance.source_params.get('host')
                        port = server_instance.source_params.get('port')
                        database = server_instance.source_params.get('database')
                        user = server_instance.source_params.get('user')
                        password = server_instance.cached_password or ''

                        if not all([host, port, database, user]):
                            self.send_json_response({
                                "success": False,
                                "message": "Database connection parameters not available"
                            }, 400)
                            return

                        sql_dump = server_instance.fetch_schema_from_database(host, port, database, user, password)
                        view_columns_from_db = server_instance.fetch_view_columns(host, port, database, user, password)
                    elif server_instance.source_type == 'file':
                        filepath = server_instance.source_params.get('filepath')

                        if not filepath or not os.path.exists(filepath):
                            self.send_json_response({
                                "success": False,
                                "message": "Source file not available"
                            }, 400)
                            return

                        with open(filepath, 'r', encoding='utf-8') as f:
                            sql_dump = f.read()
                        view_columns_from_db = {}
                    else:
                        self.send_json_response({
                            "success": False,
                            "message": "Unknown source type"
                        }, 400)
                        return

                    # Parse the schema
                    tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)

                    # Enhance views with column information from database (if available)
                    for view_name, columns in view_columns_from_db.items():
                        if view_name in views:
                            views[view_name]['columns'] = columns
                        if view_name in tables:
                            tables[view_name]['columns'] = columns

                    # Optimize layout using AI + heuristics, starting from user's current settings
                    optimized_settings, explanation = optimize_layout(
                        current_settings, tables, foreign_keys, views, triggers, use_ai=True
                    )

                    self.send_json_response({
                        "success": True,
                        "optimized_settings": optimized_settings,
                        "explanation": explanation
                    })

                except Exception as e:
                    print(f"Layout optimization failed: {e}")
                    import traceback
                    traceback.print_exc()
                    self.send_json_response({
                        "success": False,
                        "message": str(e)
                    }, 500)

            def handle_shutdown(self):
                """Handle server shutdown request."""
                print("\nBrowser closed, shutting down server...")
                self.send_json_response({"success": True, "message": "Server shutting down"})
                
                # Schedule shutdown in a separate thread to allow response to be sent
                def shutdown_server():
                    time.sleep(0.5)  # Give time for response to be sent
                    if server_instance.server:
                        server_instance.server.shutdown()
                
                threading.Thread(target=shutdown_server, daemon=True).start()
            
            def send_json_response(self, data, status_code=200):
                """Send JSON response."""
                self.send_response(status_code)
                self.send_header('Content-Type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps(data).encode('utf-8'))
        
        return ERDRequestHandler
    
    def start(self, open_browser=True):
        """Start the server."""
        handler = self.create_request_handler()
        
        # Try to bind to port, increment if already in use
        max_attempts = 10
        for attempt in range(max_attempts):
            try:
                self.server = socketserver.TCPServer(("", self.port), handler)
                break
            except OSError as e:
                if attempt < max_attempts - 1:
                    self.port += 1
                else:
                    raise Exception(f"Could not bind to any port: {e}")
        
        svg_filename = os.path.basename(self.svg_file)
        url = f"http://localhost:{self.port}/{svg_filename}"
        
        print(f"\n{'='*60}")
        print(f"ERD Server started!")
        print(f"{'='*60}")
        print(f"Viewing: {svg_filename}")
        print(f"URL: {url}")
        print(f"Source: {self.source_type}")
        if self.source_type == 'database':
            print(f"Connection: {self.source_params.get('user')}@{self.source_params.get('host')}:{self.source_params.get('port')}/{self.source_params.get('database')}")
        else:
            print(f"File: {self.source_params.get('filepath')}")
        print(f"{'='*60}")
        print(f"Press Ctrl+C to stop the server")
        print(f"{'='*60}\n")
        
        if open_browser:
            # Wait a moment for server to be ready
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer stopped.")
            self.server.shutdown()
            self.server.server_close()


def start_server(svg_file: str, source_type: str, source_params: Dict[str, Any], 
                 generation_params: Dict[str, Any], open_browser: bool = True):
    """
    Start the ERD server.
    
    Args:
        svg_file: Path to SVG file
        source_type: 'database' or 'file'
        source_params: Source connection parameters
        generation_params: ERD generation parameters
        open_browser: Whether to open browser automatically
    """
    server = ERDServer(svg_file, source_type, source_params, generation_params)
    server.start(open_browser=open_browser)
