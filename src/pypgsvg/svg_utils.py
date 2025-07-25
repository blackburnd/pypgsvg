import base64
import os
import re
import tempfile
from graphviz import Digraph

def convert_svg_to_png(svg_file_path, width=800, height=600):
    """
    Convert SVG to PNG using cairosvg if available, or fallback to other methods.
    Returns PNG data as bytes, or None on failure.
    """
    try:
        import cairosvg
        with open(svg_file_path, 'r', encoding='utf-8') as f:
            svg_content = f.read()
        png_data = cairosvg.svg2png(bytestring=svg_content.encode('utf-8'), output_width=width, output_height=height)
        return png_data
    except ImportError:
        print("cairosvg is not installed. Please install it to enable SVG to PNG conversion.")
    except Exception as e:
        print(f"Error converting SVG to PNG: {e}")
    return None
def get_svg_dimensions(svg_file_path):
    """
    Extract width and height from an SVG file.
    Returns (width, height) as integers, or (0, 0) if not found.
    """
    import re
    try:
        with open(svg_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        # Try to find width and height attributes
        width_match = re.search(r'width="([0-9.]+)"', content)
        height_match = re.search(r'height="([0-9.]+)"', content)
        if width_match and height_match:
            width = int(float(width_match.group(1)))
            height = int(float(height_match.group(1)))
            return width, height
        # Fallback: try viewBox
        viewbox_match = re.search(r'viewBox="[0-9.]+ [0-9.]+ ([0-9.]+) ([0-9.]+)"', content)
        if viewbox_match:
            width = int(float(viewbox_match.group(1)))
            height = int(float(viewbox_match.group(2)))
            return width, height
    except Exception as e:
        print(f"Warning: Could not parse SVG dimensions from file: {e}")
    return 0, 0


def wrap_main_erd_content(*args, **kwargs):
    """
    Finds the main Graphviz group and adds an ID and style to it for easy DOM manipulation.
    This version robustly handles existing id and style attributes.
    """
    svg_content = args[0] if args else kwargs.get('svg_content', None)
    if not isinstance(svg_content, str):
        return svg_content

    import re
    graph_pattern = re.compile(r'(<g\s[^>]*?(?:class="graph"|id="graph0")[^>]*>)', re.IGNORECASE)
    match = graph_pattern.search(svg_content)
    if not match:
        print("Warning: Could not find the main graph group in the SVG content.")
        return svg_content

    original_g_tag = match.group(1)
    modified_g_tag = original_g_tag

    # Step 1: Set the ID to 'main-erd-group'
    if 'id=' in modified_g_tag:
        modified_g_tag = re.sub(r'id="[^"]*"', 'id="main-erd-group"', modified_g_tag, 1, re.IGNORECASE)
    else:
        modified_g_tag = modified_g_tag.replace('<g', '<g id="main-erd-group"', 1)

    # Step 2: Ensure 'pointer-events: all' is set in the style attribute
    if 'style=' in modified_g_tag:
        style_match = re.search(r'style="([^"]*)"', modified_g_tag, re.IGNORECASE)
        if style_match and 'pointer-events' not in style_match.group(1):
            modified_g_tag = re.sub(r'style="', 'style="pointer-events: all; ', modified_g_tag, 1, re.IGNORECASE)
    else:
        modified_g_tag = modified_g_tag.rstrip('> ') + ' style="pointer-events: all;">'

    # Replace the original tag with the fully modified one, only once.
    return svg_content.replace(original_g_tag, modified_g_tag, 1)

def load_interactivity_js():
    js_path = os.path.join(os.path.dirname(__file__), 'svg_interactivity.js')
    try:
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        return f'<script type="text/javascript"><![CDATA[\n' + js_code + '\n]]></script>'
    except Exception as e:
        return f'<script><!-- Failed to load svg_interactivity.js: {e} --></script>'

SVG_INTERACTIVITY_SCRIPT = load_interactivity_js()

def load_svg_css():
    css_path = os.path.join(os.path.dirname(__file__), 'svg.css')
    try:
        with open(css_path, 'r', encoding='utf-8') as f:
            css_code = f.read()
        return f'<style type="text/css"><![CDATA[\n' + css_code + '\n]]></style>'
    except Exception as e:
        return f'<style><!-- Failed to load svg.css: {e} --></style>'

SVG_CSS_STYLE = load_svg_css()
