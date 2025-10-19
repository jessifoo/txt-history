import logging
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from utils import slugify_contact_name  # Relative import for local execution

# Assuming Contact, ContactMetadata, normalize_phone_number are defined as before
# from .constants import CONTACT_STORE_FILE # Use a .db extension now
# from .utils import write_json_file # Keep for potential compatibility/export


# --- Revised Contact Model for Normalized Schema ---
@dataclass
class Contact:
    id: int
    name: str
    phones: list[str]
    emails: list[str]


# --- Updated SQLiteContactStore with Normalized Schema ---
class SQLiteContactStore:
    """Manages contact storage and retrieval using SQLite (normalized schema)."""

    def __init__(
        self, db_path: Path = Path(os.path.dirname(__file__)) / "contacts.db"
    ) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.db_path)
        self._conn.row_factory = sqlite3.Row
        self._create_tables()
        logger.info(f"Initialized contact store at {self.db_path}")

    def ensure_contact_tables(self, contact_name: str) -> None:
        """
        Ensures per-contact tables for messages and chunks exist.
        - Slugifies the contact name (raises ValueError if invalid)
        - Creates messages_{slug} and chunks_{slug} tables if missing
        """
        try:
            slug = slugify_contact_name(contact_name)
        except ValueError as e:
            logger.error(f"Invalid contact name '{contact_name}': {e}")
            raise
        messages_table = f"messages_{slug}"
        chunks_table = f"chunks_{slug}"
        try:
            with self._conn:
                # Messages table
                self._conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {messages_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        message TEXT NOT NULL,
                        timestamp DATETIME NOT NULL,
                        sender TEXT NOT NULL,
                        prev_id INTEGER,
                        next_id INTEGER,
                        FOREIGN KEY(prev_id) REFERENCES {messages_table}(id),
                        FOREIGN KEY(next_id) REFERENCES {messages_table}(id)
                    )
                """)
                # Chunks table
                self._conn.execute(f"""
                    CREATE TABLE IF NOT EXISTS {chunks_table} (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        start_date DATETIME NOT NULL,
                        end_date DATETIME NOT NULL,
                        chunk_size_mb REAL,
                        chunk_size_lines INTEGER,
                        file_path TEXT NOT NULL,
                        UNIQUE(start_date, end_date, chunk_size_mb, chunk_size_lines)
                    )
                """)
        except sqlite3.Error as e:
            logger.error(
                f"Failed to create per-contact tables for '{contact_name}': {e}"
            )
            raise

    def _create_tables(self) -> None:
        try:
            with self._conn:
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS contacts (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT NOT NULL UNIQUE COLLATE NOCASE
                    )
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS phone_numbers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contact_id INTEGER NOT NULL,
                        phone TEXT NOT NULL,
                        FOREIGN KEY(contact_id) REFERENCES contacts(id),
                        UNIQUE(contact_id, phone)
                    )
                """)
                self._conn.execute("""
                    CREATE TABLE IF NOT EXISTS emails (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        contact_id INTEGER NOT NULL,
                        email TEXT NOT NULL,
                        FOREIGN KEY(contact_id) REFERENCES contacts(id),
                        UNIQUE(contact_id, email)
                    )
                """)
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_phone ON phone_numbers (phone)"
                )
                self._conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_email ON emails (email)"
                )
        except sqlite3.Error as e:
            logger.exception(f"Failed to create or access tables: {e}")
            raise

    def add_contact(self, name: str, phones: list[str], emails: list[str]) -> Contact:
        try:
            with self._conn:
                cursor = self._conn.execute(
                    "INSERT INTO contacts (name) VALUES (?)", (name,)
                )
                contact_id = cursor.lastrowid
        except sqlite3.IntegrityError:
            # Name already exists, fetch id
            contact = self.get_contact_by_name(name)
            if not contact:
                raise ValueError(f"Contact '{name}' exists but could not be fetched.")
            contact_id = contact.id
        except sqlite3.Error as e:
            logger.error(f"Failed to add contact '{name}': {e}")
            raise

        # Add phones
        for phone in phones:
            try:
                with self._conn:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO phone_numbers (contact_id, phone) VALUES (?, ?)",
                        (contact_id, normalize_phone_number(phone)),
                    )
            except sqlite3.Error as e:
                logger.error(f"Failed to add phone '{phone}' for contact '{name}': {e}")
                raise
        # Add emails
        for email in emails:
            try:
                with self._conn:
                    self._conn.execute(
                        "INSERT OR IGNORE INTO emails (contact_id, email) VALUES (?, ?)",
                        (contact_id, email.strip().lower()),
                    )
            except sqlite3.Error as e:
                logger.error(f"Failed to add email '{email}' for contact '{name}': {e}")
                raise
        return self.get_contact_by_id(contact_id)

    def get_contact_by_id(self, contact_id: int) -> Contact or None:
        try:
            cursor = self._conn.execute(
                "SELECT * FROM contacts WHERE id = ?", (contact_id,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            name = row["name"]
            phones = [
                r["phone"]
                for r in self._conn.execute(
                    "SELECT phone FROM phone_numbers WHERE contact_id = ?",
                    (contact_id,),
                )
            ]
            emails = [
                r["email"]
                for r in self._conn.execute(
                    "SELECT email FROM emails WHERE contact_id = ?", (contact_id,)
                )
            ]
            return Contact(id=contact_id, name=name, phones=phones, emails=emails)
        except sqlite3.Error as e:
            logger.error(f"Failed to get contact by id {contact_id}: {e}")
            return None

    def get_contact_by_name(self, name: str) -> Contact or None:
        try:
            cursor = self._conn.execute(
                "SELECT * FROM contacts WHERE name = ? COLLATE NOCASE", (name,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            contact_id = row["id"]
            return self.get_contact_by_id(contact_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to get contact by name '{name}': {e}")
            return None

    def get_contact_by_phone(self, phone: str) -> Contact or None:
        normalized = normalize_phone_number(phone)
        try:
            cursor = self._conn.execute(
                "SELECT contact_id FROM phone_numbers WHERE phone = ?", (normalized,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            contact_id = row["contact_id"]
            return self.get_contact_by_id(contact_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to get contact by phone '{phone}': {e}")
            return None

    def get_contact_by_email(self, email: str) -> Contact or None:
        normalized = email.strip().lower()
        try:
            cursor = self._conn.execute(
                "SELECT contact_id FROM emails WHERE email = ?", (normalized,)
            )
            row = cursor.fetchone()
            if not row:
                return None
            contact_id = row["contact_id"]
            return self.get_contact_by_id(contact_id)
        except sqlite3.Error as e:
            logger.error(f"Failed to get contact by email '{email}': {e}")
            return None

    def list_contacts(self) -> list[Contact]:
        try:
            cursor = self._conn.execute("SELECT id FROM contacts")
            ids = [row["id"] for row in cursor.fetchall()]
            return [
                self.get_contact_by_id(cid)
                for cid in ids
                if self.get_contact_by_id(cid)
            ]
        except sqlite3.Error as e:
            logger.error(f"Failed to list contacts: {e}")
            return []

    def close(self) -> None:
        if self._conn:
            self._conn.close()
            self._conn = None
            logger.info("Closed contact store database connection.")

    def __del__(self) -> None:
        self.close()


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number by removing non-digit characters."""
    return "".join(filter(str.isdigit, phone))


logger = logging.getLogger(__name__)
