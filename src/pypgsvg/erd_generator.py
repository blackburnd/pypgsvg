import os
import logging
import json

from datetime import datetime
from graphviz import Digraph
from typing import Dict, List, Optional
from .utils import (
    should_exclude_table,
    is_standalone_table,
    get_contrasting_text_color,
    sanitize_label
)
from .colors import color_palette, saturate_color, desaturate_color
from .metadata_injector import inject_metadata_into_svg
import re
from .svg_utils import wrap_main_erd_content
from xml.etree import ElementTree as ET

log = logging.getLogger(__name__)


def generate_erd_with_graphviz(
    tables,
    foreign_keys,
    output_file,
    input_file_path=None,
    show_standalone=True,
    exclude_patterns=None,
    include_tables=None,
    packmode='array',
    rankdir='TB',
    esep='6',
    fontname='Sans-Serif',
    fontsize='24',
    node_fontsize='20',
    edge_fontsize='16',
    node_sep='0.5',
    rank_sep='1.2',
    node_style='filled',
    node_shape='rect',
    constraints={},
    triggers={},
    views={},
    functions={},
    settings={}
):
    """
    Generate an ERD using Graphviz with explicit side connections.

    Args:
        tables: Dictionary of table definitions
        foreign_keys: List of foreign key relationships
        output_file: Output file name (without extension)
        input_file_path: Path to input SQL file for metadata
        show_standalone: (tables with no FK relationships)
        exclude_patterns: List of patterns to exclude tables/views (e.g., ['vw_', 'tmp_'])
        include_tables: List of specific table names to include (whitelist mode, e.g., ['users', 'posts'])
        packmode: Graphviz 'packmode' (e.g., 'array', 'cluster', 'graph')
        rankdir: Graphviz 'rankdir' (e.g., 'TB', 'LR', 'BT', 'RL')
        esep: Graphviz 'esep' value
        fontname: Font name for graph, nodes, and edges
        fontsize: Font size for graph label
        node_fontsize: Font size for node labels
        edge_fontsize: Font size for edge labels
        node_style: Node style (e.g., 'filled')
        node_shape: Node shape (e.g., 'rect')
        node_sep: Node separation distance
        rank_sep: Rank separation distance
        constraints: Optional list of constraints discovered during parsing
        triggers: Optional list of triggers discovered during parsing
        views: Dictionary of view definitions extracted during parsing
        functions: Dictionary of function definitions extracted during parsing
        settings: Dictionary of configuration settings (SET statements) extracted during parsing

    """
    # Filter tables based on include/exclude patterns and standalone option
    filtered_tables = {}
    for table_name, columns in tables.items():
        # If include_tables is specified (whitelist mode), only include those tables
        if include_tables is not None and len(include_tables) > 0:
            if table_name not in include_tables:
                continue

        # Skip if matches exclusion patterns (only applies when not in whitelist mode)
        if should_exclude_table(table_name, exclude_patterns):
            continue

        # Skip standalone tables if option is disabled
        if not show_standalone and is_standalone_table(table_name, foreign_keys):
            continue

        filtered_tables[table_name] = columns

    filtered_foreign_keys = [
        fk for fk in foreign_keys
        if fk[0] in filtered_tables and fk[2] in filtered_tables
    ]

    # Calculate metadata
    total_tables = len(filtered_tables)
    total_columns = sum(len(cols['columns']) for cols in filtered_tables.values())
    total_foreign_keys = len(filtered_foreign_keys)
    total_edges = len(filtered_foreign_keys)

    # Source information (file or database connection)
    file_info = {}
    is_database_source = input_file_path and '@' in input_file_path and ':' in input_file_path
    
    if is_database_source:
        # Database connection format: user@host:port/database
        file_info['source_type'] = 'database'
        file_info['connection'] = input_file_path
        # Parse the connection string for display
        if '@' in input_file_path and '/' in input_file_path:
            user_host = input_file_path.split('@')[0]
            host_port_db = input_file_path.split('@')[1]
            if ':' in host_port_db and '/' in host_port_db:
                host = host_port_db.split(':')[0]
                port_db = host_port_db.split(':')[1]
                port = port_db.split('/')[0]
                database = port_db.split('/')[1]
                file_info['host'] = f"{host}:{port}"
                file_info['database'] = database
                file_info['user'] = user_host
    elif input_file_path and os.path.exists(input_file_path):
        file_info['source_type'] = 'file'
        file_info['filename'] = os.path.basename(input_file_path)
        file_info['filesize'] = f"{os.path.getsize(input_file_path):,} bytes"
    else:
        file_info['source_type'] = 'unknown'
        file_info['filename'] = "Unknown"
        file_info['filesize'] = "Unknown"

    file_info['generated'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    dot = Digraph(comment='Database ERD', format='svg')
    dot.attr(
        nodesep=node_sep,
        style=node_style,
        pack='true',
        packmode=packmode,
        rankdir=rankdir,
        esep=esep
    )

    dot.attr(
        'graph',
        fontname=fontname,
        fontsize=str(fontsize),
        ranksep=rank_sep,
        labeljust='l',
    )

    dot.attr(
        'node',
        shape=node_shape,
        style=node_style,
        fillcolor='white',
        fontname=fontname,
        fontsize=str(node_fontsize),
    )

    dot.attr(
        'edge',
        fontname=fontname,
        penwidth='3',
        fontsize=str(edge_fontsize),
    )

    # Use deterministic color assignment based on table name
    sorted_tables = sorted(filtered_tables.keys())
    table_colors = {table_name: color_palette[i % len(color_palette)] for i, table_name in enumerate(sorted_tables)}
    # --- Data for JS Highlighting ---
    graph_data = {
        "tables": {},
        "edges": {},
        "views": {},
        "functions": {},
        "settings": settings,  # Configuration settings from the database dump
        "defaultColor": "#cccccc",
        "highlightColor": "#ff0000",
        "includedTables": list(filtered_tables.keys()) if include_tables else None,  # Store which tables were included (for focused ERD)
    }

    # Populate table data
    for table_name in filtered_tables:
        safe_name = sanitize_label(table_name)
        table_data = filtered_tables[table_name]
        column_count = len(table_data.get('columns', [])) if isinstance(table_data, dict) else 0

        graph_data["tables"][safe_name] = {
            "originalName": table_name,  # Store original name for reverse lookup
            "defaultColor": table_colors[table_name],
            "highlightColor": saturate_color(table_colors[table_name], saturation_factor=4.0),
            "desaturatedColor": desaturate_color(table_colors[table_name], desaturation_factor=0.1),
            "triggers": triggers.get(table_name, []),
            "constraints": [],
            "edges": [],
            "columnCount": column_count,
            "sql": table_data.get('lines', ''),  # Include the CREATE TABLE SQL
            "type": table_data.get('type', 'table')  # Include the type (table or view)
        }

    # Populate edge data and update table data with connected edges
    for i, (ltbl, _, rtbl, _, _, triggers, constraints) in enumerate(filtered_foreign_keys):
        edge_id = f"edge-{i}"
        safe_ltbl = sanitize_label(ltbl)
        safe_rtbl = sanitize_label(rtbl)

        graph_data["edges"][edge_id] = {
            "tables": [safe_ltbl, safe_rtbl],
            "defaultColor": table_colors[ltbl],
            "highlightColor": saturate_color(table_colors[ltbl], saturation_factor=2.0),
            "desaturatedColor": desaturate_color(table_colors[ltbl], desaturation_factor=0.5),
            "triggers": triggers,
            "constraints": constraints,
        }

        if safe_ltbl in graph_data["tables"]:
            graph_data["tables"][safe_ltbl]["edges"].append(edge_id)
        if safe_rtbl in graph_data["tables"]:
            graph_data["tables"][safe_rtbl]["edges"].append(edge_id)

    # Populate views data
    for view_name, view_data in views.items():
        safe_name = sanitize_label(view_name)
        graph_data["views"][safe_name] = {
            "name": view_name,
            "definition": view_data.get('definition', ''),
            "type": "view"
        }

    # Populate functions data
    for function_name, function_data in functions.items():
        safe_name = sanitize_label(function_name)
        graph_data["functions"][safe_name] = {
            "name": function_name,
            "parameters": function_data.get('parameters', ''),
            "return_type": function_data.get('return_type', ''),
            "language": function_data.get('language', ''),
            "body": function_data.get('body', ''),
            "full_definition": function_data.get('full_definition', '')
        }

    for table_name, cols in filtered_tables.items():
        safe_table_name = sanitize_label(table_name)
        header_color = graph_data["tables"][safe_table_name]["defaultColor"]
        bg_color = graph_data["tables"][safe_table_name]["desaturatedColor"]
        text_color = get_contrasting_text_color(header_color)

        # --- Lightning bolt SVG icon ---
        # bolt_svg = '<svg width="16" height="16" viewBox="0 0 16 16" style="vertical-align:middle;"><polygon points="7,1 2,9 7,9 6,15 14,6 9,6 10,1" fill="#FFD700" stroke="#FFA500" stroke-width="1"/></svg>'

        # Get triggers for this table
        table_triggers = graph_data["tables"][safe_table_name].get("triggers") or []
        bolt_unicode = "&#9889;"  # Unicode lightning bolt ⚡
        trigger_icons = ""
        if table_triggers:
            for idx, trigger in enumerate(table_triggers):
                # Tooltip includes trigger name and full function text
                tooltip = f"{trigger.get('trigger_name', '')}: {trigger.get('full_line', '')}".replace('"', '&quot;').replace("'", "&#39;")
                trigger_icons += f'<FONT POINT-SIZE="16" class="trigger-icon" TITLE="{tooltip}">{bolt_unicode}</FONT> '

        label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        # Lightning bolts row (left aligned)
        if trigger_icons:
            label += f'<TR><TD class="trigger-icons" ALIGN="left">{trigger_icons}</TD></TR>'
        # Table header row (full width, saturated color)
        label += (
            f'<TR><TD ALIGN="center" BGCOLOR="{header_color}">'
            f'<FONT COLOR="{text_color}" POINT-SIZE="24">{table_name}</FONT></TD></TR>'
        )
        # Table background rows (desaturated color)
        for column in cols['columns']:
            # Build column display with icons
            column_icons = ""

            # Add primary key icon if this is a primary key
            if column.get('is_primary_key', False):
                pk_key = "&#128273;"  # Unicode key 🔑
                column_icons += (
                    f'<FONT COLOR="#FFD700" POINT-SIZE="16">'
                    f'{pk_key}</FONT> '
                )

            # Add foreign key icon if this is a foreign key
            if column.get('is_foreign_key', False):
                fk_key = "&#128273;"  # Unicode key 🔑
                column_icons += (
                    f'<FONT COLOR="#4169E1" POINT-SIZE="14">'
                    f'{fk_key}</FONT>'
                    f'<FONT COLOR="#4169E1" POINT-SIZE="10">FK</FONT> '
                )

            # Add column name and type
            column_info = f'{column["name"]} ({column["type"]})'
            column_display = column_icons + column_info

            label += (
                f'<TR><TD ALIGN="left" '
                f'PORT="{sanitize_label(column["name"])}">'
                f'<FONT POINT-SIZE="18">{column_display}</FONT></TD></TR>'
            )
        label += '</TABLE>>'

        dot.node(safe_table_name, label=label, id=safe_table_name,
                 shape=node_shape, style=node_style)

    # --- Update edge creation to use parallel splines with enhanced styling
    for i, (ltbl, col, rtbl, rcol, _line, 
            triggers, constraints) in enumerate(filtered_foreign_keys):
        edge_id = f"edge-{i}"
        safe_ltbl = sanitize_label(ltbl)
        safe_rtbl = sanitize_label(rtbl)
        graph_data["edges"][edge_id] = {
            "tables": [safe_ltbl, safe_rtbl],
            "defaultColor": table_colors[ltbl],
            "highlightColor": saturate_color(table_colors[ltbl], saturation_factor=2.0),
            "desaturatedColor": desaturate_color(table_colors[ltbl], desaturation_factor=0.5),
            "triggers": triggers,
            "constraints": constraints,
            "fkText": _line,
            "fromColumn": col,
            "toColumn": rcol,
        }

        # Use Graphviz's color="A:B" syntax for parallel splines
        color1 = table_colors[ltbl]
        color2 = table_colors[rtbl]
        
        # Determine arrow style based on relationship characteristics
        edge_attrs = {
            "id": f"edge-{i}",
            "color": f"{color1}:{color2}",
            "style": "solid",
            "penwidth": "3"
        }

        # Check for self-referencing relationships
        if ltbl == rtbl:
            edge_attrs["arrowhead"] = "dot"
            edge_attrs["style"] = "dashed"
        # Check for cascade constraints
        elif constraints and any("CASCADE" in str(c) for c in constraints):
            edge_attrs["arrowhead"] = "vee"
            edge_attrs["penwidth"] = "4"
        # Check for triggers on the relationship
        elif triggers:
            edge_attrs["arrowhead"] = "diamond"
            edge_attrs["style"] = "bold"
            edge_attrs["penwidth"] = "3.5"
        else:
            edge_attrs["arrowhead"] = "vee"

        dot.edge(
            f"{safe_ltbl}:{col}:e",
            f"{safe_rtbl}:{rcol}:w",
            **edge_attrs
        )

    # Render the graph and get SVG content directly
    try:
        # Use pipe() to get the SVG content directly without file I/O issues
        svg_bytes = dot.pipe(format='svg')
        svg_content = svg_bytes.decode('utf-8') if isinstance(svg_bytes, bytes) else svg_bytes
        actual_svg_path = output_file + ".svg"
        print(f"--- ERD generated successfully: {actual_svg_path} ---")
    except Exception as e:
        log.error(f"Error rendering graph with Graphviz: {e}")
        return

    # Process the SVG content
    svg_content = re.sub(r'<svg([^>]*)>', r'<svg\1 style="overflow:hidden;">', svg_content, count=1)
    # Remove Graphviz background rects/paths (double border fix) for full-size SVG
    svg_content = re.sub(r'<rect[^>]*fill="white"[^>]*/>', '', svg_content)
    svg_content = re.sub(r'<path[^>]*fill="white"[^>]*stroke="#E8A8A8"[^>]*/>', '', svg_content)
    # Additional cleanup for any other white-filled background paths
    svg_content = re.sub(r'<path[^>]*fill="white"[^>]*/>', '', svg_content)

    # Add class="node" to all <g> elements with id matching a table name, only if class is not present
    for table_name in filtered_tables:
        safe_table_name = sanitize_label(table_name)
        # Only add class if not part of miniature ERD
        svg_content = re.sub(
            rf'(<g\b(?![^>]*\bclass=)[^>]*\bid="{safe_table_name}"(?![^>]*\bid="mini-)[^>]*)(>)',
            r'\1 class="node"\2',
            svg_content
        )

    svg_content = re.sub(
        r'(<g\b(?![^>]*\bclass=)[^>]*\bid="edge-\d+"(?![^>]*\bid="mini-)[^>]*)(>)',
        r'\1 class="edge"\2',
        svg_content
    )
    graph_data_json = json.dumps(graph_data)
    graph_data_script = f'<script id="graph-data" type="application/json">{graph_data_json}</script>';
    svg_content = svg_content.replace('</svg>', f'{graph_data_script}\n</svg>')

    wrapped_svg = wrap_main_erd_content(svg_content)

    gen_min_erd = True
    svg_content = inject_metadata_into_svg(
        wrapped_svg, file_info, total_tables, total_columns,
        total_foreign_keys, total_edges, tables=filtered_tables,
        foreign_keys=filtered_foreign_keys, show_standalone=show_standalone,
        gen_min_erd=gen_min_erd, packmode=packmode, rankdir=rankdir,
        esep=esep, fontname=fontname, fontsize=fontsize,
        node_fontsize=node_fontsize, edge_fontsize=edge_fontsize,
        node_style=node_style, node_shape=node_shape,
        node_sep=node_sep, rank_sep=rank_sep, triggers=triggers,
        views=views, functions=functions, settings=settings,
    )

    with open(actual_svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
