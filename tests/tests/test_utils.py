import pytest
import sys
import os


from pypgsvg.utils import should_exclude_table, get_contrasting_text_color, sanitize_label
from pypgsvg.db_parser import parse_sql_dump    


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

    def test_no_exclusion_patterns(self):
        """Test that no tables are excluded when no patterns are provided."""
        assert should_exclude_table("users") == False
        assert should_exclude_table("vw_users") == False
        assert should_exclude_table("tmp_table") == False

    def test_with_custom_patterns(self):
        """Test exclusion with custom patterns."""
        patterns = ['vw_', 'tmp_']
        assert should_exclude_table("users", patterns) == False
        assert should_exclude_table("vw_users", patterns) == True
        assert should_exclude_table("tmp_table", patterns) == True
        assert should_exclude_table("posts", patterns) == False

    def test_multiple_patterns(self):
        """Test exclusion with multiple patterns."""
        patterns = ['vw_', 'tmp_', 'bk', 'old']
        assert should_exclude_table("vw_report", patterns) == True
        assert should_exclude_table("tmp_data", patterns) == True
        assert should_exclude_table("posts_bk", patterns) == True
        assert should_exclude_table("old_users", patterns) == True
        assert should_exclude_table("normal_table", patterns) == False

    def test_case_insensitive_matching(self):
        """Test that pattern matching is case insensitive."""
        patterns = ['VW_', 'TMP_']
        assert should_exclude_table("vw_users", patterns) == True
        assert should_exclude_table("VW_USERS", patterns) == True
        assert should_exclude_table("Vw_Users", patterns) == True
        assert should_exclude_table("tmp_data", patterns) == True
        assert should_exclude_table("TMP_DATA", patterns) == True

    def test_empty_pattern_list(self):
        """Test with empty pattern list."""
        assert should_exclude_table("vw_users", []) == False
        assert should_exclude_table("tmp_table", []) == False

    def test_empty_string_in_patterns(self):
        """Test that empty strings in patterns are ignored."""
        patterns = ['vw_', '', 'tmp_']
        assert should_exclude_table("normal_table", patterns) == False
        assert should_exclude_table("vw_users", patterns) == True

    def test_none_patterns(self):
        """Test with None as patterns (default behavior)."""
        assert should_exclude_table("users", None) == False
        assert should_exclude_table("vw_users", None) == False
        assert should_exclude_table("tmp_table", None) == False

    def test_partial_matching(self):
        """Test that patterns match partial strings."""
        patterns = ['audit', 'log']
        assert should_exclude_table("audit_table", patterns) == True
        assert should_exclude_table("table_audit", patterns) == True
        assert should_exclude_table("log_entries", patterns) == True
        assert should_exclude_table("changelog", patterns) == True
        assert should_exclude_table("users", patterns) == False
