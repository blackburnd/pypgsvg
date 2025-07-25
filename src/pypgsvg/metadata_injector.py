import os
import re
import tempfile
import base64
import xml.etree.ElementTree as ET
from graphviz import Digraph
from datetime import datetime

from .colors import color_palette, saturate_color, desaturate_color
from .utils import get_contrasting_text_color, sanitize_label
from .svg_utils import SVG_INTERACTIVITY_SCRIPT, SVG_CSS_STYLE

xml_decl = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n'
doctype = '<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" "http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">\n'


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
    total_foreign_keys, total_edges, show_standalone=True,
    main_svg_content=None,
    packmode='array',
    rankdir='TB',
    esep='6',
    fontname='Sans-Serif',
    fontsize=24,
    node_fontsize=20,
    edge_fontsize=16,
    node_sep='0.5',
    rank_sep='1.2',
    node_style='filled',
    node_shape='rect',
):
    # Use the main SVG content and scale it down
    if not main_svg_content:
        print("No main SVG content provided for miniature ERD.")
        return None

    # Extract original dimensions
    width, height = extract_svg_dimensions_from_content(main_svg_content)
    miniature_width = max(int(width * 0.1), 150)
    miniature_height = max(int(height * 0.1), 100)
    max_width = int(1920 * 0.5)
    if miniature_width > max_width:
        scale_factor = max_width / miniature_width
        miniature_width = max_width
        miniature_height = int(miniature_height * scale_factor)

    # Scale SVG using viewBox and width/height
    # Replace the width/height attributes in the SVG tag
    import re
    def replace_svg_tag(svg, new_width, new_height):
        svg = re.sub(r'(<svg[^>]*?)\swidth="[^"]*"', r'\1', svg)
        svg = re.sub(r'(<svg[^>]*?)\sheight="[^"]*"', r'\1', svg)
        svg = re.sub(r'(<svg[^>]*?)>', r'\1 width="{}" height="{}">'.format(new_width, new_height), svg, count=1)
        return svg

    scaled_svg = replace_svg_tag(main_svg_content, miniature_width, miniature_height)
    # Return SVG string and dimensions
    return (scaled_svg, miniature_width, miniature_height)


def prefix_svg_ids(svg_content, prefix='mini-'):
    """
    Prefix all IDs and references to IDs in the SVG content with the given prefix.
    """
    # Prefix id="..."
    svg_content = re.sub(r'id="([^"]+)"', lambda m: f'id="{prefix}{m.group(1)}"', svg_content)
    # Prefix url(#...)
    svg_content = re.sub(r'url\(#([^")]+)\)', lambda m: f'url(#{prefix}{m.group(1)})', svg_content)
    # Prefix xlink:href="#..."
    svg_content = re.sub(r'xlink:href="#([^"]+)"', lambda m: f'xlink:href="#{prefix}{m.group(1)}"', svg_content)
    # Prefix href="#..."
    svg_content = re.sub(r'href="#([^"]+)"', lambda m: f'href="#{prefix}{m.group(1)}"', svg_content)
    # Prefix fill="url(#...)"
    svg_content = re.sub(r'fill="url\(#([^")]+)\)"', lambda m: f'fill="url(#{prefix}{m.group(1)})"', svg_content)
    # Prefix stroke="url(#...)"
    svg_content = re.sub(r'stroke="url\(#([^")]+)\)"', lambda m: f'stroke="url(#{prefix}{m.group(1)})"', svg_content)
    return svg_content



def inject_metadata_into_svg(
    svg_content,
    file_info,
    total_tables,
    total_columns,
    total_foreign_keys,
    total_edges,
    tables,
    foreign_keys,
    show_standalone,
    gen_min_erd,
    packmode,
    rankdir,
    esep,
    fontname,
    fontsize,
    node_fontsize,
    edge_fontsize,
    node_style,
    node_shape,
    node_sep,
    rank_sep,
    # ... other settings ...
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
    miniature_svg = ""
    miniature_width = 0
    miniature_height = 0

    if xml_decl in svg_content:
        svg_content = svg_content.replace(xml_decl, '')
  
    if doctype in svg_content:
        svg_content = svg_content.replace(doctype, '')

    for line in svg_content[:].splitlines():
        if '<!DOCTYPE' in line:
            svg_content = svg_content.replace(line, '')
    
        elif 'SVG/1.1/DTD/svg11.dtd' in line:
            svg_content = svg_content.replace(line, '')
            

        
    if tables and foreign_keys and gen_min_erd:
        print("Generating miniature ERD...")
        miniature_data = generate_miniature_erd(
            tables, foreign_keys, file_info, total_tables, total_columns,
            total_foreign_keys, total_edges, show_standalone, main_svg_content=svg_content,
            packmode=packmode, rankdir=rankdir, esep=esep, fontname=fontname,
            fontsize=fontsize, node_fontsize=node_fontsize, edge_fontsize=edge_fontsize,
            node_style=node_style, node_shape=node_shape, node_sep=node_sep,
            rank_sep=rank_sep)
        if miniature_data:
            miniature_svg, miniature_width, miniature_height = miniature_data
            print(f"Miniature SVG generated successfully: {miniature_width}x{miniature_height}")
        else:
            print("Miniature SVG generation failed")
    else:
        print("No tables or foreign_keys data provided for miniature")

    metadata_html = f"""
    <div class='metadata-box'>
      <div class='header'>Metadata</div>
      <ul>
        {''.join(f'<li>{line}</li>' for line in metadata_lines)}
      </ul>
    </div>
    """

    minimap_html = ''
    if miniature_svg:
        miniature_svg = prefix_svg_ids(miniature_svg, prefix='mini-')
        minimap_html = f'''
        <div id="miniature-container" class="miniature-box">
          <div class="header">Overview</div>
          <div class="miniature-container" id="miniature-container">
            {miniature_svg.replace('<svg', '<svg id="miniature-svg"')}
            <div id="viewport-indicator" class="viewport-indicator"></div>
          </div>
          <div class="resize-handle resize-handle-nw" style="position:absolute;left:2px;top:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
          <div class="resize-handle resize-handle-ne" style="position:absolute;right:2px;top:2px;width:16px;height:16px;cursor:nesw-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
          <div class="resize-handle resize-handle-sw" style="position:absolute;left:2px;bottom:2px;width:16px;height:16px;cursor:nesw-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
          <div class="resize-handle resize-handle-se" style="position:absolute;right:2px;bottom:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
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

    # Add custom CSS style for highlighted class
    css_styles = """
    <style>
    .highlighted {
        stroke: #ff0000 !important;
        stroke-width: 4 !important;
        filter: drop-shadow(0 0 6px #ff0000);
    }
    </style>
    """
# JavaScript for interactivity (copy from your original __init__.py, use triple braces for JS blocks)
    javascript_code = SVG_INTERACTIVITY_SCRIPT
    svg_css = SVG_CSS_STYLE
    all_injected_elements = svg_css + css_styles + overlay_container_html + javascript_code
    svg_content = svg_content.replace('</svg>', f'{all_injected_elements}\n</svg>')
    # Ensure XML declaration and DOCTYPE are at the very top
    
           
    if xml_decl not in svg_content:
        svg_content = xml_decl + doctype + svg_content

    print("Metadata and interactivity injected into SVG successfully.")
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
