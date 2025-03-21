import unittest
from unittest.mock import patch

import numpy as np
from main import (
    Coordinate,
    create_grid,
    parse_coordinates,
    process_gdoc,
)


class TestMain(unittest.IsolatedAsyncioTestCase):
    def test_parse_coordinates_valid(self):
        html = """
        <table>
            <tr><th>X</th><th>Char</th><th>Y</th></tr>
            <tr><td>0</td><td>A</td><td>1</td></tr>
            <tr><td>1</td><td>B</td><td>2</td></tr>
        </table>
        """
        coords = parse_coordinates(html)
        self.assertEqual(len(coords), 2)
        self.assertEqual(coords[0], Coordinate("A", 0, 1))
        self.assertEqual(coords[1], Coordinate("B", 1, 2))

    def test_create_grid_valid(self):
        coords = [Coordinate("A", 0, 0), Coordinate("B", 1, 1)]
        grid = create_grid(coords)
        self.assertTrue(np.array_equal(grid, np.array([["A", " "], [" ", "B"]])))

    async def test_process_gdoc_valid(self):
        with patch("aiohttp.ClientSession.get") as mock_get:
            mock_get.return_value.__aenter__.return_value.status = 200
            mock_get.return_value.__aenter__.return_value.text.return_value = """
            <table>
                <tr><th>X</th><th>Char</th><th>Y</th></tr>
                <tr><td>0</td><td>A</td><td>0</td></tr>
            </table>
            """
            result = await process_gdoc("http://example.com")
            self.assertEqual(result, "A")

    async def test_process_gdoc_invalid_url(self):
        with self.assertRaises(ValueError):
            await process_gdoc("invalid_url")

    def test_create_grid_no_coordinates(self):
        with self.assertRaises(ValueError):
            create_grid([])
