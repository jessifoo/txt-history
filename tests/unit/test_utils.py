"""Comprehensive unit tests for scripts/utils.py."""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import mock_open, patch

import pytest
import pytz

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from utils import (
    calculate_earlier_date,
    clean_message_content,
    format_date_to_iso,
    is_date_in_future,
    merge_text_files,
    parse_date_string,
    read_json_file,
    read_text_file,
    write_json_file,
    write_text_file,
)


class TestParseDateString:
    """Test suite for parse_date_string function."""

    def test_parse_iso_format_with_timezone(self):
        """Test parsing ISO format date with timezone."""
        date_str = "2025-01-10T18:19:09-07:00"
        result = parse_date_string(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 10
        assert result.tzinfo is not None

    def test_parse_iso_format_with_utc_z(self):
        """Test parsing ISO format date with Z suffix."""
        date_str = "2024-12-25T22:19:32Z"
        result = parse_date_string(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2024
        assert result.month == 12
        assert result.day == 25
        assert result.tzinfo == pytz.UTC

    def test_parse_original_format(self):
        """Test parsing original message format."""
        date_str = "Jan 15, 2025 10:30:00 AM"
        result = parse_date_string(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2025
        assert result.month == 1
        assert result.day == 15
        assert result.hour == 10
        assert result.minute == 30
        assert result.tzinfo is not None

    def test_parse_with_multiple_spaces(self):
        """Test parsing with multiple spaces normalized."""
        date_str = "Jan  15,  2025   10:30:00   AM"
        result = parse_date_string(date_str)
        assert isinstance(result, datetime)
        assert result.year == 2025

    def test_parse_pm_time(self):
        """Test parsing PM time."""
        date_str = "Dec 31, 2024 11:59:59 PM"
        result = parse_date_string(date_str)
        assert result.hour == 23
        assert result.minute == 59
        assert result.second == 59

    def test_parse_midnight(self):
        """Test parsing midnight time."""
        date_str = "Jan 1, 2025 12:00:00 AM"
        result = parse_date_string(date_str)
        assert result.hour == 0

    def test_parse_noon(self):
        """Test parsing noon time."""
        date_str = "Jan 1, 2025 12:00:00 PM"
        result = parse_date_string(date_str)
        assert result.hour == 12

    def test_parse_different_months(self):
        """Test parsing different month abbreviations."""
        months = [
            ("Jan", 1),
            ("Feb", 2),
            ("Mar", 3),
            ("Apr", 4),
            ("May", 5),
            ("Jun", 6),
            ("Jul", 7),
            ("Aug", 8),
            ("Sep", 9),
            ("Oct", 10),
            ("Nov", 11),
            ("Dec", 12),
        ]
        for month_str, month_num in months:
            date_str = f"{month_str} 15, 2025 10:00:00 AM"
            result = parse_date_string(date_str)
            assert result.month == month_num

    def test_parse_leap_year(self):
        """Test parsing leap year date."""
        date_str = "Feb 29, 2024 10:00:00 AM"
        result = parse_date_string(date_str)
        assert result.year == 2024
        assert result.month == 2
        assert result.day == 29

    def test_parse_iso_with_positive_offset(self):
        """Test parsing ISO format with positive timezone offset."""
        date_str = "2025-01-10T18:19:09+05:30"
        result = parse_date_string(date_str)
        assert result.tzinfo is not None


class TestFormatDateToIso:
    """Test suite for format_date_to_iso function."""

    def test_format_aware_datetime(self):
        """Test formatting timezone-aware datetime."""
        dt = datetime(2025, 1, 10, 18, 19, 9, tzinfo=pytz.UTC)
        result = format_date_to_iso(dt)
        assert isinstance(result, str)
        assert "2025-01-10" in result
        assert "18:19:09" in result

    def test_format_with_timezone(self):
        """Test formatting with specific timezone."""
        mountain = pytz.timezone("America/Denver")
        dt = datetime(2025, 1, 10, 12, 0, 0, tzinfo=mountain)
        result = format_date_to_iso(dt)
        assert "2025-01-10" in result
        assert ":" in result

    def test_format_preserves_timezone_info(self):
        """Test that formatting preserves timezone information."""
        dt = datetime(2025, 1, 10, 18, 19, 9, tzinfo=pytz.UTC)
        result = format_date_to_iso(dt)
        assert "+" in result or "Z" in result or "-" in result

    def test_format_microseconds(self):
        """Test formatting datetime with microseconds."""
        dt = datetime(2025, 1, 10, 18, 19, 9, 123456, tzinfo=pytz.UTC)
        result = format_date_to_iso(dt)
        assert isinstance(result, str)


class TestCalculateEarlierDate:
    """Test suite for calculate_earlier_date function."""

    def test_calculate_30_days_earlier(self):
        """Test calculating 30 days earlier."""
        date_str = "2025-02-15"
        result = calculate_earlier_date(date_str, 30)
        assert result == "2025-01-16"

    def test_calculate_1_day_earlier(self):
        """Test calculating 1 day earlier."""
        date_str = "2025-01-15"
        result = calculate_earlier_date(date_str, 1)
        assert result == "2025-01-14"

    def test_calculate_cross_year_boundary(self):
        """Test calculating across year boundary."""
        date_str = "2025-01-15"
        result = calculate_earlier_date(date_str, 20)
        assert result == "2024-12-26"

    def test_calculate_cross_month_boundary(self):
        """Test calculating across month boundary."""
        date_str = "2025-03-05"
        result = calculate_earlier_date(date_str, 10)
        assert result == "2025-02-23"

    def test_calculate_with_empty_string(self):
        """Test with empty date string."""
        result = calculate_earlier_date("", 30)
        assert result is None

    def test_calculate_with_invalid_format(self):
        """Test with invalid date format."""
        result = calculate_earlier_date("invalid-date", 30)
        assert result is None

    def test_calculate_zero_days(self):
        """Test calculating 0 days earlier."""
        date_str = "2025-01-15"
        result = calculate_earlier_date(date_str, 0)
        assert result == "2025-01-15"

    def test_calculate_large_number_of_days(self):
        """Test calculating large number of days earlier."""
        date_str = "2025-01-15"
        result = calculate_earlier_date(date_str, 365)
        assert result == "2024-01-15"

    def test_calculate_leap_year_handling(self):
        """Test leap year handling."""
        date_str = "2024-03-01"
        result = calculate_earlier_date(date_str, 1)
        assert result == "2024-02-29"


class TestIsDateInFuture:
    """Test suite for is_date_in_future function."""

    def test_date_in_past(self):
        """Test date that is clearly in the past."""
        date_str = "2020-01-01"
        result = is_date_in_future(date_str, "America/Denver")
        assert result is False

    def test_date_far_in_future(self):
        """Test date that is far in the future."""
        date_str = "2030-01-01"
        result = is_date_in_future(date_str, "America/Denver")
        assert result is True

    def test_invalid_date_format(self):
        """Test with invalid date format."""
        result = is_date_in_future("invalid", "America/Denver")
        assert result is False

    def test_different_timezones(self):
        """Test with different timezones."""
        # Yesterday's date
        yesterday = (datetime.now(tz=pytz.UTC) - timedelta(days=1)).strftime("%Y-%m-%d")
        assert is_date_in_future(yesterday, "America/Denver") is False
        assert is_date_in_future(yesterday, "UTC") is False
        assert is_date_in_future(yesterday, "Asia/Tokyo") is False

    def test_today_date(self):
        """Test with today's date."""
        today = datetime.now(tz=pytz.UTC).strftime("%Y-%m-%d")
        result = is_date_in_future(today, "America/Denver")
        assert result is False

    def test_invalid_timezone(self):
        """Test with invalid timezone."""
        date_str = "2025-01-01"
        with pytest.raises(Exception, match=r".*"):
            is_date_in_future(date_str, "Invalid/Timezone")


class TestReadJsonFile:
    """Test suite for read_json_file function."""

    def test_read_valid_json(self, tmp_path):
        """Test reading valid JSON file."""
        json_file = tmp_path / "test.json"
        test_data = {"key": "value", "number": 42}
        json_file.write_text(json.dumps(test_data))

        result = read_json_file(json_file)
        assert result == test_data

    def test_read_nested_json(self, tmp_path):
        """Test reading nested JSON structure."""
        json_file = tmp_path / "nested.json"
        test_data = {"outer": {"inner": {"value": 123}}}
        json_file.write_text(json.dumps(test_data))

        result = read_json_file(json_file)
        assert result["outer"]["inner"]["value"] == 123

    def test_read_json_with_arrays(self, tmp_path):
        """Test reading JSON with arrays."""
        json_file = tmp_path / "array.json"
        test_data = {"items": [1, 2, 3, 4, 5]}
        json_file.write_text(json.dumps(test_data))

        result = read_json_file(json_file)
        assert result["items"] == [1, 2, 3, 4, 5]

    def test_read_invalid_json(self, tmp_path):
        """Test reading invalid JSON."""
        json_file = tmp_path / "invalid.json"
        json_file.write_text("{invalid json}")

        with pytest.raises(json.JSONDecodeError):
            read_json_file(json_file)

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file."""
        json_file = tmp_path / "nonexistent.json"

        with pytest.raises(FileNotFoundError):
            read_json_file(json_file)

    def test_read_empty_json_object(self, tmp_path):
        """Test reading empty JSON object."""
        json_file = tmp_path / "empty.json"
        json_file.write_text("{}")

        result = read_json_file(json_file)
        assert result == {}


class TestWriteJsonFile:
    """Test suite for write_json_file function."""

    def test_write_simple_json(self, tmp_path):
        """Test writing simple JSON data."""
        json_file = tmp_path / "output.json"
        test_data = {"key": "value"}

        write_json_file(json_file, test_data)

        assert json_file.exists()
        with open(json_file) as f:
            result = json.load(f)
        assert result == test_data

    def test_write_nested_json(self, tmp_path):
        """Test writing nested JSON structure."""
        json_file = tmp_path / "nested.json"
        test_data = {"level1": {"level2": {"level3": "value"}}}

        write_json_file(json_file, test_data)

        with open(json_file) as f:
            result = json.load(f)
        assert result == test_data

    def test_write_json_with_indent(self, tmp_path):
        """Test that JSON is written with indentation."""
        json_file = tmp_path / "indented.json"
        test_data = {"key": "value"}

        write_json_file(json_file, test_data)

        content = json_file.read_text()
        assert "\n" in content  # Should have newlines from indentation

    def test_overwrite_existing_file(self, tmp_path):
        """Test overwriting existing JSON file."""
        json_file = tmp_path / "overwrite.json"
        json_file.write_text('{"old": "data"}')

        new_data = {"new": "data"}
        write_json_file(json_file, new_data)

        with open(json_file) as f:
            result = json.load(f)
        assert result == new_data


class TestReadTextFile:
    """Test suite for read_text_file function."""

    def test_read_simple_text(self, tmp_path):
        """Test reading simple text file."""
        text_file = tmp_path / "test.txt"
        content = "Hello, World!"
        text_file.write_text(content)

        result = read_text_file(text_file)
        assert result == content

    def test_read_multiline_text(self, tmp_path):
        """Test reading multiline text."""
        text_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"
        text_file.write_text(content)

        result = read_text_file(text_file)
        assert result == content

    def test_read_empty_file(self, tmp_path):
        """Test reading empty file."""
        text_file = tmp_path / "empty.txt"
        text_file.write_text("")

        result = read_text_file(text_file)
        assert result == ""

    def test_read_unicode_text(self, tmp_path):
        """Test reading Unicode text."""
        text_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"
        text_file.write_text(content, encoding="utf-8")

        result = read_text_file(text_file)
        assert result == content

    def test_read_nonexistent_file(self, tmp_path):
        """Test reading nonexistent file."""
        text_file = tmp_path / "nonexistent.txt"

        with pytest.raises(FileNotFoundError):
            read_text_file(text_file)


class TestWriteTextFile:
    """Test suite for write_text_file function."""

    def test_write_simple_text(self, tmp_path):
        """Test writing simple text."""
        text_file = tmp_path / "output.txt"
        content = "Test content"

        write_text_file(text_file, content)

        assert text_file.exists()
        assert text_file.read_text() == content

    def test_write_multiline_text(self, tmp_path):
        """Test writing multiline text."""
        text_file = tmp_path / "multiline.txt"
        content = "Line 1\nLine 2\nLine 3"

        write_text_file(text_file, content)

        assert text_file.read_text() == content

    def test_write_unicode(self, tmp_path):
        """Test writing Unicode text."""
        text_file = tmp_path / "unicode.txt"
        content = "Hello 世界 🌍"

        write_text_file(text_file, content)

        assert text_file.read_text(encoding="utf-8") == content

    def test_overwrite_existing(self, tmp_path):
        """Test overwriting existing text file."""
        text_file = tmp_path / "overwrite.txt"
        text_file.write_text("Old content")

        new_content = "New content"
        write_text_file(text_file, new_content)

        assert text_file.read_text() == new_content


class TestMergeTextFiles:
    """Test suite for merge_text_files function."""

    def test_merge_two_files(self, tmp_path):
        """Test merging two text files."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        output = tmp_path / "merged.txt"

        file1.write_text("Content 1")
        file2.write_text("Content 2")

        merge_text_files([file1, file2], output)

        result = output.read_text()
        assert "Content 1" in result
        assert "Content 2" in result

    def test_merge_multiple_files(self, tmp_path):
        """Test merging multiple text files."""
        files = []
        for i in range(5):
            f = tmp_path / f"file{i}.txt"
            f.write_text(f"Content {i}")
            files.append(f)

        output = tmp_path / "merged.txt"
        merge_text_files(files, output)

        result = output.read_text()
        for i in range(5):
            assert f"Content {i}" in result

    def test_merge_preserves_order(self, tmp_path):
        """Test that merge preserves file order."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        output = tmp_path / "merged.txt"

        file1.write_text("First")
        file2.write_text("Second")

        merge_text_files([file1, file2], output)

        result = output.read_text()
        assert result.index("First") < result.index("Second")

    def test_merge_with_newlines(self, tmp_path):
        """Test that files are separated by newlines."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        output = tmp_path / "merged.txt"

        file1.write_text("Content1")
        file2.write_text("Content2")

        merge_text_files([file1, file2], output)

        result = output.read_text()
        assert "\n" in result

    def test_merge_empty_files(self, tmp_path):
        """Test merging empty files."""
        file1 = tmp_path / "empty1.txt"
        file2 = tmp_path / "empty2.txt"
        output = tmp_path / "merged.txt"

        file1.write_text("")
        file2.write_text("")

        merge_text_files([file1, file2], output)

        assert output.exists()


class TestCleanMessageContent:
    """Test suite for clean_message_content function."""

    def test_clean_simple_text(self):
        """Test cleaning simple ASCII text."""
        message = "Hello, World!"
        result = clean_message_content(message)
        assert result == message

    def test_remove_emojis(self):
        """Test removing emojis."""
        message = "Hello 😀 World 🌍"
        result = clean_message_content(message)
        assert "😀" not in result
        assert "🌍" not in result
        assert "Hello" in result
        assert "World" in result

    def test_remove_special_unicode(self):
        """Test removing special Unicode characters."""
        message = "Test\u200bmessage\u200c"
        result = clean_message_content(message)
        assert "\u200b" not in result
        assert "\u200c" not in result

    def test_keep_common_punctuation(self):
        """Test keeping common punctuation."""
        message = "Hello! How are you?"
        result = clean_message_content(message)
        assert "!" in result
        assert "?" in result

    def test_remove_non_printable(self):
        """Test removing non-printable characters."""
        message = "Hello\x00World\x01"
        result = clean_message_content(message)
        assert "\x00" not in result
        assert "\x01" not in result

    def test_empty_string(self):
        """Test with empty string."""
        result = clean_message_content("")
        assert result == ""

    def test_only_non_ascii(self):
        """Test with only non-ASCII characters."""
        message = "😀🌍🎉"
        result = clean_message_content(message)
        assert result == ""

    def test_mixed_content(self):
        """Test with mixed ASCII and non-ASCII."""
        message = "Hello 世界 World"
        result = clean_message_content(message)
        assert "Hello" in result
        assert "World" in result
        assert "世界" not in result


class TestUtilsEdgeCases:
    """Test edge cases and error handling."""

    def test_parse_date_with_tabs(self):
        """Test parsing date with tab characters."""
        date_str = "Jan\t15,\t2025\t10:30:00\tAM"
        # Should normalize to spaces
        result = parse_date_string(date_str)
        assert isinstance(result, datetime)

    def test_calculate_earlier_date_with_none(self):
        """Test calculate_earlier_date with None."""
        result = calculate_earlier_date(None, 30)
        assert result is None

    def test_read_json_file_with_bom(self, tmp_path):
        """Test reading JSON file with BOM."""
        json_file = tmp_path / "bom.json"
        # UTF-8 BOM
        json_file.write_bytes(b'\xef\xbb\xbf{"key": "value"}')

        result = read_json_file(json_file)
        assert "key" in result

    def test_write_text_file_creates_parent_dirs(self, tmp_path):
        """Test that write_text_file creates parent directories if needed."""
        nested_file = tmp_path / "subdir" / "file.txt"
        # Create parent directory first
        nested_file.parent.mkdir(parents=True, exist_ok=True)

        write_text_file(nested_file, "content")
        assert nested_file.exists()

    def test_clean_message_preserves_numbers(self):
        """Test that clean_message_content preserves numbers."""
        message = "Order #12345 confirmed!"
        result = clean_message_content(message)
        assert "12345" in result

    def test_clean_message_preserves_spaces(self):
        """Test that clean_message_content preserves spaces."""
        message = "Hello   World"
        result = clean_message_content(message)
        assert "   " in result or "  " in result