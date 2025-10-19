"""
Migration script: Import contacts from JSON (test_contacts.json) into SQLiteContactStore,
overwriting any existing contacts. The JSON file is treated as the source of truth.

Usage:
    poetry run python scripts/migrate_contacts_json_to_sqlite.py

- Normalizes 'phil' (any case) to 'Phil'.
- Overwrites any existing SQLite contacts.
- Logs errors and summary.
"""
import json
import logging
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).parent))
from SQLiteContactStore import SQLiteContactStore

JSON_PATH = Path(__file__).parent.parent / "test_contacts.json"
DB_PATH = None  # Use default path from SQLiteContactStore

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

def load_json_contacts(json_path):
    with open(json_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    contacts = data.get("contacts", {})
    return contacts

def normalize_name(name):
    if name.strip().lower() == "phil":
        return "Phil"
    return name.strip()

def to_list(val):
    if isinstance(val, list):
        return val
    if isinstance(val, str) and val.strip():
        return [v.strip() for v in val.split(",") if v.strip()]
    return []

def main():
    contacts = load_json_contacts(JSON_PATH)
    store = SQLiteContactStore() if DB_PATH is None else SQLiteContactStore(DB_PATH)
    count = 0
    for name, cdata in contacts.items():
        norm_name = normalize_name(name)
        phones = to_list(cdata.get("phone") or cdata.get("phones"))
        emails = to_list(cdata.get("emails") or cdata.get("email"))
        try:
            store.add_contact(norm_name, phones, emails)
            logger.info(f"Imported: {norm_name} | Phones: {phones} | Emails: {emails}")
            count += 1
        except Exception as e:
            logger.error(f"Failed to import {norm_name}: {e}")
    logger.info(f"Imported {count} contacts from JSON into SQLite.")
    store.close()

if __name__ == "__main__":
    main()
