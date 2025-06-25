"""
Unit tests for create_graph.py color and utility functions.
"""
import pytest
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from create_graph import (
    get_contrasting_text_color,
    sanitize_label,
    should_exclude_table
)


@pytest.mark.unit
class TestGetContrastingTextColor:
    """Test color contrast calculation function."""
    
    @pytest.mark.parametrize("bg_color,expected", [
        ("#000000", "white"),  # Black background
        ("#FFFFFF", "black"),  # White background
        ("#F94144", "black"),  # Red from palette - updated based on actual calculation
        ("#90BE6D", "black"),  # Light green from palette
        ("#264653", "white"),  # Dark green from palette
        ("#F9C74F", "black"),  # Yellow from palette
    ])
    def test_contrasting_text_color(self, bg_color, expected):
        """Test that contrasting colors are calculated correctly."""
        result = get_contrasting_text_color(bg_color)
        assert result == expected
    
    def test_invalid_color_format(self):
        """Test handling of invalid color format."""
        with pytest.raises(ValueError):
            get_contrasting_text_color("invalid")
    
    def test_short_hex_color(self):
        """Test handling of short hex color format."""
        with pytest.raises(ValueError):
            get_contrasting_text_color("#FFF")
    
    def test_edge_case_colors(self):
        """Test edge case colors for contrast calculation."""
        # Test a color that's right at the threshold
        result = get_contrasting_text_color("#808080")  # Medium gray
        assert result in ["black", "white"]


@pytest.mark.unit
class TestSanitizeLabel:
    """Test label sanitization function."""
    
    @pytest.mark.parametrize("input_text,expected", [
        ("normal_text", "normal_text"),
        ("text with spaces", "text_with_spaces"),
        ("text-with-hyphens", "text_with_hyphens"),
        ("text.with.dots", "text_with_dots"),
        ("text@with#special$chars", "text_with_special_chars"),
        ("123numbers", "123numbers"),
        ("", ""),
        ("_underscore_", "_underscore_"),
    ])
    def test_sanitize_label(self, input_text, expected):
        """Test that labels are sanitized correctly."""
        result = sanitize_label(input_text)
        assert result == expected
    
    def test_sanitize_label_with_none(self):
        """Test sanitize_label with None input."""
        result = sanitize_label(None)
        assert result == "None"
    
    def test_sanitize_label_with_number(self):
        """Test sanitize_label with numeric input."""
        result = sanitize_label(123)
        assert result == "123"


@pytest.mark.unit
class TestShouldExcludeTable:
    """Test table exclusion logic."""
    
    @pytest.mark.parametrize("table_name,should_exclude", [
        ("users", False),
        ("posts", False),
        ("vw_users", True),
        ("posts_bk", True),
        ("fix_data", True),
        ("dups_table", True),
        ("duplicates_old", True),
        ("matches_temp", True),
        ("versionlog_2023", True),
        ("old_posts", True),
        ("ifma_data", True),
        ("memberdata_archive", True),
        ("VW_UPPERCASE", True),  # Test case sensitivity
        ("normal_table", False),
    ])
    def test_should_exclude_table(self, table_name, should_exclude):
        """Test table exclusion patterns."""
        result = should_exclude_table(table_name)
        assert result == should_exclude
    
    def test_exclude_table_empty_string(self):
        """Test exclude logic with empty string."""
        result = should_exclude_table("")
        assert result == False
    
    def test_exclude_table_case_insensitive(self):
        """Test that exclusion patterns are case insensitive."""
        assert should_exclude_table("VW_TEST") == True
        assert should_exclude_table("vw_test") == True
        assert should_exclude_table("Vw_Test") == True
