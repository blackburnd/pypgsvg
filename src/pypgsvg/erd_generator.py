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


def inject_edge_gradients(svg_content, graph_data):
    """
    Injects linear gradients for each edge into the SVG <defs> and assigns them to edge paths.
    The gradient transitions from the primary table color to the secondary table color,
    with a striped effect.
    """
    # Parse SVG
    ET.register_namespace('', "http://www.w3.org/2000/svg")
    root = ET.fromstring(svg_content)
    ns = {'svg': 'http://www.w3.org/2000/svg'}

    # Find or create <defs>
    defs = root.find('svg:defs', ns)
    if defs is None:
        defs = ET.Element('{http://www.w3.org/2000/svg}defs')
        root.insert(0, defs)

    # For each edge, create a gradient
    for edge_id, edge_info in graph_data['edges'].items():
        tbl1, tbl2 = edge_info['tables']
        color1 = graph_data['tables'][tbl1]['defaultColor']
        color2 = graph_data['tables'][tbl2]['defaultColor']

        # Create striped stops
        stops = []
        for i in range(6):
            offset = f"{i*20}%"
            color = color1 if i % 2 == 0 else color2
            stops.append((offset, color))

        grad = ET.Element('{http://www.w3.org/2000/svg}linearGradient', {
            'id': f'{edge_id}-gradient',
            'x1': '0%', 'y1': '0%', 'x2': '100%', 'y2': '0%',
        })
        for offset, color in stops:
            stop = ET.Element('{http://www.w3.org/2000/svg}stop', {
                'offset': offset,
                'stop-color': color,
            })
            grad.append(stop)
        defs.append(grad)

    # Assign gradients to edge paths
    for g in root.findall('.//svg:g[@class="edge"]', ns):
        edge_id = g.attrib.get('id')
        if not edge_id or edge_id not in graph_data['edges']:
            continue
        for path in g.findall('.//svg:path', ns):
            path.set('stroke', f'url(#{edge_id}-gradient)')
            # Optionally, set stroke-width if needed

    # Return modified SVG
    return ET.tostring(root, encoding='unicode')


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
    node_shape='rect'
):
    """
    Generate an ERD using Graphviz with explicit side connections.

    Args:
        tables: Dictionary of table definitions
        foreign_keys: List of foreign key relationships
        output_file: Output file name (without extension)
        input_file_path: Path to input SQL file for metadata
        show_standalone: Whether to include standalone tables (tables with no FK relationships)
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
            "highlightColor": saturate_color(table_colors[table_name], saturation_factor=2.0),
            "desaturatedColor": desaturate_color(table_colors[table_name], desaturation_factor=0.1),
            "edges": []
        }

    # Populate edge data and update table data with connected edges
    for i, (ltbl, _, rtbl, _, _, on_delete, on_update) in enumerate(filtered_foreign_keys):
        edge_id = f"edge-{i}"
        safe_ltbl = sanitize_label(ltbl)
        safe_rtbl = sanitize_label(rtbl)

        graph_data["edges"][edge_id] = {
            "tables": [safe_ltbl, safe_rtbl],
            "defaultColor": table_colors[ltbl],
            "highlightColor": saturate_color(table_colors[ltbl], saturation_factor=2.0),
            "desaturatedColor": desaturate_color(table_colors[ltbl], desaturation_factor=0.1),
            "onDelete": on_delete,
            "onUpdate": on_update,
        }

        if safe_ltbl in graph_data["tables"]:
            graph_data["tables"][safe_ltbl]["edges"].append(edge_id)
        if safe_rtbl in graph_data["tables"]:
            graph_data["tables"][safe_rtbl]["edges"].append(edge_id)

    for table_name, cols in filtered_tables.items():
        safe_table_name = sanitize_label(table_name)

        label = f'<<TABLE BORDER="0" CELLBORDER="1" CELLSPACING="0" CELLPADDING="4">'
        label += f'<TR><TD ALIGN="center" BGCOLOR="{graph_data["tables"][safe_table_name]["defaultColor"]}"><FONT COLOR="{get_contrasting_text_color(graph_data["tables"][safe_table_name]["defaultColor"])}" POINT-SIZE="24">{table_name}</FONT></TD></TR>'

        for column in cols['columns']:
            label += f'<TR><TD ALIGN="left" PORT="{sanitize_label(column["name"])}"><FONT POINT-SIZE="18">{column["name"]} ({column["type"]})</FONT></TD></TR>'

        label += '</TABLE>>'

        dot.node(safe_table_name, label=label, id=safe_table_name, shape='rect', style='filled')

    for i, (ltbl, col, rtbl, rcol, _line,  on_delete, on_update) in enumerate(filtered_foreign_keys):
        safe_ltbl = sanitize_label(ltbl)
        safe_rtbl = sanitize_label(rtbl)
        safe_col = sanitize_label(col)
        safe_rcol = sanitize_label(rcol)
        safe_on_delet = sanitize_label(on_delete)
        safe_on_update = sanitize_label(on_update)
    

        dot.edge(f"{safe_ltbl}:{safe_col}:e", f"{safe_rtbl}:{safe_rcol}:w", id=f"edge-{i}", on_delete=safe_on_delet, on_update=safe_on_update)

    actual_svg_path = output_file + ".svg"
    try:
        dot.render(filename=output_file, cleanup=True)
        print(f"--- ERD generated successfully: {actual_svg_path} ---")
    except Exception as e:
        log.error(f"Error rendering graph with Graphviz: {e}")
        return

    with open(actual_svg_path, 'r', encoding='utf-8') as f:
        svg_content = f.read()

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
        node_sep=node_sep, rank_sep=rank_sep
    )
    svg_content = inject_edge_gradients(svg_content, graph_data)

    with open(actual_svg_path, 'w', encoding='utf-8') as f:
        f.write(svg_content)
