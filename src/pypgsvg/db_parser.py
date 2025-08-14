import re
from typing import List, Tuple, Dict

def parse_sql_dump(sql_dump):
    """
    Parse an SQL dump to extract tables, foreign key relationships, and triggers.
    """
    tables = {}
    foreign_keys = []
    triggers = {}
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

    # Trigger pattern
    trigger_pattern = re.compile(
        r'CREATE\s+TRIGGER\s+([\w."]+)\s+'
        r'((?:BEFORE|AFTER|INSTEAD OF)\s+(?:INSERT|UPDATE|DELETE|TRUNCATE|OR\s+INSERT|OR\s+UPDATE|OR\s+DELETE|OR\s+TRUNCATE)+)\s+'
        r'ON\s+([\w."]+)\s+'
        r'FOR\s+EACH\s+ROW\s+EXECUTE\s+FUNCTION\s+([\w."]+)\s*\((.*?)\);',
        re.I | re.S
    )

    # Also match triggers without arguments (most common)
    trigger_pattern_noargs = re.compile(
        r'CREATE\s+TRIGGER\s+([\w."]+)\s+'
        r'((?:BEFORE|AFTER|INSTEAD OF)\s+(?:INSERT|UPDATE|DELETE|TRUNCATE|OR\s+INSERT|OR\s+UPDATE|OR\s+DELETE|OR\s+TRUNCATE)+)\s+'
        r'ON\s+([\w."]+)\s+'
        r'FOR\s+EACH\s+ROW\s+EXECUTE\s+FUNCTION\s+([\w."]+)\s*;',
        re.I | re.S
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

                        # --- Detect inline REFERENCES ---
                        fk_match = inline_fk_pattern.search(_line)
                        if fk_match:
                            ref_table = fk_match.group(1)
                            ref_column = fk_match.group(2)
                            foreign_keys.append((table_name, column_name, ref_table, ref_column, _line, {}, {}))

            tables[table_name] = {}
            tables[table_name]['lines'] = "\n".join(_lines)
            tables[table_name]['columns'] = columns

        # Extract foreign keys from ALTER TABLE
        triggers = {}
        constraints = {}
        for match in alter_fk_pattern.finditer(sql_dump):
            table_name = match.group(1)
            fk_column = match.group(2).strip()
            ref_table = match.group(3).strip()
            ref_column = match.group(4).strip()
            _line = match.string[match.start():match.end()]

            if table_name in tables and ref_table in tables:
                foreign_keys.append((table_name, fk_column, ref_table, ref_column, _line, triggers, constraints))
            else:
                parsing_errors.append(f"FK parsing issue: {match.group(0)}")

        # Extract triggers (with and without args)
        for match in trigger_pattern.finditer(sql_dump):

            trigger_name = match.group(1).strip('"')
            event = match.group(2).replace('\n', ' ').strip()
            table_name = match.group(3).strip('"')
            function_name = match.group(4).strip('"')
            function_args = match.group(5).strip()
            full_line = match.string[match.start():match.end()]
            trigger_info = {
                "trigger_name": trigger_name,
                "event": event,
                "function": function_name,
                "function_args": function_args,
                "full_line": full_line
            }
            triggers.setdefault(table_name, []).append(trigger_info)

        # Also match triggers without arguments
        for match in trigger_pattern_noargs.finditer(sql_dump):
            trigger_name = match.group(1).strip('"')
            event = match.group(2).replace('\n', ' ').strip()
            table_name = match.group(3).strip('"')
            function_name = match.group(4).strip('"')
            function_args = None
            full_line = match.string[match.start():match.end()]
            trigger_info = {
                "trigger_name": trigger_name,
                "event": event,
                "function": function_name,
                "function_args": function_args,
                "full_line": full_line
            }
            triggers.setdefault(table_name, []).append(trigger_info)

    except Exception as e:
        parsing_errors.append(f"Parsing error: {str(e)}")

    if parsing_errors:
        print("Parsing Errors Detected:")
        for error in parsing_errors:
            print(error)

    return tables, foreign_keys, triggers, parsing_errors


def extract_constraint_info(foreign_keys):
    """
    Extract and clean constraint information for a table.
    Remove SQL action syntax and keep only the constraint definitions.
    """
    _constraints = {}
    for ltbl, col, rtbl, rcol, _line, on_del, on_up in foreign_keys:
        if ltbl not in _constraints:
            _constraints[ltbl] = []
        constraints = _constraints[ltbl]
        # Clean up the constraint line by removing ALTER TABLE syntax
        constraint_line = _line.strip()  
        # Extract just the constraint definition part
        if "ADD CONSTRAINT" in constraint_line:
            # Find the constraint name and definition
            parts = constraint_line.split("ADD CONSTRAINT", 1)
            if len(parts) > 1:
                ccdef = parts[1].strip()
                # Remove trailing semicolon and extra clauses
                ccdef = ccdef.replace(";", "")
                ccdef = re.sub(r'\s+NOT VALID.*$', '', ccdef)
                ccdef = re.sub(r'\s+ON DELETE.*$', '', ccdef)
                constraints.append(ccdef.strip())

    return _constraints