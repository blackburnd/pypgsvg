#!/usr/bin/env python3
"""
pypgsvg - PostgreSQL Database Schema to SVG ERD Generator

This module generates Entity Relationship Diagrams (ERDs) from PostgreSQL 
database dump files using Graphviz to create SVG output.
"""

import re
import sys
from graphviz import Digraph
from random import choice

# Predefined accessible colors
color_palette = [
    "#F94144", "#F3722C", "#F8961E", "#F9C74F", "#90BE6D",
    "#43AA8B", "#577590", "#277DA1", "#4D908E", "#F9844A",
    "#A1D76A", "#E9C46A", "#2A9D8F", "#264653"
]
            

def get_contrasting_text_color(bg_color):
    """
    Calculate a contrasting text color (black or white) based on WCAG contrast standards.
    """
    # Convert HEX to RGB
    r, g, b = int(bg_color[1:3], 16), int(bg_color[3:5], 16), int(bg_color[5:7], 16)

    # Calculate relative luminance
    def relative_luminance(r, g, b):
        def channel_luminance(c):
            c = c / 255.0
            return c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4

        return 0.2126 * channel_luminance(r) + 0.7152 * channel_luminance(g) + 0.0722 * channel_luminance(b)

    bg_luminance = relative_luminance(r, g, b)
    white_luminance = 1.0  # Luminance of white
    black_luminance = 0.0  # Luminance of black

    # Calculate contrast ratios
    contrast_with_white = (white_luminance + 0.05) / (bg_luminance + 0.05)
    contrast_with_black = (bg_luminance + 0.05) / (black_luminance + 0.05)

    # Return the text color that meets WCAG standards (contrast >= 4.5:1)
    return 'white' if contrast_with_white >= 4.5 else 'black'

def sanitize_label(text):
    """Clean label text for Graphviz compatibility"""
    # Remove or escape special characters
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))

def should_exclude_table(table_name):
    """
    Check if a table should be excluded based on specific patterns
    """
    exclude_patterns = [ 'bk', 'fix', 'dups', 'duplicates', 'matches', 'versionlog', 'old',  'memberdata',]
    return any(pattern in table_name.lower() for pattern in exclude_patterns)

def generate_erd_with_graphviz(tables, foreign_keys, output_file):
    """                                                                                                                                                                                                                                                                                                                                       
    Generate an ERD using Graphviz with explicit side connections.                                                                                                                                                                                                                                                                            
    """

    filtered_tables = {
        table_name: columns
        for table_name, columns in tables.items()
        if not should_exclude_table(table_name)
    }
    filtered_foreign_keys = [
        (table, fk_col, ref_table, ref_col)
        for (table, fk_col, ref_table, ref_col, _line) in foreign_keys
        if table in filtered_tables and ref_table in filtered_tables
    ]


    dot = Digraph(comment='Database ERD', format='svg')
    dot.attr(nodesep='5',
             pack='true', 
             packmode='array',
             rank='BT',
             esep='4.5',
             normalize='true',
             ranksep='2.5',
             pathsep='2.5',
             concentrate='true',
             )
    table_colors = {table_name: choice(color_palette) for table_name in filtered_tables}
    for table_name, _columns in filtered_tables.items():
        color = table_colors[table_name]
        text_color = get_contrasting_text_color(color)
        fields = []
        foreign_key_columns = {}
        columns = _columns['columns']
        tabletooltip = _columns['lines']

        _fks = [x for x in foreign_keys if x[0] == table_name]
        fks = {}
        for ltbl, col, rtbl, rcol, _line in foreign_keys:
            fks[col] = _line
        
        for col in columns:
            col_name = col['name']

            col['tooltip'] = fk_ = fks.get(col_name,'')

            if fk_:
                tabletooltip += "\n\n%s\n" % fk_
                foreign_key_columns[col_name] = fks
                fields.append(f"<{col_name}> {col_name}  ({col['type']}) -FK-")
            else:
                fields.append(f"<{col_name}> {col_name} ({col['type']}) ")

        label = f"{{<table_header> {table_name} | {' | '.join(fields)}}}"

        dot.node(
            table_name,
            tooltip=tabletooltip,
            label=label,
            shape='Mrecord',
            style='filled, rounded',
            fillcolor=color,
            fontcolor=text_color,
            fontsize='25',
        )

    fks = dict([(x[0],x) for x in foreign_keys])
    for table_name, fk_column, ref_table, ref_column in filtered_foreign_keys:

        tbl = dict([(x['name'],x['type']) for x in filtered_tables[table_name]['columns']])

        _fks = fks.get(table_name, None)
        _line = ''
        tooltip = "%s.%s==%s.%s" % (table_name,fk_column, ref_table, ref_column)

        if _fks is not None:
            if fk_column == _fks[1]:
                _line = _fks[-1]

        if _line == '':
            headtooltip=_line
        else:
            headtooltip=tooltip

        if list(filtered_tables.keys()).index(table_name) >= list(filtered_tables.keys()).index(ref_table):
            from_port = f"{table_name}:<{fk_column}>"
            to_port = f"{ref_table}:<{ref_column}>"
        else:
            from_port = f"{table_name}:<{fk_column}>"
            to_port = f"{ref_table}:<{ref_column}>"

        dot.edge(
            dir='both',
            weight="2.5",
            head_name=from_port,
            headtooltip=_line,
            tail_name=to_port,
            color="%s:%s" % (table_colors[ref_table], table_colors[table_name]),
            tooltip=_line,
            fillcolor=table_colors[ref_table],
            style='solid',
            penwidth='5',
            arrowsize='3',
            arrowhead="normal",
            arrowtail='diamond'
        )

    dot.render(output_file, view=True)
    print(f"ERD saved to {output_file}.svg")

def parse_sql_dump(sql_dump):
    """
    Parse an SQL dump to extract tables and foreign key relationships, handling variations in SQL formatting.
    """
    tables = {}
    foreign_keys = []
    parsing_errors = []

    # Table creation pattern
    table_pattern = re.compile(
        r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(["\w.]+)\s*\((.*?)\);',
        re.S | re.I
    )

    # Foreign key definition in ALTER TABLE
    alter_fk_pattern = re.compile(
        r"ALTER TABLE (?:ONLY )?([\w.]+)\s+ADD CONSTRAINT [\w.]+\s+FOREIGN KEY\s*\((.*?)\)\s+REFERENCES\s+([\w.]+)\s*\((.*?)\)(?:\s+NOT VALID)?(?:\s+ON DELETE [\w\s]+)?;",
        re.S | re.I
    )

    try:
        # Extract tables and their columns
        for match in table_pattern.finditer(sql_dump):
            table_name = match.group(1).strip('"')
            columns = []
            _lines = [table_name]
            for line in match.group(2).split(','):
                line = line.strip()
                _lines.append(line)
                if line and not re.match(r'^(PRIMARY\s+KEY|FOREIGN\s+KEY)', line, re.I):
                    _line = line.strip()
                    parts = _line.split()
                    column_name = parts[0].strip('"')
                    column_type = parts[1].strip('"')
                    columns.append({"name": column_name,
                                    'type': column_type,
                                    'line': _line})

            tables[table_name] = {}
            tables[table_name]['lines'] = "\n".join(_lines)
            tables[table_name]['columns'] = columns

        for match in alter_fk_pattern.finditer(sql_dump):
            table_name = match.group(1)
            fk_column = match.group(2).strip()
            ref_table = match.group(3).strip()
            ref_column = match.group(4).strip()
            _line = match.string[match.start():match.end()]

            if table_name in tables and ref_table in tables:
                foreign_keys.append((table_name, fk_column, ref_table, ref_column, _line))
            else:
                parsing_errors.append(f"FK parsing issue: {match.group(0)}")

    except Exception as e:
        parsing_errors.append(f"Parsing error: {str(e)}")

    # Debug output for missing keys or parsing issues
    if parsing_errors:
        print("Parsing Errors Detected:")
        for error in parsing_errors:
            print(error)

    return tables, foreign_keys, parsing_errors

def main():
    """Main entry point for the pypgsvg ERD generator."""
    # Check for command line argument
    if len(sys.argv) != 2:
        print("Usage: pypgsvg <sql_dump_file>")
        print("Example: pypgsvg schema.dump")
        sys.exit(1)
    
    # Load SQL dump from command line argument
    sql_file_path = sys.argv[1]

    try:
        with open(sql_file_path, "r", encoding='utf-8') as file:
            sql_dump_content = file.read()
    except FileNotFoundError:
        print(f"Error: File '{sql_file_path}' not found.")
        sys.exit(1)
    except UnicodeDecodeError as e:
        print(f"Encoding error reading the file: {e}")
        print("Attempting to read with error handling...")

        # Read with error handling to locate problematic characters
        with open(sql_file_path, "r", encoding='utf-8', errors='replace') as file:
            sql_dump_content = file.read()

        # Identify non-UTF-8 characters
        non_utf8_chars = [(i, repr(char)) for i, char in enumerate(sql_dump_content) if ord(char) > 127]
        print("Non-UTF-8 characters found at:")
        for location, char in non_utf8_chars:
            print(f"Index {location}: {char}")

    # Parse tables and foreign keys
    tables, foreign_keys, parsing_errors = parse_sql_dump(sql_dump_content)

    # Only generate ERD if no critical errors
    if not parsing_errors:
        # Generate ERD
        output_erd_file = "database_diagram"
        generate_erd_with_graphviz(tables, foreign_keys, output_erd_file)
    else:
        print("ERD generation skipped due to parsing errors.")

# Example usage
if __name__ == "__main__":
    main()
