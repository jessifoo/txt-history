import argparse
import asyncio
import csv
import logging
import re
import os
import subprocess
from datetime import datetime
from logging import Logger
from pathlib import Path
from typing import List, Optional, Dict
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Regular expressions
date_pattern = re.compile(r"^(\w{3} \d{2}, \d{4}\s*\d{1,2}:\d{2}:\d{2} \w{2})")
read_receipt_pattern = re.compile(r"\(Read by.*$")

def normalize_phone_number(phone_number: str) -> str:
    """Normalize phone number to a consistent format.

    Args:
        phone_number: The phone number to normalize

    Returns:
        str: Normalized phone number containing only digits and '+'
    """
    # Remove all characters except digits and +
    normalized = re.sub(r"[^\d+]", "", phone_number)

    # Ensure + is only at the start if present
    if "+" in normalized and not normalized.startswith("+"):
        normalized = normalized.replace("+", "")
        normalized = "+" + normalized

    return normalized

# Map phone numbers to names
phone_number_map: Dict[str, str] = {
    "Phil": normalize_phone_number("+18673335566"),
    "Robert": normalize_phone_number("+17806793467"),
    "Rhonda": normalize_phone_number("+17803944504"),
    "Sherry": normalize_phone_number("+17807223445"),
    "Jess": "Jess",
}

# New output directory within txt-history
OUTPUT_DIR = Path(__file__).parent / "output"


async def run_imessage_exporter(
    name: str,
    date: Optional[str],
    phone_number: str,
    imessage_filter: str,
    export_path: Optional[Path] = None,
) -> None:
    """Run the iMessage-exporter command asynchronously.

    Args:
        name: Contact name
        date: Optional start date for export
        phone_number: Phone number to export
        imessage_filter: Filter string for iMessage export
        export_path: Optional path to save exported files (for testing)

    Raises:
        subprocess.CalledProcessError: If the iMessage-exporter command fails
        FileNotFoundError: If the export produces no output
        RuntimeError: If the export folder is empty after successful command execution
    """
    # Get imessage-exporter path from environment or use default
    imessage_exporter_path = os.environ.get("IMESSAGE_EXPORTER_PATH", "/opt/homebrew/bin/imessage-exporter")
    base_command = [imessage_exporter_path, "-f", "txt", "-c", "disabled", "-m", "Jess"]

    if date:
        base_command.extend(["-s", date])

    if name == "Phil":
        base_command.extend(["-t", imessage_filter])
    else:
        base_command.extend(["-t", phone_number])

    if export_path:
        base_command.extend(["-o", str(export_path)])

    logger.info(f"Running iMessage export for {name} (phone: {phone_number})")
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

        if process.returncode != 0:
            error_msg = f"iMessage-exporter failed with return code {process.returncode}: {stderr.decode().strip()}"
            logger.error(error_msg)
            raise subprocess.CalledProcessError(
                process.returncode, base_command, stderr
            )

        export_check_path = export_path or (Path.home() / "imessage_export")
        if not export_check_path.exists() or not any(export_check_path.iterdir()):
            raise RuntimeError(f"Export folder is empty: {export_check_path}")

    except subprocess.CalledProcessError as e:
        logger.error(f"iMessage-exporter command failed: {e}")
        raise


def clear_folder(folder_path: Path) -> None:
    """Forcefully delete the specified folder and its contents.

    Args:
        folder_path: Path to the folder to be cleared

    Raises:
        subprocess.CalledProcessError: If folder deletion fails
    """

    if folder_path.exists():
        try:
            subprocess.run(["rm", "-rf", str(folder_path)], check=True)
            logger.info(f"Cleared folder: {folder_path}")
        except subprocess.CalledProcessError as e:
            logger.error(f"Failed to clear folder: {folder_path}, {e}")
            raise
    else:
        logger.info(f"Folder does not exist: {folder_path}")


def detect_file(
    folder_path: Path, phone_number: str, email: Optional[str] = None
) -> Path:
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
    logger.info(f"Searching for messages with phone: {phone_number}, email: {email}")

    # Check if folder exists first
    if not folder_path.exists():
        error_msg = f"Export folder does not exist: {folder_path}"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)

    # Initialize file paths
    phone_file = folder_path / f"{phone_number}.txt" if phone_number else None
    email_file = folder_path / f"{email}.txt" if email else None

    # Track which files exist
    phone_exists = phone_file.exists() if phone_file else False
    email_exists = email_file.exists() if email_file else False

    # Return the file that exists; prioritize phone file over email file if both exist
    if phone_exists:
        return phone_file
    elif email_exists:
        return email_file
    else:
        error_msg = "No matching message files found"
        logger.error(error_msg)
        raise FileNotFoundError(error_msg)


def parse_messages(input_file: Path, name: str = "Phil") -> List[List[str]]:
    """Parse iMessage export text file into structured format.

    Args:
        input_file: Path to the input file
        name: Name of the contact to map phone number for (default: Phil)

    Returns:
        List of [sender, date, message] lists
    """
    parsed_messages = []
    date, sender, message = "", "", []
    phil_email = "apple@phil-g.com"  # Phil's email address

    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")
    if not input_file.is_file():
        raise ValueError(f"Input file is not a regular file: {input_file}")

    try:
        with open(input_file, "r", encoding="utf-8") as infile:
            lines = infile.readlines()
    except IOError as e:
        raise RuntimeError(f"Failed to read input file: {input_file}, {e}")

    if not lines:
        raise RuntimeError(f"Input file is empty: {input_file}")

    for line in lines:
        try:
            # Remove read receipt and strip whitespace
            line = re.sub(read_receipt_pattern, "", line).strip()
            
            # Skip empty lines
            if not line:
                continue
                
            # If this is a date line, store previous message and start new one
            if date_pattern.match(line):
                if date and sender and message:  # Only append if we have a complete message
                    parsed_messages.append([sender, date, " ".join(message)])
                date = line
                sender = None  # Reset sender for next message
                message = []
            # If we have a date but no sender yet, this line is the sender
            elif date and not sender:
                # If it's a phone number, check against all mapped numbers
                if re.match(r"^\+?\d+$", line):
                    normalized_line = normalize_phone_number(line)
                    # First check if it matches the requested contact's number
                    if normalized_line == phone_number_map.get(name):
                        sender = name
                    else:
                        # Check other mapped numbers
                        sender = next(
                            (n for n, number in phone_number_map.items() if number == normalized_line),
                            line  # Keep original if no match
                        )
                # If it's Phil's email and name is Phil
                elif line == phil_email and name == "Phil":
                    sender = "Phil"
                # If it's Jess
                elif line == "Jess":
                    sender = "Jess"
                # Otherwise keep the original sender
                else:
                    sender = line
            # If we have both date and sender, this is part of the message
            elif date and sender:
                message.append(line)
        except Exception as e:
            raise RuntimeError(f"Failed to parse line: {line}, {e}")

    # Don't forget the last message
    if sender and date and message:
        parsed_messages.append([sender, date, " ".join(message)])

    return parsed_messages


def estimate_rows_per_chunk(input_csv_path: Path, max_file_size_mb: float = 5) -> int:
    """Estimate the maximum rows that can fit in a file given a size limit.

    Args:
        input_csv_path: Path to the input CSV file
        max_file_size_mb: Maximum file size in MB (default: 5)

    Returns:
        int: Estimated rows per chunk
    """
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    total_rows = (
        sum(1 for _ in open(input_csv_path, "r", encoding="utf-8")) - 1
    )  # Subtract header
    file_size = input_csv_path.stat().st_size
    bytes_per_row = file_size / total_rows
    return max(1, int(max_file_size_bytes / bytes_per_row))


def generate_output_directory(base_dir: Path) -> Path:
    """Generate a timestamped directory for output.

    Args:
        base_dir: Base directory for output

    Returns:
        Path: Path to the generated output directory
    """
    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = base_dir / f"chunks_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def chunk_messages(messages: List[List[str]], base_output_folder: Path, size_mb: float) -> Path:
    """Split messages into chunks and write them to CSV and TXT files.
    Each chunk will be capped at a size determined by size_mb.

    Args:
        messages: List of [sender, date, message] lists to chunk
        base_output_folder: Base directory to create output folders in
        size_mb: Maximum size in MB for each chunk

    Returns:
        Path to the output directory containing the chunks

    Raises:
        OSError: If there are issues creating directories or writing files
        ValueError: If the input parameters are invalid
    """
    try:
        if not messages:
            raise ValueError("No messages to chunk")
        if size_mb <= 0:
            raise ValueError(f"Invalid chunk size: {size_mb}MB")

        # Create output directories
        output_dir = generate_output_directory(base_output_folder)
        chunks_dir_csv = output_dir / "_chunks_csv"
        chunks_dir_txt = output_dir / "_chunks_txt"
        chunks_dir_csv.mkdir(parents=True, exist_ok=True)
        chunks_dir_txt.mkdir(parents=True, exist_ok=True)

        # Write all messages to a single CSV first
        all_messages_csv = chunks_dir_csv / "all_messages.csv"
        with open(all_messages_csv, "w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow(["Sender", "Date", "Message"])
            writer.writerows(messages)

        # Calculate rows per chunk based on total file size
        rows_per_chunk = estimate_rows_per_chunk(all_messages_csv, size_mb)
        logger.info(f"Using {rows_per_chunk} rows per chunk based on {size_mb}MB size limit")

        # Read and split into chunks
        chunk = []
        chunk_num = 1

        with open(all_messages_csv, "r", newline="", encoding="utf-8") as f:
            reader = csv.reader(f)
            next(reader)  # Skip header

            for i, row in enumerate(reader, 1):
                chunk.append(row)

                if i % rows_per_chunk == 0:
                    # Write CSV chunk
                    chunk_csv = chunks_dir_csv / f"chunk_{chunk_num}.csv"
                    with open(chunk_csv, "w", newline="", encoding="utf-8") as f:
                        writer = csv.writer(f)
                        writer.writerow(["Sender", "Date", "Message"])
                        writer.writerows(chunk)

                    # Write TXT chunk
                    chunk_txt = chunks_dir_txt / f"chunk_{chunk_num}.txt"
                    write_chunk_to_txt(chunk, chunk_txt)

                    chunk = []
                    chunk_num += 1

        # Write any remaining rows
        if chunk:
            chunk_csv = chunks_dir_csv / f"chunk_{chunk_num}.csv"
            with open(chunk_csv, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["Sender", "Date", "Message"])
                writer.writerows(chunk)

            chunk_txt = chunks_dir_txt / f"chunk_{chunk_num}.txt"
            write_chunk_to_txt(chunk, chunk_txt)

        # Clean up all messages file
        all_messages_csv.unlink()

        return output_dir

    except OSError as e:
        logger.error(f"Failed to chunk messages: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error while chunking messages: {e}")
        raise


def write_chunk_to_txt(messages: List[List[str]], txt_file: Path) -> None:
    """Write a chunk of messages to a TXT file.
    
    Args:
        messages: List of messages, each containing [sender, date, message]
        txt_file: Output TXT file path
    """
    try:
        with open(txt_file, "w", encoding="utf-8", newline="") as f:
            for sender, date, message in messages:
                f.write(f"{sender}, {date}, {message}\n\n")
    except Exception as e:
        logger.error(f"Failed to write chunk to TXT: {e}")
        raise


async def main() -> None:
    """Main function to process iMessage exports."""
    parser = argparse.ArgumentParser(
        description="Process iMessage export and format into CSV."
    )
    parser.add_argument(
        "-d",
        "--date",
        required=False,
        help="Start date for iMessage export YYYY-MM-DD.",
    )
    parser.add_argument(
        "-m", "--name", required=False, help="Name of the contact (default: Phil)."
    )
    parser.add_argument(
        "-s",
        "--size",
        type=float,
        default=None,
        required=False,
        help="Target size of chunks in MB.",
    )
    args = parser.parse_args()

    try:
        # Default name and phone number
        default_name = "Phil"
        default_phone_number = phone_number_map.get(default_name)
        phil_email = "apple@phil-g.com"  # Store Phil's email separately

        # For Phil, we'll use both phone and email as identifiers
        if default_name == "Phil":
            imessage_filter = f"{default_phone_number},{phil_email}"
        else:
            imessage_filter = default_phone_number

        logger.info(f"Using filter: {imessage_filter}")

        # Get the specified name or default to Phil
        name = args.name or default_name
        phone_number = phone_number_map.get(name) or default_phone_number

        if not phone_number:
            raise ValueError(
                f"Invalid name '{name}'. Must be one of {list(phone_number_map.keys())}."
            )

        # Create output directory if it doesn't exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {OUTPUT_DIR}")

        # Clear and recreate the export folder
        export_path = Path.home() / "imessage_export"
        logger.info(f"clear folder path: {export_path}")
        clear_folder(export_path)

        # Run the iMessage-exporter
        await run_imessage_exporter(name, args.date, phone_number, imessage_filter, export_path)

        # Get message files
        message_files = []
        
        # Get phone number file if it exists
        try:
            phone_file = detect_file(export_path, phone_number)
            if phone_file.exists():
                message_files.append(phone_file)
        except FileNotFoundError:
            logger.warning(f"No phone messages found for {name}")

        # For Phil, also get email file
        if name == "Phil":
            try:
                email_file = detect_file(export_path, phil_email)
                if email_file.exists():
                    message_files.append(email_file)
            except FileNotFoundError:
                logger.warning("No email messages found for Phil")

        if not message_files:
            raise RuntimeError(
                f"No message files found for {name}. This could mean either:\n"
                "1. There are no messages for this contact\n"
                "2. The identifiers (phone/email) are incorrect\n"
                "3. The messages are not in iMessage format"
            )

        # Parse messages
        parsed_messages = []
        for file in message_files:
            parsed_messages.append(parse_messages(file, name))

        # If we found multiple files, combine the parsed messages
        if len(parsed_messages) > 1:
            # Flatten the list of lists
            all_messages = []
            for messages in parsed_messages:
                all_messages.extend(messages)
            # Sort by date
            all_messages.sort(key=lambda x: datetime.strptime(x[1], "%b %d, %Y %I:%M:%S %p"))
        else:
            all_messages = parsed_messages[0]

        # Create chunks and write to both formats
        output_dir = chunk_messages(all_messages, OUTPUT_DIR, args.size or 5)
        logger.info(f"Processing completed. Chunks saved in: {output_dir}")

    except FileNotFoundError as e:
        logger.error("Failed to find exported message file")
        logger.error(str(e))
        raise RuntimeError(
            "No messages were found. This could mean either:\n"
            "1. There are no messages for this contact\n"
            "2. The identifiers (phone/email) are incorrect\n"
            "3. The messages are not in iMessage format"
        ) from e


if __name__ == "__main__":
    asyncio.run(main())
