import json
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, mock_open
from datetime import datetime
import argparse
import shutil
import subprocess
import re

from txt_history.scripts.format_txts import (
    ExportConfig,
    initialize_export,
    parse_arguments,
    setup_contact,
    Contact,
    ContactStore,
    ContactMetadata,
    process_messages_with_generator,
    message_generator,
    OUTPUT_DIR,
    write_chunk
)


# Test Data Fixtures
@pytest.fixture
def mock_contact_data():
    """Fixture providing test contact data in proper JSON format."""
    return json.dumps({
        "contacts": {
            "Phil": {
                "name": "Phil",
                "phone": "+18673335566",
                "email": "phil@example.com",
                "metadata": {
                    "type": "default",
                    "created_at": "2024-01-01",
                    "last_used": "2024-01-01"
                }
            }
        }
    })


@pytest.fixture
def mock_contact_store(mock_contact_data):
    """Fixture providing a ContactStore with mocked file operations."""
    with patch("builtins.open", mock_open(read_data=mock_contact_data)), \
         patch("json.dump"):
        store = ContactStore(Path("test_contacts.json"))
        yield store


def test_export_config_initialization():
    """Test the initialization and validation of export configuration."""
    from argparse import Namespace
    from pathlib import Path
    
    # Test default behavior
    args = Namespace(
        name=None,  # Should default to "Phil"
        output=None,  # Should default to ~/imessage_export
        date=None,
        end_date=None,
        lines=None,
        size=None
    )
    
    config = initialize_export(args)
    assert config.name == "Phil"  # Default name
    assert config.export_path == Path.home() / "imessage_export"  # Default path
    assert config.date is None
    assert config.end_date is None
    assert config.chunk_size is None

    # Test custom path handling
    custom_path = Path("/tmp/custom/export/path")
    args = Namespace(
        name="Robert",
        output=custom_path,
        date="2024-01-01",
        end_date="2024-02-01",
        lines=500,
        size=None
    )
    
    config = initialize_export(args)
    assert config.name == "Robert"
    assert config.export_path == custom_path
    assert config.date == "2024-01-01"
    assert config.end_date == "2024-02-01"
    assert config.chunk_size == 500

    # Test path creation
    assert OUTPUT_DIR.exists(), "Export directory should be created"


def test_argument_validation():
    """Test argument validation for mutually exclusive options."""
    # Arrange & Act & Assert
    with pytest.raises(SystemExit):
        parse_arguments(["-s", "0.5", "-l", "500"])


def test_contact_setup(mock_contact_store):
    """Test contact setup and retrieval functionality."""
    # Test creating a new contact
    with patch("builtins.input", return_value="1234567890"):
        new_contact = setup_contact("NewPerson", mock_contact_store)
        assert isinstance(new_contact, Contact)
        assert new_contact.name == "NewPerson"
        assert new_contact.phone == "+11234567890"  # Should be normalized

    # Test retrieving an existing contact
    existing_contact = setup_contact("Phil", mock_contact_store)
    assert isinstance(existing_contact, Contact)
    assert existing_contact.name == "Phil"
    assert existing_contact.phone == "+18673335566"
    assert existing_contact.email == "phil@example.com"


def test_contact_from_dict():
    """Test Contact creation from dictionary representations."""
    # Arrange: Complete contact data
    complete_data = {
        "name": "Phil",
        "phone": "+18673335566",
        "email": "phil@example.com",
        "metadata": {
            "type": "default",
            "created_at": "2024-01-01",
            "last_used": "2024-01-01"
        }
    }
    
    # Act: Create contact from complete data
    contact = Contact.from_dict(complete_data)
    
    # Assert: Verify all fields
    assert isinstance(contact, Contact)
    assert contact.name == "Phil"
    assert contact.phone == "+18673335566"
    assert contact.email == "phil@example.com"
    assert isinstance(contact.metadata, ContactMetadata)
    assert contact.metadata.type == "default"
    assert contact.metadata.created_at == "2024-01-01"
    assert contact.metadata.last_used == "2024-01-01"

    # Arrange: Minimal contact data
    minimal_data = {
        "name": "Phil",
        "phone": "+18673335566"
    }
    
    # Act: Create contact from minimal data
    contact = Contact.from_dict(minimal_data)
    
    # Assert: Verify required fields and optional fields are None
    assert contact.name == "Phil"
    assert contact.phone == "+18673335566"
    assert contact.email is None
    assert contact.metadata is None


def test_message_formatting():
    """Test the core message formatting functionality."""
    # Setup test data
    test_messages = """Jan 20, 2025 12:21:19 PM
+18673335566
Yea, I'll have to go to bed earlier

Jan 20, 2025 12:22:28 PM
+16045551234
When she's healthy, she doesn't wake up

Jan 20, 2025 2:26:27 PM
+18673335566
Are you picking up Everly?
"""
    
    # Create a temporary message file
    message_file = Path("test_messages.txt")
    with open(message_file, "w") as f:
        f.write(test_messages)
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Create test contact
        contact = Contact(
            name="Phil",
            phone="+18673335566",
            email=None
        )
        
        # Process messages
        process_messages_with_generator(
            file_path=message_file,
            contact=contact,
            chunk_size=2,  # Small chunk size for testing
            output_dir=OUTPUT_DIR
        )
        
        # Verify TXT output
        txt_file = OUTPUT_DIR / "chunk_1.txt"
        assert txt_file.exists()
        content = txt_file.read_text()
        
        # Check format and spacing
        lines = content.split("\n")
        assert lines[0] == ""  # Empty line at start
        assert "Phil, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier" in content
        assert "Jess, Jan 20, 2025 12:22:28 PM, When she's healthy, she doesn't wake up" in content
        
        # Verify empty lines between messages
        message_lines = [l for l in lines if l.strip()]
        for i in range(len(message_lines) - 1):
            assert lines[lines.index(message_lines[i]) + 1] == ""
        
        # Verify CSV output
        csv_file = OUTPUT_DIR / "chunk_1.csv"
        assert csv_file.exists()
        csv_content = csv_file.read_text()
        
        # Check CSV has no empty lines
        csv_lines = csv_content.split("\n")
        assert all(line.strip() for line in csv_lines if line)
        
        # Verify sender replacement
        assert "+16045551234" not in content
        assert "+16045551234" not in csv_content
        assert "Jess" in content
        assert "Jess" in csv_content
        
    finally:
        # Cleanup
        if message_file.exists():
            message_file.unlink()
        for f in OUTPUT_DIR.glob("chunk_*.txt"):
            f.unlink()
        for f in OUTPUT_DIR.glob("chunk_*.csv"):
            f.unlink()


def test_message_formatting_core():
    """Test the core message formatting functionality without mocking iMessage export format."""
    # Test data - already in the format we want to validate
    messages = [
        ["Phil", "Jan 20, 2025 12:21:19 PM", "First message"],
        ["Jess", "Jan 20, 2025 12:22:28 PM", "Second message"],
        ["Phil", "Jan 20, 2025 2:26:27 PM", "Third message"]
    ]
    
    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    try:
        # Write chunks directly
        write_chunk(messages[:2], 1, OUTPUT_DIR)  # First chunk with 2 messages
        write_chunk(messages[2:], 2, OUTPUT_DIR)  # Second chunk with 1 message
        
        # Verify TXT output format
        txt_file = OUTPUT_DIR / "chunk_1.txt"
        assert txt_file.exists()
        content = txt_file.read_text()
        
        # Check format and spacing
        lines = content.split("\n")
        assert lines[0] == ""  # Empty line at start
        assert "Phil, Jan 20, 2025 12:21:19 PM, First message" in content
        assert "Jess, Jan 20, 2025 12:22:28 PM, Second message" in content
        
        # Verify empty lines between messages
        message_lines = [l for l in lines if l.strip()]
        for i in range(len(message_lines) - 1):
            assert lines[lines.index(message_lines[i]) + 1] == ""
        
        # Verify CSV output
        csv_file = OUTPUT_DIR / "chunk_1.csv"
        assert csv_file.exists()
        csv_content = csv_file.read_text()
        
        # Check CSV has no empty lines and correct format
        csv_lines = [l for l in csv_content.split("\n") if l.strip()]
        assert len(csv_lines) == 2  # Two messages
        assert "Phil,Jan 20, 2025 12:21:19 PM,First message" in csv_lines
        assert "Jess,Jan 20, 2025 12:22:28 PM,Second message" in csv_lines
        
    finally:
        # Cleanup
        for f in OUTPUT_DIR.glob("chunk_*.txt"):
            f.unlink()
        for f in OUTPUT_DIR.glob("chunk_*.csv"):
            f.unlink()


def test_end_to_end_flow():
    """Test the entire message processing flow."""
    # 1. Set up test arguments
    args = argparse.Namespace(
        size=None,        # MB per chunk
        lines=2,          # Messages per chunk
        date=None,        # No date filter
        end_date=None,    # No end date filter
        name="Phil",      # Use Phil as default
        output=None       # Use default output path
    )
    
    try:
        # 2. Initialize export config
        config = initialize_export(args)
        assert config.name == "Phil"
        assert config.chunk_size == 2
        
        # 3. Set up contact store and get contact
        contact_store = ContactStore(CONTACT_STORE_FILE)
        contact = setup_contact(config.name, contact_store)
        assert contact.name == "Phil"
        assert contact.phone == "+18673335566"
        
        # 4. Create a mock export directory with message file
        export_dir = Path("test_export")
        export_dir.mkdir(exist_ok=True)
        message_file = export_dir / "messages.txt"
        message_file.write_text(
            "Jan 20, 2025 12:21:19 PM\n"
            "+18673335566\n"
            "First message\n"
            "\n"
            "Jan 20, 2025 12:22:28 PM\n"
            "+16045551234\n"
            "Second message\n"
            "\n"
            "Jan 20, 2025 2:26:27 PM\n"
            "+18673335566\n"
            "Third message"
        )
        
        # 5. Process the messages
        process_messages_with_generator(
            file_path=message_file,
            contact=contact,
            chunk_size=config.chunk_size,
            output_dir=OUTPUT_DIR
        )
        
        # 6. Verify the output
        # First chunk should have 2 messages
        chunk1_txt = OUTPUT_DIR / "chunk_1.txt"
        assert chunk1_txt.exists()
        content = chunk1_txt.read_text()
        assert "Phil, Jan 20, 2025 12:21:19 PM, First message" in content
        assert "Jess, Jan 20, 2025 12:22:28 PM, Second message" in content
        
        # Second chunk should have 1 message
        chunk2_txt = OUTPUT_DIR / "chunk_2.txt"
        assert chunk2_txt.exists()
        content = chunk2_txt.read_text()
        assert "Phil, Jan 20, 2025 2:26:27 PM, Third message" in content
        
        # Check CSV files exist and have correct format
        chunk1_csv = OUTPUT_DIR / "chunk_1.csv"
        assert chunk1_csv.exists()
        content = chunk1_csv.read_text()
        assert "Phil,Jan 20, 2025 12:21:19 PM,First message" in content
        assert "Jess,Jan 20, 2025 12:22:28 PM,Second message" in content
        assert content.count("\n") == 2  # No extra newlines
        
        chunk2_csv = OUTPUT_DIR / "chunk_2.csv"
        assert chunk2_csv.exists()
        content = chunk2_csv.read_text()
        assert "Phil,Jan 20, 2025 2:26:27 PM,Third message" in content
        assert content.count("\n") == 1  # No extra newlines
        
    finally:
        # Clean up
        if export_dir.exists():
            shutil.rmtree(export_dir)
        for f in OUTPUT_DIR.glob("chunk_*.txt"):
            f.unlink()
        for f in OUTPUT_DIR.glob("chunk_*.csv"):
            f.unlink()


def test_end_to_end_script_execution(tmp_path):
    """
    End-to-end test that runs the actual format_txts script and validates output files.
    This test ensures the entire pipeline works as expected, from CLI to file output.
    """
    # Set up test date and name
    test_date = "2025-02-21"
    test_name = "Robert"
    
    # Create a temporary directory for output
    output_dir = tmp_path / "output"
    output_dir.mkdir()
    
    # Run the actual script using subprocess with poetry
    script_path = Path(__file__).parent.parent.parent / "src" / "txt_history" / "scripts" / "format_txts.py"
    cmd = [
        "poetry", "run", "python",
        str(script_path),
        "-d", test_date,
        "-n", test_name,
        "-o", str(output_dir)
    ]
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print("Script failed with error:")
        print(result.stderr)
        print("Script output:")
        print(result.stdout)
    assert result.returncode == 0, f"Script failed with error: {result.stderr}"
    
    # Verify output files exist
    output_files = list(output_dir.glob("chunk_*.txt"))
    assert len(output_files) > 0, "No output txt files were generated"
    
    # Check both txt and csv files
    for txt_file in output_files:
        csv_file = txt_file.with_suffix('.csv')
        assert txt_file.exists(), f"Expected txt file {txt_file} not found"
        assert csv_file.exists(), f"Expected csv file {csv_file} not found"
        
        # Validate txt file format
        with open(txt_file) as f:
            txt_content = f.read()
            lines = [line.strip() for line in txt_content.split("\n\n") if line.strip()]
            for line in lines:
                # Each line should match: Name, DateTime, Message
                match = re.match(r'^[^,]+, \w+ \d+, \d{4} \d{1,2}:\d{2}:\d{2} [AP]M, .+$', line)
                assert match, f"Invalid message format in txt file: {line}"
        
        # Validate csv file format
        with open(csv_file) as f:
            csv_content = f.read()
            csv_lines = [line.strip() for line in csv_content.split("\n") if line.strip()]
            for line in csv_lines:
                # CSV should have the same format but without blank lines
                match = re.match(r'^[^,]+, \w+ \d+, \d{4} \d{1,2}:\d{2}:\d{2} [AP]M, .+$', line)
                assert match, f"Invalid message format in csv file: {line}"
            
            # CSV should have no blank lines between entries
            assert len(csv_lines) == len([l for l in csv_content.split("\n") if l.strip()]), "CSV contains blank lines"
