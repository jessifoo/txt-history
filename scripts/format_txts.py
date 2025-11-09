import argparse
import asyncio
import csv
import io
import json
import logging
import os
import re
import shutil
import subprocess
import sys
from collections.abc import Generator
from dataclasses import asdict, dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import aiofiles
import pandas as pd
import pytz

# Handle imports differently when run as a script vs imported as a module
try:
    # When imported as a module (e.g., from scripts.format_txts import cli_main)
    from .constants import CONTACT_STORE_FILE, DEFAULT_TIMEZONE, OUTPUT_DIR, TMP_PATH
    from .utils import (
        clean_message_content,
        format_date_to_iso,
        is_date_in_future,
        merge_text_files,
        parse_date_string,
        read_json_file,
        read_text_file,
        write_json_file,
    )
except ImportError:
    # When run directly as a script
    from constants import CONTACT_STORE_FILE, DEFAULT_TIMEZONE, OUTPUT_DIR, TMP_PATH
    from utils import (
        clean_message_content,
        is_date_in_future,
        merge_text_files,
        parse_date_string,
        read_json_file,
        read_text_file,
        write_json_file,
    )

script_dir = Path(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(str(script_dir))


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
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
    emails: list[str] = field(default_factory=list)
    metadata: ContactMetadata | None = field(default=None)

    def to_dict(self) -> dict[str, Any]:
        """Convert contact to dictionary for JSON storage.

        Returns:
            Dictionary representation of the contact.

        """
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Contact":
        """Create contact from dictionary.

        Args:
            data: Dictionary containing contact data.

        Returns:
            A new Contact instance.

        """
        metadata_data = data.pop("metadata", None)
        metadata = ContactMetadata(**metadata_data) if metadata_data is not None else None
        if "email" in data and data["email"] is not None:
            if isinstance(data["email"], str):
                emails = [email.strip() for email in data["email"].split(",") if email.strip()]
                data["emails"] = emails
            data.pop("email")
        return cls(**data, metadata=metadata)

    def get_identifiers(self) -> str:
        """Get the contact identifiers for iMessage export filter.

        Returns:
            String of identifiers (phone and emails) separated by commas.

        """
        if self.emails:
            return f"{self.phone},{','.join(self.emails)}"
        return self.phone


class ContactStore:
    """Manages contact storage and retrieval."""

    def __init__(self, file_path: Path) -> None:
        """Initialize the contact store.

        Args:
            file_path: Path to the contacts JSON file.

        """
        self.file_path = file_path
        self.contacts: dict[str, Contact] = {}
        self.load()

    def load(self) -> None:
        """Load contacts from JSON file."""
        if not self.file_path.exists():
            # Create an empty contacts file with the correct structure
            self._create_empty_contacts_file()

        try:
            data = read_json_file(self.file_path)
            self.contacts = {name: Contact.from_dict(contact_data) for name, contact_data in data["contacts"].items()}
        except json.JSONDecodeError:
            logger.exception("Invalid JSON in contacts file: %s", self.file_path)
            # Create a new contacts file if the existing one is corrupted
            self._create_empty_contacts_file()
            self.contacts = {}

    def _create_empty_contacts_file(self) -> None:
        """Create an empty contacts file with the correct structure."""
        # Ensure the parent directory exists
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # Create a minimal contacts file
        empty_data = {
            "contacts": {},
            "last_updated": str(datetime.now(tz=pytz.UTC)),
            "version": "1.0",
        }

        write_json_file(self.file_path, empty_data)

        logger.info("Created new contacts file: %s", self.file_path)

    def save(self) -> None:
        """Save contacts to JSON file."""
        # Read existing data first if the file exists
        if self.file_path.exists():
            try:
                data = read_json_file(self.file_path)
            except (json.JSONDecodeError, FileNotFoundError):
                # If file is corrupted or doesn't exist, create a new structure
                data = {"contacts": {}, "version": "1.0"}
        else:
            data = {"contacts": {}, "version": "1.0"}

        # Update contacts
        data["contacts"].update(
            {name: contact.to_dict() for name, contact in self.contacts.items()},
        )
        data["last_updated"] = str(datetime.now(tz=pytz.UTC))

        # Write back to file
        write_json_file(self.file_path, data)

    def get_contact(self, name: str) -> Contact | None:
        """Get a contact by name.

        Updates last_used timestamp if found.
        """
        contact = self.contacts.get(name)
        if contact and contact.metadata:
            contact.metadata.last_used = str(datetime.now())
            self.save()
        return contact

    def add_contact(
        self,
        name: str,
        phone: str,
        emails: list[str] | None = None,
    ) -> Contact:
        """Add or update a contact.

        Args:
            name: Contact name
            phone: Phone number
            emails: Optional list of email addresses

        Returns:
            The new or updated contact

        Raises:
            ValueError: If phone number is invalid

        """
        phone = normalize_phone_number(phone)
        contact = Contact(
            name=name,
            phone=phone,
            emails=emails or [],
            metadata=ContactMetadata(),
        )
        self.contacts[name] = contact
        self.save()
        return contact


# Using constants imported from constants.py


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
    parser.add_argument(
        "--one-side",
        action="store_true",
        help="Export only the contact's messages, excluding your replies",
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
    """Initialize export configuration.

    Args:
        args: Command-line arguments

    Returns:
        ExportConfig instance
    """
    # Create export path if it doesn't exist
    export_path = Path(args.output) if args.output else Path.home() / "imessage_export"
    export_path.mkdir(exist_ok=True)

    # Ensure output directory exists
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # Set default name to "Phil" if not specified
    name = args.name or "Phil"

    # Validate date is not in the future
    date = args.date
    if date:
        try:
            if is_date_in_future(date, DEFAULT_TIMEZONE):
                logger.warning(
                    "Date %s is in the future, using today's date instead",
                    date,
                )
                today = datetime.now(tz=pytz.timezone(DEFAULT_TIMEZONE)).replace(
                    tzinfo=None,
                )
                date = today.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning("Invalid date format: %s, using no date filter", date)
            date = None

    # Validate end_date is not in the future
    end_date = args.end_date
    if end_date:
        try:
            if is_date_in_future(end_date, DEFAULT_TIMEZONE):
                logger.warning(
                    "End date %s is in the future, using today's date instead",
                    end_date,
                )
                today = datetime.now(tz=pytz.timezone(DEFAULT_TIMEZONE)).replace(
                    tzinfo=None,
                )
                end_date = today.strftime("%Y-%m-%d")
        except ValueError:
            logger.warning(
                "Invalid end date format: %s, using no end date filter",
                end_date,
            )
            end_date = None

    return ExportConfig(
        name=name,
        date=date,
        end_date=end_date,
        export_path=export_path,
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

    base_command.extend(["-t", contact.get_identifiers()])

    export_check_path = export_path or (Path.home() / "imessage-export")

    if export_path:
        base_command.extend(["-o", str(export_path)])

    logger.info(f"Running iMessage export for {contact.name} (phone: {contact.phone})")
    logger.info(f"Command: {' '.join(base_command)}")
    logger.info(f"Date filter: {date or 'None'} to {end_date or 'present'}")

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
            raise subprocess.CalledProcessError(
                process.returncode,
                base_command,
                stderr,
            )

        export_check_path = export_path or (Path.home() / "imessage_export")
        if not (export_check_path.exists() and any(export_check_path.iterdir())):
            msg = f"Export folder '{export_check_path}' is empty."
            raise RuntimeError(msg)

        logger.info(f"Export directory contents: {[p.name for p in export_check_path.iterdir()]}")

    except subprocess.CalledProcessError as e:
        logger.exception(f"iMessage-exporter command failed: {e}")
        raise

    return export_check_path


async def detect_file(
    folder_path: Path | None,
    phone_number: str | None = None,
    emails: list[str] | None = None,
) -> Path | None:
    """Detect and potentially combine message files from phone number and email.

    Args:
        folder_path: Path to the export folder
        phone_number: Phone number to look for
        emails: Optional list of email addresses to look for

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

    # Look for email files
    if emails:
        for email in emails:
            email_pattern = f"*{email}*.txt"
            email_files = list(folder_path.glob(email_pattern))
            print(email_files)
            if email_files:
                found_files.extend(email_files)

    if not found_files:
        raise FileNotFoundError("No message files found")

    # If we found multiple files, merge them
    if len(found_files) > 1:
        merged_file = folder_path / "merged_messages.txt"
        merge_text_files(found_files, merged_file)
        return merged_file

    return found_files[0]


async def find_message_files(export_path: Path, contact: Contact) -> list[Path]:
    """Find and return message files for the contact.

    Args:
        export_path: Path to the export directory
        contact: Contact to find messages for

    Returns:
        list[Path]: List of message files found, empty if none
    """
    logger.info(f"Searching for message files in {export_path} for contact {contact.name}")
    logger.info(f"Contact identifiers: phone={contact.phone}, emails={contact.emails}")

    # Log the contents of the export directory
    if export_path.exists():
        logger.info(f"Export directory contents: {[p.name for p in export_path.iterdir()]}")
    else:
        logger.warning(f"Export directory {export_path} does not exist")
        return []

    # Get combined file with both phone and email messages if available
    message_file = await detect_file(export_path, contact.phone, contact.emails)

    if message_file:
        logger.info(f"Found message file: {message_file}")
        return [message_file]

    # No message files found
    logger.warning(f"No message files found for {contact.name}")
    return []


def merge_files(file1: Path, file2: Path) -> Path:
    """Merge two files into a single file."""
    combined_file = file1.parent / f"{file1.stem}_combined.txt"
    merge_text_files([file1, file2], combined_file)
    return combined_file


def sort_messages(messages: list[list[str]]) -> list[list[str]]:
    """Sort messages by date.

    Args:
        messages: List of messages, each containing [sender, date, content]

    Returns:
        Sorted list of messages by date
    """

    # Convert each message's date to a comparable format for sorting
    def get_sortable_date(message):
        date_value = message[1]
        # If it's already a pandas Timestamp or similar datetime object, use it directly
        if hasattr(date_value, "timestamp"):
            return date_value
        # Otherwise parse it as a string
        return parse_date_string(date_value)

    return sorted(messages, key=get_sortable_date)


def chunk_messages(
    messages: list[list[str]],
    chunk_size: int | None = None,
    size_mb: float | None = None,
    lines: int | None = None,
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
            current_chunk.append(message)
        elif lines:
            # Count number of newlines in the message text plus 1 for the message itself
            message_lines = message[2].count("\n") + 1
            if current_lines + message_lines > lines and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_lines = 0
            current_lines += message_lines
            current_chunk.append(message)
        elif chunk_size:
            if len(current_chunk) >= chunk_size:
                chunks.append(current_chunk)
                current_chunk = []
            current_chunk.append(message)
        else:
            # Fallback case - should not happen with proper validation
            current_chunk.append(message)

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def message_generator(
    file_path: Path,
    contact: Contact,
) -> Generator[list[str], None, None]:
    """Generate parsed messages from a file.

    Args:
        file_path: Path to the message file
        contact: Contact whose messages to parse

    Yields:
        List of messages, where each message is [sender: str, date: str, content: str]
    Raises:
        FileNotFoundError: If the input file does not exist
        ValueError: If the input file is not a regular file
    """
    if not file_path.exists():
        error_msg = f"Input file does not exist: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    if not file_path.is_file():
        error_msg = f"Input file is not a regular file: {file_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)

    # Read the file content using the utility function
    content = read_text_file(file_path)
    date: str = ""
    sender: str = ""
    message: list[str] = []
    prev_line_empty: bool = True  # Track if previous line was empty

    for line_content in content.splitlines():
        line = line_content.strip()

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
            raw_date = read_receipt_pattern.sub("", date_match.group(1)).strip()

            # Check for invalid dates
            if not raw_date:
                logger.warning("Skipping invalid date: %s", date_match.group(1))
                continue

            # Parse the date with proper Mountain Time zone awareness
            try:
                dt_obj = parse_date_string(raw_date)
                # Convert to pandas Timestamp with timezone info preserved
                date = pd.Timestamp(dt_obj).tz_convert("America/Edmonton")
            except ValueError:
                # Fallback to original date format if parsing fails
                logger.warning(
                    "Failed to parse date: %s, using as-is",
                    raw_date,
                )
                date = raw_date

            sender = None
            message = []
        elif date and not sender:
            # If it's a phone number, check if it matches our contact
            if re.match(r"^\+?\d+$", line):
                normalized_line = normalize_phone_number(line)
                sender = contact.name if normalized_line == contact.phone else line
            # If it's Phil's email
            elif line in contact.emails:
                sender = contact.name
            # If it's Jess
            elif line == "Jess":
                sender = "Jess"
            # Otherwise keep the original sender
            else:
                sender = line
        elif date and sender:
            # Clean the line by removing emojis and special characters, preserving text
            message.append(
                clean_message_content(line),
            )

        prev_line_empty = False

    # Yield the last message
    if date and sender and message:
        yield [sender, date, ",".join(message)]


def parse_messages(file_path: Path, contact: Contact, *, only_contact: bool = False) -> list[list[str]]:
    """Parse and sort all messages from a file.

    Args:
        file_path: Path to the message file
        contact: Contact whose messages to parse
        only_contact: Whether to only include messages from the contact

    Returns:
        List of sorted messages, where each message is [sender, date, content]
    """
    messages = list(message_generator(file_path, contact))
    if only_contact:
        # Keep only messages from the contact (not from "Jess") contact.name
        messages = [message for message in messages if message[0] == contact.name]
        # Filter out messages with more than 3000 characters
        # messages = [message for message in messages if len(message[2]) <= 1600]
        # # Filter out messages containing "Brenda:" or "Frank:"
        # messages = [message for message in messages if "Brenda:" not in message[2] and "Frank:" not in message[2]]
    return sort_messages(messages)


async def process_messages_with_generator(
    file_path: Path,
    contact: Contact,
    *,
    only_contact: bool = False,
    chunk_size: int | None = None,
    output_dir: Path = OUTPUT_DIR,
) -> Path:
    """Process messages using a generator and write them to chunks.

    Args:
        file_path: Path to the message file
        contact: Contact to export messages for
        only_contact: Whether to only include messages from the contact
        chunk_size: Optional number of messages per chunk
        output_dir: Directory to write output files to

    Returns:
        Path to the output directory containing the chunks
    """
    # Generate a single timestamp for all chunks in this run
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Parse messages
    messages = parse_messages(file_path, contact, only_contact=only_contact)

    # Chunk messages
    chunks = chunk_messages(messages, chunk_size=chunk_size)

    # Write chunks to files
    for i, chunk in enumerate(chunks, 1):
        await write_chunk(chunk, i, output_dir, run_timestamp)

    return output_dir


# def run_analytics(csv_buffer: str) -> None:
#     """Run analytics on the messages."""
#     df = pd.read_csv(io.StringIO(csv_buffer))

#     # Get analytics of data: ID, Sender, Datetime, Message
#     # frequency of messages per hour of day per week for each chunk and printed to graph
#     # Convert datetime string to datetime object
#     df["Datetime"] = pd.to_datetime(df["Datetime"])

#     # Extract hour of day and day of week
#     df["hour"] = df["Datetime"].dt.hour
#     df["day_of_week"] = df["Datetime"].dt.day_name()

#     # Create frequency analysis
#     hourly_counts = df.groupby(["day_of_week", "hour"]).size().unstack(fill_value=0)

#     # Sort days of week in correct order
#     days_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
#     hourly_counts = hourly_counts.reindex(days_order)

#     # Create heatmap
#     plt.figure(figsize=(12, 8))
#     sns.heatmap(hourly_counts, cmap="viridis", annot=True, fmt="d")
#     plt.title("Message Frequency by Hour and Day of Week")
#     plt.xlabel("Hour of Day")
#     plt.ylabel("Day of Week")
#     plt.tight_layout()

#     # Save the plot
#     analytics_dir = output_dir / timestamp / "analytics"
#     analytics_dir.mkdir(exist_ok=True)
#     plt.savefig(analytics_dir / "message_frequency_heatmap.png")
#     plt.close()

#     logger.info(f"Analytics completed and saved to {analytics_dir}")

#     # word cloud of messages for words of at least 4 characters

#     return True


async def write_chunk(chunk: list[list[str]], chunk_num: int, output_dir: Path, timestamp: str) -> None:
    """Write a chunk of messages to CSV and TXT files.

    Args:
        chunk: List of messages to write
        chunk_num: Chunk number
        output_dir: Directory to write output files to
        timestamp: Timestamp string to use for the folder name
    """
    # Get the date from the first message in the chunk
    if chunk:
        date_dir = output_dir / timestamp
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

        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["ID", "Sender", "Datetime", "Message"])
        # Add ID column with autoincrementing values starting from 1
        for i, row in enumerate(chunk, 1):
            writer.writerow([i, *row])

        # Write the CSV content to the file
        await csvfile.write(csv_buffer.getvalue())

        # getAnalytics = runAnalytics(csv_buffer.getvalue())

    # Write to TXT with empty lines between rows (no ID column for TXT)
    txt_file_path = txt_dir / f"chunk_{chunk_num}.txt"
    async with aiofiles.open(txt_file_path, "w", encoding="utf-8") as txtfile:
        for row in chunk:
            await txtfile.write(f"{row[0]},{row[1]},{row[2]}\n")

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
    logger.info(f"\nContact '{name}' not found in contacts.")
    while True:
        phone = input(
            f"Please enter phone number for {name} (or 'cancel' to exit): ",
        ).strip()
        if phone.lower() == "cancel":
            return None

        try:
            normalized = normalize_phone_number(phone)
            if not normalized:
                logger.warning("Phone number cannot be empty")
                continue

            confirm = input(
                f"Normalized number: {normalized}. Is this correct? (y/n): ",
            ).lower()
            if confirm == "y":
                return normalized
        except Exception as e:
            logger.warning(f"Invalid phone number: {e}")


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
            emails=[],
        )
        logger.info(f"Added new contact: {name} ({phone})")

    return contact


async def process_message_files(
    message_files: list[Path],
    contact: Contact,
    *,
    chunk_size: float | None = None,
    lines: int | None = None,
    only_contact: bool = False,
) -> None:
    """Process message files and generate output chunks.

    Args:
        message_files: List of message files to process
        contact: Contact to export messages for
        chunk_size: Optional size in MB per chunk
        lines: Optional number of lines per chunk
        only_contact: Whether to only include messages from the contact
    """
    # Generate a single timestamp for all chunks in this run
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

    # Combine messages from all files
    all_messages = []
    for file_path in message_files:
        messages = parse_messages(file_path, contact, only_contact=only_contact)
        all_messages.extend(messages)

    # Sort all messages chronologically
    sorted_messages = sort_messages(all_messages)

    # Split into chunks based on size in MB or number of lines
    chunks = chunk_messages(sorted_messages, size_mb=chunk_size, lines=lines)

    # Write chunks to files
    for i, chunk in enumerate(chunks, 1):
        await write_chunk(chunk, i, OUTPUT_DIR, run_timestamp)


async def process_messages(
    config: ExportConfig,
    contact: Contact,
    args: argparse.Namespace,
) -> bool:
    """Process iMessage export without retry logic.

    Args:
        config: Export configuration
        contact: Contact to export messages for
        args: Command line arguments

    Returns:
        bool: True if messages were found and processed, False otherwise
    """
    # Clear temporary directory
    clear_folder(TMP_PATH)

    # Run the iMessage-exporter
    logger.info(f"Running iMessage export for {contact.name} with date: {config.date or 'no date filter'}")
    await run_imessage_exporter(
        contact,
        config.date,
        config.end_date,
        TMP_PATH,
    )

    # Find message files
    message_files = await find_message_files(TMP_PATH, contact)

    # If no message files were found, print a message and return False
    if not message_files:
        date_info = f" for date {config.date}" if config.date else ""
        print(f"\nNo messages found for {contact.name}{date_info}.")
        print("This could mean:")
        print("1. There are no messages for this contact on the specified date")
        print("2. The contact identifiers (phone/email) are incorrect")
        print("3. The messages are not in the expected iMessage format")
        print("\nTry using an earlier date or no date filter.")
        return False

    # Process message files
    await process_message_files(
        message_files,
        contact,
        chunk_size=config.chunk_size,
        lines=args.lines,
        only_contact=args.one_side,
    )

    return True


async def main() -> None:
    """Process iMessage exports with error handling."""
    try:
        # Parse arguments and initialize config
        args = parse_arguments()
        config = initialize_export(args)

        # Set up contact store and get contact
        contact_store = ContactStore(CONTACT_STORE_FILE)
        contact = setup_contact(config.name, contact_store)

        # Clear export directory
        clear_folder(config.export_path)

        # Process messages - if it returns False, messages were not found
        # and a user-friendly message has already been printed
        if not await process_messages(config, contact, args):
            sys.exit(1)

    except Exception:
        logger.exception("Unexpected error occurred")
        sys.exit(1)


def cli_main() -> None:
    """Command-line interface entry point for the application.

    This function serves as the main entry point when the script is executed from the command line.
    It sets up the asyncio event loop and runs the main coroutine.
    """
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
