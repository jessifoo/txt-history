# ruff: noqa: D100, D101, D102, D103, D104, D105, D106, D107, ERA001  # noqa: CPY001
"""DO NOT EVER CHANGE THIS.

Coding Exercise: Decoding a Secret Message
In this exercise, you will write code to solve a problem. Your code must be in either Python or JavaScript—solutions in other languages will not be accepted! You can write your code using any IDE you want.


Problem
You are given a Google Doc like this one that contains a list of Unicode characters and their positions in a 2D grid. Your task is to write a function that takes in the URL for such a Google Doc as an argument, retrieves and parses the data in the document, and prints the grid of characters. When printed in a fixed-width font, the characters in the grid will form a graphic showing a sequence of uppercase letters, which is the secret message.

The document specifies the Unicode characters in the grid, along with the x- and y-coordinates of each character.

The minimum possible value of these coordinates is 0. There is no maximum possible value, so the grid can be arbitrarily large.

Any positions in the grid that do not have a specified character should be filled with a space character.

You can assume the document will always have the same format as the example document linked above.

For example, the simplified example document linked above draws out the letter 'F':

█▀▀▀
█▀▀
█
Note that the coordinates (0, 0) will always correspond to the same corner of the grid as in this example, so make sure to understand in which directions the x- and y-coordinates increase.

Specifications
Your code must be written in Python (preferred) or JavaScript.

You may use external libraries.

You may write helper functions, but there should be one function that:

1. Takes in one argument, which is a string containing the URL for the Google Doc with the input data, AND

2. When called, prints the grid of characters specified by the input data, displaying a graphic of correctly oriented uppercase letters.

Please submit the complete code for your function.

Explain how your code works in 2-3+ complete sentences.

"""  # noqa: E501

import asyncio
import logging
import sys
from dataclasses import dataclass
from typing import TypeAlias

import aiohttp
import numpy as np
import pandas as pd
import validators

# Type aliases for better readability
Coordinates: TypeAlias = list["Coordinate"]
Grid: TypeAlias = np.ndarray

MIN_COLUMNS = 3
logger = logging.getLogger(__name__)


@dataclass
class Coordinate:
    """A character with its position in the grid."""

    char: str
    x: int
    y: int

    def __post_init__(self) -> None:
        """Validate coordinate on creation.

        Raises:
            ValueError: If character is not a single character.

        """
        if self.char is None or len(self.char) != 1:
            msg = "Character must be a single character"
            raise ValueError(msg)


def parse_coordinates(html: str) -> Coordinates:
    """Extract coordinates from HTML table.

    Args:
        html: HTML content containing the table with coordinates.

    Returns:
        Coordinates: List of parsed coordinates.

    Raises:
        ValueError: If table is missing or has invalid columns.

    """
    tables = pd.read_html(html)  # Let pandas handle HTML parsing errors
    if not tables:
        raise ValueError("No table found")  # noqa: EM101, TRY003

    table = tables[0]
    if len(table.columns) < MIN_COLUMNS:
        raise ValueError("Table must have at least 3 columns")  # noqa: EM101, TRY003

    # More efficient list comprehension without multiple checks
    valid_rows = table.iloc[1:].dropna(subset=[0, 1, 2])
    return [Coordinate(str(row[1]), int(row[0]), int(row[2])) for _, row in valid_rows.iterrows()]


def create_grid(coords: Coordinates) -> Grid:
    """Create character grid from coordinates.

    Args:
        coords: List of coordinates to place in the grid.

    Returns:
        Grid: 2D grid of characters with spaces for empty positions.

    Raises:
        ValueError: If no coordinates provided.

    """
    match coords:
        case []:  # Empty list pattern matching
            raise ValueError("No coordinates provided")  # noqa: EM101, TRY003
        case _:  # Non-empty list
            # Calculate dimensions in one pass O(n)
            width = max(c.x for c in coords) + 1
            height = max(c.y for c in coords) + 1

            # Create grid using numpy (more efficient than list comprehension)
            grid = np.full((height, width), " ", dtype=str)

            # Fill coordinates O(n)
            for coord in coords:
                grid[coord.y][coord.x] = coord.char

            return grid


async def process_gdoc(url: str | None) -> str:
    """Convert Google Doc table into ASCII art.

    Args:
        url: URL of the Google Doc containing the table.

    Returns:
        str: ASCII art representation of the grid.

    Raises:
        ValueError: If URL is invalid or document processing fails.

    """
    if url is None:
        raise ValueError("URL cannot be None")  # noqa: EM101, TRY003

    if not validators.url(url):
        raise ValueError("Invalid URL")  # noqa: EM101, TRY003

    try:
        async with aiohttp.ClientSession() as session, session.get(url, timeout=10) as response:
            if response.status == 404:
                msg = f"Document not found: {url}"
                raise ValueError(msg)
            if response.status == 403:
                msg = f"Access denied. Make sure the document is publicly accessible: {url}"
                raise ValueError(msg)
            response.raise_for_status()
            html = await response.text()

        coords = parse_coordinates(html)
        grid = create_grid(coords)
        return "\n".join("".join(row) for row in grid)
    except aiohttp.ClientError as e:
        msg = f"Failed to fetch document: {e}"
        raise ValueError(msg) from e


def main() -> None:
    """Entry point for the script."""
    try:
        result = asyncio.run(
            process_gdoc(
                "https://docs.google.com/document/d/1xZrcQkl5UgO5ZCoZfzzyZDlnpz_ZrQv5JU1bZQSWX1E/edit",
            ),
        )
        print(result)  # Print the actual grid output  # noqa: T201
    except (ValueError, aiohttp.ClientError):
        logger.exception("Failed to process Google Doc")


if __name__ == "__main__":
    main()
