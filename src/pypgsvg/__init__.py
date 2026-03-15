#!/usr/bin/env python3
"""
pypgsvg - PostgreSQL Database Schema to SVG ERD Generator.

This module generates Entity-Relationship Diagrams (ERDs) from PostgreSQL
database dump files using Graphviz to create SVG output.
"""
import argparse
import getpass
import os
import subprocess
import sys
import logging

from .db_parser import parse_sql_dump, extract_constraint_info
from .erd_generator import generate_erd_with_graphviz


log = logging.getLogger("pypgsvg")


def fetch_view_columns(host, port, database, user, password):
    """Fetch column metadata for views from a PostgreSQL database."""
    env = os.environ.copy()
    if password:
        env['PGPASSWORD'] = password

    query = (
        "SELECT c.table_name, c.column_name, c.data_type, c.ordinal_position "
        "FROM information_schema.columns c "
        "JOIN information_schema.views v ON c.table_name = v.table_name "
        "WHERE c.table_schema = 'public' "
        "ORDER BY c.table_name, c.ordinal_position;"
    )

    cmd = [
        'psql',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', database,
        '-t',
        '-A',
        '-F', '|',
        '-c', query,
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    except subprocess.CalledProcessError as e:
        print(f"Warning: Could not fetch view columns: {e.stderr}")
        return {}

    view_columns = {}
    try:
        for line in result.stdout.strip().split('\n'):
            if not line.strip():
                continue
            parts = line.split('|')
            if len(parts) < 4:
                continue

            view_name = parts[0].strip()
            column_name = parts[1].strip()
            data_type = parts[2].strip()

            if view_name not in view_columns:
                view_columns[view_name] = []
            view_columns[view_name].append({
                'name': column_name,
                'type': data_type,
                'is_primary_key': False,
                'is_foreign_key': False,
            })
    except Exception as e:
        print(f"Warning: Error parsing view columns: {e}")
        return {}

    return view_columns


def fetch_schema_from_database(host, port, database, user):
    """Fetch schema SQL and view column metadata from a PostgreSQL database."""
    password = getpass.getpass("Enter PostgreSQL password: ")
    env = os.environ.copy()
    if password:
        env['PGPASSWORD'] = password

    cmd = [
        'pg_dump',
        '-h', host,
        '-p', str(port),
        '-U', user,
        '-d', database,
        '-s',
        '--no-owner',
        '--no-privileges',
    ]

    try:
        result = subprocess.run(
            cmd,
            env=env,
            capture_output=True,
            text=True,
            check=True,
        )
    except FileNotFoundError:
        print("Error: pg_dump command not found. Please install PostgreSQL client tools.")
        sys.exit(1)
        return "", {}

    sql_dump = result.stdout
    view_columns = fetch_view_columns(host, port, database, user, password)
    return sql_dump, view_columns


def _unpack_parse_result(parse_result):
    """Support both legacy and extended parse_sql_dump return signatures."""
    if len(parse_result) == 4:
        tables, foreign_keys, triggers, errors = parse_result
        return tables, foreign_keys, triggers, errors, {}, {}, {}
    if len(parse_result) >= 7:
        return parse_result[:7]
    raise ValueError("parse_sql_dump returned an unexpected number of values")


def main():
    """
    Main function to parse command-line arguments and generate ERD.
    """
    parser = argparse.ArgumentParser(description='Generate ERD from PostgreSQL dump file')
    parser.add_argument('input_file', nargs='?', help='Path to the PostgreSQL dump file')
    parser.add_argument('-o', '--output', default='schema_erd', help='Output file name (without extension)')
    parser.add_argument('--show-standalone', default='true', help='Hide standalone tables')
    parser.add_argument('--view', action='store_true', help='Trigger the host to open the generated SVG in default app usually the browser')

    parser.add_argument('--host', help='PostgreSQL host')
    parser.add_argument('--port', help='PostgreSQL port')
    parser.add_argument('--database', help='PostgreSQL database name')
    parser.add_argument('--user', help='PostgreSQL user')
    parser.add_argument('--exclude', nargs='+', help='Exclude tables/views by prefix or pattern')
    parser.add_argument('--include', nargs='+', help='Include only the listed tables')

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

    output_file = args.output
    show_standalone = args.show_standalone != 'false'

    db_params = [args.host, args.port, args.database, args.user]
    any_db_params = any(db_params)
    all_db_params = all(db_params)

    if args.input_file and any_db_params:
        print("Cannot specify both input file and database connection parameters.")
        sys.exit(1)
        return

    if not args.input_file and not any_db_params:
        print("Must provide either an input dump file or database connection parameters.")
        sys.exit(1)
        return

    if any_db_params and not all_db_params:
        print("When using database connection, all four parameters must be provided: --host --port --database --user")
        sys.exit(1)
        return

    source_type = 'file'
    source_params = {}
    view_columns_from_db = {}

    try:
        if all_db_params:
            source_type = 'database'
            source_params = {
                'host': args.host,
                'port': args.port,
                'database': args.database,
                'user': args.user,
            }
            sql_dump, view_columns_from_db = fetch_schema_from_database(
                args.host, args.port, args.database, args.user
            )
            input_source = f"{args.user}@{args.host}:{args.port}/{args.database}"
        else:
            source_type = 'file'
            source_params = {'filepath': args.input_file}
            with open(args.input_file, 'r', encoding='utf-8') as f:
                sql_dump = f.read()
            input_source = args.input_file
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
        return
    except subprocess.CalledProcessError as e:
        print(f"Database schema fetch failed: {e}")
        sys.exit(1)
        return
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        sys.exit(1)
        return

    tables, foreign_keys, triggers, errors, views, functions, settings = _unpack_parse_result(parse_sql_dump(sql_dump))

    # Merge live view-column metadata when available (database mode)
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
                show_standalone=show_standalone,
                exclude_patterns=args.exclude,
                include_tables=args.include,
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
                from . import server
                generation_params = {
                    'show_standalone': show_standalone,
                    'exclude_patterns': args.exclude,
                    'include_tables': args.include,
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
                server.start_server(f"{output_file}.svg", source_type, source_params, generation_params)

        except Exception as e:
            print(f"--- ERROR during ERD generation ---")
            print(f"An unexpected error occurred: {e}")
            log.exception("Detailed traceback:")
            sys.exit(1)
            return


if __name__ == '__main__':
    # A basic logger setup for better error reporting if needed
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    main()
