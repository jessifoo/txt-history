#!/usr/bin/env python3
"""
Script to add phone number 1 (780) 266-2377 to user Karly in the contacts database.
"""

import sys
from pathlib import Path

# Add the scripts directory to the Python path
sys.path.insert(0, str(Path(__file__).parent))

# Import the required functions directly
from SQLiteContactStore import SQLiteContactStore


def normalize_phone_number(phone: str) -> str:
    """Normalize a phone number by removing non-digit characters."""
    return "".join(filter(str.isdigit, phone))


def main():
    """Add phone number to Karly contact."""
    # Initialize the contact store
    contact_store = SQLiteContactStore()

    # Normalize the phone number
    phone_number = "1 (780) 266-2377"
    normalized_phone = normalize_phone_number(phone_number)
    print(f"Normalized phone number: {normalized_phone}")

    # Check if Karly already exists
    karly = contact_store.get_contact_by_name("Karly")

    if karly:
        print(f"Found existing contact: {karly.name}")
        print(f"Current phones: {karly.phones}")
        print(f"Current emails: {karly.emails}")

        # Check if the phone number already exists
        if normalized_phone in karly.phones:
            print(f"Phone number {normalized_phone} already exists for Karly")
            return

        # Add the phone number to existing contact
        try:
            with contact_store._conn:
                contact_store._conn.execute(
                    "INSERT OR IGNORE INTO phone_numbers (contact_id, phone) VALUES (?, ?)",
                    (karly.id, normalized_phone),
                )
            print(f"Successfully added phone number {normalized_phone} to Karly")
        except Exception as e:
            print(f"Error adding phone number: {e}")
            return
    else:
        print("Karly not found, creating new contact...")
        try:
            # Create new contact with the phone number
            karly = contact_store.add_contact("Karly", [phone_number], [])
            print(
                f"Successfully created contact Karly with phone number {normalized_phone}"
            )
        except Exception as e:
            print(f"Error creating contact: {e}")
            return

    # Verify the contact was updated
    updated_karly = contact_store.get_contact_by_name("Karly")
    if updated_karly:
        print(f"Updated contact: {updated_karly.name}")
        print(f"Phones: {updated_karly.phones}")
        print(f"Emails: {updated_karly.emails}")

    # Close the connection
    contact_store.close()


if __name__ == "__main__":
    main()
