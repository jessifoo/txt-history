import pytest
from pathlib import Path
from datetime import datetime
from format_txt_history_full import (
    parse_messages,
    detect_file,
    chunk_messages,
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

@pytest.mark.asyncio
async def test_main_message_combining(tmp_path, monkeypatch):
    """Test the message combining logic in the main function."""
    from format_txt_history_full import main, OUTPUT_DIR
    import argparse
    
    # Create test directories
    test_output_dir = tmp_path / "test_output"
    test_output_dir.mkdir()
    
    # Mock command-line arguments
    class MockArgs:
        date = None
        name = "Phil"
        size = 0.2
    
    # Mock functions to avoid actual system calls
    monkeypatch.setattr('argparse.ArgumentParser.parse_args', lambda x: MockArgs())
    monkeypatch.setattr('pathlib.Path.home', lambda: tmp_path)
    
    # Patch OUTPUT_DIR to use our test directory
    monkeypatch.setattr('format_txt_history_full.OUTPUT_DIR', test_output_dir)
    
    # Run main which will call the actual imessage-exporter
    await main()
    
    # Check output directory for chunks
    output_chunks = list(test_output_dir.glob("**/chunk_*.txt"))
    assert len(output_chunks) > 0
    
    # Read content of first chunk to verify messages were combined
    chunk_content = output_chunks[0].read_text()
    assert len(chunk_content.strip()) > 0  # Just verify we got some content
