"""Unit tests for the practise_test module."""

from xml.etree import ElementTree

import pytest
import responses

from scripts.practise_test import (
    Coordinate,
    FetchError,
    GridError,
    InvalidURLError,
    ParseError,
    create_grid,
    fetch_document,
    parse_cell_value,
    parse_table_data,
    validate_url,
)


def test_coordinate_validation():
    """Test Coordinate validation."""
    # Valid coordinate
    coord = Coordinate("A", 0, 0)
    assert coord.character == "A"
    assert coord.x == 0
    assert coord.y == 0

    # Invalid character (empty)
    with pytest.raises(ValueError, match="single character"):
        Coordinate("", 0, 0)

    # Invalid character (multiple)
    with pytest.raises(ValueError, match="single character"):
        Coordinate("AB", 0, 0)

    # Invalid coordinates (negative)
    with pytest.raises(ValueError, match="Invalid coordinates"):
        Coordinate("A", -1, 0)
    with pytest.raises(ValueError, match="Invalid coordinates"):
        Coordinate("A", 0, -1)


def test_url_validation():
    """Test URL validation."""
    # Valid URLs
    validate_url("https://docs.google.com/document")
    validate_url("http://example.com")

    # Invalid URLs
    with pytest.raises(InvalidURLError, match="Invalid URL format"):
        validate_url("")
    with pytest.raises(InvalidURLError, match="Invalid URL format"):
        validate_url("not-a-url")
    with pytest.raises(InvalidURLError, match="HTTP or HTTPS"):
        validate_url("ftp://example.com")


@responses.activate
def test_fetch_document():
    """Test document fetching with mocked responses."""
    url = "https://docs.google.com/test"
    html_content = "<html><body>Test content</body></html>"

    # Test successful fetch
    responses.add(responses.GET, url, body=html_content, status=200)
    assert fetch_document(url) == html_content

    # Test failed fetch
    responses.replace(responses.GET, url, status=404)
    with pytest.raises(FetchError, match="Failed to fetch document"):
        fetch_document(url)


def test_parse_cell_value():
    """Test cell value parsing."""

    # Create test elements
    def create_element(text):
        span = ElementTree.Element("span")
        span.text = text
        return span

    # Test valid integer
    element = create_element("42")
    assert parse_cell_value(element, int) == 42

    # Test valid string
    element = create_element("A")
    assert parse_cell_value(element, str) == "A"

    # Test invalid integer
    element = create_element("not-a-number")
    with pytest.raises(ValueError, match="Invalid numeric value"):
        parse_cell_value(element, int)

    # Test empty value
    element = create_element("")
    with pytest.raises(ValueError, match="Empty cell value"):
        parse_cell_value(element, str)


def test_parse_table_data():
    """Test table data parsing."""
    # Valid table HTML
    html = """
    <table>
        <tr><th>X</th><th>Char</th><th>Y</th></tr>
        <tr><td><p><span>0</span></p></td><td><p><span>A</span></p></td><td><p><span>0</span></p></td></tr>
    </table>
    """
    coordinates = parse_table_data(html)
    assert len(coordinates) == 1
    assert coordinates[0] == Coordinate("A", 0, 0)

    # Invalid table HTML
    with pytest.raises(ParseError, match="No data rows found"):
        parse_table_data("<table></table>")


def test_create_grid():
    """Test grid creation."""
    coordinates = [
        Coordinate("A", 0, 0),
        Coordinate("B", 1, 0),
        Coordinate("C", 0, 1),
    ]

    grid = create_grid(coordinates)
    assert len(grid) == 2  # Two rows
    assert len(grid[0]) == 2  # Two columns
    assert grid[1][0] == "A"  # Bottom left
    assert grid[1][1] == "B"  # Bottom right
    assert grid[0][0] == "C"  # Top left

    # Test empty coordinates
    assert create_grid([]) == [[]]

    # Test grid size limit
    with pytest.raises(GridError, match="exceed maximum allowed size"):
        create_grid([Coordinate("A", 2000, 0)])  # Exceeds MAX_DIMENSION
