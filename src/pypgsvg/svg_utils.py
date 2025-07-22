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


def inject_edge_gradients(svg_content, graph_data):
    """Inject edge gradients into the SVG content."""
    return svg_content
    

def generate_miniature_erd(*args, **kwargs):
    """
    Generate a miniature version of the ERD as a PNG image.
    Returns tuple: (base64_png_data, width, height) or None if failed.
    """
    import base64
    from .utils import should_exclude_table, is_standalone_table

    # Unpack arguments
    if args and len(args) >= 7:
        tables, foreign_keys, file_info, total_tables, total_columns, total_foreign_keys, total_edges = args[:7]
        show_standalone = args[7] if len(args) > 7 else True
        main_svg_content = args[8] if len(args) > 8 else None
    else:
        tables = kwargs.get('tables')
        foreign_keys = kwargs.get('foreign_keys')
        file_info = kwargs.get('file_info')
        total_tables = kwargs.get('total_tables')
        total_columns = kwargs.get('total_columns')
        total_foreign_keys = kwargs.get('total_foreign_keys')
        total_edges = kwargs.get('total_edges')
        show_standalone = kwargs.get('show_standalone', True)
        main_svg_content = kwargs.get('main_svg_content', None)

    # Miniature size
    miniature_width = 480
    miniature_height = 320

    # Filter tables based on exclusion patterns and standalone option
    filtered_tables = {}
    for table_name, columns in tables.items():
        if should_exclude_table(table_name):
            continue
        if not show_standalone and is_standalone_table(table_name, foreign_keys):
            continue
        filtered_tables[table_name] = columns

    filtered_foreign_keys = [
        (table, fk_col, ref_table, ref_col, _line)
        for (table, fk_col, ref_table, ref_col, _line) in foreign_keys
        if table in filtered_tables and ref_table in filtered_tables
    ]

    if not filtered_tables:
        return None

    dot = Digraph(comment='Mini ERD', format='svg')
    dot.attr(nodesep='8', pack='true', packmode='array', rankdir='TB', esep='6', normalize='true', ranksep='3.0', pathsep='2.5', concentrate='true', margin='0.1', pad='0.1')

    # Use deterministic color assignment based on table name
    color_palette = [
        "#E8A8A8", "#E8B093", "#E8C093", "#E8D8A8", "#B8D1A8",
        "#93C4B8", "#9BB0C0", "#7BB0C0", "#98B8B8", "#E8B8A8",
        "#C4D8A8", "#E8D8A8", "#7BB8B0", "#6B8B73"
    ]
    sorted_tables = sorted(filtered_tables.keys())
    table_colors = {table_name: color_palette[i % len(color_palette)] for i, table_name in enumerate(sorted_tables)}

    from .utils import get_contrasting_text_color, sanitize_label

    # Create tables
    for table_name, _columns in filtered_tables.items():
        default_color = table_colors[table_name]
        text_color = get_contrasting_text_color(default_color)
        fields = []
        columns = _columns['columns']
        for col in columns:
            col_name = col['name']
            fields.append(f"<{col_name}> {col_name} ({col['type']})")
        left_aligned_fields = [field + "\\l" for field in fields]
        label_parts = [sanitize_label(table_name)] + left_aligned_fields
        label = "{" + "|".join(label_parts) + "}"
        dot.node(
            table_name,
            id=table_name,
            tooltip=table_name,
            labelloc='t',
            label=label,
            shape='record',
            style='filled,rounded',
            fillcolor=default_color,
            fontcolor=text_color,
            fontsize='24',
            margin='0.35,0.175',
            width='3.5',
            height='2.1'
        )

    # Create foreign key relationships
    for table_name, fk_column, ref_table, ref_column, _line in filtered_foreign_keys:
        tooltip = f"{table_name}.{fk_column}=={ref_table}.{ref_column}"
        from_port = f"{table_name}:{fk_column}"
        to_port = f"{ref_table}:{ref_column}"
        dot.edge(
            from_port,
            to_port,
            dir='both',
            weight="2.5",
            headtooltip=_line,
            color=f"{table_colors[ref_table]}:{table_colors[table_name]}",
            tooltip=tooltip,
            fillcolor=table_colors[ref_table],
            style='solid',
            penwidth='3',
            arrowsize='3',
            arrowhead="normal",
            arrowtail='diamond'
        )

    # Generate SVG first
    with tempfile.NamedTemporaryFile(suffix='.svg', delete=False) as tmp_svg:
        svg_output_path = tmp_svg.name
        try:
            dot.render(svg_output_path[:-4], format='svg', cleanup=True)
        except Exception as e:
            print(f"--- ERROR: Graphviz failed to generate the miniature SVG. ---")
            print(f"Original error: {e}")
            if os.path.exists(svg_output_path):
                os.unlink(svg_output_path)
            return None

        actual_svg_path = svg_output_path[:-4] + '.svg'
        if not os.path.exists(actual_svg_path):
            print(f"--- ERROR: Graphviz did not create the miniature SVG file: {actual_svg_path} ---")
            return None

        svg_width, svg_height = get_svg_dimensions(actual_svg_path)
        display_width = miniature_width
        display_height = miniature_height
        if svg_width > 0 and svg_height > 0:
            aspect_ratio = svg_width / svg_height
            if display_width / display_height > aspect_ratio:
                display_width = int(display_height * aspect_ratio)
            else:
                display_height = int(display_width / aspect_ratio)

        png_data = convert_svg_to_png(actual_svg_path, display_width, display_height)
        if png_data:
            b64_png = base64.b64encode(png_data).decode('utf-8')
            return b64_png, display_width, display_height
        else:
            print("Miniature generation failed: PNG conversion returned no data.")
            return None


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


import os

def load_interactivity_js():
    js_path = os.path.join(os.path.dirname(__file__), 'svg_interactivity.js')
    try:
        with open(js_path, 'r', encoding='utf-8') as f:
            js_code = f.read()
        return f'<script type="text/javascript"><![CDATA[\n' + js_code + '\n]]></script>'
    except Exception as e:
        return f'<script><!-- Failed to load svg_interactivity.js: {e} --></script>'

SVG_INTERACTIVITY_SCRIPT = load_interactivity_js()
