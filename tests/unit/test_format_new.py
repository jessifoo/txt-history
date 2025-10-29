"""Comprehensive unit tests for scripts/format_new.py."""

import asyncio
import json
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, mock_open, patch

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "scripts"))

from format_new import (
    Contact,
    ContactStore,
    get_contact_info,
    main,
    parse_arguments,
)


class TestContact:
    """Test suite for Contact dataclass."""

    def test_contact_creation(self):
        """Test basic contact creation."""
        contact = Contact(name="John Doe", phone="+1234567890")
        assert contact.name == "John Doe"
        assert contact.phone == "+1234567890"
        assert contact.emails == []

    def test_contact_with_emails(self):
        """Test contact creation with emails."""
        emails = ["john@example.com", "doe@example.com"]
        contact = Contact(name="John Doe", phone="+1234567890", emails=emails)
        assert contact.emails == emails

    def test_contact_without_phone(self):
        """Test contact creation without phone."""
        contact = Contact(name="John Doe")
        assert contact.name == "John Doe"
        assert contact.phone is None
        assert contact.emails == []

    def test_contact_post_init_emails(self):
        """Test that post_init initializes emails to empty list."""
        contact = Contact(name="John Doe", phone="+1234567890")
        assert isinstance(contact.emails, list)
        assert len(contact.emails) == 0

    def test_contact_equality(self):
        """Test contact equality comparison."""
        contact1 = Contact(name="John", phone="+123")
        contact2 = Contact(name="John", phone="+123")
        # Dataclasses with same values should be equal
        assert contact1 == contact2

    def test_contact_with_empty_name(self):
        """Test contact with empty name."""
        contact = Contact(name="", phone="+123")
        assert contact.name == ""

    def test_contact_string_representation(self):
        """Test contact string representation."""
        contact = Contact(name="John Doe", phone="+1234567890")
        str_repr = str(contact)
        assert "John Doe" in str_repr

    def test_contact_emails_mutable(self):
        """Test that emails list is mutable."""
        contact = Contact(name="John")
        contact.emails.append("john@example.com")
        assert "john@example.com" in contact.emails


class TestContactStore:
    """Test suite for ContactStore class."""

    def test_contactstore_creation(self, tmp_path):
        """Test ContactStore initialization."""
        store_file = tmp_path / "contacts.json"
        store = ContactStore(store_file)
        assert store.file_path == store_file
        assert isinstance(store.contacts, dict)

    def test_contactstore_load_nonexistent_file(self, tmp_path):
        """Test loading from nonexistent file."""
        store_file = tmp_path / "nonexistent.json"
        store = ContactStore(store_file)
        assert store.contacts == {}

    def test_contactstore_load_existing_file(self, tmp_path):
        """Test loading from existing file."""
        store_file = tmp_path / "contacts.json"
        test_data = {
            "John": {"phone": "+1234567890", "emails": ["john@example.com"]}
        }
        store_file.write_text(json.dumps(test_data))

        store = ContactStore(store_file)
        assert "John" in store.contacts
        assert store.contacts["John"]["phone"] == "+1234567890"

    def test_contactstore_load_invalid_json(self, tmp_path):
        """Test loading invalid JSON file."""
        store_file = tmp_path / "invalid.json"
        store_file.write_text("{invalid json}")

        store = ContactStore(store_file)
        assert store.contacts == {}

    def test_get_contact_exists(self, tmp_path):
        """Test getting existing contact."""
        store_file = tmp_path / "contacts.json"
        test_data = {
            "John": {"phone": "+1234567890", "emails": ["john@example.com"]}
        }
        store_file.write_text(json.dumps(test_data))

        store = ContactStore(store_file)
        contact = store.get_contact("John")

        assert contact is not None
        assert contact.name == "John"
        assert contact.phone == "+1234567890"
        assert "john@example.com" in contact.emails

    def test_get_contact_not_exists(self, tmp_path):
        """Test getting non-existent contact."""
        store_file = tmp_path / "contacts.json"
        store = ContactStore(store_file)

        contact = store.get_contact("NonExistent")
        assert contact is None

    def test_get_contact_without_phone(self, tmp_path):
        """Test getting contact without phone number."""
        store_file = tmp_path / "contacts.json"
        test_data = {"John": {"emails": ["john@example.com"]}}
        store_file.write_text(json.dumps(test_data))

        store = ContactStore(store_file)
        contact = store.get_contact("John")

        assert contact is not None
        assert contact.phone is None

    def test_get_contact_without_emails(self, tmp_path):
        """Test getting contact without emails."""
        store_file = tmp_path / "contacts.json"
        test_data = {"John": {"phone": "+1234567890"}}
        store_file.write_text(json.dumps(test_data))

        store = ContactStore(store_file)
        contact = store.get_contact("John")

        assert contact is not None
        assert contact.emails == []

    def test_save_contact_new(self, tmp_path):
        """Test saving new contact."""
        store_file = tmp_path / "contacts.json"
        store = ContactStore(store_file)

        contact = Contact(name="Jane", phone="+9876543210", emails=["jane@example.com"])
        store.save_contact(contact)

        # Verify file was written
        assert store_file.exists()

        # Load and verify
        with open(store_file) as f:
            data = json.load(f)

        assert "Jane" in data
        assert data["Jane"]["phone"] == "+9876543210"
        assert "jane@example.com" in data["Jane"]["emails"]

    def test_save_contact_overwrite(self, tmp_path):
        """Test overwriting existing contact."""
        store_file = tmp_path / "contacts.json"
        initial_data = {"John": {"phone": "+1111111111", "emails": []}}
        store_file.write_text(json.dumps(initial_data))

        store = ContactStore(store_file)
        contact = Contact(name="John", phone="+2222222222", emails=["new@example.com"])
        store.save_contact(contact)

        # Load and verify
        with open(store_file) as f:
            data = json.load(f)

        assert data["John"]["phone"] == "+2222222222"
        assert "new@example.com" in data["John"]["emails"]

    def test_save_contact_persists(self, tmp_path):
        """Test that saved contact persists across instances."""
        store_file = tmp_path / "contacts.json"

        # First instance
        store1 = ContactStore(store_file)
        contact = Contact(name="Bob", phone="+5555555555")
        store1.save_contact(contact)

        # Second instance
        store2 = ContactStore(store_file)
        retrieved = store2.get_contact("Bob")

        assert retrieved is not None
        assert retrieved.phone == "+5555555555"


class TestGetContactInfo:
    """Test suite for get_contact_info function."""

    @patch("format_new.ContactStore")
    def test_get_existing_contact(self, mock_store_class, tmp_path):
        """Test getting existing contact."""
        store_file = tmp_path / "contacts.json"

        # Setup mock
        mock_store = MagicMock()
        mock_contact = Contact(name="Phil", phone="+1234567890")
        mock_store.get_contact.return_value = mock_contact
        mock_store_class.return_value = mock_store

        with patch("format_new.CONTACT_STORE_FILE", store_file):
            result = get_contact_info("Phil")

        assert result is not None
        assert result.name == "Phil"

    @patch("format_new.ContactStore")
    @patch("builtins.input")
    def test_get_new_contact_with_phone(self, mock_input, mock_store_class, tmp_path):
        """Test getting new contact with phone input."""
        store_file = tmp_path / "contacts.json"
        mock_input.side_effect = ["+1234567890", ""]

        # Setup mock
        mock_store = MagicMock()
        mock_store.get_contact.return_value = None
        mock_store_class.return_value = mock_store

        with patch("format_new.CONTACT_STORE_FILE", store_file):
            result = get_contact_info("NewPerson")

        assert result is not None
        assert result.name == "NewPerson"
        assert result.phone == "+1234567890"

    @patch("format_new.ContactStore")
    @patch("builtins.input")
    def test_get_new_contact_with_email(self, mock_input, mock_store_class, tmp_path):
        """Test getting new contact with email."""
        store_file = tmp_path / "contacts.json"
        mock_input.side_effect = ["+1234567890", "test@example.com"]

        mock_store = MagicMock()
        mock_store.get_contact.return_value = None
        mock_store_class.return_value = mock_store

        with patch("format_new.CONTACT_STORE_FILE", store_file):
            result = get_contact_info("NewPerson")

        assert result is not None
        assert "test@example.com" in result.emails

    @patch("format_new.ContactStore")
    @patch("builtins.input")
    def test_get_new_contact_cancel(self, mock_input, mock_store_class, tmp_path):
        """Test canceling contact creation."""
        store_file = tmp_path / "contacts.json"
        mock_input.return_value = "cancel"

        mock_store = MagicMock()
        mock_store.get_contact.return_value = None
        mock_store_class.return_value = mock_store

        with patch("format_new.CONTACT_STORE_FILE", store_file):
            result = get_contact_info("NewPerson")

        assert result is None


class TestParseArguments:
    """Test suite for parse_arguments function."""

    def test_parse_default_arguments(self):
        """Test parsing with default arguments."""
        with patch("sys.argv", ["format_new.py"]):
            args = parse_arguments()
            assert args.name == "Phil"
            assert args.date is None
            assert args.end_date is None
            assert args.size is None
            assert args.lines is None
            assert args.one_side is False

    def test_parse_with_name(self):
        """Test parsing with custom name."""
        with patch("sys.argv", ["format_new.py", "-n", "John"]):
            args = parse_arguments()
            assert args.name == "John"

    def test_parse_with_date(self):
        """Test parsing with date."""
        with patch("sys.argv", ["format_new.py", "-d", "2025-01-01"]):
            args = parse_arguments()
            assert args.date == "2025-01-01"

    def test_parse_with_end_date(self):
        """Test parsing with end date."""
        with patch("sys.argv", ["format_new.py", "-e", "2025-12-31"]):
            args = parse_arguments()
            assert args.end_date == "2025-12-31"

    def test_parse_with_size(self):
        """Test parsing with size."""
        with patch("sys.argv", ["format_new.py", "-s", "10.5"]):
            args = parse_arguments()
            assert args.size == 10.5

    def test_parse_with_lines(self):
        """Test parsing with lines."""
        with patch("sys.argv", ["format_new.py", "-l", "1000"]):
            args = parse_arguments()
            assert args.lines == 1000

    def test_parse_with_one_side_flag(self):
        """Test parsing with one-side flag."""
        with patch("sys.argv", ["format_new.py", "-o"]):
            args = parse_arguments()
            assert args.one_side is True

    def test_parse_all_arguments(self):
        """Test parsing with all arguments."""
        with patch(
            "sys.argv",
            [
                "format_new.py",
                "-n",
                "Alice",
                "-d",
                "2025-01-01",
                "-e",
                "2025-12-31",
                "-s",
                "5.0",
                "-l",
                "500",
                "-o",
            ],
        ):
            args = parse_arguments()
            assert args.name == "Alice"
            assert args.date == "2025-01-01"
            assert args.end_date == "2025-12-31"
            assert args.size == 5.0
            assert args.lines == 500
            assert args.one_side is True


class TestMain:
    """Test suite for main async function."""

    @pytest.mark.asyncio
    async def test_main_with_future_date(self):
        """Test main with date in future."""
        with patch("sys.argv", ["format_new.py", "-d", "2030-01-01"]):
            with patch("format_new.is_date_in_future", return_value=True):
                result = await main()
                assert result == 1

    @pytest.mark.asyncio
    async def test_main_without_contact(self):
        """Test main when contact info cannot be obtained."""
        with patch("sys.argv", ["format_new.py"]):
            with patch("format_new.is_date_in_future", return_value=False):
                with patch("format_new.get_contact_info", return_value=None):
                    result = await main()
                    assert result == 1

    @pytest.mark.asyncio
    async def test_main_with_valid_contact(self):
        """Test main with valid contact."""
        mock_contact = Contact(name="Phil", phone="+1234567890")

        with patch("sys.argv", ["format_new.py"]):
            with patch("format_new.is_date_in_future", return_value=False):
                with patch("format_new.get_contact_info", return_value=mock_contact):
                    result = await main()
                    assert result == 0

    @pytest.mark.asyncio
    async def test_main_with_no_date(self):
        """Test main without date argument."""
        mock_contact = Contact(name="Phil", phone="+1234567890")

        with patch("sys.argv", ["format_new.py"]):
            with patch("format_new.get_contact_info", return_value=mock_contact):
                result = await main()
                assert result == 0


class TestFormatNewEdgeCases:
    """Test edge cases and error conditions."""

    def test_contact_with_multiple_emails(self):
        """Test contact with multiple email addresses."""
        emails = ["email1@test.com", "email2@test.com", "email3@test.com"]
        contact = Contact(name="MultiEmail", phone="+123", emails=emails)
        assert len(contact.emails) == 3

    def test_contact_with_special_characters_in_name(self):
        """Test contact with special characters."""
        contact = Contact(name="O'Brien-Smith", phone="+123")
        assert contact.name == "O'Brien-Smith"

    def test_contactstore_empty_file(self, tmp_path):
        """Test ContactStore with empty file."""
        store_file = tmp_path / "empty.json"
        store_file.write_text("")

        store = ContactStore(store_file)
        assert store.contacts == {}

    def test_contactstore_malformed_json(self, tmp_path):
        """Test ContactStore with malformed JSON."""
        store_file = tmp_path / "malformed.json"
        store_file.write_text('{"name": ')

        store = ContactStore(store_file)
        assert store.contacts == {}

    def test_save_contact_without_emails(self, tmp_path):
        """Test saving contact without emails."""
        store_file = tmp_path / "contacts.json"
        store = ContactStore(store_file)

        contact = Contact(name="NoEmail", phone="+123")
        store.save_contact(contact)

        with open(store_file) as f:
            data = json.load(f)

        assert data["NoEmail"]["emails"] == []

    def test_get_contact_case_sensitive(self, tmp_path):
        """Test that contact names are case-sensitive."""
        store_file = tmp_path / "contacts.json"
        test_data = {"John": {"phone": "+123"}}
        store_file.write_text(json.dumps(test_data))

        store = ContactStore(store_file)
        assert store.get_contact("John") is not None
        assert store.get_contact("john") is None

    def test_contact_with_unicode_name(self):
        """Test contact with Unicode characters in name."""
        contact = Contact(name="José García", phone="+123")
        assert contact.name == "José García"

    def test_contactstore_concurrent_access(self, tmp_path):
        """Test multiple ContactStore instances on same file."""
        store_file = tmp_path / "contacts.json"

        store1 = ContactStore(store_file)

        contact1 = Contact(name="User1", phone="+111")
        store1.save_contact(contact1)

        # Reload store2
        store2_reloaded = ContactStore(store_file)
        retrieved = store2_reloaded.get_contact("User1")

        assert retrieved is not None
        assert retrieved.phone == "+111"