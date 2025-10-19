#!/usr/bin/env python3
"""
Direct iMessage database reader - alternative to imessage-exporter
Reads messages directly from the iMessage SQLite database.
"""

import logging
import sqlite3
from pathlib import Path
from typing import Any

import pandas as pd

logger = logging.getLogger(__name__)


class IMessageDBReader:
    """Direct reader for iMessage database."""

    def __init__(self, db_path: Path | None = None):
        """Initialize the iMessage database reader.

        Args:
            db_path: Path to the iMessage database. If None, uses default location.
        """
        if db_path is None:
            # Default iMessage database location
            self.db_path = Path.home() / "Library" / "Messages" / "chat.db"
        else:
            self.db_path = db_path

        if not self.db_path.exists():
            raise FileNotFoundError(f"iMessage database not found at {self.db_path}")

        logger.info(f"Using iMessage database at: {self.db_path}")

    def get_contacts(self) -> list[dict[str, Any]]:
        """Get all contacts from the iMessage database.

        Returns:
            List of contact dictionaries with name, phone, and email info.
        """
        contacts = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Query to get unique contacts from messages
                cursor = conn.execute("""
                    SELECT DISTINCT
                        COALESCE(display_name, id) as name,
                        identifier,
                        CASE
                            WHEN identifier LIKE '%@%' THEN 'email'
                            ELSE 'phone'
                        END as type
                    FROM chat
                    JOIN chat_message_join ON chat.ROWID = chat_message_join.chat_id
                    JOIN message ON chat_message_join.message_id = message.ROWID
                    JOIN chat_handle_join ON message.ROWID = chat_handle_join.message_id
                    JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                    WHERE identifier IS NOT NULL AND identifier != ''
                    ORDER BY name
                """)

                # Group by contact name and collect phone/email
                contact_map = {}
                for row in cursor.fetchall():
                    name = row[0] or "Unknown"
                    identifier = row[1]
                    id_type = row[2]

                    if name not in contact_map:
                        contact_map[name] = {"name": name, "phone": None, "email": None}

                    if id_type == "phone":
                        contact_map[name]["phone"] = identifier
                    elif id_type == "email":
                        contact_map[name]["email"] = identifier

                contacts = list(contact_map.values())

        except sqlite3.Error as e:
            logger.error(f"Failed to read contacts from iMessage database: {e}")
            raise

        logger.info(f"Found {len(contacts)} contacts in iMessage database")
        return contacts

    def get_messages_for_contact(
        self,
        contact_info: dict[str, Any],
        start_date: str | None = None,
        end_date: str | None = None,
        limit: int | None = None,
    ) -> list[dict[str, Any]]:
        """Get messages for a specific contact.

        Args:
            contact_info: Contact dictionary with name, phone, email
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            limit: Maximum number of messages to return

        Returns:
            List of message dictionaries
        """
        messages = []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Build WHERE clause for contact identifiers
                where_conditions = []
                params = []

                if contact_info.get("phone"):
                    where_conditions.append("handle.identifier = ?")
                    params.append(contact_info["phone"])

                if contact_info.get("email"):
                    where_conditions.append("handle.identifier = ?")
                    params.append(contact_info["email"])

                if not where_conditions:
                    logger.warning(
                        f"No valid identifiers for contact {contact_info['name']}"
                    )
                    return []

                where_clause = f"({' OR '.join(where_conditions)})"

                # Add date filters if provided
                if start_date:
                    where_clause += " AND message.date >= ?"
                    # Convert date to Unix timestamp (iMessage uses Unix timestamps in milliseconds)
                    start_timestamp = pd.Timestamp(start_date).timestamp() * 1000
                    params.append(int(start_timestamp))

                if end_date:
                    where_clause += " AND message.date <= ?"
                    end_timestamp = (
                        pd.Timestamp(end_date) + pd.Timedelta(days=1)
                    ).timestamp() * 1000
                    params.append(int(end_timestamp))

                # Build the query
                query = f"""
                    SELECT
                        message.ROWID as msg_id,
                        message.text as content,
                        message.date as timestamp,
                        message.is_from_me as is_from_me,
                        handle.identifier as sender_id,
                        COALESCE(chat.display_name, 'Unknown') as chat_name
                    FROM message
                    JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                    JOIN chat ON chat_message_join.chat_id = chat.ROWID
                    JOIN chat_handle_join ON message.ROWID = chat_handle_join.message_id
                    JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                    WHERE {where_clause}
                    AND message.text IS NOT NULL
                    AND message.text != ''
                    ORDER BY message.date
                """

                if limit:
                    query += f" LIMIT {limit}"

                cursor = conn.execute(query, params)

                for row in cursor.fetchall():
                    try:
                        # Convert timestamp from milliseconds to pandas timestamp
                        timestamp_ms = row[2]
                        if timestamp_ms:
                            timestamp = pd.Timestamp(
                                timestamp_ms / 1000000000, tz="UTC"
                            ).tz_convert("America/Edmonton")
                        else:
                            timestamp = pd.Timestamp.now()

                        # Determine sender name
                        is_from_me = bool(row[3])
                        if is_from_me:
                            sender = "Me"
                        else:
                            sender = contact_info["name"]

                        messages.append(
                            {
                                "id": row[0],
                                "content": row[1],
                                "timestamp": timestamp,
                                "sender": sender,
                                "contact_name": contact_info["name"],
                                "source_file": "iMessage Database",
                            }
                        )

                    except Exception as e:
                        logger.warning(f"Failed to process message {row[0]}: {e}")
                        continue

        except sqlite3.Error as e:
            logger.error(f"Failed to read messages from iMessage database: {e}")
            raise

        logger.info(f"Retrieved {len(messages)} messages for {contact_info['name']}")
        return messages

    def search_contacts(self, search_term: str) -> list[dict[str, Any]]:
        """Search for contacts by name.

        Args:
            search_term: Term to search for in contact names

        Returns:
            List of matching contacts
        """
        all_contacts = self.get_contacts()
        search_lower = search_term.lower()

        return [
            contact
            for contact in all_contacts
            if search_lower in contact["name"].lower()
        ]

    def get_message_stats(self, contact_info: dict[str, Any]) -> dict[str, Any]:
        """Get statistics about messages for a contact.

        Args:
            contact_info: Contact dictionary

        Returns:
            Dictionary with message statistics
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                where_conditions = []
                params = []

                if contact_info.get("phone"):
                    where_conditions.append("handle.identifier = ?")
                    params.append(contact_info["phone"])

                if contact_info.get("email"):
                    where_conditions.append("handle.identifier = ?")
                    params.append(contact_info["email"])

                if not where_conditions:
                    return {
                        "total_messages": 0,
                        "oldest_date": None,
                        "newest_date": None,
                    }

                where_clause = f"({' OR '.join(where_conditions)})"

                # Get total count
                count_query = f"""
                    SELECT COUNT(*)
                    FROM message
                    JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                    JOIN chat_handle_join ON message.ROWID = chat_handle_join.message_id
                    JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                    WHERE {where_clause}
                    AND message.text IS NOT NULL
                    AND message.text != ''
                """

                cursor = conn.execute(count_query, params)
                total_messages = cursor.fetchone()[0]

                # Get date range
                date_query = f"""
                    SELECT MIN(message.date), MAX(message.date)
                    FROM message
                    JOIN chat_message_join ON message.ROWID = chat_message_join.message_id
                    JOIN chat_handle_join ON message.ROWID = chat_handle_join.message_id
                    JOIN handle ON chat_handle_join.handle_id = handle.ROWID
                    WHERE {where_clause}
                    AND message.text IS NOT NULL
                    AND message.text != ''
                """

                cursor = conn.execute(date_query, params)
                min_date, max_date = cursor.fetchone()

                def format_timestamp(ts):
                    if ts:
                        return (
                            pd.Timestamp(ts / 1000000000, tz="UTC")
                            .tz_convert("America/Edmonton")
                            .strftime("%Y-%m-%d")
                        )
                    return None

                return {
                    "total_messages": total_messages,
                    "oldest_date": format_timestamp(min_date),
                    "newest_date": format_timestamp(max_date),
                }

        except sqlite3.Error as e:
            logger.error(f"Failed to get message stats: {e}")
            return {"total_messages": 0, "oldest_date": None, "newest_date": None}


def find_imessage_database() -> Path | None:
    """Find the iMessage database on the system.

    Returns:
        Path to the iMessage database if found, None otherwise.
    """
    possible_paths = [
        Path.home() / "Library" / "Messages" / "chat.db",
        Path.home() / "Library" / "Messages" / "chat.db-shm",
        Path.home() / "Library" / "Messages" / "chat.db-wal",
    ]

    for path in possible_paths:
        if path.exists():
            return path

    return None


def test_database_connection(db_path: Path) -> bool:
    """Test if we can connect to the iMessage database.

    Args:
        db_path: Path to the database file

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' LIMIT 1"
            )
            cursor.fetchone()
            return True
    except sqlite3.Error:
        return False
