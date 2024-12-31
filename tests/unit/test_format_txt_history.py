import pytest
from pathlib import Path
import csv
from format_txt_history_full import write_chunk_to_txt

def test_write_chunk_to_txt(tmp_path):
    """Test writing messages to TXT format."""
    txt_file = tmp_path / "test.txt"
    
    messages = [
        ["Jess", "Aug 30, 2024 10:42:49 PM", "I totally forgot"],
        ["Phil", "Aug 30, 2024 10:43:00 PM", "Another message"]
    ]
    
    write_chunk_to_txt(messages, txt_file)
    
    expected_content = (
        "Jess, Aug 30, 2024 10:42:49 PM, I totally forgot\n\n"
        "Phil, Aug 30, 2024 10:43:00 PM, Another message\n\n"
    )
    
    assert txt_file.read_text() == expected_content
