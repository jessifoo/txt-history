#!/usr/bin/env python3
"""
New implementation of the iMessage formatting tool with cleaner architecture.
Features:
- Database-backed persistent storage
- Incremental processing (no file recreation)
- Configurable chunking strategies
- Better separation of concerns
"""

import argparse
import asyncio
import logging
import re
import sqlite3
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

import aiofiles
import pandas as pd

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import existing utilities
try:
    from .constants import DEFAULT_TIMEZONE, OUTPUT_DIR, TMP_PATH
    from .utils import clean_message_content, is_date_in_future, parse_date_string
except ImportError:
    try:
        from constants import DEFAULT_TIMEZONE, OUTPUT_DIR, TMP_PATH
        from utils import clean_message_content, is_date_in_future, parse_date_string
    except ImportError:
        # Fallback defaults if modules aren't found
        from pathlib import Path
        OUTPUT_DIR = Path.home() / "txt_history_output"
        TMP_PATH = Path.home() / "imessage-export"
        DEFAULT_TIMEZONE = "America/Denver"

        # Simple fallback implementations
        def clean_message_content(message: str) -> str:
            return "".join(char for char in message if char.isascii() and char.isprintable())

        def is_date_in_future(date_str: str) -> bool:
            from datetime import datetime
            try:
                date_obj = datetime.strptime(date_str, "%Y-%m-%d")
                return date_obj > datetime.now()
            except ValueError:
                return False

        def parse_date_string(date_str: str) -> datetime:
            from datetime import datetime
            import pytz
            normalized = " ".join(date_str.split())
            dt = datetime.strptime(normalized, "%b %d, %Y %I:%M:%S %p")
            mountain_tz = pytz.timezone("America/Denver")
            return mountain_tz.localize(dt)


class ChunkStrategy(Enum):
    """Different strategies for chunking messages."""

    SIZE_MB = "size_mb"
    LINES = "lines"
    COUNT = "count"
    DATE_RANGE = "date_range"


@dataclass
class ChunkConfig:
    """Configuration for message chunking."""

    strategy: ChunkStrategy
    value: float  # Size in MB, line count, or message count
    date_range_days: int | None = None  # For date-based chunking


@dataclass
class ExportConfig:
    """Configuration for message export."""

    contact_names: list[str]
    start_date: str | None = None
    end_date: str | None = None
    chunk_config: ChunkConfig | None = None
    only_contact_messages: bool = False
    output_format: str = "both"  # "csv", "txt", or "both"


@dataclass
class Message:
    """Represents a single message."""

    id: int | None = None
    sender: str = ""
    timestamp: pd.Timestamp = field(default_factory=lambda: pd.Timestamp.now())
    content: str = ""
    contact_name: str = ""
    source_file: str = ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for storage."""
        return {
            "sender": self.sender,
            "timestamp": self.timestamp.isoformat(),
            "content": self.content,
            "contact_name": self.contact_name,
            "source_file": self.source_file,
        }


class DatabaseManager:
    """Manages the SQLite database for persistent storage."""

    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            # Use a persistent location in the project directory
            project_root = Path(__file__).parent.parent
            db_path = project_root / "data" / "messages.db"
            # Ensure the data directory exists
            db_path.parent.mkdir(exist_ok=True)

        self.db_path = db_path
        logger.info(f"Using database: {self.db_path}")
        self._init_database()

    def _init_database(self):
        """Initialize database tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS messages (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        sender TEXT NOT NULL,
                        timestamp TEXT NOT NULL,
                        content TEXT NOT NULL,
                        contact_name TEXT NOT NULL,
                        source_file TEXT NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        phone TEXT,
                        email TEXT,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS export_sessions (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contact_names TEXT NOT NULL,
                        start_date TEXT,
                        end_date TEXT,
                        chunk_strategy TEXT,
                        chunk_value REAL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """)

                conn.execute("""
                    CREATE TABLE IF NOT EXISTS chunks (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        session_id INTEGER,
                        chunk_number INTEGER,
                        start_date TEXT,
                        end_date TEXT,
                        message_count INTEGER,
                        file_path TEXT,
                        FOREIGN KEY (session_id) REFERENCES export_sessions (id)
                    )
                """)

                # Create indexes for better performance
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_timestamp ON messages (timestamp)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_contact ON messages (contact_name)"
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages (sender)"
                )
                logger.info(f"Database initialized successfully at {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

    def store_messages(self, messages: list[Message]) -> None:
        """Store messages in the database, avoiding duplicates."""
        if not messages:
            logger.warning("No messages to store")
            return

        try:
            with sqlite3.connect(self.db_path) as conn:
                for message in messages:
                    try:
                        # Validate message data
                        if not message.sender or not message.content:
                            logger.warning(f"Skipping invalid message: missing sender or content")
                            continue

                        # Check if message already exists (same timestamp, sender, content, contact)
                        cursor = conn.execute(
                            """
                            SELECT COUNT(*) FROM messages
                            WHERE timestamp = ? AND sender = ? AND content = ? AND contact_name = ?
                            """,
                            (
                                message.timestamp.isoformat(),
                                message.sender,
                                message.content,
                                message.contact_name,
                            ),
                        )
                        if cursor.fetchone()[0] == 0:
                            # Only insert if it doesn't exist
                            conn.execute(
                                """
                                INSERT INTO messages (sender, timestamp, content, contact_name, source_file)
                                VALUES (?, ?, ?, ?, ?)
                            """,
                                (
                                    message.sender,
                                    message.timestamp.isoformat(),
                                    message.content,
                                    message.contact_name,
                                    message.source_file,
                                ),
                            )
                    except sqlite3.Error as e:
                        logger.error(f"Failed to store message: {e}")
                        continue

                logger.info(f"Successfully stored {len(messages)} messages in database")
        except sqlite3.Error as e:
            logger.error(f"Database error while storing messages: {e}")
            raise

    def get_messages(
        self,
        contact_names: list[str],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Message]:
        """Retrieve messages from database."""
        if not contact_names:
            logger.warning("No contact names provided")
            return []

        try:
            query = "SELECT * FROM messages WHERE contact_name IN ({})".format(
                ",".join(["?" for _ in contact_names])
            )
            params = contact_names

            if start_date:
                query += " AND timestamp >= ?"
                params.append(start_date)

            if end_date:
                query += " AND timestamp <= ?"
                params.append(end_date)

            query += " ORDER BY timestamp"

            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute(query, params)
                messages = []
                for row in cursor.fetchall():
                    try:
                        messages.append(
                            Message(
                                id=row[0],
                                sender=row[1],
                                timestamp=pd.Timestamp(row[2]),
                                content=row[3],
                                contact_name=row[4],
                                source_file=row[5],
                            )
                        )
                    except Exception as e:
                        logger.warning(f"Failed to parse message row {row}: {e}")
                        continue

                logger.info(f"Retrieved {len(messages)} messages from database")
                return messages
        except sqlite3.Error as e:
            logger.error(f"Database error while retrieving messages: {e}")
            raise


class ContactManager:
    """Manages contact information."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def get_contact(self, name: str) -> dict[str, Any] | None:
        """Get contact by name."""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            cursor = conn.execute("SELECT * FROM contacts WHERE name = ?", (name,))
            row = cursor.fetchone()
            if row:
                return {"id": row[0], "name": row[1], "phone": row[2], "email": row[3]}
            return None

    def save_contact(
        self, name: str, phone: str | None = None, email: str | None = None
    ) -> None:
        """Save contact information."""
        with sqlite3.connect(self.db_manager.db_path) as conn:
            conn.execute(
                """
                INSERT OR REPLACE INTO contacts (name, phone, email)
                VALUES (?, ?, ?)
            """,
                (name, phone, email),
            )


class MessageProcessor:
    """Handles message processing and chunking."""

    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def chunk_messages(
        self, messages: list[Message], config: ChunkConfig
    ) -> list[list[Message]]:
        """Split messages into chunks based on configuration."""
        if not messages:
            return []

        if config.strategy == ChunkStrategy.COUNT:
            return self._chunk_by_count(messages, int(config.value))
        elif config.strategy == ChunkStrategy.SIZE_MB:
            return self._chunk_by_size(messages, config.value)
        elif config.strategy == ChunkStrategy.LINES:
            return self._chunk_by_lines(messages, int(config.value))
        elif config.strategy == ChunkStrategy.DATE_RANGE:
            return self._chunk_by_date_range(messages, config.date_range_days or 7)

        return [messages]

    def _chunk_by_count(
        self, messages: list[Message], count: int
    ) -> list[list[Message]]:
        """Chunk by message count."""
        return [messages[i : i + count] for i in range(0, len(messages), count)]

    def _chunk_by_size(
        self, messages: list[Message], size_mb: float
    ) -> list[list[Message]]:
        """Chunk by approximate size in MB."""
        chunks = []
        current_chunk = []
        current_size = 0
        size_bytes = size_mb * 1024 * 1024

        for message in messages:
            message_size = len(message.content.encode("utf-8"))
            if current_size + message_size > size_bytes and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_size = 0
            current_chunk.append(message)
            current_size += message_size

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _chunk_by_lines(
        self, messages: list[Message], lines: int
    ) -> list[list[Message]]:
        """Chunk by line count."""
        chunks = []
        current_chunk = []
        current_lines = 0

        for message in messages:
            message_lines = message.content.count("\n") + 1
            if current_lines + message_lines > lines and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_lines = 0
            current_chunk.append(message)
            current_lines += message_lines

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def _chunk_by_date_range(
        self, messages: list[Message], days: int
    ) -> list[list[Message]]:
        """Chunk by date ranges."""
        if not messages:
            return []

        chunks = []
        current_chunk = []
        current_start = messages[0].timestamp

        for message in messages:
            days_diff = (message.timestamp - current_start).days
            if days_diff >= days and current_chunk:
                chunks.append(current_chunk)
                current_chunk = []
                current_start = message.timestamp
            current_chunk.append(message)

        if current_chunk:
            chunks.append(current_chunk)

        return chunks


class ExportManager:
    """Manages the export process and file generation."""

    def __init__(self, db_manager: DatabaseManager, processor: MessageProcessor):
        self.db_manager = db_manager
        self.processor = processor

    async def export_messages(self, config: ExportConfig) -> bool:
        """Export messages based on configuration."""
        # Always fetch from iMessage export to get latest messages
        logger.info("Fetching messages from iMessage export")
        messages = await self._fetch_messages(config)

        # Store in database (duplicates are automatically prevented)
        if messages:
            logger.info(f"Storing {len(messages)} messages in database")
            self.db_manager.store_messages(messages)

        # Get complete message history from database for the requested date range
        logger.info("Retrieving complete message history from database")
        messages = self.db_manager.get_messages(
            config.contact_names, config.start_date, config.end_date
        )

        if not messages:
            logger.warning("No messages found for the specified criteria")
            return False

        # Filter messages if needed
        if config.only_contact_messages:
            messages = [m for m in messages if m.sender in config.contact_names]

        # Chunk messages if configuration provided
        if config.chunk_config:
            chunks = self.processor.chunk_messages(messages, config.chunk_config)
        else:
            chunks = [messages]

        # Generate output files
        await self._generate_output_files(chunks, config)

        return True

    async def _fetch_messages(self, config: ExportConfig) -> list[Message]:
        """Fetch messages from iMessage export."""
        # Get contact information from database
        contacts = []
        with sqlite3.connect(self.db_manager.db_path) as conn:
            for name in config.contact_names:
                cursor = conn.execute(
                    "SELECT name, phone, email FROM contacts WHERE name = ?", (name,)
                )
                row = cursor.fetchone()
                if row:
                    contacts.append({"name": row[0], "phone": row[1], "email": row[2]})
                else:
                    logger.warning(f"Contact {name} not found in database")

        if not contacts:
            logger.error("No valid contacts found for export")
            return []

        # Run iMessage export
        messages = await self._run_imessage_export(
            contacts, config.start_date, config.end_date
        )
        return messages

    async def _run_imessage_export(
        self,
        contacts: list[dict],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Message]:
        """Run iMessage export and parse results using direct database access."""
        try:
            # Try direct database access first
            from .imessage_db_reader import IMessageDBReader, find_imessage_database

            db_path = find_imessage_database()
            if db_path:
                logger.info("Using direct iMessage database access")
                return self._fetch_from_database(contacts, start_date, end_date)
            else:
                logger.warning("iMessage database not found, falling back to imessage-exporter")
                return await self._run_imessage_exporter_fallback(contacts, start_date, end_date)

        except ImportError:
            logger.warning("Direct database reader not available, using imessage-exporter")
            return await self._run_imessage_exporter_fallback(contacts, start_date, end_date)
        except Exception as e:
            logger.error(f"Direct database access failed: {e}, falling back to imessage-exporter")
            return await self._run_imessage_exporter_fallback(contacts, start_date, end_date)

    def _fetch_from_database(
        self,
        contacts: list[dict],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Message]:
        """Fetch messages directly from iMessage database."""
        try:
            from .imessage_db_reader import IMessageDBReader

            db_reader = IMessageDBReader()
            all_messages = []

            for contact in contacts:
                logger.info(f"Fetching messages for {contact['name']} from database")
                db_messages = db_reader.get_messages_for_contact(
                    contact, start_date, end_date
                )

                # Convert to Message objects
                for msg in db_messages:
                    message = Message(
                        sender=msg["sender"],
                        timestamp=msg["timestamp"],
                        content=msg["content"],
                        contact_name=msg["contact_name"],
                        source_file=msg["source_file"]
                    )
                    all_messages.append(message)

            logger.info(f"Fetched {len(all_messages)} messages from database")
            return all_messages

        except Exception as e:
            logger.error(f"Database fetch failed: {e}")
            raise

    async def _run_imessage_exporter_fallback(
        self,
        contacts: list[dict],
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> list[Message]:
        """Fallback to imessage-exporter if direct database access fails."""
        logger.info("Using imessage-exporter as fallback")

        # Clean up old export files for these contacts to force a fresh export
        self._cleanup_old_export_files()

        # Build command
        base_command = [
            "/opt/homebrew/bin/imessage-exporter",
            "-f",
            "txt",
            "-c",
            "disabled",
            "-m",
            "Jess",
        ]

        if start_date:
            base_command.extend(["-s", start_date])
        if end_date:
            base_command.extend(["-e", end_date])

        # Combine identifiers from all contacts
        combined_identifiers = self._get_combined_identifiers(contacts)
        base_command.extend(["-t", combined_identifiers])
        base_command.extend(["-o", str(TMP_PATH)])

        # Logging
        contact_names = [contact["name"] for contact in contacts]
        logger.info(f"Running iMessage export for contacts: {', '.join(contact_names)}")
        logger.info(f"Combined identifiers: {combined_identifiers}")

        try:
            process = await asyncio.create_subprocess_exec(
                *base_command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await process.communicate()

            if process.returncode:
                error_msg = f"iMessage-exporter failed: {stderr.decode().strip()}"
                logger.error(error_msg)
                raise RuntimeError(error_msg)

            # Find and parse message files
            message_files = self._find_message_files(TMP_PATH, contacts)
            all_messages = []

            for file_path in message_files:
                messages = self._parse_message_file(file_path, contacts)
                all_messages.extend(messages)

            # Sort by timestamp
            all_messages.sort(key=lambda m: m.timestamp)
            logger.info(
                f"Fetched {len(all_messages)} messages from {len(message_files)} files"
            )

            return all_messages

        except Exception:
            logger.exception("iMessage export failed")
            raise

    def _get_combined_identifiers(self, contacts: list[dict]) -> str:
        """Get combined identifiers from multiple contacts."""
        all_identifiers = []

        for contact in contacts:
            identifiers = []
            if contact.get("phone"):
                identifiers.append(self._normalize_phone_number(contact["phone"]))
            if contact.get("email"):
                identifiers.append(contact["email"])

            if identifiers:
                all_identifiers.extend(identifiers)
            else:
                logger.warning(f"Contact {contact['name']} has no phone or email")

        if not all_identifiers:
            raise ValueError("No valid identifiers found for any contacts")

        return ",".join(all_identifiers)

    def _normalize_phone_number(self, phone: str) -> str:
        """Normalize a phone number to E.164 format."""
        digits = re.sub(r"\D", "", phone)

        if phone == "Jess":
            return phone

        if len(digits) == 10:
            return f"+1{digits}"
        if (len(digits) >= 11 and digits.startswith("1")) or len(digits) >= 11:
            return f"+{digits}"

        raise ValueError(f"Invalid phone number format: {phone}")

    def _cleanup_old_export_files(self) -> None:
        """Delete and recreate the export directory to ensure a clean slate."""
        import shutil

        logger.info(f"Clearing temporary export directory: {TMP_PATH}")
        if TMP_PATH.exists():
            try:
                shutil.rmtree(TMP_PATH)
                logger.info("Cleared temporary directory.")
            except OSError as e:
                logger.error(f"Error removing directory {TMP_PATH}: {e}")
                raise

    def _find_message_files(
        self, export_path: Path, contacts: list[dict]
    ) -> list[Path]:
        """Find message files for the given contacts."""
        found_files = []

        for contact in contacts:
            if contact.get("phone"):
                phone_pattern = (
                    f"*{self._normalize_phone_number(contact['phone'])}*.txt"
                )
                phone_files = list(export_path.glob(phone_pattern))
                found_files.extend(phone_files)

            if contact.get("email"):
                email_pattern = f"*{contact['email']}*.txt"
                email_files = list(export_path.glob(email_pattern))
                found_files.extend(email_files)

        if not found_files:
            raise FileNotFoundError("No message files found for contacts")

        return found_files

    def _parse_message_file(
        self, file_path: Path, contacts: list[dict]
    ) -> list[Message]:
        """Parse a message file and return Message objects."""
        if not file_path.exists():
            logger.error(f"Message file not found: {file_path}")
            return []

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logger.error(f"Failed to read message file {file_path}: {e}")
            return []

        messages = []
        date: pd.Timestamp | None = None
        sender: str = ""
        message_lines: list[str] = []
        prev_line_empty: bool = True

        # Regular expressions for parsing
        date_pattern = re.compile(r"^(\w{3} \d{2}, \d{4}\s*\d{1,2}:\d{2}:\d{2} \w{2})")
        read_receipt_pattern = re.compile(r"\(Read by.*$")

        lines = content.splitlines()
        for line_num, line_content in enumerate(lines, 1):
            line = line_content.strip()

            if not line:
                prev_line_empty = True
                continue

            try:
                if prev_line_empty and (date_match := date_pattern.match(line)):
                    # Save previous message if exists
                    if date and sender and message_lines:
                        try:
                            messages.append(
                                Message(
                                    sender=sender,
                                    timestamp=date,
                                    content=" ".join(message_lines).strip(),
                                    contact_name=sender,
                                    source_file=str(file_path),
                                )
                            )
                        except Exception as e:
                            logger.warning(f"Failed to create message object: {e}")

                    # Parse new date
                    raw_date = read_receipt_pattern.sub("", date_match.group(1)).strip()
                    try:
                        dt_obj = parse_date_string(raw_date)
                        date = pd.Timestamp(dt_obj).tz_convert("America/Edmonton")
                    except Exception as e:
                        logger.warning(f"Failed to parse date on line {line_num}: {raw_date}, error: {e}")
                        date = None
                        sender = ""
                        message_lines = []
                        continue

                    sender = ""
                    message_lines = []

                elif date and not sender:
                    # Parse sender
                    sender = self._parse_sender_line(line, contacts, line_num)

                elif date and sender:
                    message_lines.append(clean_message_content(line))

                prev_line_empty = not line

            except Exception as e:
                logger.warning(f"Error processing line {line_num} in {file_path}: {e}")
                continue

        # Save final message
        if date and sender and message_lines:
            try:
                messages.append(
                    Message(
                        sender=sender,
                        timestamp=date,
                        content=" ".join(message_lines).strip(),
                        contact_name=sender,
                        source_file=str(file_path),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to create final message object: {e}")

        logger.info(f"Parsed {len(messages)} messages from {file_path}")
        return messages

    def _parse_sender_line(self, line: str, contacts: list[dict], line_num: int) -> str:
        """Parse a sender line and return the sender name."""
        # Check if it's a phone number
        if re.match(r"^\+?\d+$", line):
            try:
                normalized_line = self._normalize_phone_number(line)
                # Check against all contacts
                for contact in contacts:
                    if contact.get("phone"):
                        normalized_phone = self._normalize_phone_number(contact["phone"])
                        if normalized_line == normalized_phone:
                            return contact["name"]
                return line  # Return original if no match found
            except Exception as e:
                logger.warning(f"Failed to normalize phone number on line {line_num}: {e}")
                return line

        # Check if it's an email for any contact
        for contact in contacts:
            if contact.get("email") and line == contact["email"]:
                return contact["name"]

        # Special case for Jess
        if line == "Jess":
            return "Jess"

        return line

    async def _generate_output_files(
        self, chunks: list[list[Message]], config: ExportConfig
    ) -> None:
        """Generate output files for chunks."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        contact_names_str = "_".join(config.contact_names[:3])

        for i, chunk in enumerate(chunks, 1):
            if not chunk:
                continue

            start_date = chunk[0].timestamp.strftime("%Y-%m-%d")
            end_date = chunk[-1].timestamp.strftime("%Y-%m-%d")

            # Create output directory
            output_dir = OUTPUT_DIR / timestamp
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filenames
            base_filename = f"{contact_names_str}_{start_date}_to_{end_date}"
            if len(chunks) > 1:
                base_filename += f"_chunk{i}"

            # Write CSV file
            if config.output_format in ["csv", "both"]:
                csv_path = output_dir / f"{base_filename}.csv"
                await self._write_csv(chunk, csv_path)

            # Write TXT file
            if config.output_format in ["txt", "both"]:
                txt_path = output_dir / f"{base_filename}.txt"
                await self._write_txt(chunk, txt_path)

    async def _write_csv(self, messages: list[Message], file_path: Path) -> None:
        """Write messages to CSV file."""
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            # Write header
            await f.write("ID,Sender,Timestamp,Content\n")

            # Write messages
            for i, message in enumerate(messages, 1):
                await f.write(
                    f"{i},{message.sender},{message.timestamp},{message.content}\n"
                )

        logger.info(f"CSV file written: {file_path}")

    async def _write_txt(self, messages: list[Message], file_path: Path) -> None:
        """Write messages to TXT file."""
        async with aiofiles.open(file_path, "w", encoding="utf-8") as f:
            for message in messages:
                await f.write(
                    f"{message.sender},{message.timestamp},{message.content}\n"
                )

        logger.info(f"TXT file written: {file_path}")


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Format iMessage history with improved architecture",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s -n "John Doe" -d 2024-01-01 -e 2024-12-31
  %(prog)s -n "Mom" "Dad" --size 10 -o
  %(prog)s --names "Best Friend" --lines 1000 --format csv
        """,
    )

    # Required contact names
    parser.add_argument(
        "-n",
        "--names",
        nargs="+",
        required=True,
        help="Contact names (can specify multiple) - REQUIRED",
    )

    # Date filters
    parser.add_argument(
        "-d",
        "--date",
        help="Start date (YYYY-MM-DD). If not provided, exports all available history."
    )
    parser.add_argument(
        "-e",
        "--end-date",
        help="End date (YYYY-MM-DD). If not provided, exports up to today."
    )

    # Chunking options (mutually exclusive)
    chunk_group = parser.add_mutually_exclusive_group()
    chunk_group.add_argument(
        "-s",
        "--size",
        type=float,
        help="Size per chunk in MB"
    )
    chunk_group.add_argument(
        "-l",
        "--lines",
        type=int,
        help="Lines per chunk"
    )
    chunk_group.add_argument(
        "-c",
        "--count",
        type=int,
        help="Messages per chunk"
    )
    chunk_group.add_argument(
        "--date-range",
        type=int,
        help="Days per chunk"
    )

    # Other options
    parser.add_argument(
        "-o",
        "--one-side",
        action="store_true",
        help="Only include messages from contacts (not your replies)",
    )
    parser.add_argument(
        "--format",
        choices=["csv", "txt", "both"],
        default="both",
        help="Output format (default: both)"
    )
    parser.add_argument(
        "--db-path",
        type=Path,
        help="Custom database path (default: project_root/data/messages.db)",
    )

    args = parser.parse_args()

    # Additional validation
    if args.date and args.end_date and args.date > args.end_date:
        parser.error("Start date must be before or equal to end date")

    if not any([args.size, args.lines, args.count, args.date_range]):
        logger.info("No chunking specified - will create single output file(s)")

    return args


async def main() -> int:
    """Main function."""
    print("🚀 Starting iMessage History Export Tool")
    print("=" * 50)

    args = parse_arguments()

    # Validate dates
    if args.date and is_date_in_future(args.date):
        logger.error(f"❌ Start date {args.date} is in the future")
        return 1

    if args.end_date and is_date_in_future(args.end_date):
        logger.error(f"❌ End date {args.end_date} is in the future")
        return 1

    # Show configuration summary
    print("📋 Configuration Summary:")
    print(f"   Contacts: {', '.join(args.names)}")
    if args.date:
        print(f"   Start Date: {args.date}")
    if args.end_date:
        print(f"   End Date: {args.end_date}")
    else:
        print("   End Date: Today")
    if args.one_side:
        print("   Mode: Contact messages only")
    else:
        print("   Mode: All messages")
    print(f"   Format: {args.format}")

    chunking_info = []
    if args.size:
        chunking_info.append(f"Size chunks: {args.size}MB")
    elif args.lines:
        chunking_info.append(f"Line chunks: {args.lines} lines")
    elif args.count:
        chunking_info.append(f"Count chunks: {args.count} messages")
    elif args.date_range:
        chunking_info.append(f"Date chunks: {args.date_range} days")

    if chunking_info:
        print(f"   Chunking: {', '.join(chunking_info)}")
    else:
        print("   Chunking: Single file")
    print()

    # Determine chunking strategy
    chunk_config = None
    if args.size:
        chunk_config = ChunkConfig(ChunkStrategy.SIZE_MB, args.size)
    elif args.lines:
        chunk_config = ChunkConfig(ChunkStrategy.LINES, args.lines)
    elif args.count:
        chunk_config = ChunkConfig(ChunkStrategy.COUNT, args.count)
    elif args.date_range:
        chunk_config = ChunkConfig(
            ChunkStrategy.DATE_RANGE, args.date_range, args.date_range
        )

    # Create configuration
    config = ExportConfig(
        contact_names=args.names,
        start_date=args.date,
        end_date=args.end_date,
        chunk_config=chunk_config,
        only_contact_messages=args.one_side,
        output_format=args.format,
    )

    # Initialize components
    print("🔧 Initializing components...")
    db_manager = DatabaseManager(args.db_path)
    contact_manager = ContactManager(db_manager)
    processor = MessageProcessor(db_manager)
    export_manager = ExportManager(db_manager, processor)

    # Process contacts
    print("👥 Checking contact information...")
    missing_contacts = []
    for name in config.contact_names:
        contact = contact_manager.get_contact(name)
        if not contact:
            missing_contacts.append(name)

    if missing_contacts:
        print(f"⚠️  {len(missing_contacts)} contact(s) need information:")
        for name in missing_contacts:
            print(f"   • {name}")
        print()

        for name in missing_contacts:
            print(f"📞 Setting up contact: {name}")
            phone = input(f"   Enter phone number for {name}: ").strip()
            email = input(f"   Enter email for {name} (optional): ").strip() or None
            contact_manager.save_contact(name, phone, email)
            print(f"   ✅ Contact '{name}' saved")
        print()

    # Export messages
    print("📤 Starting export process...")
    try:
        success = await export_manager.export_messages(config)

        if success:
            print()
            print("🎉 Export completed successfully!")
            print("📁 Check your output directory for the exported files")
            return 0
        else:
            print()
            print("❌ Export failed")
            return 1

    except KeyboardInterrupt:
        print()
        print("⏹️  Export cancelled by user")
        return 1
    except Exception as e:
        print()
        print(f"💥 Unexpected error during export: {e}")
        logger.exception("Export failed with exception")
        return 1


def cli_main():
    """Entry point for the CLI."""
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(1)
    except Exception as e:
        logger.exception(f"Unexpected error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    cli_main()
