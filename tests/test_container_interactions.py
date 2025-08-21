"""
Test file to compare selection-container vs miniature-container functionality.
This test will help identify why drag and resize work for selection-container
but fail for miniature-container.
"""

import pytest
import time
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
import subprocess
import tempfile
import os
import threading
import http.server
import socketserver
from contextlib import contextmanager


class TestContainerInteractions:
    """Test drag and resize functionality for both selection and miniature containers"""

    @pytest.fixture(scope="class")
    def test_svg_content(self):
        """Generate a test SVG with both containers for testing"""
        # Create a minimal test SVG with both containers
        svg_content = '''<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" 
     width="800" height="600" viewBox="0 0 800 600">
  
  <!-- Main ERD content -->
  <g id="main-group">
    <rect x="100" y="100" width="200" height="100" fill="lightblue" stroke="black"/>
    <text x="200" y="150">Test Table</text>
  </g>

  <!-- Selection Container -->
  <div id="selection-container" class="overlay-container" style="position: absolute; left: 50px; top: 50px; width: 300px; height: 200px; border: 2px solid blue; background: rgba(255,255,255,0.9); z-index: 1000;">
    <div class="window-header" style="background: blue; color: white; padding: 5px; cursor: move;">
      Selection Container
    </div>
    <div class="window-content" style="padding: 10px;">
      <p>This container should be draggable and resizable</p>
    </div>
    <div id="resize_handle_nw" class="resize-handle nw" style="position: absolute; top: 0; left: 0; width: 10px; height: 10px; background: blue; cursor: nw-resize;"></div>
    <div id="resize_handle_se" class="resize-handle se" style="position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; background: blue; cursor: se-resize;"></div>
  </div>

  <!-- Miniature Container -->
  <div id="miniature-container" class="overlay-container" style="position: absolute; left: 400px; top: 50px; width: 300px; height: 200px; border: 2px solid red; background: rgba(255,255,255,0.9); z-index: 1000;">
    <div class="window-header" style="background: red; color: white; padding: 5px; cursor: move;">
      Miniature Container
    </div>
    <div class="window-content" style="padding: 10px;">
      <p>This container should also be draggable and resizable</p>
    </div>
    <div id="resize_handle_nw" class="resize-handle nw" style="position: absolute; top: 0; left: 0; width: 10px; height: 10px; background: red; cursor: nw-resize;"></div>
    <div id="resize_handle_se" class="resize-handle se" style="position: absolute; bottom: 0; right: 0; width: 10px; height: 10px; background: red; cursor: se-resize;"></div>
  </div>

</svg>'''
        return svg_content

    @pytest.fixture(scope="class")
    def web_server(self, test_svg_content):
        """Start a local web server to serve the test SVG"""
        # Create temporary directory and files
        temp_dir = tempfile.mkdtemp()
        svg_file = os.path.join(temp_dir, "test.svg")
        html_file = os.path.join(temp_dir, "test.html")
        
        # Write SVG content
        with open(svg_file, 'w') as f:
            f.write(test_svg_content)
        
        # Create HTML wrapper with JavaScript
        html_content = f'''<!DOCTYPE html>
<html>
<head>
    <title>Container Interaction Test</title>
    <style>
        body {{ margin: 0; padding: 20px; }}
        .overlay-container {{ 
            border: 2px solid #ccc; 
            background: rgba(255,255,255,0.9);
            z-index: 1000;
        }}
        .window-header {{ 
            background: #333; 
            color: white; 
            padding: 5px; 
            cursor: move; 
        }}
        .resize-handle {{ 
            position: absolute; 
            background: #333; 
        }}
        .resize-handle.nw {{ 
            top: 0; 
            left: 0; 
            width: 10px; 
            height: 10px; 
            cursor: nw-resize; 
        }}
        .resize-handle.se {{ 
            bottom: 0; 
            right: 0; 
            width: 10px; 
            height: 10px; 
            cursor: se-resize; 
        }}
    </style>
</head>
<body>
    <div id="test-container" style="position: relative; width: 100%; height: 100vh;">
        {test_svg_content}
    </div>
    
    <script src="svg_interactivity.js"></script>
</body>
</html>'''
        
        with open(html_file, 'w') as f:
            f.write(html_content)
        
        # Copy the JavaScript file
        js_source = "/Users/danielblackburn/Documents/pypgsvg/src/pypgsvg/svg_interactivity.js"
        js_dest = os.path.join(temp_dir, "svg_interactivity.js")
        
        with open(js_source, 'r') as src, open(js_dest, 'w') as dst:
            dst.write(src.read())
        
        # Start web server
        os.chdir(temp_dir)
        handler = http.server.SimpleHTTPRequestHandler
        httpd = socketserver.TCPServer(("", 8000), handler)
        
        server_thread = threading.Thread(target=httpd.serve_forever)
        server_thread.daemon = True
        server_thread.start()
        
        yield "http://localhost:8000/test.html"
        
        httpd.shutdown()
        httpd.server_close()

    @pytest.fixture
    def driver(self):
        """Set up Chrome webdriver"""
        chrome_options = Options()
        chrome_options.add_argument("--headless")  # Run in headless mode
        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_window_size(1200, 800)
        yield driver
        driver.quit()

    def test_selection_container_drag(self, driver, web_server):
        """Test that selection-container can be dragged"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "selection-container")))
        time.sleep(1)  # Allow JavaScript to initialize
        
        # Get initial position
        container = driver.find_element(By.ID, "selection-container")
        header = container.find_element(By.CLASS_NAME, "window-header")
        
        initial_location = container.location
        print(f"Selection container initial position: {initial_location}")
        
        # Drag the container
        actions = ActionChains(driver)
        actions.click_and_hold(header).move_by_offset(100, 50).release().perform()
        
        # Check new position
        time.sleep(0.5)  # Allow animation to complete
        new_location = container.location
        print(f"Selection container new position: {new_location}")
        
        # Verify it moved
        assert new_location['x'] != initial_location['x'] or new_location['y'] != initial_location['y'], \
            "Selection container should have moved when dragged"

    def test_selection_container_resize(self, driver, web_server):
        """Test that selection-container can be resized"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "selection-container")))
        time.sleep(1)
        
        # Get initial size
        container = driver.find_element(By.ID, "selection-container")
        resize_handle = container.find_element(By.CSS_SELECTOR, ".resize-handle.se")
        
        initial_size = container.size
        print(f"Selection container initial size: {initial_size}")
        
        # Resize the container
        actions = ActionChains(driver)
        actions.click_and_hold(resize_handle).move_by_offset(50, 30).release().perform()
        
        # Check new size
        time.sleep(0.5)
        new_size = container.size
        print(f"Selection container new size: {new_size}")
        
        # Verify it resized
        assert new_size['width'] != initial_size['width'] or new_size['height'] != initial_size['height'], \
            "Selection container should have resized when handle dragged"

    def test_miniature_container_drag(self, driver, web_server):
        """Test that miniature-container can be dragged"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "miniature-container")))
        time.sleep(1)
        
        # Get initial position
        container = driver.find_element(By.ID, "miniature-container")
        header = container.find_element(By.CLASS_NAME, "window-header")
        
        initial_location = container.location
        print(f"Miniature container initial position: {initial_location}")
        
        # Drag the container
        actions = ActionChains(driver)
        actions.click_and_hold(header).move_by_offset(100, 50).release().perform()
        
        # Check new position
        time.sleep(0.5)
        new_location = container.location
        print(f"Miniature container new position: {new_location}")
        
        # Verify it moved
        assert new_location['x'] != initial_location['x'] or new_location['y'] != initial_location['y'], \
            "Miniature container should have moved when dragged"

    def test_miniature_container_resize(self, driver, web_server):
        """Test that miniature-container can be resized"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "miniature-container")))
        time.sleep(1)
        
        # Get initial size
        container = driver.find_element(By.ID, "miniature-container")
        resize_handle = container.find_element(By.CSS_SELECTOR, ".resize-handle.se")
        
        initial_size = container.size
        print(f"Miniature container initial size: {initial_size}")
        
        # Resize the container
        actions = ActionChains(driver)
        actions.click_and_hold(resize_handle).move_by_offset(50, 30).release().perform()
        
        # Check new size
        time.sleep(0.5)
        new_size = container.size
        print(f"Miniature container new size: {new_size}")
        
        # Verify it resized
        assert new_size['width'] != initial_size['width'] or new_size['height'] != initial_size['height'], \
            "Miniature container should have resized when handle dragged"

    def test_cursor_styles(self, driver, web_server):
        """Test that resize handles show proper cursor styles"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "selection-container")))
        time.sleep(1)
        
        # Check selection container resize handles
        selection_nw = driver.find_element(By.CSS_SELECTOR, "#selection-container .resize-handle.nw")
        selection_se = driver.find_element(By.CSS_SELECTOR, "#selection-container .resize-handle.se")
        
        selection_nw_cursor = selection_nw.value_of_css_property("cursor")
        selection_se_cursor = selection_se.value_of_css_property("cursor")
        
        print(f"Selection NW handle cursor: {selection_nw_cursor}")
        print(f"Selection SE handle cursor: {selection_se_cursor}")
        
        # Check miniature container resize handles
        miniature_nw = driver.find_element(By.CSS_SELECTOR, "#miniature-container .resize-handle.nw")
        miniature_se = driver.find_element(By.CSS_SELECTOR, "#miniature-container .resize-handle.se")
        
        miniature_nw_cursor = miniature_nw.value_of_css_property("cursor")
        miniature_se_cursor = miniature_se.value_of_css_property("cursor")
        
        print(f"Miniature NW handle cursor: {miniature_nw_cursor}")
        print(f"Miniature SE handle cursor: {miniature_se_cursor}")
        
        # Verify cursors are correct
        assert "nw-resize" in selection_nw_cursor, f"Selection NW handle should have nw-resize cursor, got {selection_nw_cursor}"
        assert "se-resize" in selection_se_cursor, f"Selection SE handle should have se-resize cursor, got {selection_se_cursor}"
        assert "nw-resize" in miniature_nw_cursor, f"Miniature NW handle should have nw-resize cursor, got {miniature_nw_cursor}"
        assert "se-resize" in miniature_se_cursor, f"Miniature SE handle should have se-resize cursor, got {miniature_se_cursor}"

    def test_event_propagation(self, driver, web_server):
        """Test that container events don't propagate to background SVG"""
        driver.get(web_server)
        wait = WebDriverWait(driver, 10)
        
        # Wait for page to load
        wait.until(EC.presence_of_element_located((By.ID, "selection-container")))
        time.sleep(1)
        
        # Click on selection container header
        selection_header = driver.find_element(By.CSS_SELECTOR, "#selection-container .window-header")
        
        # Record any console errors or unexpected behaviors
        logs_before = driver.get_log('browser')
        
        # Click on container header
        actions = ActionChains(driver)
        actions.click(selection_header).perform()
        time.sleep(0.5)
        
        logs_after = driver.get_log('browser')
        
        # Check for any new errors
        new_logs = logs_after[len(logs_before):]
        errors = [log for log in new_logs if log['level'] == 'SEVERE']
        
        print(f"Browser errors after selection container click: {errors}")
        
        # Now test miniature container
        miniature_header = driver.find_element(By.CSS_SELECTOR, "#miniature-container .window-header")
        
        logs_before = driver.get_log('browser')
        
        actions = ActionChains(driver)
        actions.click(miniature_header).perform()
        time.sleep(0.5)
        
        logs_after = driver.get_log('browser')
        new_logs = logs_after[len(logs_before):]
        errors = [log for log in new_logs if log['level'] == 'SEVERE']
        
        print(f"Browser errors after miniature container click: {errors}")
