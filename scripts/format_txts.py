import argparse
import asyncio
import csv
import io
import logging
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

# NOTE: This script is intended to be run as a module (e.g., `python -m scripts.format_txts` or via Poetry CLI).
# Running it directly (e.g., `python scripts/format_txts.py`) may cause import errors due to package structure.
from scripts.constants import DEFAULT_TIMEZONE, OUTPUT_DIR, TMP_PATH
from scripts.SQLiteContactStore import Contact, SQLiteContactStore
from scripts.utils import (
    clean_message_content,
    is_date_in_future,
    merge_text_files,
    parse_date_string,
    read_text_file,
)

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
class Contact:
    """Represents a contact with their messaging identifiers."""

    name: str
    phones: list[str]
    emails: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Convert contact to dictionary for storage.

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
        return cls(**data)


# --- BEGIN SQLITE CONTACT STORE INTEGRATION ---


# Helper: select all identifiers for iMessage exporter
def get_identifiers(contact: Contact) -> str:
    """Return a comma-separated string of all normalized phone numbers and emails for the contact."""
    identifiers = []
    if hasattr(contact, "phones") and contact.phones:
        for p in contact.phones:
            if p:
                identifiers.append(normalize_phone_number(p))
    if hasattr(contact, "emails") and contact.emails:
        identifiers.extend([e for e in contact.emails if e])
    if not identifiers:
        raise ValueError(f"Contact {contact.name} has no phone numbers or emails.")
    return ",".join(identifiers)


def get_combined_identifiers(contacts: list[Contact]) -> str:
    """Return a comma-separated string of all identifiers from multiple contacts."""
    all_identifiers = []
    for contact in contacts:
        try:
            contact_identifiers = get_identifiers(contact)
            all_identifiers.extend(contact_identifiers.split(","))
        except ValueError as e:
            logger.warning(f"Skipping contact {contact.name}: {e}")
            continue

    if not all_identifiers:
        raise ValueError("No valid identifiers found for any contacts.")

    return ",".join(all_identifiers)


# Helper function to get or create a contact by name (case-insensitive, exact)
def get_or_create_contact(store: SQLiteContactStore, name: str) -> Contact:
    contact = store.get_contact_by_name(name)
    if contact:
        return contact
    # Prompt for phone and email if not found
    phone = input(f"Enter phone number for {name}: ")
    phones = [phone] if phone else []
    emails = []
    email = input(f"Enter email for {name} (optional, press Enter to skip): ")
    if email:
        emails.append(email)
    return store.add_contact(name, phones, emails)


# Update main CLI flow to use SQLiteContactStore
def setup_contact(name: str, store: SQLiteContactStore) -> Contact:
    contact = store.get_contact_by_name(name)
    if contact:
        return contact
    print(f"Contact '{name}' not found. You will be prompted to enter details.")
    return get_or_create_contact(store, name)


# --- END SQLITE CONTACT STORE INTEGRATION ---


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
        "--names",
        type=str,
        nargs="+",
        help="Names of contacts to export messages for (can specify multiple)",
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


def initialize_export(args: argparse.Namespace) -> dict[str, Any]:
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

    # Set default names to ["Phil"] if not specified
    names = args.names or ["Phil"]

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

    return {
        "names": names,
        "date": date,
        "end_date": end_date,
        "export_path": export_path,
        "chunk_size": args.size,  # Pass size in MB directly
    }


async def run_imessage_exporter(
    contacts: list[Contact],
    date: str | None = None,
    end_date: str | None = None,
    export_path: Path | None = None,
) -> Path | None:
    """Run the iMessage-exporter command asynchronously.

    Args:
        contacts: List of Contact instances
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

    # Combine identifiers from all contacts
    combined_identifiers = get_combined_identifiers(contacts)
    base_command.extend(["-t", combined_identifiers])

    export_check_path = export_path or (Path.home() / "imessage-export")

    if export_path:
        base_command.extend(["-o", str(export_path)])

    # Logging
    contact_names = [contact.name for contact in contacts]
    logger.info(f"Running iMessage export for contacts: {', '.join(contact_names)}")
    logger.info(f"Combined identifiers: {combined_identifiers}")
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
            error_msg = f"iMessage-exporter failed with return code {process.returncode or 0}: {stderr.decode().strip()}"
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

        logger.info(
            f"Export directory contents: {[p.name for p in export_check_path.iterdir()]}"
        )

    except subprocess.CalledProcessError:
        logger.exception("iMessage-exporter command failed")
        raise

    return export_check_path


def detect_file(
    folder_path: Path | None,
    phone_numbers: list[str] | None = None,
    emails: list[str] | None = None,
) -> Path | None:
    """Detect and potentially combine message files from phone numbers and emails.

    Args:
        folder_path: Path to the export folder
        phone_numbers: List of phone numbers to look for
        emails: Optional list of email addresses to look for

    Returns:
        Path: Path to the message file (might be a combined file)

    Raises:
        FileNotFoundError: If no matching files are found
    """
    if not folder_path or not folder_path.exists():
        raise FileNotFoundError("Export folder not found")

    found_files = []

    # Look for phone number files
    if phone_numbers:
        for phone in phone_numbers:
            phone_pattern = f"*+{phone}*.txt"
            phone_files = list(folder_path.glob(phone_pattern))
            print(phone_pattern, phone_files)
            if phone_files:
                found_files.extend(phone_files)

    # Look for email files
    if emails:
        for email in emails:
            email_pattern = f"*{email}*.txt"
            email_files = list(folder_path.glob(email_pattern))
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


def find_message_files(export_path: Path, contacts: list[Contact]) -> list[Path]:
    """Find and return message files for multiple contacts.

    Args:
        export_path: Path to the export directory
        contacts: List of contacts to find messages for

    Returns:
        list[Path]: List of message files found, empty if none
    """
    contact_names = [contact.name for contact in contacts]
    logger.info(
        f"Searching for message files in {export_path} for contacts: {', '.join(contact_names)}"
    )

    # Collect all phone numbers and emails from all contacts
    all_phones = []
    all_emails = []
    for contact in contacts:
        if hasattr(contact, "phones") and contact.phones:
            all_phones.extend(contact.phones)
        if hasattr(contact, "emails") and contact.emails:
            all_emails.extend(contact.emails)

    phone_str = ",".join(all_phones) if all_phones else "none"
    email_str = ",".join(all_emails) if all_emails else "none"
    logger.info(f"Combined identifiers: phones={phone_str}, emails={email_str}")

    # Log the contents of the export directory
    if export_path.exists():
        logger.info(
            f"Export directory contents: {[p.name for p in export_path.iterdir()]}"
        )
    else:
        logger.warning(f"Export directory {export_path} does not exist")
        return []

    # Get combined file with both phone and email messages if available
    message_file = detect_file(export_path, all_phones, all_emails)

    if message_file:
        logger.info(f"Found message file: {message_file}")
        return [message_file]

    # No message files found
    logger.warning(f"No message files found for contacts: {', '.join(contact_names)}")
    return []


def merge_files(file1: Path, file2: Path) -> Path:
    """Merge two files into a single file."""
    combined_file = file1.parent / f"{file1.stem}_combined.txt"
    merge_text_files([file1, file2], combined_file)
    return combined_file


def sort_messages(messages: list[list[Any]]) -> list[list[Any]]:
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
    messages: list[list[Any]],
    chunk_size: int | None = None,
    size_mb: float | None = None,
    lines: int | None = None,
) -> list[list[list[Any]]]:
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

    chunks: list[list[list[Any]]] = []
    current_chunk: list[list[Any]] = []
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


def format_timestamp(dt: pd.Timestamp, fmt: str = "%Y-%m-%d") -> str:
    """Format a pandas.Timestamp as a string."""
    if not isinstance(dt, pd.Timestamp):
        raise TypeError(f"Expected pandas.Timestamp, got {type(dt)}")
    return dt.strftime(fmt)


def generate_chunk_filename(
    contact_name: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
    chunk_num: int = None,
    ext: str = "txt",
) -> str:
    """Generate a safe, descriptive filename for a message chunk."""
    safe_name = "".join(c for c in contact_name[:20] if c.isalnum())
    start = format_timestamp(start_date, "%Y-%m-%d")
    end = format_timestamp(end_date, "%Y-%m-%d")
    filename = f"{safe_name}_{start}_to_{end}"
    if chunk_num is not None and chunk_num > 1:
        filename += f"_chunk{chunk_num}"
    return f"{filename}.{ext}"


async def write_chunk(
    chunk: list[list[Any]],
    chunk_num: int,
    output_dir: Path,
    timestamp: str,
    contact_name: str,
    start_date: pd.Timestamp,
    end_date: pd.Timestamp,
) -> None:
    """Write a chunk of messages to CSV and TXT files with descriptive filenames."""
    if chunk:
        date_dir = output_dir / timestamp
        date_dir.mkdir(parents=True, exist_ok=True)
        txt_dir = date_dir / "chunks_txt"
        csv_dir = date_dir / "chunks_csv"
        txt_dir.mkdir(exist_ok=True)
        csv_dir.mkdir(exist_ok=True)
    else:
        return
    txt_filename = generate_chunk_filename(
        contact_name, start_date, end_date, chunk_num, ext="txt"
    )
    csv_filename = generate_chunk_filename(
        contact_name, start_date, end_date, chunk_num, ext="csv"
    )
    csv_file_path = csv_dir / csv_filename
    async with aiofiles.open(csv_file_path, "w", encoding="utf-8") as csvfile:
        csv_buffer = io.StringIO()
        writer = csv.writer(csv_buffer)
        writer.writerow(["ID", "Sender", "Datetime", "Message"])
        for i, row in enumerate(chunk, 1):
            # row[1] is always pd.Timestamp
            writer.writerow(
                [i, row[0], format_timestamp(row[1], "%Y-%m-%d %H:%M:%S"), row[2]]
            )
        await csvfile.write(csv_buffer.getvalue())
    txt_file_path = txt_dir / txt_filename
    async with aiofiles.open(txt_file_path, "w", encoding="utf-8") as txtfile:
        for row in chunk:
            await txtfile.write(
                f"{row[0]},{format_timestamp(row[1], '%Y-%m-%d %H:%M:%S')},{row[2]}\n"
            )
    logger.info(f"Chunk {chunk_num} written to {csv_file_path} and {txt_file_path}")


def chunk_messages_with_dates(
    messages: list[list[Any]],
    chunk_size: int | None = None,
    size_mb: float | None = None,
    lines: int | None = None,
) -> list[tuple[list[list[Any]], pd.Timestamp, pd.Timestamp]]:
    """Split messages into chunks, returning chunk with start/end dates as pd.Timestamp."""
    if not chunk_size and not size_mb and not lines:
        if messages:
            start_date = messages[0][1]
            end_date = messages[-1][1]
            return [(messages, start_date, end_date)]
        return []
    chunks = []
    current_chunk = []
    current_size = 0
    current_lines = 0
    for message in messages:
        if size_mb:
            message_size = sum(len(str(field).encode("utf-8")) for field in message)
            if current_size + message_size > size_mb * 1024 * 1024 and current_chunk:
                start_date = current_chunk[0][1]
                end_date = current_chunk[-1][1]
                chunks.append((current_chunk, start_date, end_date))
                current_chunk = []
                current_size = 0
            current_size += message_size
            current_chunk.append(message)
        elif lines:
            message_lines = message[2].count("\n") + 1
            if current_lines + message_lines > lines and current_chunk:
                start_date = current_chunk[0][1]
                end_date = current_chunk[-1][1]
                chunks.append((current_chunk, start_date, end_date))
                current_chunk = []
                current_lines = 0
            current_lines += message_lines
            current_chunk.append(message)
        elif chunk_size:
            if len(current_chunk) >= chunk_size:
                start_date = current_chunk[0][1]
                end_date = current_chunk[-1][1]
                chunks.append((current_chunk, start_date, end_date))
                current_chunk = []
            current_chunk.append(message)
        else:
            current_chunk.append(message)
    if current_chunk:
        start_date = current_chunk[0][1]
        end_date = current_chunk[-1][1]
        chunks.append((current_chunk, start_date, end_date))
    return chunks


async def process_message_files(
    message_files: list[Path],
    contacts: list[Contact],
    *,
    chunk_size: float | None = None,
    lines: int | None = None,
    only_contact: bool = False,
) -> None:
    """Process message files and generate output chunks with descriptive filenames."""
    run_timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    all_messages = []

    # Create a combined contact name for file naming
    contact_names = [contact.name for contact in contacts]
    combined_name = "_".join(
        contact_names[:3]
    )  # Limit to first 3 names to avoid overly long filenames
    if len(contact_names) > 3:
        combined_name += f"_and_{len(contact_names) - 3}_more"

    for file_path in message_files:
        # Parse messages for all contacts
        messages = parse_messages(file_path, contacts, only_contact=only_contact)
        all_messages.extend(messages)

    sorted_messages = sort_messages(all_messages)
    chunks = chunk_messages_with_dates(sorted_messages, size_mb=chunk_size, lines=lines)
    for i, (chunk, start_date, end_date) in enumerate(chunks, 1):
        await write_chunk(
            chunk, i, OUTPUT_DIR, run_timestamp, combined_name, start_date, end_date
        )


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


async def process_messages(
    config: dict[str, Any],
    contacts: list[Contact],
    args: argparse.Namespace,
) -> bool:
    """Process iMessage export without retry logic.

    Args:
        config: Export configuration
        contacts: List of contacts to export messages for
        args: Command line arguments

    Returns:
        bool: True if messages were found and processed, False otherwise
    """
    # Clear temporary directory
    clear_folder(TMP_PATH)

    # Run the iMessage-exporter
    contact_names = [contact.name for contact in contacts]
    logger.info(
        f"Running iMessage export for contacts: {', '.join(contact_names)} with date: {config['date'] or 'None'}"
    )
    await run_imessage_exporter(
        contacts,
        config["date"],
        config["end_date"],
        TMP_PATH,
    )

    # Find message files
    message_files = find_message_files(TMP_PATH, contacts)

    # If no message files were found, print a message and return False
    if not message_files:
        date_info = f" for date {config['date']}" if config["date"] else ""
        print(
            f"\nNo messages found for contacts: {', '.join(contact_names)}{date_info}."
        )
        print("This could mean:")
        print("1. There are no messages for these contacts on the specified date")
        print("2. The contact identifiers (phone/email) are incorrect")
        print("3. The messages are not in the expected iMessage format")
        print("\nTry using an earlier date or no date filter.")
        return False

    # Process message files
    await process_message_files(
        message_files,
        contacts,
        chunk_size=config["chunk_size"],
        lines=args.lines,
        only_contact=args.one_side,
    )

    return True


def message_generator(
    file_path: Path,
    contacts: list[Contact],
) -> Generator[list[Any], None, None]:
    """Generate parsed messages from a file, always yielding pd.Timestamp for date."""
    if not file_path.exists():
        error_msg = f"Input file does not exist: {file_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)
    if not file_path.is_file():
        error_msg = f"Input file is not a regular file: {file_path}"
        logger.error(error_msg)
        raise ValueError(error_msg)
    content = read_text_file(file_path)
    date: pd.Timestamp | None = None
    sender: str = ""
    message: list[str] = []
    prev_line_empty: bool = True
    for line_content in content.splitlines():
        line = line_content.strip()
        if not line:
            prev_line_empty = True
            continue
        if prev_line_empty and (date_match := date_pattern.match(line)):
            if date and sender and message:
                yield [sender, date, " ".join(message)]
            raw_date = read_receipt_pattern.sub("", date_match.group(1)).strip()
            if not raw_date:
                logger.warning("Skipping invalid date: %s", date_match.group(1))
                continue
            try:
                dt_obj = parse_date_string(raw_date)
                date = pd.Timestamp(dt_obj).tz_convert("America/Edmonton")
            except Exception as e:
                logger.warning(
                    f"Failed to parse date: {raw_date}, error: {e}. Skipping message."
                )
                date = None
                sender = ""
                message = []
                continue
            sender = None
            message = []
        elif date and not sender:
            print(line)
            if re.match(r"^\+?\d+$", line):
                normalized_line = normalize_phone_number(line)
                # Check against all contacts
                for contact in contacts:
                    normalized_phones = [
                        normalize_phone_number(p) for p in contact.phones
                    ]
                    if normalized_line in normalized_phones:
                        sender = contact.name
                        break
                else:
                    sender = line
            else:
                # Check if it's an email for any contact
                for contact in contacts:
                    if line in contact.emails:
                        sender = contact.name
                        break
                else:
                    if line == "Jess":
                        sender = "Jess"
                    else:
                        sender = line
        elif date and sender:
            message.append(clean_message_content(line))
        prev_line_empty = not line
    if date and sender and message:
        yield [sender, date, " ".join(message)]


def parse_messages(
    file_path: Path, contacts: list[Contact], *, only_contact: bool = False
) -> list[list[Any]]:
    """Parse and sort all messages from a file, always using pd.Timestamp for date."""
    messages = list(message_generator(file_path, contacts))
    if only_contact:
        contact_names = [contact.name for contact in contacts]
        messages = [message for message in messages if message[0] in contact_names]
    return sort_messages(messages)


async def main() -> None:
    """Process iMessage exports with error handling."""
    store = None
    try:
        # Parse arguments and initialize config
        args = parse_arguments()
        config = initialize_export(args)

        # Set up contact store and get contacts
        store = SQLiteContactStore()
        contacts = []
        for name in config["names"]:
            contact = setup_contact(name, store)
            contacts.append(contact)
            # Ensure per-contact message and chunk tables exist before any DB operations
            store.ensure_contact_tables(contact.name)

        # Clear export directory
        clear_folder(config["export_path"])

        # Process messages - if it returns False, messages were not found
        # and a user-friendly message has already been printed
        if not await process_messages(config, contacts, args):
            sys.exit(1)

    except Exception:
        logger.exception("Unexpected error occurred")
        sys.exit(1)
    finally:
        # Ensure the database connection is closed gracefully
        if store is not None:
            store.close()


def cli_main() -> None:
    """Command-line interface entry point for the application.

    This function serves as the main entry point when the script is executed from the command line.
    It sets up the asyncio event loop and runs the main coroutine.
    """
    asyncio.run(main())


if __name__ == "__main__":
    cli_main()
