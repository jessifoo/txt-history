"""In this exercise, you will write code to solve a problem. Your code must be in either Python or JavaScript—solutions in other languages will not be accepted! You can write your code using any IDE you want.

https://docs.google.com/document/d/e/2PACX-1vRMx5YQlZNa3ra8dYYxmv-QIQ3YJe8tbI3kqcuC7lQiZm-CSEznKfN_HYNSpoXcZIV3Y_O3YoUB1ecq/pub

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
"""

import logging
from dataclasses import dataclass

from bs4 import Tag
from bs4.element import ResultSet

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class GridCoordinate:
    """Represents a character and its position in the grid."""

    character: str
    x: int
    y: int

    def __post_init__(self) -> None:
        """Validate the coordinate data after initialization."""
        if not isinstance(self.x, int) or self.x < 0 or not isinstance(self.y, int) or self.y < 0:
            msg = "Coordinates must be non-negative integers"
            raise ValueError(msg)
        if not isinstance(self.character, str) or len(self.character) != 1:
            msg = "Character must be a single string character"
            raise TypeError(msg)
        if self.x < 0 or self.y < 0:
            msg = "Coordinates cannot be negative"
            raise ValueError(msg)


class TableProcessor:
    """Handles processing of table data with strict type checking."""

    @staticmethod
    def validate_row(row: Tag) -> bool:
        """Validate if a table row has the correct structure.

        Args:
            row: BeautifulSoup Tag object representing a table row

        Returns:
            bool: True if row is valid, False otherwise

        """
        return len(row.find_all("td")) == 3

    @staticmethod
    def parse_column_value(value: str, is_coordinate: bool = False) -> str | int:
        """Parse and validate a column value.

        Args:
            value: The string value to parse
            is_coordinate: Whether the value should be parsed as a coordinate

        Returns:
            Union[str, int]: Parsed value

        Raises:
            ValueError: If value cannot be parsed correctly

        """
        cleaned_value = value.lstrip().rstrip()
        if is_coordinate:
            try:
                coordinate = int(cleaned_value)
                return coordinate if coordinate >= 0 else ValueError("Coordinate cannot be negative")
            except ValueError:
                msg = f"Invalid coordinate value: {cleaned_value}"
                raise ValueError(msg)
        return cleaned_value

    @classmethod
    def process_row(cls, row: Tag) -> GridCoordinate | None:
        """Process a single table row into a GridCoordinate.

        Args:
            row: BeautifulSoup Tag object representing a table row

        Returns:
            Optional[GridCoordinate]: Processed coordinate or None if invalid

        """
        try:
            cols = row.find_all("td")
            if not cls.validate_row(row) or len(cols) != 3:
                logger.warning(f"Invalid row structure: {row}")
                return None

            col_values = [col.text for col in cols]
            x_coord = cls.parse_column_value(col_values[0], is_coordinate=True)
            character = cls.parse_column_value(col_values[1])
            y_coord = cls.parse_column_value(col_values[2], is_coordinate=True)

            return GridCoordinate(character=character, x=x_coord, y=y_coord)

        except (ValueError, TypeError) as e:
            logger.warning(f"Error processing row {row}: {e!s}")
            return None

    @classmethod
    def process_table_data(cls, rows: ResultSet[Tag]) -> list[GridCoordinate]:
        """Process all table rows into a list of GridCoordinates.

        Args:
            rows: BeautifulSoup ResultSet containing table rows

        Returns:
            List[GridCoordinate]: List of processed coordinates

        Raises:
            ValueError: If no valid coordinates are found

        """
        coordinates: list[GridCoordinate] = []

        for row in rows:
            if (coordinate := cls.process_row(row)) is not None:
                coordinates.append(coordinate)

        if not coordinates:
            msg = "No valid coordinate data found in the table."
            raise ValueError(msg)

        return coordinates


def create_grid(coordinates: list[GridCoordinate]) -> list[list[str]]:
    """Create a 2D grid from the processed coordinates.

    Args:
        coordinates: List of GridCoordinate objects

    Returns:
        List[List[str]]: 2D grid with characters placed at correct positions

    """
    if not coordinates:
        return [[]]

    max_x = max(coord.x for coord in coordinates)
    max_y = max(coord.y for coord in coordinates)

    # Create empty grid filled with spaces
    grid = [[" " for _ in range(max_x + 1)] for _ in range(max_y + 1)]

    # Place characters in grid
    for coord in coordinates:
        grid[max_y - coord.y][coord.x] = coord.character

    return grid


def print_grid(grid: list[list[str]]) -> None:
    """Print the grid with characters.

    Args:
        grid (List[List[str]]): 2D grid of characters

    """
    for _row in grid:
        pass


def process_gdoc(url: str) -> None:
    """Main function that processes a Google Doc URL and prints the character grid.
    Takes a URL as input, fetches the content, parses the coordinates,
    and prints the resulting character grid.

    Args:
        url (str): URL of the Google Doc containing character coordinates

    """
    try:
        # 1. Fetch the document
        html_content = fetch_document(url)

        # 2. Parse the table data
        chars_with_coords = parse_table_data(html_content)
        if not chars_with_coords:
            return

        # 3. Create the grid
        grid = create_grid(chars_with_coords)

        # 4. Print the result
        print_grid(grid)

    except Exception:
        pass


if __name__ == "__main__":
    doc_url = "https://docs.google.com/document/d/e/2PACX-1vRMx5YQlZNa3ra8dYYxmv-QIQ3YJe8tbI3kqcuC7lQiZm-CSEznKfN_HYNSpoXcZIV3Y_O3YoUB1ecq/pub"
    process_gdoc(doc_url)
