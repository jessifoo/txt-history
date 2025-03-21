import pytest
from format_txt_history_full import run_imessage_exporter, write_chunk_to_txt


def test_write_chunk_to_txt(tmp_path):
    """Test writing messages to TXT format."""
    txt_file = tmp_path / "test.txt"

    messages = [
        ["Jess", "Aug 30, 2024 10:42:49 PM", "I totally forgot"],
        ["Phil", "Aug 30, 2024 10:43:00 PM", "Another message"],
    ]

    write_chunk_to_txt(messages, txt_file)

    expected_content = (
        "Jess, Aug 30, 2024 10:42:49 PM, I totally forgot\n\nPhil, Aug 30, 2024 10:43:00 PM, Another message\n\n"
    )

    assert txt_file.read_text() == expected_content


@pytest.mark.asyncio
async def test_run_imessage_exporter_dates(monkeypatch, tmp_path):
    """Test that run_imessage_exporter correctly handles start and end dates."""
    # Mock subprocess.create_subprocess_exec to capture command
    command_args = []

    async def mock_create_subprocess_exec(*args, **kwargs):
        command_args.extend(args)

        class MockProcess:
            async def communicate(self):
                return b"", b""

            @property
            def returncode(self):
                return 0

        return MockProcess()

    monkeypatch.setattr("asyncio.create_subprocess_exec", mock_create_subprocess_exec)

    # Create test export path
    export_path = tmp_path / "export"
    export_path.mkdir()

    # Run with both start and end dates
    await run_imessage_exporter(
        name="Phil",
        date="2024-01-01",
        end_date="2024-12-31",
        phone_number="+1234567890",
        imessage_filter="+1234567890,test@email.com",
        export_path=export_path,
    )

    # Check that both -s and -e flags were used with correct dates
    assert "-s" in command_args
    assert "2024-01-01" in command_args
    assert "-e" in command_args
    assert "2024-12-31" in command_args

    # Check flag order
    s_index = command_args.index("-s")
    e_index = command_args.index("-e")
    assert command_args[s_index + 1] == "2024-01-01"
    assert command_args[e_index + 1] == "2024-12-31"
