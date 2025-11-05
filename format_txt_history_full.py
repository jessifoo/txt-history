"""Utilities for exporting and formatting iMessage history into chunked files."""

from __future__ import annotations

import argparse
import asyncio
import csv
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

MessageRow = List[str]

DATE_PATTERN = re.compile(r"^(\w{3} \d{2}, \d{4}\s*\d{1,2}:\d{2}:\d{2} \w{2})")
READ_RECEIPT_PATTERN = re.compile(r"\(Read by.*$")

PHIL_EMAIL = "apple@phil-g.com"
DEFAULT_CHUNK_SIZE_MB = 5.0
DEFAULT_EXPORT_SUBDIR = "imessage_export"
DEFAULT_IMESSAGE_EXPORTER_PATH = "/opt/homebrew/bin/imessage-exporter"


def normalize_phone_number(phone_number: str) -> str:
    """Normalize a phone number to a predictable E.164-like format."""

    if not phone_number:
        raise ValueError("Phone number cannot be empty.")

    if not re.search(r"\d", phone_number):
        return phone_number.strip()

    digits = re.sub(r"\D", "", phone_number)
    if not digits:
        raise ValueError(f"Invalid phone number: {phone_number}")

    if phone_number.strip().startswith("+"):
        return f"+{digits}"

    if len(digits) == 11 and digits.startswith("1"):
        return f"+{digits}"

    if len(digits) == 10:
        return f"+1{digits}"

    return f"+{digits}"


PHONE_NUMBER_MAP: Dict[str, str] = {
    "Phil": normalize_phone_number("+18673335566"),
    "Robert": normalize_phone_number("+17806793467"),
    "Rhonda": normalize_phone_number("+17803944504"),
    "Sherry": normalize_phone_number("+17807223445"),
    "Jess": "Jess",
}

OUTPUT_DIR = Path(__file__).parent / "output"


def _message_date_key(date_text: str) -> datetime:
    """Convert a message date string into a comparable ``datetime`` object."""

    normalized = re.sub(r"\s+", " ", date_text.strip())
    for fmt in ("%b %d, %Y %I:%M:%S %p", "%b %d, %Y %H:%M:%S %p"):
        try:
            return datetime.strptime(normalized, fmt)
        except ValueError:
            continue
    logger.debug("Falling back to epoch for unsupported date format: %s", date_text)
    return datetime.fromtimestamp(0)


def sort_messages_by_date(messages: Sequence[MessageRow]) -> List[MessageRow]:
    """Return messages sorted chronologically by their date field."""

    return sorted(messages, key=lambda row: _message_date_key(row[1]))


async def run_imessage_exporter(
    *,
    name: str,
    phone_number: str,
    imessage_filter: str,
    date: Optional[str] = None,
    end_date: Optional[str] = None,
    export_path: Optional[Path] = None,
) -> None:
    """Execute the iMessage exporter CLI with the provided filters."""

    export_dir = export_path or (Path.home() / DEFAULT_EXPORT_SUBDIR)
    export_dir.mkdir(parents=True, exist_ok=True)

    exporter_path = os.environ.get("IMESSAGE_EXPORTER_PATH", DEFAULT_IMESSAGE_EXPORTER_PATH)
    command: List[str] = [exporter_path, "-f", "txt", "-c", "disabled", "-m", "Jess"]

    if date:
        command.extend(["-s", date])
    if end_date:
        command.extend(["-e", end_date])

    command.extend(["-t", imessage_filter if name == "Phil" else phone_number])

    if export_path:
        command.extend(["-o", str(export_path)])

    logger.info("Running iMessage export for %s", name)
    logger.debug("Command: %s", " ".join(command))

    process = await asyncio.create_subprocess_exec(
        *command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()

    if stdout:
        logger.info(stdout.decode().strip())
    if stderr:
        logger.warning(stderr.decode().strip())

    if process.returncode:
        msg = f"iMessage-exporter failed with code {process.returncode}"
        raise subprocess.CalledProcessError(process.returncode, command, stderr)

    if not export_dir.exists() or not any(export_dir.iterdir()):
        raise RuntimeError(f"Export folder is empty: {export_dir}")


def clear_folder(folder_path: Path) -> None:
    """Remove all contents inside ``folder_path`` and recreate it."""

    if folder_path.exists():
        shutil.rmtree(folder_path)
    folder_path.mkdir(parents=True, exist_ok=True)


def _matching_files(folder_path: Path, identifier: str) -> List[Path]:
    """Return any text exports whose stem contains the given identifier."""

    if not identifier:
        return []
    normalized = normalize_phone_number(identifier) if re.search(r"\d", identifier) else identifier
    candidates = {identifier.strip(), normalized}
    if normalized.startswith("+1"):
        candidates.add(normalized[1:])
    return [path for path in folder_path.glob("*.txt") if any(candidate in path.stem for candidate in candidates)]


def _safe_identifier(identifier: str) -> str:
    """Return a sanitized name suitable for filenames."""

    return re.sub(r"[^A-Za-z0-9+]+", "_", identifier).strip("_") or "messages"


def detect_file(folder_path: Path, phone_number: str, email: Optional[str] = None) -> Path:
    """Return the best matching export file, combining phone and email when needed."""

    if not folder_path.exists():
        raise FileNotFoundError(f"Export folder does not exist: {folder_path}")

    phone_files = _matching_files(folder_path, phone_number)
    email_files: List[Path] = []
    if email:
        email_files = _matching_files(folder_path, email)

    if phone_files and email_files:
        safe_name = _safe_identifier(phone_number or email or "combined")
        combined_path = folder_path / f"combined_{safe_name}.txt"
        combined_contents = []
        for file_path in phone_files + email_files:
            text = file_path.read_text(encoding="utf-8").rstrip()
            if text:
                combined_contents.append(text)
        combined_text = "\n\n".join(combined_contents)
        if combined_text:
            combined_text += "\n\n"
        combined_path.write_text(combined_text, encoding="utf-8")
        return combined_path

    if phone_files:
        return phone_files[0]
    if email_files:
        return email_files[0]

    raise FileNotFoundError("No matching message files found")


def parse_messages(input_file: Path, name: str = "Phil") -> List[MessageRow]:
    if not input_file.exists():
        raise FileNotFoundError(f"Input file does not exist: {input_file}")
    if not input_file.is_file():
        raise ValueError(f"Input path is not a file: {input_file}")

    lines = input_file.read_text(encoding="utf-8").splitlines()
    if not lines:
        raise RuntimeError(f"Input file is empty: {input_file}")

    messages: List[MessageRow] = []
    current_date: Optional[str] = None
    current_sender: Optional[str] = None
    buffer: List[str] = []

    for raw_line in lines:
        line = READ_RECEIPT_PATTERN.sub("", raw_line).strip()
        if not line:
            continue

        if DATE_PATTERN.match(line):
            if current_date and current_sender and buffer:
                messages.append([current_sender, current_date, " ".join(buffer)])
            current_date = line
            current_sender = None
            buffer = []
            continue

        if current_date and current_sender is None:
            if re.match(r"^\+?\d+$", line):
                normalized = normalize_phone_number(line)
                if normalized == PHONE_NUMBER_MAP.get(name):
                    current_sender = name
                else:
                    current_sender = next(
                        (label for label, number in PHONE_NUMBER_MAP.items() if number == normalized),
                        line,
                    )
            elif line == PHIL_EMAIL and name == "Phil":
                current_sender = "Phil"
            elif line == "Jess":
                current_sender = "Jess"
            else:
                current_sender = line
            continue

        if current_date and current_sender:
            buffer.append(line)

    if current_date and current_sender and buffer:
        messages.append([current_sender, current_date, " ".join(buffer)])

    return messages


def combine_message_files(files: Iterable[Path], name: str) -> List[MessageRow]:
    all_messages: List[MessageRow] = []
    for file_path in files:
        all_messages.extend(parse_messages(file_path, name))
    return sort_messages_by_date(all_messages)


def estimate_rows_per_chunk(input_csv_path: Path, max_file_size_mb: float = DEFAULT_CHUNK_SIZE_MB) -> int:
    if max_file_size_mb <= 0:
        raise ValueError("max_file_size_mb must be positive")

    with open(input_csv_path, "r", encoding="utf-8") as handle:
        rows = max(sum(1 for _ in handle) - 1, 1)

    file_size = max(input_csv_path.stat().st_size, 1)
    bytes_per_row = file_size / rows
    target_bytes = max_file_size_mb * 1024 * 1024
    return max(1, int(target_bytes / max(bytes_per_row, 1)))


def generate_output_directory(base_dir: Path) -> Path:
    """Create and return a timestamped output directory under ``base_dir``."""

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    output_dir = base_dir / f"chunks_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def chunk_messages(messages: Sequence[MessageRow], base_output_folder: Path, size_mb: float) -> Path:
    """Write messages into CSV/TXT chunk pairs bounded by ``size_mb`` megabytes."""

    if not messages:
        raise ValueError("No messages to chunk")
    if size_mb <= 0:
        raise ValueError("size_mb must be positive")

    output_dir = generate_output_directory(base_output_folder)
    csv_dir = output_dir / "_chunks_csv"
    txt_dir = output_dir / "_chunks_txt"
    csv_dir.mkdir(parents=True, exist_ok=True)
    txt_dir.mkdir(parents=True, exist_ok=True)

    all_messages_csv = csv_dir / "all_messages.csv"
    with open(all_messages_csv, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Sender", "Date", "Message"])
        writer.writerows(messages)

    rows_per_chunk = estimate_rows_per_chunk(all_messages_csv, size_mb)
    logger.info("Using %s rows per chunk", rows_per_chunk)

    chunk: List[MessageRow] = []
    chunk_index = 1

    with open(all_messages_csv, "r", newline="", encoding="utf-8") as file:
        reader = csv.reader(file)
        next(reader, None)
        for current_index, row in enumerate(reader, start=1):
            chunk.append(row)
            if current_index % rows_per_chunk == 0:
                _flush_chunk(chunk, chunk_index, csv_dir, txt_dir)
                chunk_index += 1
                chunk = []

    if chunk:
        _flush_chunk(chunk, chunk_index, csv_dir, txt_dir)

    all_messages_csv.unlink(missing_ok=True)
    return output_dir


def _flush_chunk(chunk: List[MessageRow], chunk_index: int, csv_dir: Path, txt_dir: Path) -> None:
    """Persist a single chunk to disk in both CSV and TXT formats."""

    csv_path = csv_dir / f"chunk_{chunk_index}.csv"
    with open(csv_path, "w", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["Sender", "Date", "Message"])
        writer.writerows(chunk)

    txt_path = txt_dir / f"chunk_{chunk_index}.txt"
    write_chunk_to_txt(chunk, txt_path)


def write_chunk_to_txt(messages: Sequence[MessageRow], txt_file: Path) -> None:
    """Write ``messages`` to ``txt_file`` separated by blank lines."""

    with open(txt_file, "w", encoding="utf-8", newline="") as handle:
        for sender, date, message in messages:
            handle.write(f"{sender}, {date}, {message}\n\n")


def build_argument_parser() -> argparse.ArgumentParser:
    """Construct and return the CLI argument parser for the script."""

    parser = argparse.ArgumentParser(description="Process iMessage export and format into chunked CSV/TXT outputs.")
    parser.add_argument("-d", "--date", help="Start date for export (YYYY-MM-DD)")
    parser.add_argument("-e", "--end-date", help="End date for export (YYYY-MM-DD)")
    parser.add_argument("-m", "--name", help="Contact name (default: Phil)")
    parser.add_argument("-s", "--size", type=float, help="Chunk size in MB (default: 5)")
    parser.add_argument("-r", "--rows", type=int, help="Limit output to the most recent N messages")
    return parser


async def main() -> None:
    """Command-line entry point for exporting, parsing, and chunking iMessages."""

    parser = build_argument_parser()
    args = parser.parse_args()

    name = args.name or "Phil"
    phone_number = PHONE_NUMBER_MAP.get(name)
    if not phone_number:
        raise ValueError(f"Invalid name '{name}'. Choose from {sorted(PHONE_NUMBER_MAP)}")

    if args.rows is not None and args.rows <= 0:
        raise ValueError("--rows must be a positive integer")
    if args.size is not None and args.size <= 0:
        raise ValueError("--size must be positive")

    filter_parts = [phone_number]
    if name == "Phil":
        filter_parts.append(PHIL_EMAIL)
    imessage_filter = ",".join(filter_parts)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    export_dir = Path.home() / DEFAULT_EXPORT_SUBDIR
    if export_dir.exists():
        clear_folder(export_dir)
    else:
        export_dir.mkdir(parents=True, exist_ok=True)
    await run_imessage_exporter(
        name=name,
        phone_number=phone_number,
        imessage_filter=imessage_filter,
        date=args.date,
        end_date=args.end_date,
        export_path=export_dir,
    )

    message_file = detect_file(export_dir, phone_number, PHIL_EMAIL if name == "Phil" else None)
    messages = parse_messages(message_file, name)
    sorted_messages = sort_messages_by_date(messages)

    if args.rows:
        sorted_messages = sorted_messages[-args.rows :]

    size_mb = args.size or DEFAULT_CHUNK_SIZE_MB
    output_dir = chunk_messages(sorted_messages, OUTPUT_DIR, size_mb)
    logger.info("Processing completed. Chunks saved in: %s", output_dir)


if __name__ == "__main__":
    asyncio.run(main())
