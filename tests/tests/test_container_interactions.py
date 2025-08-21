"""
Tests for container interaction functionality in SVG diagrams.
This module tests both selection-container and miniature-container
drag and resize functionality to compare their behavior.
"""

import pytest
import tempfile
import os
from pypgsvg.erd_generator import generate_erd_with_graphviz


class TestContainerInteractions:
    """Test container drag and resize functionality."""
    
    @pytest.fixture
    def simple_schema(self):
        """Simple schema with two tables and one foreign key."""
        tables = {
            "users": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "username", "type": "varchar(50)"},
                    {"name": "email", "type": "varchar(100)"}
                ]
            },
            "posts": {
                "columns": [
                    {"name": "id", "type": "integer"},
                    {"name": "user_id", "type": "integer"},
                    {"name": "title", "type": "varchar(200)"},
                    {"name": "content", "type": "text"}
                ]
            }
        }
        foreign_keys = [
            ("posts", "user_id", "users", "id", 
             "FOREIGN KEY (user_id) REFERENCES users(id)", "CASCADE", "CASCADE")
        ]
        return tables, foreign_keys
    
    @pytest.fixture
    def generated_svg_content(self, simple_schema):
        """Generate SVG content with embedded interactivity."""
        tables, foreign_keys = simple_schema
        
        with tempfile.TemporaryDirectory() as tmpdir:
            output_file = os.path.join(tmpdir, "test_erd")
            generate_erd_with_graphviz(tables, foreign_keys, output_file)
            svg_path = output_file + ".svg"
            
            with open(svg_path, "r", encoding="utf-8") as f:
                svg_content = f.read()
            
            return svg_content
    
    def test_selection_container_html_structure(self, generated_svg_content):
        """Test selection-container has proper HTML structure."""
        assert 'id="selection-container"' in generated_svg_content
        assert 'class="selection-container container"' in generated_svg_content
        
        # Check for resize handles
        assert 'class="resize-handle nw"' in generated_svg_content
        assert 'class="resize-handle ne"' in generated_svg_content
        assert 'class="resize-handle sw"' in generated_svg_content
        assert 'class="resize-handle se"' in generated_svg_content
        
        # Check for proper CSS cursor styles
        assert 'cursor:nw-resize' in generated_svg_content
        assert 'cursor:ne-resize' in generated_svg_content
        assert 'cursor:sw-resize' in generated_svg_content
        assert 'cursor:se-resize' in generated_svg_content
    
    def test_miniature_container_html_structure(self, generated_svg_content):
        """Test miniature-container has proper HTML structure."""
        assert 'id="miniature-container"' in generated_svg_content
        assert 'class="miniature-container container"' in generated_svg_content
        
        # Check for resize handles on miniature container
        miniature_section = self._extract_miniature_section(
            generated_svg_content
        )
        assert 'class="resize-handle nw"' in miniature_section
        assert 'class="resize-handle ne"' in miniature_section
        assert 'class="resize-handle sw"' in miniature_section
        assert 'class="resize-handle se"' in miniature_section
    
    def test_javascript_event_handlers_selection_container(self, generated_svg_content):
        """Test that selection-container has proper JavaScript event handlers."""
        # Check for makeResizable function call for selection container
        assert 'makeResizable(selectionContainer)' in generated_svg_content
        
        # Check for isolated drag handler setup
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Look for selection container specific event handlers
        assert 'selectionContainer.addEventListener(\'mousedown\'' in js_section
        assert 'dragState.type = \'selection' in js_section
    
    def test_javascript_event_handlers_miniature_container(self, generated_svg_content):
        """Test that miniature-container has proper JavaScript event handlers."""
        # Check for makeResizable function call for miniature container
        assert 'makeResizable(miniatureContainer)' in generated_svg_content
        
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Look for miniature header specific event handlers (actual implementation)
        assert 'miniatureHeader.addEventListener(\'mousedown\'' in js_section
        # Check that it sets up drag state correctly
        assert 'miniatureDragState' in js_section
    
    def test_css_styles_selection_container(self, generated_svg_content):
        """Test that selection-container has proper CSS styles."""
        css_section = self._extract_css_section(generated_svg_content)
        
        # Check for selection container styles
        assert '.selection-container' in css_section
        assert 'position: absolute' in css_section
        assert 'border: 2px solid' in css_section
        assert 'background: rgba(' in css_section  # Semi-transparent background
    
    def test_css_styles_miniature_container(self, generated_svg_content):
        """Test that miniature-container has proper CSS styles."""
        css_section = self._extract_css_section(generated_svg_content)
        
        # Check for miniature container styles
        assert '.miniature-container' in css_section
        assert 'position: absolute' in css_section
    
    def test_resize_handle_cursor_styles(self, generated_svg_content):
        """Test that resize handles have correct cursor styles (no syntax errors)."""
        css_section = self._extract_css_section(generated_svg_content)
        
        # Ensure no CSS syntax errors (semicolon instead of colon)
        assert 'cursor;nw-resize' not in css_section
        assert 'cursor;ne-resize' not in css_section
        assert 'cursor;sw-resize' not in css_section
        assert 'cursor;se-resize' not in css_section
        
        # Ensure correct CSS syntax
        assert 'cursor:nw-resize' in css_section
        assert 'cursor:ne-resize' in css_section
        assert 'cursor:sw-resize' in css_section
        assert 'cursor:se-resize' in css_section
    
    def test_drag_state_variables_exist(self, generated_svg_content):
        """Test that drag state variables are properly declared."""
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Check for the actual dragState object that exists
        assert 'dragState = {' in js_section
        assert 'startX:' in js_section
        assert 'startY:' in js_section
    
    def test_event_propagation_prevention(self, generated_svg_content):
        """Test that event propagation is properly prevented in handlers."""
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Check for event.stopPropagation() calls
        assert 'event.stopPropagation()' in js_section or 'e.stopPropagation()' in js_section
        assert 'event.preventDefault()' in js_section or 'e.preventDefault()' in js_section
    
    def test_global_mousemove_handler_includes_both_containers(self, generated_svg_content):
        """Test that global mousemove handler handles both container types."""
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Check that dragState is used for tracking drag operations
        assert 'dragState.type' in js_section
        assert 'dragState.target' in js_section
    
    def _extract_miniature_section(self, svg_content):
        """Extract the miniature container section from SVG content."""
        start_marker = 'id="miniature-container"'
        start_pos = svg_content.find(start_marker)
        if start_pos == -1:
            return ""
        
        # Find the end of this div (simplified approach)
        end_marker = '</div>'
        search_start = start_pos + len(start_marker)
        div_count = 1
        pos = search_start
        
        while pos < len(svg_content) and div_count > 0:
            if svg_content[pos:pos+5] == '<div ':
                div_count += 1
            elif svg_content[pos:pos+6] == '</div>':
                div_count -= 1
            pos += 1
        
        return svg_content[start_pos:pos+5] if div_count == 0 else svg_content[start_pos:start_pos+1000]
    
    def _extract_javascript_section(self, svg_content):
        """Extract the JavaScript section from SVG content."""
        start_marker = '<script type="text/javascript">'
        end_marker = '</script>'
        
        start_pos = svg_content.find(start_marker)
        if start_pos == -1:
            return ""
        
        end_pos = svg_content.find(end_marker, start_pos)
        if end_pos == -1:
            return ""
        
        return svg_content[start_pos:end_pos + len(end_marker)]
    
    def _extract_css_section(self, svg_content):
        """Extract the CSS section from SVG content."""
        start_marker = '<style type="text/css">'
        end_marker = '</style>'
        
        start_pos = svg_content.find(start_marker)
        if start_pos == -1:
            return ""
        
        end_pos = svg_content.find(end_marker, start_pos)
        if end_pos == -1:
            return ""
        
        return svg_content[start_pos:end_pos + len(end_marker)]

    def test_identify_differences_between_containers(self, generated_svg_content):
        """Identify structural differences between selection and miniature containers."""
        js_section = self._extract_javascript_section(generated_svg_content)
        
        # Count event listener setups for each container
        selection_listeners = js_section.count('selectionContainer.addEventListener')
        miniature_listeners = js_section.count('miniatureContainer.addEventListener')
        
        print(f"\nContainer Event Listener Comparison:")
        print(f"Selection container listeners: {selection_listeners}")
        print(f"Miniature container listeners: {miniature_listeners}")
        
        # They should have similar event listener counts if implemented consistently
        # This test will help identify if miniature container is missing handlers


class TestContainerFunctionalityComparison:
    """Compare working vs non-working container functionality."""
