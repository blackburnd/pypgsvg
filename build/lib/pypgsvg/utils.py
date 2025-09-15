import re
import colorsys
from typing import List, Tuple, Dict


def get_contrasting_text_color(bg_color: str) -> str:
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


def sanitize_label(text: str) -> str:
    """Clean label text for Graphviz compatibility"""
    # Remove or escape special characters
    return re.sub(r'[^a-zA-Z0-9_]', '_', str(text))


def should_exclude_table(table_name: str) -> bool:
    """
    Check if a table should be excluded based on specific patterns
    """
    name = table_name.lower()
    exclude_patterns = ['tmp_', 'vw_', 'bk', 'fix', 'dups', 'duplicates', 'matches', 'versionlog', 'old', 'ifma', 'memberdata',]
    return any(pattern in name for pattern in exclude_patterns)


def is_standalone_table(table_name: str, foreign_keys: List[Tuple[str, str, str, str, str, str, str]]) -> bool:
    """
    Check if a table is standalone (has no foreign key relationships).
    Returns True if the table has no incoming or outgoing foreign key relationships.
    """
    for fk_table, _, ref_table, _, _, on_delete, on_update in foreign_keys:
        if table_name == fk_table or table_name == ref_table:
            return False
    return True
