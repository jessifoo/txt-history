# utils.py
import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytz

logger = logging.getLogger(__name__)


def parse_date_string(date_str: str) -> datetime:
    """Parses a date string in various formats and returns a timezone-aware datetime object."""
    # Normalize multiple spaces to single space
    normalized = " ".join(date_str.split())

    # Handle ISO format dates with timezone (e.g., "2025-01-10T18:19:09-07:00")
    if "T" in normalized and ("+" in normalized or "-" in normalized):
        # Parse as ISO format with timezone
        return datetime.fromisoformat(normalized)

    # Handle ISO format dates without timezone (e.g., "2024-12-25T22:19:32Z")
    if "T" in normalized and normalized.endswith("Z"):
        # Remove the Z suffix and parse as ISO format
        dt = datetime.fromisoformat(normalized[:-1])
        # Make timezone-aware by adding UTC timezone
        return dt.replace(tzinfo=pytz.UTC)

    # Handle the original format - make timezone-aware with Mountain Time
    dt = datetime.strptime(normalized, "%b %d, %Y %I:%M:%S %p")
    mountain_tz = pytz.timezone("America/Denver")
    return mountain_tz.localize(dt)


def format_date_to_iso(dt: datetime) -> str:
    """Formats a datetime object to ISO 8601 format with timezone information."""
    return dt.isoformat()


def calculate_earlier_date(date_str: str, days: int = 30) -> str | None:
    """Calculates a date a certain number of days earlier than the given date."""
    if not date_str:
        return None

    try:
        current_date = datetime.strptime(date_str, "%Y-%m-%d")
        earlier_date = current_date - timedelta(days=days)
        return earlier_date.strftime("%Y-%m-%d")
    except ValueError:
        logger.warning(
            "Invalid date format: %s, cannot calculate earlier date",
            date_str,
        )
        return None


def is_date_in_future(date_str: str, timezone_str: str) -> bool:
    """Checks if a date string represents a date in the future."""
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%d")
        today = datetime.now(tz=pytz.timezone(timezone_str)).replace(tzinfo=None)
        return date_obj > today
    except ValueError:
        logger.warning("Invalid date format: %s", date_str)
        return False


def read_json_file(file_path: Path) -> dict[str, Any]:
    """Reads a JSON file and returns its content as a dictionary."""
    try:
        with file_path.open(encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError:
        logger.exception("Invalid JSON in file: %s", file_path)
        raise
    except FileNotFoundError:
        logger.exception("File not found: %s", file_path)
        raise


def write_json_file(file_path: Path, data: dict[str, Any]) -> None:
    """Writes data to a JSON file."""
    with file_path.open("w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def read_text_file(file_path: Path) -> str:
    """Reads a text file and returns its content as a string."""
    try:
        with file_path.open(encoding="utf-8") as f:
            return f.read()
    except FileNotFoundError:
        logger.exception("File not found: %s", file_path)
        raise


def write_text_file(file_path: Path, content: str) -> None:
    """Writes content to a text file."""
    with file_path.open("w", encoding="utf-8") as f:
        f.write(content)


def merge_text_files(file_paths: list[Path], output_file: Path) -> None:
    """Merges multiple text files into a single output file."""
    with output_file.open("w", encoding="utf-8") as outfile:
        for file_path in file_paths:
            with file_path.open(encoding="utf-8") as infile:
                outfile.write(infile.read())
                outfile.write("\n")  # Add newline between files


def clean_message_content(message: str) -> str:
    """Cleans message content by removing emojis and special characters."""
    return "".join(char for char in message if char.isascii() and char.isprintable())
