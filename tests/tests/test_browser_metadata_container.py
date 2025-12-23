"""Pytest-Playwright version of metadata container tests."""
import pytest
from playwright.sync_api import Page, expect


def test_metadata_container_exists_in_svg(page: Page):
    """Test that metadata container exists in SVG."""
    # Use relative URL which will use Playwright's configured baseURL
    page.goto('/Samples/complex_schema.svg')
    page.wait_for_load_state('domcontentloaded')

    # Wait for metadata container to be visible, then we're ready
    metadata_container = page.locator('#metadata-container')
    expect(metadata_container).to_be_visible()


def test_copy_button_exists_and_can_be_clicked(page: Page):
    """Test that copy button exists and can be clicked."""
    import pathlib

    # Use file:// URL to load the SVG directly from filesystem
    svg_path = pathlib.Path(__file__).parent.parent.parent / 'Samples' / 'complex_schema.svg'
    file_url = f"file://{svg_path.resolve()}"

    page.goto(file_url)
    page.wait_for_load_state('domcontentloaded')

    # Wait for metadata container to be visible first
    metadata_container = page.locator('#metadata-container')
    expect(metadata_container).to_be_visible()

    # Verify the copy button exists and is visible
    copy_button = page.locator('#metadata-container .copy-btn')
    expect(copy_button).to_be_visible()

    # Click the copy button
    copy_button.click()

    # Verify the button was successfully clicked by checking if it's still visible
    # (we can't easily test clipboard functionality in headless mode without special permissions)
    expect(copy_button).to_be_visible()
