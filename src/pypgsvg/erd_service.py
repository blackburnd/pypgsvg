#!/usr/bin/env python3
"""
ERD service for pypgsvg - handles ERD generation operations.

Extracted from server.py for better testability and separation of concerns.
"""
import os
import tempfile
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path

from .db_parser import parse_sql_dump, extract_constraint_info
from .erd_generator import generate_erd_with_graphviz
from .database_service import DatabaseService


class ERDService:
    """Service class for ERD generation operations."""

    def __init__(self, database_service: DatabaseService):
        """
        Initialize ERD service.

        Args:
            database_service: DatabaseService instance for database operations
        """
        self.database_service = database_service

    def generate_from_database(
        self,
        host: str,
        port: str,
        database: str,
        user: str,
        password: str,
        output_file: str,
        generation_params: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Generate ERD from database connection.

        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
            output_file: Path for output SVG file (without extension)
            generation_params: Parameters for ERD generation

        Returns:
            Tuple of (svg_file_path, success)

        Raises:
            Exception: If schema fetch or generation fails
        """
        print(f"Generating ERD from {database}@{host}:{port}...")
        sql_dump = self.database_service.fetch_schema(host, port, database, user, password)

        # Also fetch view column information
        view_columns_from_db = self.database_service.fetch_view_columns(
            host, port, database, user, password
        )

        # Parse and generate new ERD
        tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)

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

        input_source = f"{user}@{host}:{port}/{database}"

        generate_erd_with_graphviz(
            tables, foreign_keys, output_file,
            input_file_path=input_source,
            show_standalone=generation_params.get('show_standalone', True),
            exclude_patterns=generation_params.get('exclude_patterns'),
            include_tables=generation_params.get('include_tables'),
            packmode=generation_params.get('packmode', 'array'),
            rankdir=generation_params.get('rankdir', 'TB'),
            esep=generation_params.get('esep', '8'),
            fontname=generation_params.get('fontname', 'Arial'),
            fontsize=generation_params.get('fontsize', 18),
            node_fontsize=generation_params.get('node_fontsize', 14),
            edge_fontsize=generation_params.get('edge_fontsize', 12),
            node_style=generation_params.get('node_style', 'rounded,filled'),
            node_shape=generation_params.get('node_shape', 'rect'),
            node_sep=generation_params.get('node_sep', '0.5'),
            rank_sep=generation_params.get('rank_sep', '1.2'),
            constraints=constraints,
            triggers=triggers,
            views=views,
            functions=functions,
            settings=settings,
        )

        svg_file = output_file + ".svg"
        print(f"ERD generated successfully! File: {svg_file}")
        return svg_file, True

    def generate_from_file(
        self,
        filepath: str,
        output_file: str,
        generation_params: Dict[str, Any]
    ) -> Tuple[str, bool]:
        """
        Generate ERD from SQL dump file.

        Args:
            filepath: Path to SQL dump file
            output_file: Path for output SVG file (without extension)
            generation_params: Parameters for ERD generation

        Returns:
            Tuple of (svg_file_path, success)

        Raises:
            FileNotFoundError: If input file doesn't exist
            Exception: If parsing or generation fails
        """
        print(f"Generating ERD from file: {filepath}...")

        if not os.path.exists(filepath):
            raise FileNotFoundError(f"File not found: {filepath}")

        with open(filepath, 'r', encoding='utf-8') as f:
            sql_dump = f.read()

        # Parse and generate new ERD
        tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)
        constraints = extract_constraint_info(foreign_keys)

        if errors:
            print("Parsing errors encountered:")
            for error in errors:
                print(f"  - {error}")

        generate_erd_with_graphviz(
            tables, foreign_keys, output_file,
            input_file_path=filepath,
            show_standalone=generation_params.get('show_standalone', True),
            exclude_patterns=generation_params.get('exclude_patterns'),
            include_tables=generation_params.get('include_tables'),
            packmode=generation_params.get('packmode', 'array'),
            rankdir=generation_params.get('rankdir', 'TB'),
            esep=generation_params.get('esep', '8'),
            fontname=generation_params.get('fontname', 'Arial'),
            fontsize=generation_params.get('fontsize', 18),
            node_fontsize=generation_params.get('node_fontsize', 14),
            edge_fontsize=generation_params.get('edge_fontsize', 12),
            node_style=generation_params.get('node_style', 'rounded,filled'),
            node_shape=generation_params.get('node_shape', 'rect'),
            node_sep=generation_params.get('node_sep', '0.5'),
            rank_sep=generation_params.get('rank_sep', '1.2'),
            constraints=constraints,
            triggers=triggers,
            views=views,
            functions=functions,
            settings=settings,
        )

        svg_file = output_file + ".svg"
        print("ERD generated successfully!")
        return svg_file, True

    def generate_focused_erd(
        self,
        sql_dump: str,
        table_ids: List[str],
        output_dir: str,
        input_source: str,
        graphviz_settings: Dict[str, Any],
        view_columns_from_db: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> str:
        """
        Generate focused ERD with only selected tables (interactive).

        Args:
            sql_dump: SQL schema dump
            table_ids: List of table names to include
            output_dir: Directory for output file
            input_source: Source description for metadata
            graphviz_settings: Graphviz layout settings
            view_columns_from_db: Optional view column data from database

        Returns:
            Path to generated SVG file

        Raises:
            Exception: If parsing or generation fails
        """
        # Parse the schema
        tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)

        # Enhance views with column information from database (if available)
        if view_columns_from_db:
            for view_name, columns in view_columns_from_db.items():
                if view_name in views:
                    views[view_name]['columns'] = columns
                if view_name in tables:
                    tables[view_name]['columns'] = columns

        constraints = extract_constraint_info(foreign_keys)

        # Generate output filename
        focused_filename = 'focused_erd'
        output_file = os.path.join(output_dir, focused_filename)

        # Generate interactive ERD (with JavaScript/interactivity)
        # Use include_tables to filter to only provided tables
        generate_erd_with_graphviz(
            tables,
            foreign_keys,
            output_file,
            input_file_path=input_source,
            show_standalone=False,  # Don't show standalone tables
            exclude_patterns=None,
            include_tables=table_ids,  # WHITELIST: Only include provided tables
            packmode=graphviz_settings.get('packmode', 'array'),
            rankdir=graphviz_settings.get('rankdir', 'TB'),
            esep=graphviz_settings.get('esep', '8'),
            fontname=graphviz_settings.get('fontname', 'Arial'),
            fontsize=graphviz_settings.get('fontsize', 18),
            node_fontsize=graphviz_settings.get('node_fontsize', 14),
            edge_fontsize=graphviz_settings.get('edge_fontsize', 12),
            node_style=graphviz_settings.get('node_style', 'rounded,filled'),
            node_shape=graphviz_settings.get('node_shape', 'rect'),
            node_sep=graphviz_settings.get('node_sep', '0.5'),
            rank_sep=graphviz_settings.get('rank_sep', '1.2'),
            constraints=constraints,
            triggers=triggers,
            views=views,
            functions=functions,
            settings=graphviz_settings,
        )

        return output_file + '.svg'

    def generate_selected_svg(
        self,
        sql_dump: str,
        table_ids: List[str],
        output_dir: str,
        input_source: str,
        graphviz_settings: Dict[str, Any],
        view_columns_from_db: Optional[Dict[str, List[Dict[str, Any]]]] = None
    ) -> str:
        """
        Generate standalone SVG with only selected tables (no JavaScript).

        Args:
            sql_dump: SQL schema dump
            table_ids: List of table names to include
            output_dir: Directory for output file
            input_source: Source description for metadata
            graphviz_settings: Graphviz layout settings
            view_columns_from_db: Optional view column data from database

        Returns:
            SVG content as string

        Raises:
            Exception: If parsing or generation fails
        """
        # Parse the schema
        tables, foreign_keys, triggers, errors, views, functions, settings = parse_sql_dump(sql_dump)

        # Enhance views with column information from database (if available)
        if view_columns_from_db:
            for view_name, columns in view_columns_from_db.items():
                if view_name in views:
                    views[view_name]['columns'] = columns
                if view_name in tables:
                    tables[view_name]['columns'] = columns

        constraints = extract_constraint_info(foreign_keys)

        # Generate temporary SVG file with selected elements only
        with tempfile.NamedTemporaryFile(
            mode='w',
            suffix='_selected',
            delete=False,
            dir=output_dir
        ) as tmp_file:
            output_file = tmp_file.name

        # Remove the .svg extension if generate_erd_with_graphviz adds it
        output_file_base = output_file.replace('.svg', '')

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
            packmode=graphviz_settings.get('packmode', 'array'),
            rankdir=graphviz_settings.get('rankdir', 'TB'),
            esep=graphviz_settings.get('esep', '8'),
            fontname=graphviz_settings.get('fontname', 'Arial'),
            fontsize=graphviz_settings.get('fontsize', 18),
            node_fontsize=graphviz_settings.get('node_fontsize', 14),
            edge_fontsize=graphviz_settings.get('edge_fontsize', 12),
            node_style=graphviz_settings.get('node_style', 'rounded,filled'),
            node_shape=graphviz_settings.get('node_shape', 'rect'),
            node_sep=graphviz_settings.get('node_sep', '0.5'),
            rank_sep=graphviz_settings.get('rank_sep', '1.2'),
            constraints=constraints,
            triggers=triggers,
            views=views,
            functions=functions,
            settings=graphviz_settings,
        )

        # Read the generated SVG file
        svg_file_path = output_file_base + '.svg'
        if os.path.exists(svg_file_path):
            with open(svg_file_path, 'r', encoding='utf-8') as f:
                svg_content = f.read()

            # Clean up the temporary file
            try:
                os.remove(svg_file_path)
            except Exception:
                pass

            return svg_content
        else:
            raise Exception("Failed to generate SVG file")
