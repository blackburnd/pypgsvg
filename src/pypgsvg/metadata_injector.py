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
 
    svg_match = re.search(r'<svg[^>]*width="([^"]*)"[^>]*height="([^"]*)"[^>]*>', svg_content)
    if svg_match:
        width_str, height_str = svg_match.groups()
        width = float(re.sub(r'[^0-9.]', '', width_str))
        height = float(re.sub(r'[^0-9.]', '', height_str))
        return int(width), int(height)


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
   
    # Extract original dimensions
    width, height = extract_svg_dimensions_from_content(main_svg_content)
    max_dim = 500
    scale = min(max_dim / width, max_dim / height, 1.0)
    miniature_width = int(width * scale)
    miniature_height = int(height * scale)

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
    triggers={},
):
    # Remove XML declaration and DOCTYPE robustly
    svg_content = re.sub(r'<\?xml[^>]*\?>\s*', '', svg_content)
    svg_content = re.sub(r'<!DOCTYPE[^>]*>\s*', '', svg_content)

    # Metadata lines
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
        f"rank_sep: {rank_sep}",
        f"triggers: {len(triggers)}",
    ]

    # Generate miniature ERD if requested
    miniature_svg = ""
    miniature_width = 0
    miniature_height = 0
    if tables and foreign_keys and gen_min_erd:
        miniature_data = generate_miniature_erd(
            tables, foreign_keys, file_info, total_tables, total_columns,
            total_foreign_keys, total_edges, show_standalone, main_svg_content=svg_content,
            packmode=packmode, rankdir=rankdir, esep=esep, fontname=fontname,
            fontsize=fontsize, node_fontsize=node_fontsize, edge_fontsize=edge_fontsize,
            node_style=node_style, node_shape=node_shape, node_sep=node_sep,
            rank_sep=rank_sep)
        if miniature_data:
            miniature_svg, miniature_width, miniature_height = miniature_data
            miniature_svg = prefix_svg_ids(miniature_svg, prefix='mini-')

    # HTML overlays
    metadata_html = f"""
<div class='metadata-container container' id='metadata-container'>
    <div class="window-controls" style="position:absolute;right:2px;top:2px;"></div>
    <div class='header'>Metadata</div>
    <div class='metadata-inner-container container-content'>
    <ul>
        {''.join(f'<li>{line}</li>' for line in metadata_lines)}
    </ul>
    </div>
</div>
"""
    minimap_html = ''
    if miniature_svg:
        minimap_html = f'''
<div id="miniature-container" class="miniature-container container" style="z-index:10000;" >
    <div class="window-controls" style="position:absolute;right:2px;top:2px;"></div>
  <div class="header" id="miniature-header">Directed GraphOverview
  </div>
  <div class="miniature-inner-container container-content" id="miniature-inner-container">
    {miniature_svg.replace('<svg', '<svg id="miniature-svg"')}
    <div id="viewport-indicator" class="viewport-indicator"></div>
  </div>
  <div class="resize-handle resize-handle-nw" id="resize_handle_nw" style="position:absolute;left:2px;top:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
  <div class="resize-handle resize-handle-se" id="resize_handle_se" style="position:absolute;right:2px;bottom:2px;width:16px;height:16px;cursor;nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
</div>
'''
    instructions_html = '''
    <div class="instructions">
        💡 Drag to pan • Scroll to zoom • Click map to navigate • Click tables/edges to highlight • ESC/R to reset
    </div>
    '''
    selection_html = f'''
<div id="selection-container" class="selection-box container" style="display:none">
      <div class="window-controls" style="position:absolute;right:2px;top:2px;"></div>

  <div class="header" id="selection-header"></div>
  <div class="selection-container container-content" id="selection-inner-container">
    <div id="viewport-indicator" class="viewport-indicator"></div>
  </div>
  <div class="resize-handle resize-handle-nw" id="resize_handle_nw" style="position:absolute;left:2px;top:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
  <div class="resize-handle resize-handle-se" id="resize_handle_se" style="position:absolute;right:2px;bottom:2px;width:16px;height:16px;cursor:nwse-resize;background:rgba(0,0,0,0.1);border-radius:3px;"></div>
</div>
'''
    all_overlays_html = f"""
        {instructions_html}
        {metadata_html}
        <div class='metadata-minimap-row'>
            {minimap_html}
        </div>
        {selection_html}
    """
    overlay_container_html = f'''
    <foreignObject id="overlay-container" x="0" y="0" width="100%" height="100%" pointer-events="none">
        <div xmlns="http://www.w3.org/1999/xhtml" id="overlay-container-div" style="position: fixed; top: 0; left: 0; width: 100vw; height: 100vh; pointer-events: none; font-family: system-ui, -apple-system, sans-serif; z-index: 9999;">
            {all_overlays_html}
        </div>
    </foreignObject>
    '''

    # Inject marker definitions for normal and large arrowheads/tails
    svg_content = inject_marker_defs(svg_content)

   
# JavaScript for interactivity (copy from your original __init__.py, use triple braces for JS blocks)
    javascript_code = SVG_INTERACTIVITY_SCRIPT
    svg_css = SVG_CSS_STYLE
    all_injected_elements = svg_css + overlay_container_html + javascript_code
    svg_content = svg_content.replace('</svg>', f'{all_injected_elements}\n</svg>')
    # Ensure XML declaration and DOCTYPE are at the very top
    
           
    if xml_decl not in svg_content:
        svg_content = xml_decl + doctype + svg_content

    # Wrap main ERD content in a group with ID "main-erd-group"
    svg_content = re.sub(r'(<svg[^>]*>)\s*<g[^>]*id="main-erd-group"[^>]*transform="translate\(0 0\) scale\(1\)">\s*(.*?)\s*</g>', r'\1<g id="main-erd-group" transform="translate(0 0) scale(1)">\2</g>', svg_content, flags=re.DOTALL)

    print("Metadata and interactivity injected into SVG successfully.")
    return svg_content

def inject_marker_defs(svg_content):
    """
    Injects enlarged and normal arrowhead/tail marker definitions into the SVG <defs> section.
    If <defs> does not exist, it will be created.
    """
    marker_defs = """
    <marker id="arrowhead" markerWidth="6" markerHeight="4" refX="6" refY="2"
      orient="auto" markerUnits="strokeWidth">
      <polygon points="0 0, 6 2, 0 4" />
    </marker>
    <marker id="arrowhead-large" markerWidth="12" markerHeight="8" refX="12" refY="4"
      orient="auto" markerUnits="strokeWidth">
      <polygon points="0 0, 12 4, 0 8" />
    </marker>
    """

    # Find <defs> and inject, or create <defs> if not present
    if '<defs>' in svg_content:
        svg_content = re.sub(r'(<defs[^>]*>)', r'\1' + marker_defs, svg_content, count=1)
    else:
        # Insert <defs> after <svg ...>
        svg_content = re.sub(r'(<svg[^>]*>)', r'\1\n<defs>' + marker_defs + '</defs>', svg_content, count=1)
    return svg_content
