import os
import re
import csv
import logging
import argparse
import subprocess
import asyncio
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Optional, Dict

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
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

# New output directory
OUTPUT_DIR = Path.home() / "PycharmProjects" / "format_text_history_full"

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
            logger.error(f"Failed to clear folder: {folder_path}")
            raise
    else:
        logger.info(f"Folder does not exist: {folder_path}")

def detect_file(folder_path: Path, phone_number: str, email: Optional[str] = None) -> Path:
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
        
    # List all files in the directory for debugging
    files = list(folder_path.glob("*.txt"))
    if files:
        logger.info(f"Found {len(files)} text files in export folder:")
        for file in files:
            logger.info(f"  - {file.name}")
    else:
        logger.warning("No .txt files found in export folder")

    # Initialize file paths
    phone_file = folder_path / f"{phone_number}.txt" if phone_number else None
    email_file = folder_path / f"{email}.txt" if email else None
    
    logger.info(f"Looking for phone file: {phone_file}")
    logger.info(f"Looking for email file: {email_file}")
    
    # Track which files exist
    phone_exists = phone_file.exists() if phone_file else False
    email_exists = email_file.exists() if email_file else False
    
    logger.info(f"Phone file exists: {phone_exists}")
    logger.info(f"Email file exists: {email_exists}")

    # If both exist, combine them
    if phone_exists and email_exists:
        logger.info("Both files exist - combining them")
        combined_file = folder_path / "combined.txt"
        
        with open(phone_file, 'r', encoding='utf-8') as pf, \
             open(email_file, 'r', encoding='utf-8') as ef, \
             open(combined_file, 'w', encoding='utf-8') as cf:
            
            # Read all messages from both files
            phone_messages = pf.readlines()
            email_messages = ef.readlines()
            
            # Combine and sort messages (they should start with dates)
            all_messages = phone_messages + email_messages
            all_messages.sort()
            
            # Write combined messages
            cf.writelines(all_messages)
        
        logger.info(f"Created combined message file: {combined_file}")
        return combined_file
    
    # Otherwise return whichever one exists
    if email_exists:
        logger.info("Using email file only")
        return email_file
    if phone_exists:
        logger.info("Using phone file only")
        return phone_file
    
    # No valid files found
    error_msg = (
        "No message files found for identifiers:\n"
        f"Phone: {phone_number}\n"
        + (f"Email: {email}\n" if email else "")
        + f"Directory: {folder_path}\n"
        + f"Available files: {[f.name for f in files]}"
    )
    logger.error(error_msg)
    raise FileNotFoundError(error_msg)

async def run_imessage_exporter(name: str, date: Optional[str], phone_number: str, imessage_filter: str) -> None:
    """Run the iMessage-exporter command asynchronously.
    
    Args:
        name: Contact name
        date: Optional start date for export
        phone_number: Phone number to export
        imessage_filter: Filter string for iMessage export
        
    Raises:
        subprocess.CalledProcessError: If the iMessage-exporter command fails
        FileNotFoundError: If the export produces no output
        RuntimeError: If the export folder is empty after successful command execution
    """
    export_path = Path.home() / "imessage_export"
    base_command = ["imessage-exporter", "-f", "txt", "-c", "disabled", "-m", "Jess"]
    
    if date:
        base_command.extend(["-s", date])
    
    if name == "Phil":
        base_command.extend(["-t", imessage_filter])
    else:
        base_command.extend(["-t", phone_number])

    logger.info(f"Running iMessage export for {name} (phone: {phone_number})")
    logger.info(f"Command: {' '.join(base_command)}")

    try:
        process = await asyncio.create_subprocess_exec(
            *base_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if stdout:
            logger.info(f"Command output: {stdout.decode().strip()}")
        if stderr:
            logger.warning(f"Command stderr: {stderr.decode().strip()}")

        if process.returncode != 0:
            error_msg = f"iMessage-exporter failed with return code {process.returncode}: {stderr.decode().strip()}"
            logger.error(error_msg)
            raise subprocess.CalledProcessError(process.returncode, base_command, stderr)

        # Wait a short time for file system operations to complete
        await asyncio.sleep(1)

        if not export_path.exists():
            error_msg = f"Export directory was not created at {export_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)
        
        if not any(export_path.iterdir()):
            error_msg = (
                f"No messages found for {name} (phone: {phone_number}). "
                f"This could mean either:\n"
                f"1. There are no messages in the specified date range\n"
                f"2. The phone number/email is incorrect\n"
                f"3. The messages are not in iMessage format"
            )
            logger.error(error_msg)
            raise RuntimeError(error_msg)

    except (subprocess.CalledProcessError, FileNotFoundError, RuntimeError) as e:
        logger.error(f"Export failed: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during export: {str(e)}")
        raise RuntimeError(f"Unexpected error during iMessage export: {str(e)}") from e

def parse_messages(input_file: Path, output_csv: Path) -> None:
    """Parse iMessage export text file into structured CSV format.
    
    Args:
        input_file: Path to the input file
        output_csv: Path to the output CSV file
    """
    parsed_messages = []
    date, sender, message = "", "", []
    phil_email = "apple@phil-g.com"  # Phil's email address

    with open(input_file, "r", encoding="utf-8") as infile:
        lines = infile.readlines()

    for line in lines:
        line = re.sub(read_receipt_pattern, "", line).strip()
        if date_pattern.match(line):
            if date and sender and message:
                parsed_messages.append([sender, date, " ".join(message)])
            date, sender, message = line, "", []
        elif not sender:
            # Check if line is a phone number
            if re.match(r"^\+?\d+$", line):  # Line contains only numbers and optional "+"
                normalized_line = normalize_phone_number(line)
                sender = next((name for name, number in phone_number_map.items() if number == normalized_line), line)
            else:
                # Check if it's Phil's email
                if line == phil_email:
                    sender = "Phil"
                else:
                    # Treat as a name if not a phone number or Phil's email
                    sender = line
        else:
            message.append(line)

    if date and sender and message:
        parsed_messages.append([sender, date, " ".join(message)])

    with open(output_csv, "w", newline="", encoding="utf-8") as outfile:
        writer = csv.writer(outfile)
        writer.writerow(["sender", "date", "message"])
        writer.writerows(parsed_messages)

def estimate_rows_per_chunk(input_csv_path: Path, max_file_size_mb: float = 5) -> int:
    """Estimate the maximum rows that can fit in a file given a size limit.
    
    Args:
        input_csv_path: Path to the input CSV file
        max_file_size_mb: Maximum file size in MB (default: 5)
    
    Returns:
        int: Estimated rows per chunk
    """
    max_file_size_bytes = max_file_size_mb * 1024 * 1024
    sample_rows = 100

    with open(input_csv_path, 'r', encoding='utf-8') as csv_file:
        csv_reader = csv.reader(csv_file)
        header = next(csv_reader)
        sample_data = [row for _, row in zip(range(sample_rows), csv_reader)]

    sample_file = "sample_size_test.csv"
    with open(sample_file, 'w', newline='', encoding='utf-8') as temp_file:
        csv_writer = csv.writer(temp_file)
        csv_writer.writerow(header)
        csv_writer.writerows(sample_data)

    sample_file_size = os.path.getsize(sample_file)
    avg_row_size = sample_file_size / (sample_rows + 1)
    os.remove(sample_file)

    return int(max_file_size_bytes / avg_row_size)

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

def chunk_csv(input_csv_path: Path, base_output_folder: Path, rows_per_chunk: int = 1000) -> Path:
    """Split a large CSV file into smaller chunks and save as both CSV and TXT.
    
    Args:
        input_csv_path: Path to the input CSV file
        base_output_folder: Base directory for output
        rows_per_chunk: Rows per chunk (default: 1000)
    
    Returns:
        Path: Path to the output directory
    """
    output_folder = generate_output_directory(base_output_folder)
    chunks_dir_csv = output_folder / "_chunks_csv"
    chunks_dir_txt = output_folder / "_chunks_txt"
    chunks_dir_csv.mkdir(parents=True, exist_ok=True)
    chunks_dir_txt.mkdir(parents=True, exist_ok=True)

    with open(input_csv_path, 'r', encoding='utf-8') as input_file:
        csv_reader = csv.reader(input_file)
        header = next(csv_reader)  # Read the header
        chunk_rows, chunk_index = [], 0

        for row in csv_reader:
            chunk_rows.append(row)
            if len(chunk_rows) >= rows_per_chunk:
                write_chunk(chunk_index, header, chunk_rows, chunks_dir_csv, chunks_dir_txt)
                chunk_rows, chunk_index = [], chunk_index + 1

        if chunk_rows:
            write_chunk(chunk_index, header, chunk_rows, chunks_dir_csv, chunks_dir_txt)

    return output_folder  # Return the output directory for reference

def write_chunk(chunk_index: int, header: List[str], chunk_rows: List[List[str]], chunks_dir_csv: Path, chunks_dir_txt: Path) -> None:
    """Write a chunk of rows to both CSV and TXT files.
    
    Args:
        chunk_index: Chunk index
        header: CSV header
        chunk_rows: Chunk rows
        chunks_dir_csv: Directory for CSV chunks
        chunks_dir_txt: Directory for TXT chunks
    """
    chunk_filename_csv = chunks_dir_csv / f"chunk_{chunk_index+1}.csv"
    with open(chunk_filename_csv, 'w', newline='', encoding='utf-8') as chunk_file_csv:
        csv_writer = csv.writer(chunk_file_csv)
        csv_writer.writerow(header)  # Write the header
        csv_writer.writerows(chunk_rows)  # Write the rows
    logger.info(f"Chunk {chunk_index+1} written to {chunk_filename_csv}")

    chunk_filename_txt = chunks_dir_txt / f"chunk_{chunk_index+1}.txt"
    with open(chunk_filename_txt, 'w', encoding='utf-8') as chunk_file_txt:
        for row in chunk_rows:
            chunk_file_txt.write(", ".join(row) + "\n\n")  # comma-separated for readability
    logger.info(f"Chunk {chunk_index+1} written to {chunk_filename_txt}")

async def main() -> None:
    parser = argparse.ArgumentParser(description="Process iMessage export and format into CSV.")
    parser.add_argument(
        "-d", "--date", required=False, help="Start date for iMessage export YYYY-MM-DD."
    )
    parser.add_argument(
        "-m", "--name", required=False, help="Name of the contact (default: Phil)."
    )
    parser.add_argument(
        "-s", "--size", type=float, default=None, required=False, help="Target size of chunks in MB."
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
            raise ValueError(f"Invalid name '{name}'. Must be one of {list(phone_number_map.keys())}.")

        # Create output directory if it doesn't exist
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        logger.info(f"Created output directory: {OUTPUT_DIR}")

        # Clear and recreate the export folder
        export_path = Path.home() / "imessage_export"
        clear_folder(export_path)

        # Run the iMessage-exporter
        await run_imessage_exporter(name, args.date, phone_number, imessage_filter)

        try:
            # For Phil, try both phone and email
            email_to_try = phil_email if name == "Phil" else None
            input_file = detect_file(export_path, phone_number, email_to_try)

            # Create output CSV file
            output_csv = OUTPUT_DIR / f"{name}_formatted.csv"
            logger.info(f"Processing messages to: {output_csv}")
            parse_messages(input_file, output_csv)

            # Estimate rows per chunk
            max_rows = estimate_rows_per_chunk(output_csv, args.size or 5)
            logger.info(f"Estimated {max_rows} rows per chunk")

            # Chunk the CSV and get the output directory
            chunk_output_dir = chunk_csv(output_csv, OUTPUT_DIR, rows_per_chunk=max_rows)
            logger.info(f"Processing completed. Chunks saved in: {chunk_output_dir}")

        except FileNotFoundError as e:
            logger.error("Failed to find exported message file")
            logger.error(str(e))
            raise RuntimeError(
                "No messages were found. This could mean either:\n"
                "1. There are no messages for this contact\n"
                "2. The identifiers (phone/email) are incorrect\n"
                "3. The messages are not in iMessage format"
            ) from e

    except Exception as e:
        logger.error(f"Error processing messages: {str(e)}")
        raise SystemExit(1)

if __name__ == "__main__":
    asyncio.run(main())