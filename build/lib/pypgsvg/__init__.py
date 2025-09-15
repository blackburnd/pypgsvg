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

from .db_parser import parse_sql_dump, extract_constraint_info
from .erd_generator import generate_erd_with_graphviz


log = logging.getLogger("pypgsvg")


def main():
    """
    Main function to parse command-line arguments and generate ERD.
    """
    parser = argparse.ArgumentParser(description='Generate ERD from PostgreSQL dump file')
    parser.add_argument('input_file', help='Path to the PostgreSQL dump file')
    parser.add_argument('-o', '--output', default='schema_erd', help='Output file name (without extension)')
    parser.add_argument('--show-standalone', default='true', help='Hide standalone tables')
    parser.add_argument('--view', action='store_true', help='Open the generated SVG in a browser')
    parser.add_argument('--saturate', type=float, default=1.8, help='Saturation factor for table colors')
    parser.add_argument('--brightness', type=float, default=1.0, help='Brightness factor for table colors')

    # New Graphviz/ERD parameters
    parser.add_argument('--packmode', default='array', choices=['array', 'cluster', 'graph'], help='Graphviz packmode (array, cluster, graph)')
    parser.add_argument('--rankdir', default='TB', choices=['TB', 'LR', 'BT', 'RL'], help='Graphviz rankdir (TB, LR, BT, RL)')
    parser.add_argument('--esep', default='8', help='Graphviz esep value')
    parser.add_argument('--fontname', default='Arial', help='Font name for graph, nodes, and edges')
    parser.add_argument('--fontsize', type=int, default=18, help='Font size for graph label')
    parser.add_argument('--node-fontsize', type=int, default=14, help='Font size for node labels')
    parser.add_argument('--edge-fontsize', type=int, default=12, help='Font size for edge labels')
    parser.add_argument('--node-style', default='rounded,filled', help='Node style (e.g., "filled", "rounded,filled")')
    parser.add_argument('--node-shape', default='rect', help='Node shape (e.g., "rect", "ellipse")')
    parser.add_argument('--node-sep', default='0.5', help='Node separation distance')
    parser.add_argument('--rank-sep', default='1.2', help='Rank separation distance')

    args = parser.parse_args()

    output_file = args.output

    try:
        with open(args.input_file, 'r', encoding='utf-8') as f:
            sql_dump = f.read()
    except FileNotFoundError:
        print(f"Error: Input file not found: {args.input_file}")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred while reading the file: {e}")
        sys.exit(1)

    tables, foreign_keys, triggers, errors = parse_sql_dump(sql_dump)
    constraints = extract_constraint_info(foreign_keys)

    if errors:
        print("--- PARSING ERRORS ---")
        for error in errors:
            print(error)
    else:
        try:
            generate_erd_with_graphviz(
                tables, foreign_keys, output_file,
                input_file_path=args.input_file,
                show_standalone=args.show_standalone!='false',
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
            )

            print(f"Successfully generated ERD: {output_file}.svg")

            if args.view:
                path = os.path.abspath(f"{output_file}.svg")
                webbrowser.open(f"file://{path}")

        except Exception as e:
            print(f"--- ERROR during ERD generation ---")
            print(f"An unexpected error occurred: {e}")
            log.exception("Detailed traceback:")
            sys.exit(1)


if __name__ == '__main__':
    # A basic logger setup for better error reporting if needed
    logging.basicConfig(level=logging.DEBUG, format='%(levelname)s: %(message)s')
    main()
