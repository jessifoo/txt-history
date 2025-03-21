import argparse  # noqa: CPY001, D100
import sys
import os
from pathlib import Path
script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(script_dir))
from constants import OUTPUT_DIR, TMP_PATH, CONTACT_STORE_FILE
import asyncio
import csv
import json
import logging
import re
import shutil
import subprocess
from collections.abc import Generator
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import pytz

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Regular expressions
date_pattern = re.compile(r"^(\w{3} \d{2}, \d{4}\s*\d{1,2}:\d{2}:\d{2} \w{2})")
read_receipt_pattern = re.compile(r"\(Read by.*$")


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number to E.164 format."""
    # Remove all non-digit characters
    digits = re.sub(r"\D", "", phone)

    # Handle special case for "Jess"
    if phone == "Jess":
        return phone

    # If it's a 10-digit number, assume US/Canada (+1)
    if len(digits) == 10:
        return f"+1{digits}"
    # If it already has a country code (11+ digits starting with 1)
    if (len(digits) >= 11 and digits.startswith("1")) or len(digits) >= 11:
        return f"+{digits}"
    msg = f"Invalid phone number format: {phone}"
    raise ValueError(msg)


@dataclass
class ContactMetadata:
    """Metadata for a contact."""

    type: str = "regular"  # or "default"
    created_at: str = str(datetime.now())
    last_used: str = str(datetime.now())


@dataclass
class Contact:
    """Represents a contact with their messaging identifiers."""

    name: str
    phone: str
    email: str | None = None
    metadata: ContactMetadata | None = None

    @classmethod
    def get_default_contacts(cls) -> dict[str, "Contact"]:
        """Get all default contacts."""
        return {
            "Phil": cls(
                name="Phil",
                phone=normalize_phone_number("+18673335566"),
                email="apple@phil-g.com",
                metadata=ContactMetadata(type="default"),
            ),
            "Robert": cls(
                name="Robert",
                phone=normalize_phone_number("+17806793467"),
            ),
            "Rhonda": cls(
                name="Rhonda",
                phone=normalize_phone_number("+17803944504"),
            ),
            "Sherry": cls(
                name="Sherry",
                phone=normalize_phone_number("+17807223445"),
            ),
            "Karly": cls(
                name="Karly",
                phone=normalize_phone_number("+17802810871"),
            ),
            "Roxanne": cls(
                name="Roxanne",
                phone=normalize_phone_number("+1587338-8979"),
            ),
            "Jess": cls(
                name="Jess",
                phone="Jess",  # Special case
            ),
        }

    def to_dict(self) -> dict[str, Any]:
        """Convert contact to dictionary for JSON storage."""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contact":
        """Create contact from dictionary."""
        metadata_data = data.pop("metadata", None)
        metadata = ContactMetadata(**metadata_data) if metadata_data is not None else None
        return cls(**data, metadata=metadata)

    def get_identifiers(self) -> str:
        """Get the contact identifiers for iMessage export filter."""
        if self.email:
            return f"{self.phone},{self.email}"
        return self.phone


class ContactStore:
    """Manages contact storage and retrieval."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.contacts: dict[str, Contact] = {}
        self.load()

    def load(self) -> None:
        """Load contacts from JSON file."""
        if not self.file_path.exists():
            msg = f"Contacts file not found: {self.file_path}"
            raise FileNotFoundError(msg)

        with open(self.file_path) as f:
            data = json.load(f)
            self.contacts = {name: Contact.from_dict(contact_data) for name, contact_data in data["contacts"].items()}

    def save(self) -> None:
        """Save contacts to JSON file."""
        # Read existing data first
        with open(self.file_path) as f:
            data = json.load(f)

        # Only update the specific contact that changed
        data["contacts"].update({
            name: contact.to_dict()
            for name, contact in self.contacts.items()
            if name not in data["contacts"]  # Only add new contacts
        })
        data["last_updated"] = str(datetime.now())

        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def get_contact(self, name: str) -> Contact | None:
        """Get a contact by name.

        Updates last_used timestamp if found.
        """
        contact = self.contacts.get(name)
        if contact and contact.metadata:
            contact.metadata.last_used = str(datetime.now())
            self.save()
        return contact

    def add_contact(self, name: str, phone: str, email: str | None = None) -> Contact:
        """Add or update a contact.

        Args:
            name: Contact name
            phone: Phone number
            email: Optional email address

        Returns:
            The new or updated contact

        Raises:
            ValueError: If phone number is invalid

        """
        phone = normalize_phone_number(phone)
        contact = Contact(
            name=name,
            phone=phone,
            email=email,
            metadata=ContactMetadata(),
        )
        self.contacts[name] = contact
        self.save()
        return contact


# File paths
CONTACT_STORE_FILE = Path(__file__).parent / "contacts.json"
OUTPUT_DIR = Path(__file__).parent / "output"


@dataclass
class ExportConfig:
    """Configuration for message export."""

    export_path: Path
    name: str
    date: str | None
    end_date: str | None
    chunk_size: float | None


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and return the argument parser.

    This is separate from parse_arguments() to allow:
    1. Testing the parser configuration
    2. Generating help text without parsing
    3. Reusing the parser in different contexts
    """
    parser = argparse.ArgumentParser(description="Process iMessage exports")
    parser.add_argument(
        "-s",
        "--size",
        type=float,
        help="Size of each chunk in MB",
    )
    parser.add_argument(
        "-l",
        "--lines",
        type=int,
        help="Number of lines per chunk",
    )
    parser.add_argument(
        "-d",
        "--date",
        type=str,
        help="Start date for message export (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-e",
        "--end-date",
        type=str,
        help="End date for message export (YYYY-MM-DD)",
    )
    parser.add_argument(
        "-n",
        "--name",
        type=str,
        help="Name of contact to export messages for",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        help="Path to save exported files (for testing)",
    )
    return parser


def parse_arguments(args: list[str] | None = None) -> argparse.Namespace:
    """Parse and validate command line arguments.

    Args:
        args: Optional list of arguments to parse. If None, uses sys.argv[1:].
              This allows testing argument parsing without command line args.

    """
    parser = create_argument_parser()
    parsed_args = parser.parse_args(args)

    # Add argument validation here if needed
    if parsed_args.size is not None and parsed_args.lines is not None:
        parser.error("Cannot specify both --size and --lines")

    return parsed_args


def initialize_export(args: argparse.Namespace) -> ExportConfig:
    """Initialize export configuration from arguments."""
    # Set up paths and basic config
    export_path = args.output or (Path.home() / "imessage_export")
    name = args.name or "Phil"

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    return ExportConfig(
        export_path=export_path,
        name=name,
        date=args.date,
        end_date=args.end_date,
        chunk_size=args.size,  # Pass size in MB directly
    )


async def run_imessage_exporter(
    contact: Contact,
    date: str | None = None,
    end_date: str | None = None,
    export_path: Path | None = None,
) -> Path | None:
    """Run the iMessage-exporter command asynchronously.

    Args:
        contact: Contact instance
        date: Optional start date for export
        end_date: Optional end date for export
        export_path: Optional path to save exported files (for testing)

    Returns: Path to the export folder.

    Raises:
        subprocess.CalledProcessError: If the iMessage-exporter command fails
        FileNotFoundError: If the export produces no output
        RuntimeError: If the export folder is empty after successful command execution

    """
    base_command = [
        "/opt/homebrew/bin/imessage-exporter",
        "-f",
        "txt",
        "-c",
        "disabled",
        "-m",
        "Jess",
    ]

    if date:
        base_command.extend(["-s", date])
    if end_date:
        base_command.extend(["-e", end_date])

    if contact.name == "Phil":
        base_command.extend(["-t", contact.get_identifiers()])
    else:
        base_command.extend(["-t", contact.phone])

    if export_path:
        base_command.extend(["-o", str(export_path)])

    logger.info(f"Running iMessage export for {contact.name} (phone: {contact.phone})")
    logger.info(f"Command: {' '.join(base_command)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *base_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await process.communicate()

        if stdout:
            logger.info(f"Command output: {stdout.decode().strip()}")
        if stderr:
            logger.warning(f"Command stderr: {stderr.decode().strip()}")

        if process.returncode:
            error_msg = (
                f"iMessage-exporter failed with return code {process.returncode or 0}: {stderr.decode().strip()}"
            )
            logger.error(error_msg)
            raise subprocess.CalledProcessError(process.returncode, base_command, stderr)

        export_check_path = export_path or (Path.home() / "imessage_export")
        if not (export_check_path.exists() and any(export_check_path.iterdir())):
            msg = f"Export folder '{export_check_path}' is empty."
            raise RuntimeError(msg)

    except subprocess.CalledProcessError as e:
        logger.exception(f"iMessage-exporter command failed: {e}")
        raise

    return export_check_path


async def detect_file(
    folder_path: Path | None,
    phone_number: str | None = None,
    email: str | None = None,
) -> Path | None:
    """Detect and potentially combine message files from phone number and email.

    Args:
        folder_path: Path to the export folder
        phone_number: Phone number to look for
        email: Optional email address to look for

    Returns:
        Path: Path to the message file (might be a combined file)

    Raises:
        FileNotFoundError: If no matching files are found

    """
    if not folder_path or not folder_path.exists():
        raise FileNotFoundError("Export folder not found")

    found_files = []

    # Look for phone number file
    if phone_number:
        phone_pattern = f"*{phone_number}*.txt"
        phone_files = list(folder_path.glob(phone_pattern))
        if phone_files:
            found_files.extend(phone_files)

    # Look for email file
    if email:
        email_pattern = f"*{email}*.txt"
        email_files = list(folder_path.glob(email_pattern))
        if email_files:
            found_files.extend(email_files)

    if not found_files:
        raise FileNotFoundError("No message files found")

    # If we found multiple files, merge them
    if len(found_files) > 1:
        merged_file = folder_path / "merged_messages.txt"
        with Path.open(merged_file, mode="w") as outfile:
            for file in found_files:
                with Path.open(file) as infile:
                    outfile.write(infile.read())
                    outfile.write("\n")  # Add newline between files
        return merged_file

    return found_files[0]


async def find_message_files(export_path: Path, contact: Contact) -> list[Path]:
    """Find and return message files for the contact."""
    try:
        # Get combined file with both phone and email messages if available
        message_file = await detect_file(export_path, contact.phone, contact.email)
        return [message_file] if message_file else []
    except FileNotFoundError:
        logger.warning(f"No messages found for {contact.name}")
        return []


def merge_files(file1: Path, file2: Path) -> Path:
    """Merge two files into a single file."""
    combined_file = file1.parent / f"{file1.stem}_combined.txt"
    with Path.open(combined_file, "w", encoding="utf-8") as outfile:
        for file_path in [file1, file2]:
            with Path.open(file_path, encoding="utf-8") as infile:
                outfile.write(infile.read())
    return combined_file


def sort_messages(messages: list[list[str]]) -> list[list[str]]:
    """Sort messages chronologically.

    Messages are sorted based on the datetime in the second element of each message list.
    The dates should already be cleaned and in the correct format.

    Returns:
        Sorted list of messages in chronological order.
    """

    def parse_date(date_str: str) -> datetime:
        # Normalize multiple spaces to single space
        normalized = " ".join(date_str.split())

        # Handle ISO format dates with timezone (e.g., "2025-01-10T18:19:09-07:00")
        if "T" in normalized and ("+" in normalized or "-" in normalized):
            # Parse as ISO format with timezone
            return datetime.fromisoformat(normalized)

        # Handle ISO format dates without timezone (e.g., "2024-12-25T22:19:32Z")
        if "T" in normalized and normalized.endswith("Z"):
            # Remove the Z suffix and parse as ISO format
            dt = datetime.fromisoformat(normalized[:-1])
            # Make timezone-aware by adding UTC timezone
            return dt.replace(tzinfo=pytz.UTC)

        # Handle the original format - make timezone-aware with Mountain Time
        dt = datetime.strptime(normalized, "%b %d, %Y %I:%M:%S %p")
        mountain_tz = pytz.timezone("America/Denver")
        return mountain_tz.localize(dt)

    return sorted(messages, key=lambda x: parse_date(x[1]))


def chunk_messages(
    messages: list[list[str]], chunk_size: int | None = None, size_mb: float | None = None, lines: int | None = None
) -> list[list[list[str]]]:
    """Split messages into chunks.

    Args:
        messages: List of messages to chunk, where each message is a list of [sender, date, message]
        chunk_size: Optional number of messages per chunk
        size_mb: Optional size in MB per chunk
        lines: Optional number of lines per chunk

    Returns:
        List of chunks, where each chunk is a list of messages

    """
    if not chunk_size and not size_mb and not lines:
        return [messages]

    chunks: list[list[list[str]]] = []
    current_chunk: list[list[str]] = []
    current_size = 0
    current_lines = 0

    for message in messages:
        if size_mb:
            # Calculate size of message in bytes
            message_size = sum(len(str(field).encode("utf-8")) for field in message)
            if current_size + message_size > size_mb * 1024 * 1024 and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_size += message_size
        elif lines:
            # Count number of newlines in the message text plus 1 for the message itself
            message_lines = message[2].count('\n') + 1
            if current_lines + message_lines > lines and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_lines = 0
            current_lines += message_lines
        elif len(current_chunk) >= chunk_size:
            chunks.append(current_chunk)
            current_chunk = []
        current_chunk.append(message)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def message_generator(file_path: Path, contact: Contact) -> Generator[list[str], None, None]:
    """Generate parsed messages from a file.

    Args:
        file_path: Path to the message file
        contact: Contact whose messages to parse

    Yields:
        List of messages, where each message is [sender: str, date: str, content: str]

    """
    with open(file_path, encoding="utf-8") as infile:
        date: str = ""
        sender: str = ""
        message: list[str] = []
        prev_line_empty: bool = True  # Track if previous line was empty

        for line in infile:
            line = line.strip()

            # If we see an empty line, mark it and continue
            if not line:
                prev_line_empty = True
                continue

            # Only check for date if previous line was empty
            if prev_line_empty and (date_match := date_pattern.match(line)):
                # If we have a complete message, yield it before starting new one
                if date and sender and message:
                    yield [sender, date, ", ".join(message)]

                # Clean the date by removing read receipt if present
                date = read_receipt_pattern.sub("", date_match.group(1)).strip()
                sender = None
                message = []
            elif date and not sender:
                # If it's a phone number, check if it matches our contact
                if re.match(r"^\+?\d+$", line):
                    normalized_line = normalize_phone_number(line)
                    sender = contact.name if normalized_line == contact.phone else line
                # If it's Phil's email
                elif line == contact.email:
                    sender = contact.name
                # If it's Jess
                elif line == "Jess":
                    sender = "Jess"
                # Otherwise keep the original sender
                else:
                    sender = line
            elif date and sender:
                # Clean the line by removing emojis and special characters, preserving text
                message.append("".join(char for char in line if char.isascii() and char.isprintable()))

            prev_line_empty = False

        # Yield the last message
        if date and sender and message:
            # Parse the date with proper Mountain Time zone awareness
            dt_obj = datetime.strptime(date, "%b %d, %Y %I:%M:%S %p")
            # Assume Mountain Time (MST/MDT) - this will handle DST correctly
            mountain_tz = pytz.timezone("America/Denver")
            # Localize the datetime to Mountain Time
            dt_obj = mountain_tz.localize(dt_obj)
            # Convert to ISO 8601 format with timezone information
            formatted_date = dt_obj.isoformat()
            yield [sender, formatted_date, ", ".join(message)]


def parse_messages(file_path: Path, contact: Contact) -> list[list[str]]:
    """Parse and sort all messages from a file.

    Args:
        file_path: Path to the message file
        contact: Contact whose messages to parse

    Returns:
        List of messages, where each message is [sender, date, content]

    """
    messages = list(message_generator(file_path, contact))
    return sort_messages(messages)


async def process_messages_with_generator(
    file_path: Path,
    contact: Contact,
    chunk_size: int | None = None,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Process messages using a generator and write them to chunks."""
    messages = parse_messages(file_path, contact)
    chunks = chunk_messages(messages, chunk_size)

    for i, chunk in enumerate(chunks, 1):
        await write_chunk(chunk, i, output_dir)

    return output_dir


async def write_chunk(chunk: list[list[str]], chunk_num: int, output_dir: Path) -> None:
    """Write a chunk of messages to CSV and TXT files."""
    # Get the date from the first message in the chunk
    if chunk:
        date_str = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        date_dir = output_dir / date_str
        date_dir.mkdir(parents=True, exist_ok=True)

        # Create txt and csv subdirectories
        txt_dir = date_dir / "chunks_txt"
        csv_dir = date_dir / "chunks_csv"
        txt_dir.mkdir(exist_ok=True)
        csv_dir.mkdir(exist_ok=True)
    else:
        return

    # Write to CSV with ID column
    csv_file_path = csv_dir / f"chunk_{chunk_num}.csv"
    async with aiofiles.open(csv_file_path, "w", encoding="utf-8") as csvfile:
        # Use a StringIO buffer to create the CSV content
        import io

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["ID", "Sender", "Date", "Message"])
        # Add ID column with autoincrementing values starting from 1
        for i, row in enumerate(chunk, 1):
            writer.writerow([i, *row])

        # Write the CSV content to the file
        await csvfile.write(csv_buffer.getvalue())

    # Write to TXT with empty lines between rows (no ID column for TXT)
    txt_file_path = txt_dir / f"chunk_{chunk_num}.txt"
    async with aiofiles.open(txt_file_path, "w", encoding="utf-8") as txtfile:
        for row in chunk:
            await txtfile.write(f"{row[0]}, {row[1]}, {row[2]}\n\n")

    logger.info(f"Chunk {chunk_num} written to {csv_file_path} and {txt_file_path}")


def clear_folder(folder_path: Path) -> None:
    """Forcefully delete the specified folder and its contents.

    Args:
        folder_path: Path to the folder to be cleared

    Raises:
        OSError: If folder deletion fails

    """
    if not folder_path.exists():
        logger.info(f"Folder does not exist: {folder_path}")
        return

    try:
        shutil.rmtree(folder_path)
        logger.info(f"Cleared folder: {folder_path}")
    except OSError as e:
        logger.exception(f"Failed to clear folder: {folder_path}, {e}")
        raise


def prompt_for_phone_number(name: str) -> str | None:
    """Prompt user for a phone number for a new contact.

    Args:
        name: Name of the contact

    Returns:
        Normalized phone number if provided, None if user cancels

    """
    print(f"\nContact '{name}' not found in contacts.")
    while True:
        phone = input(f"Please enter phone number for {name} (or 'cancel' to exit): ").strip()
        if phone.lower() == "cancel":
            return None

        try:
            normalized = normalize_phone_number(phone)
            if not normalized:
                print("Phone number cannot be empty")
                continue

            confirm = input(f"Normalized number: {normalized}. Is this correct? (y/n): ").lower()
            if confirm == "y":
                return normalized
        except Exception as e:
            print(f"Invalid phone number: {e}")


def setup_contact(name: str, contact_store: ContactStore) -> Contact:
    """Set up and return a contact, creating if necessary."""
    contact = contact_store.get_contact(name)
    if not contact:
        phone = prompt_for_phone_number(name)
        if phone is None:
            msg = "Operation cancelled by user"
            raise ValueError(msg)

        contact = contact_store.add_contact(
            name=name,
            phone=phone,
            email="apple@phil-g.com" if name == "Phil" else None,
        )
        logger.info(f"Added new contact: {name} ({phone})")

    logger.info(f"Using filter: {contact.get_identifiers()}")
    return contact


async def process_message_files(
    message_files: list[Path],
    contact: Contact,
    chunk_size: float | None = None,
    lines: int | None = None
) -> None:
    """Process message files and generate output chunks."""
    if not message_files:
        msg = (
            f"No message files found for {contact.name}. This could mean either:\n"
            "1. There are no messages for this contact\n"
            "2. The identifiers (phone/email) are incorrect\n"
            "3. The messages are not in the expected iMessage format"
        )
        raise FileNotFoundError(msg)

    # Combine messages from all files
    all_messages = []
    for file_path in message_files:
        messages = parse_messages(file_path, contact)
        all_messages.extend(messages)

    # Sort all messages chronologically
    sorted_messages = sort_messages(all_messages)

    # Split into chunks based on size in MB or number of lines
    chunks = chunk_messages(sorted_messages, size_mb=chunk_size, lines=lines)

    # Write chunks to files
    for i, chunk in enumerate(chunks, 1):
        await write_chunk(chunk, i, OUTPUT_DIR)


async def main() -> None:
    """Main function to process iMessage exports."""
    try:
        # Parse arguments and initialize config
        args = parse_arguments()
        config = initialize_export(args)

        # Set up contact store and get contact
        contact_store = ContactStore(CONTACT_STORE_FILE)
        contact = setup_contact(config.name, contact_store)

        # Clear temporary and export directories
        clear_folder(TMP_PATH)
        clear_folder(config.export_path)

        # Run the iMessage-exporter
        await run_imessage_exporter(
            contact,
            config.date,
            config.end_date,
            TMP_PATH,  # Use TMP_PATH instead of export_path
        )

        # Find and process message files
        message_files = await find_message_files(TMP_PATH, contact)
        await process_message_files(
            message_files,
            contact,
            chunk_size=config.chunk_size,
            lines=args.lines,
        )

    except FileNotFoundError as e:
        logger.error(str(e))
        raise
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        raise
    finally:
        # Clean up temporary files
        pass


def cli_main() -> None:
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
