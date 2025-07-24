import os
import re
import tempfile
import base64
import xml.etree.ElementTree as ET
from graphviz import Digraph
from datetime import datetime

from .utils import sanitize_label
from .svg_utils import generate_miniature_erd, SVG_INTERACTIVITY_SCRIPT


# --- Utility functions (copy from original) ---
def extract_svg_dimensions_from_content(svg_content):
    try:
        svg_match = re.search(r'<svg[^>]*width="([^"]*)"[^>]*height="([^"]*)"[^>]*>', svg_content)
        if svg_match:
            width_str, height_str = svg_match.groups()
            width = float(re.sub(r'[^0-9.]', '', width_str))
            height = float(re.sub(r'[^0-9.]', '', height_str))
            return int(width), int(height)
        viewbox_match = re.search(r'viewBox="([^"]*)"', svg_content)
        if viewbox_match:
            viewbox = viewbox_match.group(1)
            parts = viewbox.split()
            if len(parts) >= 4:
                width = float(parts[2])
                height = float(parts[3])
                return int(width), int(height)
        return 800, 600
    except Exception as e:
        print(f"Warning: Could not parse SVG dimensions from content: {e}")
        return 800, 600


def convert_svg_to_png(svg_file_path, width=800, height=600):
    try:
        import cairosvg
        png_data = cairosvg.svg2png(url=svg_file_path, output_width=width, output_height=height)
        return base64.b64encode(png_data).decode('utf-8')
    except Exception as e:
        print(f"Error converting SVG to PNG: {e}")
        return ""


def generate_miniature_erd(
    tables, foreign_keys, file_info, total_tables, total_columns,
    total_foreign_keys, total_edges, show_standalone=True, main_svg_content=None
):
    main_svg_width, main_svg_height = extract_svg_dimensions_from_content(main_svg_content) if main_svg_content else (800, 600)
    miniature_width = int(main_svg_width * 0.1)
    miniature_height = int(main_svg_height * 0.1)
    miniature_width = max(miniature_width, 150)
    miniature_height = max(miniature_height, 100)
    max_width = int(1920 * 0.5)
    if miniature_width > max_width:
        scale_factor = max_width / miniature_width
        miniature_width = max_width
        miniature_height = int(miniature_height * scale_factor)

    dot = Digraph(comment='Mini ERD', format='svg')
    dot.attr(
        nodesep='8',
        pack='true',
        packmode='array',
        rankdir='TB',
        esep='6',
        normalize='true',
        ranksep='3.0',
        pathsep='2.5',
        concentrate='true',
        margin='0.05',   # <<--- Make margin very small
        pad='0.05',      # <<--- Make pad very small
        # size=f"{miniature_width/96},{miniature_height/96}!",  # Optional: force size
    )
    # Make tables more visible
    for table_name in tables:
        dot.node(
            table_name,
            shape='rect',
            style='filled',
            fillcolor='#e0e0e0',
            color='#444444',         # Darker border
            fontcolor='#222222',     # Darker text
            fontsize='12',
            penwidth='2'             # Thicker border
        )
    # Make edges more visible
    for fk in foreign_keys:
        ltbl, _, rtbl, _, _, on_delete, on_update = fk
        dot.edge(
            ltbl, rtbl,
            color='#444444',         # Darker edge
            penwidth='2.5'           # Thicker edge
        )
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_svg:
        svg_output_path = tmp_svg.name
        try:
            dot.render(svg_output_path[:-4], format='svg', cleanup=True)
        except Exception as e:
            print(f"Miniature SVG generation failed: {e}")
            if os.path.exists(svg_output_path):
                os.unlink(svg_output_path)
            return None
        actual_svg_path = svg_output_path[:-4] + '.svg'
        if not os.path.exists(actual_svg_path):
            print(f"Miniature SVG file not found: {actual_svg_path}")
            return None
        png_data = convert_svg_to_png(actual_svg_path, miniature_width, miniature_height)
        if png_data:
            return (png_data, miniature_width, miniature_height)
        else:
            return None


def inject_metadata_into_svg(
    svg_content, file_info, total_tables, total_columns, total_foreign_keys, total_edges,
    tables=None, foreign_keys=None, show_standalone=True, generate_miniature_erd=None,
    packmode='array', rankdir='TB', esep='8', fontname='Arial', fontsize=18,
        node_fontsize='14', edge_fontsize='12',
        node_style='filled', node_shape='rect',
        node_sep='0.5', rank_sep='0.5'
):
    """
    Inject metadata and miniature ERD (as PNG) directly into the SVG using a single foreignObject for fixed positioning.
    Also includes JavaScript for interactive click-to-zoom functionality.
    """
    # Create metadata lines
    metadata_lines = [
        f"Source: {file_info['filename']}",
        f"File Size: {file_info['filesize']}",
        f"Generated: {file_info['generated']}",
        f"Tables: {total_tables}",
        f"Columns: {total_columns}",
        f"Foreign Keys: {total_foreign_keys}",
        f"Connections: {total_edges}",
        f"rankdir: {rankdir}",
        f"packmode: {packmode}",
        f"show_standalone: {show_standalone}",
        f"esep: {esep}",
        f"fontname: {fontname}",
        f"fontsize: {fontsize}",
        f"node_fontsize: {node_fontsize}",
        f"edge_fontsize: {edge_fontsize}",
        f"node_style: {node_style}",
        f"node_shape: {node_shape}",
        f"node_sep: {node_sep}",
        f"rank_sep: {rank_sep}"
    ]
    miniature_png_b64 = ""
    miniature_width = 0
    miniature_height = 0

    if tables and foreign_keys and generate_miniature_erd:
        print("Generating miniature ERD...")
        miniature_data = generate_miniature_erd(
            tables, foreign_keys, file_info, total_tables, total_columns,
            total_foreign_keys, total_edges, show_standalone, svg_content
        )
        if miniature_data:
            miniature_png_b64, miniature_width, miniature_height = miniature_data
            print(f"Miniature generated successfully: {miniature_width}x{miniature_height}, data length: {len(miniature_png_b64)}")
        else:
            print("Miniature generation failed")
    else:
        print("No tables or foreign_keys data provided for miniature")


    svg_content = svg_content.replace('<svg', '<svg id="main-svg"')


    # --- Start of Injected Elements ---
    # 1. CSS Styles
    css_styles = '''
    <defs>
        <style type="text/css">
            #main-svg { overflow: visible; }
            #overlay-container-div {
                position: fixed;
                top: 0;
                left: 0;
                width: 100vw;
                height: 100vh;
                pointer-events: none;
                font-family: system-ui, -apple-system, sans-serif;
                z-index: 9999;
            }

         .metadata-box, .miniature-box, .instructions {
                z-index: 9999;
                pointer-events: auto;
                box-shadow: 2px 2px 5px rgba(0,0,0,0.2);
                border-radius: 4px;
            }
            .metadata-box {
                transform: translate(0px,0px);
                background: lightyellow;
                border: 1px solid #000;
                padding: 10px;
                font-family: monospace;
                font-size: 14px;
                line-height: 1.5;
                max-width: 300px;
                position: absolute;
            }
            .miniature-box {
                position: absolute;
                translate: (300px,0px);
                background: white;
                border: 1px solid #ccc;
                padding: 10px;
                z-index: 10000;
                pointer-events: auto;
            }
            .miniature-title {
                font-size: 12px;
                font-weight: bold;
                margin-bottom: 5px;
                text-align: center;
                color: #333;
            }
            .miniature-container {
                position: relative;
                cursor: crosshair;
                border: 1px solid #ccc;
                max-height: 100%;
                overflow: hidden;
            }
            .miniature-container img {
                max-width: 100%;
                height: auto;
                display: block;
            }
            .viewport-indicator {
                position: absolute;
                border: 2px solid red;
                background-color: rgba(255,0,0,0.2);
                pointer-events: auto;
                opacity: 0.8;
                transition: all 0.1s ease;
                box-sizing: border-box;
                cursor: grab;
                user-select: none;
                -webkit-user-select: none;
                -moz-user-select: none;
                -ms-user-select: none;
            }

            .viewport-indicator.dragging {
                cursor: grabbing;
            }
            .instructions {
                bottom: 10px;
                right: 20px;
                font-size: 11px;
                color: #666;
                background-color: rgba(255,255,255,0.7);
                padding: 3px 6px;
            }
            #main-svg.grabbing {
                cursor: grabbing;
            }
            .node, .edge {
                pointer-events: auto;
                cursor: pointer;
            }

            .metadata-minimap-row {
                display: flex;
                flex-direction: row;
                align-items: flex-start;
                gap: 16px;
                position: absolute;
                top: 10px;
                left: 10px;
                z-index: 9999;
            }
            .metadata-box, .miniature-box {
                position: relative;
                /* Remove absolute here */
            }
        </style>
    </defs>
    '''

    # 2. Metadata and minimap (foreignObject for HTML/CSS)
    metadata_html = "<div class='metadata-box'>" + "".join(f"<div>{line}</div>" for line in metadata_lines) + "</div>"
    minimap_html = ''
    if miniature_png_b64:
        minimap_html = f'''
        <div id="miniature-container" class="miniature-box">
          <div class="header">Overview</div>
          <div class="miniature-container" id="miniature-container">
            <img id="miniature-erd" src="data:image/png;base64,{miniature_png_b64}" width="{miniature_width}" height="{miniature_height}" />
            <div id="viewport-indicator" class="viewport-indicator"></div>
          </div>
          <div class="resize-handle" style="position:absolute;right:2px;bottom:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
        </div>
        '''

    instructions_html = '''
    <div class="instructions">
        💡 Drag to pan • Scroll to zoom • Click map to navigate • Click tables/edges to highlight • ESC/R to reset
    </div>
    '''

    all_overlays_html = f"""
        {instructions_html}

     <div class='metadata-minimap-row'>
      {metadata_html}
         {minimap_html}
    </div>
    """

    overlay_container_html = f'''
    <foreignObject id="overlay-container" x="0" y="0" width="100%" height="100%" pointer-events="none">
        <div xmlns="http://www.w3.org/1999/xhtml" id="overlay-container-div" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; font-family: system-ui, -apple-system, sans-serif; z-index: 9999;">
            {all_overlays_html}
        </div>
    </foreignObject>
    '''

    # JavaScript for interactivity (copy from your original __init__.py, use triple braces for JS blocks)
    javascript_code = SVG_INTERACTIVITY_SCRIPT
    all_injected_elements = css_styles + overlay_container_html + javascript_code
    svg_content = svg_content.replace('</svg>', f'{all_injected_elements}\n</svg>')

    # Ensure XML declaration and DOCTYPE are at the very top
    xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
    doctype = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'
    if not svg_content.startswith(xml_decl):
        svg_content = xml_decl + doctype + svg_content
    return svg_content


def inject_edge_gradients(svg_content, graph_data):
    """
    Injects <linearGradient> definitions into the SVG for edges, allowing them
    to be colored based on their connected tables.
    """
    if not graph_data or 'edges' not in graph_data or 'tables' not in graph_data:
        return svg_content

    defs_block = '<defs>\n'
    for edge_id, edge_data in graph_data.get('edges', {}).items():
        try:
            table1_id, table2_id = edge_data['tables']
            table1_color = graph_data['tables'][table1_id]['defaultColor']
            table2_color = graph_data['tables'][table2_id]['defaultColor']
            gradient_id = f"edge-gradient-{edge_id}"
            defs_block += (
                f'<linearGradient id="{gradient_id}" gradientUnits="userSpaceOnUse">\n'
                f'  <stop offset="0%" stop-color="{table1_color}" />\n'
                f'  <stop offset="100%" stop-color="{table2_color}" />\n'
                '</linearGradient>\n')
        except KeyError as e:           
            print(f"Warning: Missing data for edge {edge_id}: {e}")
            continue

    defs_block += '</defs>\n'
    svg_content = svg_content.replace('</svg>', f'{defs_block}\n</svg>')
    return svg_content
