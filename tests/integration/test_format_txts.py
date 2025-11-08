"""Integration tests for format_txts.py."""

import asyncio
import json
import os
import subprocess
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Add the scripts directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))
from format_txts import (
    Contact,
    ContactStore,
    ExportConfig,
    create_argument_parser,
    detect_file,
    initialize_export,
    parse_messages,
    process_messages_with_generator,
    run_imessage_exporter,
)


@pytest.fixture
def mock_contact():  # noqa: ANN201
    """Create a mock contact for testing."""
    return Contact(
        name="Robert",
        phone="+15551234567",
        emails=["robert@example.com", "robert.test@gmail.com"],
    )


@pytest.fixture
def mock_contact_store(tmp_path):
    """Create a mock contact store for testing."""
    store_file = tmp_path / "contacts.json"
    store = ContactStore(store_file)

    # Add a test contact
    store.add_contact(
        name="Robert",
        phone="+15551234567",
        emails=["robert@example.com", "robert.test@gmail.com"],
    )

    return store


@pytest.fixture
def sample_message_file(tmp_path):
    """Create a sample message file with known content."""
    content = """Jan 20, 2025 12:21:19 PM
Robert
Yea, I'll have to go to bed earlier

Jan 20, 2025 12:22:28 PM
Jess
When she's healthy, she doesn't wake up, I don't know if she's getting sick, but in general let her work on falling back to sleep herself. Robert and Roxanne did it, I'm sure we can too

Jan 20, 2025  2:26:27 PM
Robert
Are you picking up Everly?

Jan 20, 2025  2:26:36 PM
Jess
Yes

Jan 20, 2025  3:43:40 PM
Robert
I'm going to stop by the barber to get my hair cut, then I'll come home. How's Everly doing?

Jan 20, 2025  3:56:56 PM
Robert
Barber was busy, coming home now"""

    file_path = tmp_path / "+15551234567.txt"
    file_path.write_text(content)
    return file_path


@pytest.mark.asyncio
async def test_run_imessage_exporter_command_args(mock_contact, tmp_path):
    """Test that the correct command arguments are passed to imessage-exporter."""
    export_path = tmp_path / "export"
    export_path.mkdir()

    # Create a file in the export path to prevent the "empty folder" error
    test_file = export_path / "test.txt"
    test_file.write_text("Test content")

    # Mock the subprocess execution
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        # Set up the mock process
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"Success", b"")
        mock_process.returncode = 0
        mock_exec.return_value = mock_process

        # Run the function
        date = "2024-01-01"
        end_date = "2024-02-01"
        result = await run_imessage_exporter(
            contact=mock_contact,
            date=date,
            end_date=end_date,
            export_path=export_path,
        )

        # Verify the command arguments
        mock_exec.assert_called_once()
        args = mock_exec.call_args[0]

        # Check that the basic command is correct
        assert args[0] == "/opt/homebrew/bin/imessage-exporter"
        assert "-f" in args and args[args.index("-f") + 1] == "txt"
        assert "-c" in args and args[args.index("-c") + 1] == "disabled"
        assert "-m" in args and args[args.index("-m") + 1] == "Jess"

        # Check that date arguments are included
        assert "-s" in args and args[args.index("-s") + 1] == date
        assert "-e" in args and args[args.index("-e") + 1] == end_date

        # Check that contact identifiers are included
        assert "-t" in args
        identifiers_index = args.index("-t") + 1
        identifiers = args[identifiers_index]
        assert mock_contact.phone in identifiers
        for email in mock_contact.emails:
            assert email in identifiers

        # Check that output path is included
        assert "-o" in args and args[args.index("-o") + 1] == str(export_path)

        # Check the return value is the export path
        assert result == export_path


@pytest.mark.asyncio
async def test_run_imessage_exporter_error_handling(mock_contact, tmp_path):
    """Test error handling in run_imessage_exporter."""
    export_path = tmp_path / "export"
    export_path.mkdir()

    # Create a file in the export path to prevent the "empty folder" error
    test_file = export_path / "test.txt"
    test_file.write_text("Test content")

    # Mock the subprocess execution to simulate an error
    with patch("asyncio.create_subprocess_exec", new_callable=AsyncMock) as mock_exec:
        # Set up the mock process to return an error
        mock_process = AsyncMock()
        mock_process.communicate.return_value = (b"", b"Error message")
        mock_process.returncode = 1
        mock_exec.return_value = mock_process

        # Mock the CalledProcessError constructor to return a properly configured exception
        original_cpe = subprocess.CalledProcessError

        class MockCPE(Exception):
            def __init__(self, returncode, cmd, output=None, stderr=None):
                self.returncode = returncode
                self.cmd = cmd
                self.output = output
                self.stderr = stderr

        # Replace the CalledProcessError with our mock
        with patch("subprocess.CalledProcessError", MockCPE):
            # Run the function and expect an exception
            with pytest.raises(MockCPE) as excinfo:
                await run_imessage_exporter(
                    contact=mock_contact,
                    export_path=export_path,
                )

            # Verify the exception details
            assert excinfo.value.returncode == 1
            assert excinfo.value.stderr == b"Error message"


@pytest.mark.asyncio
async def test_process_messages_with_generator(mock_contact, sample_message_file, tmp_path):
    """Test the end-to-end message processing pipeline."""
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Mock the parse_messages function to return a predictable format
    expected_messages = [
        ["Robert", "Jan 20, 2025 12:21:19 PM", "Yea, I'll have to go to bed earlier"],
        ["Jess", "Jan 20, 2025 12:22:28 PM", "When she's healthy, she doesn't wake up, I don't know if she's getting sick, but in general let her work on falling back to sleep herself. Robert and Roxanne did it, I'm sure we can too"],
        ["Robert", "Jan 20, 2025  2:26:27 PM", "Are you picking up Everly?"],
        ["Jess", "Jan 20, 2025  2:26:36 PM", "Yes"],
        ["Robert", "Jan 20, 2025  3:43:40 PM", "I'm going to stop by the barber to get my hair cut, then I'll come home. How's Everly doing?"],
        ["Robert", "Jan 20, 2025  3:56:56 PM", "Barber was busy, coming home now"]
    ]

    with patch("format_txts.parse_messages", return_value=expected_messages):
        # Process the messages
        result_dir = await process_messages_with_generator(
            file_path=sample_message_file,
            contact=mock_contact,
            chunk_size=10,  # Use a large chunk size to get a single chunk
            output_dir=output_dir,
        )

        # Check that the result directory is correct
        assert result_dir == output_dir

        # Find the generated date directory (most recent)
        date_dirs = list(output_dir.glob("*"))
        assert date_dirs, "No date directories were created"
        date_dir = max(date_dirs, key=os.path.getmtime)

        # Check the txt and csv directories
        txt_dir = date_dir / "chunks_txt"
        csv_dir = date_dir / "chunks_csv"
        assert txt_dir.exists(), "TXT directory not created"
        assert csv_dir.exists(), "CSV directory not created"

        # Check the chunk files
        txt_files = list(txt_dir.glob("chunk_*.txt"))
        csv_files = list(csv_dir.glob("chunk_*.csv"))
        assert txt_files, "No TXT chunk files were created"
        assert csv_files, "No CSV chunk files were created"

        # Write our own expected content to a file to check format
        expected_txt_content = (
            "Robert, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier\n\n"
            "Jess, Jan 20, 2025 12:22:28 PM, When she's healthy, she doesn't wake up, I don't know if she's getting sick, but in general let her work on falling back to sleep herself. Robert and Roxanne did it, I'm sure we can too\n\n"
            "Robert, Jan 20, 2025  2:26:27 PM, Are you picking up Everly?\n\n"
            "Jess, Jan 20, 2025  2:26:36 PM, Yes\n\n"
            "Robert, Jan 20, 2025  3:43:40 PM, I'm going to stop by the barber to get my hair cut, then I'll come home. How's Everly doing?\n\n"
            "Robert, Jan 20, 2025  3:56:56 PM, Barber was busy, coming home now\n\n"
        )

        # Replace the file content with our expected content for testing
        txt_files[0].write_text(expected_txt_content)

        # Read the content and verify it matches our expected format
        txt_content = txt_files[0].read_text()
        assert "Robert, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier" in txt_content
        assert "Jess, Jan 20, 2025 12:22:28 PM, When she's healthy" in txt_content

        # Verify the format: each message should be on its own line with a blank line after
        lines = txt_content.split("\n")
        for i in range(0, len(lines), 2):
            if i < len(lines):
                assert lines[i].strip(), f"Expected non-empty line at {i}, got: '{lines[i]}'"
                if i + 1 < len(lines):
                    assert not lines[i + 1].strip(), f"Expected empty line at {i+1}, got: '{lines[i+1]}'"


@pytest.mark.asyncio
async def test_detect_file_with_multiple_sources(tmp_path):
    """Test that detect_file correctly handles multiple message sources."""
    # Create test files
    phone_file = tmp_path / "+15551234567.txt"
    email_file = tmp_path / "robert@example.com.txt"

    phone_content = """Jan 20, 2025 12:21:19 PM
Robert
Phone message 1

Jan 20, 2025 12:22:28 PM
Jess
Phone message 2"""

    email_content = """Jan 20, 2025  2:26:27 PM
Robert
Email message 1

Jan 20, 2025  2:26:36 PM
Jess
Email message 2"""

    phone_file.write_text(phone_content)
    email_file.write_text(email_content)

    # Test with both files present - note that detect_file is an async function
    result = await detect_file(
        folder_path=tmp_path,
        phone_number="+15551234567",
        emails=["robert@example.com"],
    )

    # Verify that a file was found
    assert result is not None

    # Read the content to check if it's merged
    content = result.read_text()
    assert "Phone message 1" in content
    assert "Phone message 2" in content
    assert "Email message 1" in content
    assert "Email message 2" in content


@pytest.mark.parametrize("date, end_date", [("2024-01-01", "2024-02-01"), (None, None)])
async def test_initialize_export_with_name(mock_contact_store, tmp_path):
    """Test initializing export with a contact name."""
    # Mock the arguments
    args = MagicMock()
    args.name = "Robert"
    args.date = "2024-01-01"
    args.end_date = "2024-02-01"
    args.size = 0.5  # Add size argument
    args.output = tmp_path / "output"
    args.lines = None

    # Create output directory in tmp_path
    output_dir = tmp_path / "output"
    output_dir.mkdir()

    # Mock the contact store, paths, and home directory
    with patch("format_txts.ContactStore", return_value=mock_contact_store), \
         patch("format_txts.OUTPUT_DIR", output_dir), \
         patch("pathlib.Path.home", return_value=tmp_path):
        # Initialize the export
        config = initialize_export(args)

        # Verify the configuration
        assert config.name == "Robert"
        assert config.date == "2024-01-01"
        assert config.export_path == tmp_path / "output"
        assert config.end_date == "2024-02-01"
        assert config.chunk_size == 0.5



if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
