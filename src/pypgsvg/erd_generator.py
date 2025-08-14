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
    triggers={}
):
    """
    Generate an ERD using Graphviz with explicit side connections.

    Args:
        tables: Dictionary of table definitions
        foreign_keys: List of foreign key relationships
        output_file: Output file name (without extension)
        input_file_path: Path to input SQL file for metadata
        show_standalone: (tables with no FK relationships)
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

    """
    # Filter tables based on exclusion patterns and standalone option
    filtered_tables = {}
    for table_name, columns in tables.items():
        # Skip if matches exclusion patterns
        if should_exclude_table(table_name):
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

    # File information
    file_info = {}
    if input_file_path and os.path.exists(input_file_path):
        file_info['filename'] = os.path.basename(input_file_path)
        file_info['filesize'] = f"{os.path.getsize(input_file_path):,} bytes"
    else:
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
        "defaultColor": "#cccccc",
        "highlightColor": "#ff0000",
    }

    # Populate table data
    for table_name in filtered_tables:
        safe_name = sanitize_label(table_name)
        graph_data["tables"][safe_name] = {
            "defaultColor": table_colors[table_name],
            "highlightColor": saturate_color(table_colors[table_name], saturation_factor=4.0),
            "desaturatedColor": desaturate_color(table_colors[table_name], desaturation_factor=0.1),
            "triggers": triggers.get(table_name, []),  # <-- Add this line
            "constraints": [],
            "edges": []
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

    for table_name, cols in filtered_tables.items():
        safe_table_name = sanitize_label(table_name)
        header_color = graph_data["tables"][safe_table_name]["defaultColor"]
        bg_color = graph_data["tables"][safe_table_name]["desaturatedColor"]
        text_color = get_contrasting_text_color(header_color)

        # --- Lightning bolt SVG icon ---
        # bolt_svg = '<svg width="16" height="16" viewBox="0 0 16 16" style="vertical-align:middle;"><polygon points="7,1 2,9 7,9 6,15 14,6 9,6 10,1" fill="#FFD700" stroke="#FFA500" stroke-width="1"/></svg>'

        # Get triggers for this table
        triggers = graph_data["tables"][safe_table_name].get("triggers", [])
        bolt_unicode = "&#9889;"  # Unicode lightning bolt ⚡
        trigger_icons = ""
        for idx, trigger in enumerate(triggers):
            trigger_icons += f'<FONT POINT-SIZE="16" class="trigger-icon" TITLE="{trigger.get("trigger_name", "")}">{bolt_unicode}</FONT> '

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
            label += (
                f'<TR><TD ALIGN="left" PORT="{sanitize_label(column["name"])}"><FONT POINT-SIZE="18">{column["name"]} ({column["type"]})</FONT></TD></TR>'
            )
        label += '</TABLE>>'

        dot.node(safe_table_name, label=label, id=safe_table_name, shape=node_shape, style=node_style)

    # --- Update edge creation to use parallel splines ---
    for i, (ltbl, col, rtbl, rcol, _line, triggers, constraints) in enumerate(filtered_foreign_keys):
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
        dot.edge(
            f"{safe_ltbl}:{col}:e",
            f"{safe_rtbl}:{rcol}:w",
            id=f"edge-{i}",
            color=f"{color1}:{color2}"
        )

    actual_svg_path = output_file + ".svg"
    try:
        dot.render(filename=output_file, cleanup=True)
        print(f"--- ERD generated successfully: {actual_svg_path} ---")
    except Exception as e:
        log.error(f"Error rendering graph with Graphviz: {e}")
        return

    with open(actual_svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()

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
    )

    with open(actual_svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
