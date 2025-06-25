"""
Python ERD Generator Package

A package for parsing SQL dump files and generating Entity Relationship Diagrams.
"""

__version__ = "1.0.0"
__author__ = "ERD Generator"

from .create_graph import (
    parse_sql_dump,
    generate_erd_with_graphviz,
    get_contrasting_text_color,
    sanitize_label,
    should_exclude_table
)

__all__ = [
    "parse_sql_dump",
    "generate_erd_with_graphviz", 
    "get_contrasting_text_color",
    "sanitize_label",
    "should_exclude_table"
]
