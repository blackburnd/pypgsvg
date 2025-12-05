#!/usr/bin/env python3
"""
Web server for pypgsvg to handle interactive ERD viewing with reload capabilities.
"""
import http.server
import socketserver
import json
import os
import subprocess
import threading
import webbrowser
import time
import getpass
from urllib.parse import urlparse, parse_qs
from typing import Optional, Dict, Any

from .db_parser import parse_sql_dump, extract_constraint_info
from .erd_generator import generate_erd_with_graphviz
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
        self.cached_password = None  # Cache password for database connections
        
    def fetch_schema_from_database(self, host: str, port: str, database: str,
                                   user: str, password: str = None) -> str:
        """Fetch schema from PostgreSQL database using pg_dump."""
        if password is None and self.cached_password is not None:
            password = self.cached_password

        if password is None:
            password = ''  # Allow empty password for passwordless connections

        # Cache password for future use
        self.cached_password = password

        env = os.environ.copy()
        if password:  # Only set PGPASSWORD if password is not empty
            env['PGPASSWORD'] = password

        cmd = [
            'pg_dump',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-s',  # Schema only
            '--no-owner',
            '--no-privileges'
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise Exception(f"Database connection failed: {e.stderr}")
        except FileNotFoundError:
            raise Exception("pg_dump command not found. Please install PostgreSQL client tools.")

    def fetch_view_columns(self, host: str, port: str, database: str,
                          user: str, password: str) -> Dict[str, Any]:
        """
        Fetch column information for all views in the database.

        Returns:
            Dict mapping view names to their column lists
        """
        env = os.environ.copy()
        if password:  # Only set PGPASSWORD if password is not empty
            env['PGPASSWORD'] = password

        # Query to get view columns
        query = """
        SELECT
            c.table_name as view_name,
            c.column_name,
            c.data_type,
            c.ordinal_position
        FROM information_schema.columns c
        JOIN information_schema.views v ON c.table_name = v.table_name
        WHERE c.table_schema = 'public'
        ORDER BY c.table_name, c.ordinal_position;
        """

        cmd = [
            'psql',
            '-h', host,
            '-p', str(port),
            '-U', user,
            '-d', database,
            '-t',  # Tuples only
            '-A',  # Unaligned output
            '-F', '|',  # Field separator
            '-c', query
        ]

        try:
            result = subprocess.run(
                cmd,
                env=env,
                capture_output=True,
                text=True,
                check=True
            )

            # Parse the output
            view_columns = {}
            for line in result.stdout.strip().split('\n'):
                if line.strip():
                    parts = line.split('|')
                    if len(parts) >= 4:
                        view_name = parts[0].strip()
                        column_name = parts[1].strip()
                        data_type = parts[2].strip()

                        if view_name not in view_columns:
                            view_columns[view_name] = []

                        view_columns[view_name].append({
                            'name': column_name,
                            'type': data_type,
                            'is_primary_key': False,
                            'is_foreign_key': False
                        })

            return view_columns
        except subprocess.CalledProcessError as e:
            print(f"Warning: Could not fetch view columns: {e.stderr}")
            return {}
        except Exception as e:
            print(f"Warning: Error parsing view columns: {e}")
            return {}
    
    def test_database_connection(self, host: str, port: str, database: str, 
                                user: str, password: str) -> Dict[str, Any]:
        """Test database connection."""
        try:
            # Try to fetch schema (will fail if connection is bad)
            self.fetch_schema_from_database(host, port, database, user, password)
            return {
                "success": True,
                "message": "Connection successful"
            }
        except Exception as e:
            return {
                "success": False,
                "message": str(e)
            }
    
    def reload_from_database(self, host: str, port: str, database: str,
                           user: str, password: str) -> Dict[str, Any]:
        """Reload ERD from database connection."""
        try:
            print(f"Reloading schema from {database}@{host}:{port}...")
            sql_dump = self.fetch_schema_from_database(host, port, database, user, password)

            # Also fetch view column information
            view_columns_from_db = self.fetch_view_columns(host, port, database, user, password)

            # Parse and generate new ERD
            tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)

            # Enhance views with column information from database (if available)
            for view_name, columns in view_columns_from_db.items():
                if view_name in views:
                    views[view_name]['columns'] = columns
                if view_name in tables:
                    tables[view_name]['columns'] = columns

            constraints = extract_constraint_info(foreign_keys)

            if errors:
                print("Parsing errors encountered:")
                for error in errors:
                    print(f"  - {error}")
            
            # Generate new filename with database name
            svg_dir = os.path.dirname(os.path.abspath(self.svg_file))
            new_filename = f"{database}_erd"
            output_file = os.path.join(svg_dir, new_filename)
            new_svg_file = output_file + ".svg"
            input_source = f"{user}@{host}:{port}/{database}"

            generate_erd_with_graphviz(
                tables, foreign_keys, output_file,
                input_file_path=input_source,
                show_standalone=self.generation_params.get('show_standalone', True),
                exclude_patterns=self.generation_params.get('exclude_patterns'),
                include_tables=self.generation_params.get('include_tables'),
                packmode=self.generation_params.get('packmode', 'array'),
                rankdir=self.generation_params.get('rankdir', 'TB'),
                esep=self.generation_params.get('esep', '8'),
                fontname=self.generation_params.get('fontname', 'Arial'),
                fontsize=self.generation_params.get('fontsize', 18),
                node_fontsize=self.generation_params.get('node_fontsize', 14),
                edge_fontsize=self.generation_params.get('edge_fontsize', 12),
                node_style=self.generation_params.get('node_style', 'rounded,filled'),
                node_shape=self.generation_params.get('node_shape', 'rect'),
                node_sep=self.generation_params.get('node_sep', '0.5'),
                rank_sep=self.generation_params.get('rank_sep', '1.2'),
                constraints=constraints,
                triggers=triggers,
                views=views,
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
            print(f"Reloading schema from file: {filepath}...")
            
            if not os.path.exists(filepath):
                raise FileNotFoundError(f"File not found: {filepath}")
            
            with open(filepath, 'r', encoding='utf-8') as f:
                sql_dump = f.read()
            
            # Parse and generate new ERD
            tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)
            constraints = extract_constraint_info(foreign_keys)
            
            if errors:
                print("Parsing errors encountered:")
                for error in errors:
                    print(f"  - {error}")
            
            # Extract base filename without extension
            output_file = os.path.splitext(self.svg_file)[0]
            
            generate_erd_with_graphviz(
                tables, foreign_keys, output_file,
                input_file_path=filepath,
                show_standalone=self.generation_params.get('show_standalone', True),
                exclude_patterns=self.generation_params.get('exclude_patterns'),
                include_tables=self.generation_params.get('include_tables'),
                packmode=self.generation_params.get('packmode', 'array'),
                rankdir=self.generation_params.get('rankdir', 'TB'),
                esep=self.generation_params.get('esep', '8'),
                fontname=self.generation_params.get('fontname', 'Arial'),
                fontsize=self.generation_params.get('fontsize', 18),
                node_fontsize=self.generation_params.get('node_fontsize', 14),
                edge_fontsize=self.generation_params.get('edge_fontsize', 12),
                node_style=self.generation_params.get('node_style', 'rounded,filled'),
                node_shape=self.generation_params.get('node_shape', 'rect'),
                node_sep=self.generation_params.get('node_sep', '0.5'),
                rank_sep=self.generation_params.get('rank_sep', '1.2'),
                constraints=constraints,
                triggers=triggers,
                views=views,
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
                    # Query databases using psql command
                    env = os.environ.copy()
                    if password:
                        env['PGPASSWORD'] = password
                    
                    # Connect to 'postgres' database to query list of databases
                    cmd = [
                        'psql',
                        '-h', host,
                        '-p', str(port),
                        '-U', user,
                        '-d', 'postgres',  # Connect to default postgres database
                        '-t',  # Tuples only
                        '-A',  # Unaligned output
                        '-c', "SELECT datname FROM pg_database WHERE datistemplate = false ORDER BY datname;"
                    ]
                    
                    result = subprocess.run(
                        cmd,
                        env=env,
                        capture_output=True,
                        text=True,
                        check=True
                    )
                    
                    # Parse database list
                    databases = [db.strip() for db in result.stdout.strip().split('\n') if db.strip()]
                    
                    self.send_json_response({
                        "success": True,
                        "databases": databases
                    })
                except subprocess.CalledProcessError as e:
                    self.send_json_response({
                        "success": False,
                        "message": f"Failed to query databases: {e.stderr}"
                    }, 500)
                except FileNotFoundError:
                    self.send_json_response({
                        "success": False,
                        "message": "psql command not found. Please install PostgreSQL client tools."
                    }, 500)
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

                    # Parse the schema
                    tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)

                    # Enhance views with column information from database (if available)
                    for view_name, columns in view_columns_from_db.items():
                        if view_name in views:
                            views[view_name]['columns'] = columns
                        if view_name in tables:
                            tables[view_name]['columns'] = columns

                    constraints = extract_constraint_info(foreign_keys)

                    # Generate output filename
                    svg_dir = os.path.dirname(os.path.abspath(server_instance.svg_file))
                    focused_filename = 'focused_erd'
                    output_file = os.path.join(svg_dir, focused_filename)

                    # Apply graphviz settings from request
                    settings = graphviz_settings.copy()

                    # Generate interactive ERD (with JavaScript/interactivity)
                    # Use include_tables to filter to only the provided tables
                    generate_erd_with_graphviz(
                        tables,
                        foreign_keys,
                        output_file,
                        input_file_path=input_source,
                        show_standalone=False,  # Don't show standalone tables
                        exclude_patterns=None,
                        include_tables=table_ids,  # WHITELIST: Only include provided tables
                        packmode=settings.get('packmode', 'array'),
                        rankdir=settings.get('rankdir', 'TB'),
                        esep=settings.get('esep', '8'),
                        fontname=settings.get('fontname', 'Arial'),
                        fontsize=settings.get('fontsize', 18),
                        node_fontsize=settings.get('node_fontsize', 14),
                        edge_fontsize=settings.get('edge_fontsize', 12),
                        node_style=settings.get('node_style', 'rounded,filled'),
                        node_shape=settings.get('node_shape', 'rect'),
                        node_sep=settings.get('node_sep', '0.5'),
                        rank_sep=settings.get('rank_sep', '1.2'),
                        constraints=constraints,
                        triggers=triggers,
                        views=views,
                    )

                    # Update server instance to use the new focused ERD
                    new_svg_file = output_file + '.svg'
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
                        password = server_instance.cached_password or ''  # Allow empty password

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

                    # Parse the schema
                    tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)

                    # Enhance views with column information from database (if available)
                    for view_name, columns in view_columns_from_db.items():
                        if view_name in views:
                            views[view_name]['columns'] = columns
                        if view_name in tables:
                            tables[view_name]['columns'] = columns

                    constraints = extract_constraint_info(foreign_keys)

                    # Generate temporary SVG file with selected elements only
                    import tempfile
                    with tempfile.NamedTemporaryFile(mode='w', suffix='_selected', delete=False, dir=os.path.dirname(server_instance.svg_file)) as tmp_file:
                        output_file = tmp_file.name

                    # Remove the .svg extension if generate_erd_with_graphviz adds it
                    output_file_base = output_file.replace('.svg', '')

                    # Apply graphviz settings from request, with fallbacks to server defaults
                    settings = server_instance.generation_params.copy()
                    settings.update(graphviz_settings)

                    # Generate standalone SVG (without JavaScript/interactivity)
                    # Use include_tables to filter to only selected tables
                    generate_erd_with_graphviz(
                        tables,
                        foreign_keys,
                        output_file_base,
                        input_file_path=input_source,
                        show_standalone=True,  # Show all selected tables (standalone or not)
                        exclude_patterns=None,
                        include_tables=table_ids,  # WHITELIST: Only include selected tables
                        packmode=settings.get('packmode', 'array'),
                        rankdir=settings.get('rankdir', 'TB'),
                        esep=settings.get('esep', '8'),
                        fontname=settings.get('fontname', 'Arial'),
                        fontsize=settings.get('fontsize', 18),
                        node_fontsize=settings.get('node_fontsize', 14),
                        edge_fontsize=settings.get('edge_fontsize', 12),
                        node_style=settings.get('node_style', 'rounded,filled'),
                        node_shape=settings.get('node_shape', 'rect'),
                        node_sep=settings.get('node_sep', '0.5'),
                        rank_sep=settings.get('rank_sep', '1.2'),
                        constraints=constraints,
                        triggers=triggers,
                        views=views,
                    )

                    # Read the generated SVG file
                    svg_file_path = output_file_base + '.svg'
                    if os.path.exists(svg_file_path):
                        with open(svg_file_path, 'r', encoding='utf-8') as f:
                            svg_content = f.read()

                        # Clean up the temporary file
                        try:
                            os.remove(svg_file_path)
                        except:
                            pass

                        # Send SVG content as response
                        self.send_response(200)
                        self.send_header('Content-Type', 'image/svg+xml')
                        self.send_header('Content-Disposition', 'attachment; filename="selected_erd.svg"')
                        self.end_headers()
                        self.wfile.write(svg_content.encode('utf-8'))
                    else:
                        self.send_json_response({
                            "success": False,
                            "message": "Failed to generate SVG file"
                        }, 500)

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

                    # Parse the schema
                    tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)

                    # Enhance views with column information from database (if available)
                    for view_name, columns in view_columns_from_db.items():
                        if view_name in views:
                            views[view_name]['columns'] = columns
                        if view_name in tables:
                            tables[view_name]['columns'] = columns

                    constraints = extract_constraint_info(foreign_keys)

                    # Generate output filename
                    svg_dir = os.path.dirname(os.path.abspath(server_instance.svg_file))
                    focused_filename = 'focused_erd'
                    output_file = os.path.join(svg_dir, focused_filename)

                    # Apply graphviz settings from request
                    settings = graphviz_settings.copy()

                    # Generate interactive ERD (with JavaScript/interactivity)
                    # Use include_tables to filter to only selected tables
                    generate_erd_with_graphviz(
                        tables,
                        foreign_keys,
                        output_file,
                        input_file_path=input_source,
                        show_standalone=False,  # Don't show standalone tables
                        exclude_patterns=None,
                        include_tables=table_ids,  # WHITELIST: Only include selected tables
                        packmode=settings.get('packmode', 'array'),
                        rankdir=settings.get('rankdir', 'TB'),
                        esep=settings.get('esep', '8'),
                        fontname=settings.get('fontname', 'Arial'),
                        fontsize=settings.get('fontsize', 18),
                        node_fontsize=settings.get('node_fontsize', 14),
                        edge_fontsize=settings.get('edge_fontsize', 12),
                        node_style=settings.get('node_style', 'rounded,filled'),
                        node_shape=settings.get('node_shape', 'rect'),
                        node_sep=settings.get('node_sep', '0.5'),
                        rank_sep=settings.get('rank_sep', '1.2'),
                        constraints=constraints,
                        triggers=triggers,
                        views=views,
                    )

                    # Update server instance to use the new focused ERD
                    new_svg_file = output_file + '.svg'
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
                    tables, foreign_keys, triggers, errors, views = parse_sql_dump(sql_dump)

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
                print("\n🔌 Browser closed, shutting down server...")
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
        print(f"🚀 ERD Server started!")
        print(f"{'='*60}")
        print(f"📊 Viewing: {svg_filename}")
        print(f"🌐 URL: {url}")
        print(f"⚙️  Source: {self.source_type}")
        if self.source_type == 'database':
            print(f"🔌 Connection: {self.source_params.get('user')}@{self.source_params.get('host')}:{self.source_params.get('port')}/{self.source_params.get('database')}")
        else:
            print(f"📁 File: {self.source_params.get('filepath')}")
        print(f"{'='*60}")
        print(f"Press Ctrl+C to stop the server")
        print(f"{'='*60}\n")
        
        if open_browser:
            # Wait a moment for server to be ready
            threading.Timer(0.5, lambda: webbrowser.open(url)).start()
        
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\n\n🛑 Server stopped.")
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
