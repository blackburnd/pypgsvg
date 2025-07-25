import re
from typing import List, Tuple, Dict

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
        r"ALTER TABLE (?:ONLY )?([\w.]+)\s+ADD CONSTRAINT [\w.]+\s+FOREIGN KEY\s*\((.*?)\)\s+REFERENCES\s+([\w.]+)\s*\((.*?)\)(?:\s+NOT VALID)?(?:\s+ON DELETE ([\w\s]+))?(?:\s+ON UPDATE ([\w\s]+))?;",
        re.S | re.I
    )

    # Inline REFERENCES pattern
    inline_fk_pattern = re.compile(
        r'REFERENCES\s+([\w.]+)\s*\(([\w.]+)\)', re.I
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
                    if len(parts) >= 2:
                        column_name = parts[0].strip('"')
                        # Handle complex column types better
                        remainder = _line.split(None, 1)[1] if len(_line.split(None, 1)) > 1 else ''
                        # Extract column type
                        type_pattern = r'^(\w+(?:\([^)]*\))?(?:\s+with\s+\w+(?:\s+\w+)*)?)\s*(?:NOT\s+NULL|DEFAULT|UNIQUE|PRIMARY|REFERENCES|CHECK|$)'
                        type_match = re.match(type_pattern, remainder, re.I)
                        if type_match:
                            column_type = type_match.group(1).strip()
                        else:
                            words = remainder.split()
                            type_words = []
                            for word in words:
                                if word.upper() in ['NOT', 'DEFAULT', 'UNIQUE', 'PRIMARY', 'REFERENCES', 'CHECK']:
                                    break
                                type_words.append(word)
                            column_type = ' '.join(type_words) if type_words else parts[1].strip('"')
                        columns.append({"name": column_name,
                                        'type': column_type,
                                        'line': _line})

                        # --- NEW: Detect inline REFERENCES ---
                        fk_match = inline_fk_pattern.search(_line)
                        if fk_match:
                            ref_table = fk_match.group(1)
                            ref_column = fk_match.group(2)
                            # Add to foreign_keys: (table_name, column_name, ref_table, ref_column, _line)
                            foreign_keys.append((table_name, column_name, ref_table, ref_column, _line, None, None))

            tables[table_name] = {}
            tables[table_name]['lines'] = "\n".join(_lines)
            tables[table_name]['columns'] = columns

        for match in alter_fk_pattern.finditer(sql_dump):
            table_name = match.group(1)
            fk_column = match.group(2).strip()
            ref_table = match.group(3).strip()
            ref_column = match.group(4).strip()
            on_delete = match.group(5).strip().upper() if match.group(5) else None
            on_update = match.group(6).strip().upper() if match.group(6) else None
            _line = match.string[match.start():match.end()]

            if table_name in tables and ref_table in tables:
                foreign_keys.append((table_name, fk_column, ref_table, ref_column, _line, on_delete, on_update))
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


def extract_constraint_info(foreign_keys, table_name):
    """
    Extract and clean constraint information for a table.
    Remove SQL action syntax and keep only the constraint definitions.
    """
    constraints = []  
    for ltbl, col, rtbl, rcol, _line in foreign_keys:
        if ltbl == table_name:
            # Clean up the constraint line by removing ALTER TABLE syntax
            constraint_line = _line.strip()         
            # Extract just the constraint definition part
            if "ADD CONSTRAINT" in constraint_line:
                # Find the constraint name and definition
                parts = constraint_line.split("ADD CONSTRAINT", 1)
                if len(parts) > 1:
                    constraint_def = parts[1].strip()
                    # Remove trailing semicolon and extra clauses
                    constraint_def = constraint_def.replace(";", "")
                    constraint_def = re.sub(r'\s+NOT VALID.*$', '', constraint_def)
                    constraint_def = re.sub(r'\s+ON DELETE.*$', '', constraint_def)
                    constraints.append(constraint_def.strip())
  
    return constraints