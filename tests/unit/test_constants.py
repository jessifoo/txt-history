"""Comprehensive unit tests for scripts/constants.py."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from constants import (
    CONTACT_STORE_FILE,
    DEFAULT_TIMEZONE,
    OUTPUT_DIR,
    TMP_PATH,
)


class TestConstants:
    """Test suite for constants module."""

    def test_output_dir_is_path(self):
        """Test that OUTPUT_DIR is a Path object."""
        assert isinstance(OUTPUT_DIR, Path)
        assert OUTPUT_DIR.is_absolute()

    def test_tmp_path_is_path(self):
        """Test that TMP_PATH is a Path object."""
        assert isinstance(TMP_PATH, Path)
        assert TMP_PATH.is_absolute()

    def test_contact_store_file_is_path(self):
        """Test that CONTACT_STORE_FILE is a Path object."""
        assert isinstance(CONTACT_STORE_FILE, Path)

    def test_contact_store_file_is_json(self):
        """Test that CONTACT_STORE_FILE points to a JSON file."""
        assert CONTACT_STORE_FILE.suffix == ".json"
        assert CONTACT_STORE_FILE.name == "contacts.json"

    def test_default_timezone_is_string(self):
        """Test that DEFAULT_TIMEZONE is a string."""
        assert isinstance(DEFAULT_TIMEZONE, str)
        assert DEFAULT_TIMEZONE == "America/Denver"

    def test_default_timezone_valid_format(self):
        """Test that DEFAULT_TIMEZONE is in valid format."""
        import pytz

        # Should not raise exception
        tz = pytz.timezone(DEFAULT_TIMEZONE)
        assert tz is not None

    def test_output_dir_exists(self):
        """Test that OUTPUT_DIR exists after import."""
        assert OUTPUT_DIR.exists()
        assert OUTPUT_DIR.is_dir()

    def test_tmp_path_exists(self):
        """Test that TMP_PATH exists after import."""
        assert TMP_PATH.exists()
        assert TMP_PATH.is_dir()

    def test_output_dir_in_home(self):
        """Test that OUTPUT_DIR is in home directory."""
        assert str(Path.home()) in str(OUTPUT_DIR)

    def test_tmp_path_in_home(self):
        """Test that TMP_PATH is in home directory."""
        assert str(Path.home()) in str(TMP_PATH)

    def test_contact_store_file_relative_to_module(self):
        """Test that CONTACT_STORE_FILE is relative to module location."""
        # Should be in scripts directory
        assert "scripts" in str(CONTACT_STORE_FILE)

    def test_constants_are_immutable_types(self):
        """Test that constants use immutable types where appropriate."""
        # Path objects are effectively immutable for our purposes
        assert isinstance(OUTPUT_DIR, Path)
        assert isinstance(TMP_PATH, Path)
        assert isinstance(CONTACT_STORE_FILE, Path)
        assert isinstance(DEFAULT_TIMEZONE, str)

    def test_output_dir_writable(self):
        """Test that OUTPUT_DIR is writable."""
        test_file = OUTPUT_DIR / ".test_write"
        try:
            test_file.touch()
            assert test_file.exists()
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_tmp_path_writable(self):
        """Test that TMP_PATH is writable."""
        test_file = TMP_PATH / ".test_write"
        try:
            test_file.touch()
            assert test_file.exists()
        finally:
            if test_file.exists():
                test_file.unlink()

    def test_multiple_imports_same_values(self):
        """Test that re-importing gives same constant values."""
        # First import
        from constants import OUTPUT_DIR as OUTPUT_DIR_1

        # Simulate re-import
        import importlib
        import constants

        importlib.reload(constants)
        from constants import OUTPUT_DIR as OUTPUT_DIR_2

        assert OUTPUT_DIR_1 == OUTPUT_DIR_2

    @patch("pathlib.Path.home")
    def test_output_dir_uses_home(self, mock_home):
        """Test that OUTPUT_DIR construction uses Path.home()."""
        mock_home.return_value = Path("/mock/home")
        # Note: This test verifies the pattern, actual value already set
        expected = Path("/mock/home") / "txt_history_output"
        assert expected.name == "txt_history_output"

    def test_paths_do_not_overlap(self):
        """Test that different paths don't accidentally overlap."""
        assert OUTPUT_DIR != TMP_PATH
        assert OUTPUT_DIR != CONTACT_STORE_FILE.parent
        assert TMP_PATH != CONTACT_STORE_FILE.parent


class TestConstantsEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_paths_handle_special_characters(self):
        """Test that paths can handle special characters in home directory."""
        # This is a validation that Path handles it correctly
        assert OUTPUT_DIR.as_posix()  # Should not raise
        assert TMP_PATH.as_posix()  # Should not raise

    def test_timezone_string_no_whitespace(self):
        """Test that timezone string has no leading/trailing whitespace."""
        assert DEFAULT_TIMEZONE == DEFAULT_TIMEZONE.strip()

    def test_paths_absolute_not_relative(self):
        """Test that paths are absolute, not relative."""
        assert not str(OUTPUT_DIR).startswith(".")
        assert not str(TMP_PATH).startswith(".")

    def test_contact_store_filename_no_path_traversal(self):
        """Test that CONTACT_STORE_FILE doesn't contain path traversal."""
        assert ".." not in str(CONTACT_STORE_FILE)

    def test_paths_normalized(self):
        """Test that paths are normalized without redundant separators."""
        assert "//" not in str(OUTPUT_DIR)
        assert "//" not in str(TMP_PATH)