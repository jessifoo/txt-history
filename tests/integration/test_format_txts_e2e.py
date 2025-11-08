"""End-to-end integration tests for format_txts.py."""

import asyncio
import json
import os
import pytest
import shutil
import subprocess
from pathlib import Path
from unittest.mock import patch, AsyncMock, MagicMock, call

import sys
# Add the scripts directory to the path
sys.path.append(str(Path(__file__).parent.parent.parent / "scripts"))

from format_txts import (
    main,
    run_imessage_exporter,
    Contact,
    ContactStore,
    parse_arguments,
    process_with_retry,
)


@pytest.fixture
def setup_test_environment(tmp_path):
    """Set up a complete test environment with necessary directories and files."""
    # Create the base directories
    export_dir = tmp_path / "imessage_export"
    output_dir = tmp_path / "output"
    contacts_dir = tmp_path / "contacts"
    
    export_dir.mkdir()
    output_dir.mkdir()
    contacts_dir.mkdir()
    
    # Create a sample contacts file
    contacts_file = contacts_dir / "contacts.json"
    contacts_data = {
        "contacts": {
            "Robert": {
                "name": "Robert",
                "phone": "+15551234567",
                "emails": ["robert@example.com", "robert.test@gmail.com"],
                "metadata": {
                    "type": "regular",
                    "created_at": "2024-01-01T00:00:00",
                    "last_used": "2024-01-01T00:00:00"
                }
            }
        }
    }
    contacts_file.write_text(json.dumps(contacts_data, indent=2))
    
    # Create sample message files in the export directory
    phone_file = export_dir / "+15551234567.txt"
    email_file = export_dir / "robert@example.com.txt"
    
    phone_content = """Jan 20, 2025 12:21:19 PM
Robert
Yea, I'll have to go to bed earlier

Jan 20, 2025 12:22:28 PM
Jess
When she's healthy, she doesn't wake up, I don't know if she's getting sick, but in general let her work on falling back to sleep herself. Robert and Roxanne did it, I'm sure we can too"""

    email_content = """Jan 20, 2025  2:26:27 PM
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
    
    phone_file.write_text(phone_content)
    email_file.write_text(email_content)
    
    # Return the paths and a cleanup function
    yield {
        "export_dir": export_dir,
        "output_dir": output_dir,
        "contacts_file": contacts_file,
        "phone_file": phone_file,
        "email_file": email_file,
    }


@pytest.mark.asyncio
async def test_e2e_command_line_processing(setup_test_environment, monkeypatch):
    """Test the end-to-end processing from command line arguments to output files."""
    env = setup_test_environment
    
    # Mock the command line arguments
    test_args = [
        "-n", "Robert",
        "-d", "2024-01-01",
        "-s", "0.5",
    ]
    
    # Mock the paths and environment
    monkeypatch.setattr("format_txts.CONTACT_STORE_FILE", env["contacts_file"])
    monkeypatch.setattr("format_txts.OUTPUT_DIR", env["output_dir"])
    monkeypatch.setattr("pathlib.Path.home", lambda: env["export_dir"].parent)
    
    # Mock the run_imessage_exporter function to return our test export directory
    async def mock_run_imessage_exporter(*args, **kwargs):
        return env["export_dir"]
    
    # Patch the necessary functions
    with patch("format_txts.run_imessage_exporter", mock_run_imessage_exporter):
        # Run the main function with our test arguments
        with patch("sys.argv", ["format_txts.py"] + test_args):
            await main()
    
    # Verify the output directory structure
    date_dirs = list(env["output_dir"].glob("*"))
    assert date_dirs, "No date directories were created"
    
    # Get the most recent date directory
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
    
    # Check the content of the TXT file
    txt_content = txt_files[0].read_text()
    
    # Verify the format matches our expected output format
    assert "Robert, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier" in txt_content
    assert "Jess, Jan 20, 2025 12:22:28 PM, When she's healthy" in txt_content
    
    # Verify the CSV file has the correct structure with ID column
    import csv
    with open(csv_files[0], 'r') as f:
        reader = csv.reader(f)
        header = next(reader)
        assert header == ["ID", "Sender", "Date", "Message"], f"Unexpected CSV header: {header}"
        
        # Check the first row
        first_row = next(reader)
        assert len(first_row) == 4, f"Unexpected CSV row length: {len(first_row)}"
        assert first_row[0] == "1", f"Expected ID to be 1, got: {first_row[0]}"
        assert first_row[1] in ["Robert", "Jess"], f"Unexpected sender: {first_row[1]}"


@pytest.mark.asyncio
async def test_process_with_retry_logic(setup_test_environment, monkeypatch):
    """Test the retry logic when imessage-exporter fails."""
    env = setup_test_environment
    
    # Mock the necessary paths
    monkeypatch.setattr("format_txts.CONTACT_STORE_FILE", env["contacts_file"])
    monkeypatch.setattr("format_txts.OUTPUT_DIR", env["output_dir"])
    
    # Create a contact and config for testing
    contact = Contact(
        name="Robert",
        phone="+15551234567",
        emails=["robert@example.com"],
    )
    
    # Mock the ExportConfig
    from format_txts import ExportConfig
    config = ExportConfig(
        export_path=env["export_dir"],
        name="Robert",
        date="2024-01-01",
        end_date=None,
        chunk_size=0.5,
    )
    
    # Mock the args
    args = MagicMock()
    args.name = "Robert"
    args.date = "2024-01-01"
    args.end_date = None
    args.size = 0.5
    args.lines = None
    
    # First, test successful processing without retry
    with patch("format_txts.run_imessage_exporter", new_callable=AsyncMock) as mock_exporter:
        mock_exporter.return_value = env["export_dir"]
        
        # Mock the input function to avoid prompts
        with patch("builtins.input", return_value="n"):
            await process_with_retry(config, contact, args, prompt_for_retry=False)
        
        # Verify run_imessage_exporter was called once with the correct arguments
        mock_exporter.assert_called_once()
        call_args = mock_exporter.call_args[0]
        assert call_args[0] == contact
        assert call_args[1] == "2024-01-01"
    
    # Now test retry logic with a failure then success
    with patch("format_txts.run_imessage_exporter", new_callable=AsyncMock) as mock_exporter:
        # First call fails, second call succeeds
        mock_exporter.side_effect = [
            subprocess.CalledProcessError(1, "cmd", b"", b"Error"),
            env["export_dir"]
        ]
        
        # Mock the input function to simulate user choosing to retry
        with patch("builtins.input", return_value="y"):
            await process_with_retry(config, contact, args, prompt_for_retry=True)
        
        # Verify run_imessage_exporter was called twice
        assert mock_exporter.call_count == 2
        
        # Check that the second call used an earlier date
        first_call = mock_exporter.call_args_list[0]
        second_call = mock_exporter.call_args_list[1]
        
        # The date in the second call should be earlier than the first call
        assert first_call[0][1] == "2024-01-01"
        assert second_call[0][1] < "2024-01-01"


@pytest.mark.asyncio
async def test_command_line_argument_parsing():
    """Test parsing of command line arguments."""
    # Test with name only
    args = parse_arguments(["-n", "Robert"])
    assert args.name == "Robert"
    assert args.date is None
    assert args.size is None
    assert args.lines is None
    
    # Test with all arguments
    args = parse_arguments([
        "-n", "Robert",
        "-d", "2024-01-01",
        "-e", "2024-02-01",
        "-s", "0.5",
        "-l", "100",
    ])
    assert args.name == "Robert"
    assert args.date == "2024-01-01"
    assert args.end_date == "2024-02-01"
    assert args.size == 0.5
    assert args.lines == 100
    
    # Test with mutually exclusive arguments (size and lines)
    with pytest.raises(SystemExit):
        parse_arguments(["-n", "Robert", "-s", "0.5", "-l", "100"])


if __name__ == "__main__":
    pytest.main(["-xvs", __file__])
