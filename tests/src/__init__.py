"""
Python ERD Generator Package

A package for parsing SQL dump files and generating Entity Relationship Diagrams.
"""

__version__ = "1.0.0"
__author__ = "ERD Generator"

from pypgsvg.db_parser import parse_sql_dump
from pypgsvg.erd_generator import generate_erd_with_graphviz
from pypgsvg.metadata_injector import inject_metadata_into_svg
from pypgsvg.utils import (
    get_contrasting_text_color,
    sanitize_label, 
    should_exclude_table)

__all__ = [
    "parse_sql_dump",
    "generate_erd_with_graphviz", 
    "get_contrasting_text_color",
    "sanitize_label",
    "should_exclude_table"
]
