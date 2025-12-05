#!/usr/bin/env python3
"""
pypgsvg - PostgreSQL Database Schema to SVG ERD Generator.

This module generates Entity-Relationship Diagrams (ERDs) from PostgreSQL
database dump files using Graphviz to create SVG output.
"""
import argparse
import os
import sys
import webbrowser
import logging
import subprocess
import getpass

from .db_parser import parse_sql_dump, extract_constraint_info
from .erd_generator import generate_erd_with_graphviz


log = logging.getLogger("pypgsvg")


def fetch_schema_from_database(host, port, database, user):
    """
    Fetch schema from a PostgreSQL database using pg_dump.
    Also queries the database to get view column information.

    Args:
        host: Database host
        port: Database port
        database: Database name
        user: Database user

    Returns:
        Tuple of (SQL dump string, view columns dict)

    Raises:
        Exception if pg_dump fails
    """
    # Prompt for password
    password = getpass.getpass(f"Password for {user}@{host}:{port}/{database}: ")

    # Set environment variable for password
    env = os.environ.copy()
    env['PGPASSWORD'] = password

    # Build pg_dump command
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
        # Run pg_dump
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True
        )
        sql_dump = result.stdout

        # Also fetch view column information using psql
        view_columns = fetch_view_columns(host, port, database, user, password)

        return sql_dump, view_columns
    except subprocess.CalledProcessError as e:
        print(f"Error connecting to database: {e.stderr}")
        raise
    except FileNotFoundError:
        print("Error: pg_dump command not found. Please ensure PostgreSQL client tools are installed.")
        sys.exit(1)


def fetch_view_columns(host, port, database, user, password):
    """
    Fetch column information for all views in the database.

    Returns:
        Dict mapping view names to their column lists
    """
    env = os.environ.copy()
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


def main():
    """
    Main function to parse command-line arguments and generate ERD.
    """
    parser = argparse.ArgumentParser(description='Generate ERD from PostgreSQL dump file or database connection')
    parser.add_argument('input_file', nargs='?', default=None, help='Path to the PostgreSQL dump file')
    parser.add_argument('-o', '--output', default='schema_erd', help='Output file name (without extension)')
    parser.add_argument('--show-standalone', default='true', help='Hide standalone tables')
    parser.add_argument('--view', action='store_true', help='Trigger the host to open the generated SVG in default app usually the browser')
    parser.add_argument('--exclude', nargs='*', default=[], help='Space-separated patterns to exclude tables/views (e.g., --exclude vw_ tmp_)')
    parser.add_argument('--include', nargs='*', default=[], help='Space-separated table names to include (whitelist mode, e.g., --include users posts)')

    # Database connection arguments
    parser.add_argument('--host', help='Database host')
    parser.add_argument('--port', help='Database port')
    parser.add_argument('--database', help='Database name')
    parser.add_argument('--user', help='Database user')

    parser.add_argument('--packmode', default='array', choices=['array', 'cluster', 'graph'], help='Graphviz packmode (array, cluster, graph)')
    parser.add_argument('--rankdir', default='TB', choices=['TB', 'LR', 'BT', 'RL'], help='Graphviz rankdir (TB, LR, BT, RL)')
    parser.add_argument('--esep', default='8', help='Graphviz esep value')
    parser.add_argument('--node-sep', default='0.5', help='Node separation distance')
    parser.add_argument('--rank-sep', default='1.2', help='Rank separation distance')

    parser.add_argument('--node-fontsize', type=int, default=14, help='Font size for node labels')
    parser.add_argument('--edge-fontsize', type=int, default=12, help='Font size for edge labels')
    parser.add_argument('--node-style', default='rounded,filled', help='Node style (e.g., "filled", "rounded,filled")')
    parser.add_argument('--node-shape', default='rect', help='Node shape (e.g., "rect", "ellipse")')
    parser.add_argument('--fontname', default='Arial', help='Font name for graph, nodes, and edges')
    parser.add_argument('--fontsize', type=int, default=18, help='Font size for graph label')


    # New Graphviz/ERD parameters
    parser.add_argument('--saturate', type=float, default=1.8, help='Saturation factor for table colors')
    parser.add_argument('--brightness', type=float, default=1.0, help='Brightness factor for table colors')


    args = parser.parse_args()

    # Validation: Check for mutually exclusive input modes
    db_params = [args.host, args.port, args.database, args.user]
    db_params_provided = [p for p in db_params if p is not None]

    # Error if dump file and database connection parameters are both provided
    if args.input_file and db_params_provided:
        print("Error: Cannot specify both input file and database connection parameters.")
        print("Use either a dump file OR database connection (--host, --port, --database, --user).")
        sys.exit(1)

    # Error if some but not all database parameters are provided
    if db_params_provided and len(db_params_provided) != 4:
        print("Error: When using database connection, all four parameters must be provided:")
        print("  --host, --port, --database, --user")
        print(f"Currently provided: {', '.join(['--' + n for n, p in zip(['host', 'port', 'database', 'user'], db_params) if p is not None])}")
        sys.exit(1)

    # Error if neither input mode is provided
    if not args.input_file and not db_params_provided:
        print("Error: Must provide either:")
        print("  1. A dump file: pypgsvg <dump_file>")
        print("  2. Database connection: pypgsvg --host <host> --port <port> --database <db> --user <user>")
        sys.exit(1)

    output_file = args.output

    # Get SQL dump from either file or database connection
    sql_dump = None
    input_source = None
    view_columns_from_db = {}

    if args.input_file:
        # Read from dump file
        try:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                sql_dump = f.read()
            input_source = args.input_file
        except FileNotFoundError:
            print(f"Error: Input file not found: {args.input_file}")
            sys.exit(1)
        except Exception as e:
            print(f"An error occurred while reading the file: {e}")
            sys.exit(1)
    else:
        # Fetch from database connection
        try:
            print(f"Connecting to database {args.database} at {args.host}:{args.port}...")
            sql_dump, view_columns_from_db = fetch_schema_from_database(args.host, args.port, args.database, args.user)
            input_source = f"{args.user}@{args.host}:{args.port}/{args.database}"
            print("Schema fetched successfully.")
        except Exception as e:
            print(f"Failed to fetch schema from database: {e}")
            sys.exit(1)

    # Parse the SQL dump
    tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)

    # Enhance views with column information from database (if available)
    for view_name, columns in view_columns_from_db.items():
        if view_name in views:
            views[view_name]['columns'] = columns
        if view_name in tables:
            tables[view_name]['columns'] = columns

    constraints = extract_constraint_info(foreign_keys)

    if errors:
        print("--- PARSING ERRORS ---")
        for error in errors:
            print(error)
    else:
        try:
            generate_erd_with_graphviz(
                tables, foreign_keys, output_file,
                input_file_path=input_source,
                show_standalone=args.show_standalone!='false',
                exclude_patterns=args.exclude if args.exclude else None,
                include_tables=args.include if args.include else None,
                packmode=args.packmode,
                rankdir=args.rankdir,
                esep=args.esep,
                fontname=args.fontname,
                fontsize=args.fontsize,
                node_fontsize=args.node_fontsize,
                edge_fontsize=args.edge_fontsize,
                node_style=args.node_style,
                node_shape=args.node_shape,
                node_sep=args.node_sep,
                rank_sep=args.rank_sep,
                constraints=constraints,
                triggers=triggers,
                views=views,
                functions=functions,
                settings=settings,
            )

            print(f"Successfully generated ERD: {output_file}.svg")

            if args.view:
                # Start server for interactive viewing with reload capabilities
                from .server import start_server
                
                svg_file = os.path.abspath(f"{output_file}.svg")
                
                # Determine source type and parameters
                if db_params_provided:
                    source_type = 'database'
                    source_params = {
                        'host': args.host,
                        'port': args.port,
                        'database': args.database,
                        'user': args.user
                    }
                else:
                    source_type = 'file'
                    source_params = {
                        'filepath': os.path.abspath(args.input_file)
                    }
                
                # Collect generation parameters
                generation_params = {
                    'show_standalone': args.show_standalone != 'false',
                    'exclude_patterns': args.exclude if args.exclude else None,
                    'include_tables': args.include if args.include else None,
                    'packmode': args.packmode,
                    'rankdir': args.rankdir,
                    'esep': args.esep,
                    'fontname': args.fontname,
                    'fontsize': args.fontsize,
                    'node_fontsize': args.node_fontsize,
                    'edge_fontsize': args.edge_fontsize,
                    'node_style': args.node_style,
                    'node_shape': args.node_shape,
                    'node_sep': args.node_sep,
                    'rank_sep': args.rank_sep,
                }
                
                start_server(svg_file, source_type, source_params, generation_params)

        except Exception as e:
            print(f"--- ERROR during ERD generation ---")
            print(f"An unexpected error occurred: {e}")
            log.exception("Detailed traceback:")
            sys.exit(1)


if __name__ == '__main__':
    # A basic logger setup for better error reporting if needed
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    main()
