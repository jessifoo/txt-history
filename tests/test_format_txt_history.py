import pytest
from pathlib import Path
import shutil
import tempfile
from datetime import datetime
import csv
from format_txt_history_full import (
    parse_messages,
    detect_file,
    chunk_messages,
    write_chunk_to_txt,
    combine_message_files,
)

@pytest.fixture
def sample_message_file(tmp_path):
    """Create a sample message file with known content."""
    content = '''Dec 17, 2024  4:31:51 PM
Jess
Ohh ok 16 mins at 425

Dec 17, 2024 10:14:08 PM (Read by Jess after 11 seconds)
apple@phil-g.com
I can take the night shift today and you can sleep through until ~7am if that works for you. If you'd rather do the night shift I need to get ready for bed now

Dec 17, 2024 10:15:02 PM (Read by them after 2 seconds)
Jess
Sure I can set an alarm for 7 but if she wakes up in the next little bit I'll still be up

Dec 17, 2024 10:17:23 PM (Read by Jess after 5 seconds)
apple@phil-g.com
Ok message me when you're laying down to sleep. Keep in mind that it may take me a bit longer than you to wake up from her crying depending on which sleep phase I am in, but I will hear it'''
    
    file_path = tmp_path / "messages.txt"
    file_path.write_text(content)
    return file_path

def test_parse_messages_basic(sample_message_file):
    """Test basic message parsing functionality."""
    messages = parse_messages(sample_message_file)
    assert len(messages) == 4
    
    # Check first message
    assert messages[0][0] == "Jess"  # sender
    assert messages[0][1] == "Dec 17, 2024  4:31:51 PM"  # date
    assert messages[0][2] == "Ohh ok 16 mins at 425"  # message

    # Check Phil's message (email should be mapped to Phil)
    assert messages[1][0] == "Phil"  # sender mapped from email
    assert "night shift" in messages[1][2]  # message content

def test_parse_messages_sender_mapping(sample_message_file):
    """Test that senders are mapped correctly."""
    messages = parse_messages(sample_message_file)
    
    # Check that Jess remains Jess
    jess_messages = [m for m in messages if m[0] == "Jess"]
    assert len(jess_messages) == 2
    
    # Check that Phil's email is mapped to Phil
    phil_messages = [m for m in messages if m[0] == "Phil"]
    assert len(phil_messages) == 2

def test_detect_file(tmp_path):
    """Test file detection logic."""
    # Create test files
    phone_file = tmp_path / "+1234567890.txt"
    email_file = tmp_path / "apple@phil-g.com.txt"
    phone_file.touch()
    email_file.touch()

    # Test phone number priority
    result = detect_file(tmp_path, "+1234567890", "apple@phil-g.com")
    assert result == phone_file

    # Test email fallback
    phone_file.unlink()
    result = detect_file(tmp_path, "+1234567890", "apple@phil-g.com")
    assert result == email_file

    # Test no matching files
    email_file.unlink()
    with pytest.raises(FileNotFoundError):
        detect_file(tmp_path, "+1234567890", "apple@phil-g.com")

def test_detect_file_combines_messages(tmp_path):
    """Test that detect_file combines phone and email messages when both exist."""
    # Create test files
    phone_file = tmp_path / "+1234567890.txt"
    email_file = tmp_path / "apple@phil-g.com.txt"
    
    # Write test content
    phone_file.write_text('''Dec 17, 2024  4:31:51 PM
Jess
Message 1''')
    
    email_file.write_text('''Dec 17, 2024  5:31:51 PM
apple@phil-g.com
Message 2''')
    
    # Test that both files are combined
    result = detect_file(tmp_path, "+1234567890", "apple@phil-g.com")
    assert result == tmp_path / "combined_+1234567890.txt"
    
    # Verify combined content
    content = result.read_text()
    assert "Message 1" in content
    assert "Message 2" in content
    assert content.count("\n\n") == 2  # Two messages with blank lines between

@pytest.fixture
def sample_messages():
    """Create a sample list of messages for chunking tests."""
    return [
        ["Jess", "Aug 30, 2024 10:42:49 PM", "I totally forgot"],
        ["Jess", "Aug 31, 2024 12:33:42 AM", "Look outside"],
        ["Jess", "Aug 31, 2024 12:33:46 AM", "Go outside and look up"],
        ["Rhonda", "Aug 31, 2024 11:29:50 AM", "Oh shit. I would have liked that."],
    ]

def test_chunk_messages(tmp_path, sample_messages):
    """Test message chunking functionality."""
    # Test with very small chunk size to force multiple chunks
    output_dir = chunk_messages(sample_messages, tmp_path, 0.0001)
    
    # Check directory structure
    assert (output_dir / "_chunks_csv").exists()
    assert (output_dir / "_chunks_txt").exists()
    
    # Check that files were created
    csv_files = list((output_dir / "_chunks_csv").glob("chunk_*.csv"))
    txt_files = list((output_dir / "_chunks_txt").glob("chunk_*.txt"))
    assert len(csv_files) > 0
    assert len(txt_files) == len(csv_files)

def test_chunk_messages_csv_format(tmp_path):
    """Test CSV format in chunked messages."""
    messages = [
        ["Jess", "Aug 30, 2024 10:42:49 PM", "I totally forgot"],
        ["Jess", "Aug 31, 2024 12:33:42 AM", "Look outside"]
    ]
    
    output_dir = chunk_messages(messages, tmp_path, 0.0001)  # Small size to force chunks
    
    # Get first chunk
    csv_file = next((output_dir / "_chunks_csv").glob("chunk_*.csv"))
    
    # Read the content and verify format
    with open(csv_file, "r", newline="", encoding="utf-8") as f:
        content = f.read()
        
    expected_content = '''Sender,Date,Message
Jess,Aug 30, 2024 10:42:49 PM,I totally forgot
Jess,Aug 31, 2024 12:33:42 AM,Look outside
'''
    
    assert content == expected_content
    
    # Verify no blank lines between entries
    lines = content.splitlines()
    assert len(lines) == 3  # Header + 2 messages
    assert all(line for line in lines)  # No empty lines

def test_write_chunk_to_txt(tmp_path):
    """Test writing messages to TXT format."""
    txt_file = tmp_path / "test.txt"
    
    messages = [
        ["Jess", "Aug 30, 2024 10:42:49 PM", "I totally forgot"],
        ["Jess", "Aug 31, 2024 12:33:42 AM", "Look outside"]
    ]
    
    write_chunk_to_txt(messages, txt_file)
    
    expected_content = (
        "Jess, Aug 30, 2024 10:42:49 PM, I totally forgot\n\n"
        "Jess, Aug 31, 2024 12:33:42 AM, Look outside\n\n"
    )
    
    assert txt_file.read_text() == expected_content

def test_combine_message_files(tmp_path):
    """Test combining multiple message files."""
    # Create two message files
    file1 = tmp_path / "file1.txt"
    file2 = tmp_path / "file2.txt"
    
    file1.write_text('''Dec 17, 2024  4:31:51 PM
Jess
Message 1''')
    
    file2.write_text('''Dec 17, 2024  5:31:51 PM
apple@phil-g.com
Message 2''')
    
    # Parse each file individually first
    messages1 = parse_messages(file1, "Phil")
    messages2 = parse_messages(file2, "Phil")
    
    # Combine and sort manually to compare
    expected_messages = sorted(
        messages1 + messages2,
        key=lambda x: datetime.strptime(x[1], "%b %d, %Y %I:%M:%S %p")
    )
    
    # Now test the combine function
    combined = combine_message_files([file1, file2], "Phil")
    
    assert len(combined) == 2
    assert combined == expected_messages  # Should match our manual combination
    assert combined[0][2] == "Message 1"  # Earlier message
    assert combined[1][2] == "Message 2"  # Later message
    assert "Phil" in [msg[0] for msg in combined]  # Should have mapped the email to Phil

def test_main_combines_files(tmp_path):
    """Test that main function combines multiple message files when found."""
    # Create test files
    phone_file = tmp_path / "+18673335566.txt"
    email_file = tmp_path / "apple@phil-g.com.txt"
    
    phone_file.write_text('''Dec 17, 2024  4:31:51 PM
Jess
Message 1

''')
    
    email_file.write_text('''Dec 17, 2024  5:31:51 PM
apple@phil-g.com
Message 2

''')
    
    # Run main with both files
    main(str(tmp_path))
    
    # Find the output directory (most recent)
    output_dirs = list(tmp_path.glob("*"))
    output_dir = max(output_dirs, key=lambda p: p.stat().st_mtime)
    
    # Check that chunks contain both messages
    chunk_files = list((output_dir / "_chunks_txt").glob("chunk_*.txt"))
    content = ""
    for f in chunk_files:
        content += f.read_text()
    
    assert "Message 1" in content
    assert "Message 2" in content
