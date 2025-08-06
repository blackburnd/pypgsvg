import base64
import os
import re
import tempfile
from graphviz import Digraph


def wrap_main_erd_content(*args, **kwargs):
    """
    Finds the main Graphviz group and adds an ID and style to it for easy DOM manipulation.
    This version robustly handles existing id and style attributes.
    """
    svg_content = args[0] if args else kwargs.get('svg_content', None)
    if not isinstance(svg_content, str):
        return svg_content

    graph_pattern = re.compile(r'(<g\s[^>]*?(?:class="graph"|id="graph0")[^>]*>)', re.IGNORECASE)
    match = graph_pattern.search(svg_content)
    if not match:
        print("Warning: Could not find the main graph group in the SVG content.")
        return svg_content

    original_g_tag = match.group(1)
    modified_g_tag = original_g_tag

    # Step 1: Set the ID to 'main-erd-group'
    if 'id=' in modified_g_tag:
        modified_g_tag = re.sub(r'id="[^"]*"', 'id="main-erd-group"', modified_g_tag, count=1, flags=re.IGNORECASE)
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
    with open(js_path, 'r', encoding='utf-8') as f:
        js_code = f.read()
    return f'<script type="text/javascript"><![CDATA[\n' + js_code + '\n]]></script>'
SVG_INTERACTIVITY_SCRIPT = load_interactivity_js()

def load_svg_css():
    css_path = os.path.join(os.path.dirname(__file__), 'svg.css')
    with open(css_path, 'r', encoding='utf-8') as f:
        css_code = f.read()
    return f'<style type="text/css"><![CDATA[\n' + css_code + '\n]]></style>'
 
SVG_CSS_STYLE = load_svg_css()
