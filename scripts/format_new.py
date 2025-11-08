#!/usr/bin/env python3
"""
New implementation of the iMessage formatting tool with cleaner code structure.
"""
import argparse
import asyncio
import json
import logging
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Import existing utilities
try:
    # When imported as a module
    from .constants import CONTACT_STORE_FILE, OUTPUT_DIR, TMP_PATH
    from .utils import format_date_to_iso, is_date_in_future
except ImportError:
    # When run directly as a script
    from constants import CONTACT_STORE_FILE, OUTPUT_DIR, TMP_PATH
    from utils import format_date_to_iso, is_date_in_future

# Constants
EXPORT_PATH = Path("/Users/jessicajohnson/imessage-export")


@dataclass
class Contact:
    """Contact information."""
    name: str
    phone: Optional[str] = None
    emails: List[str] = None
    
    def __post_init__(self):
        """Initialize default values."""
        if self.emails is None:
            self.emails = []


class ContactStore:
    """Store for contact information."""
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.contacts = self._load_contacts()
    
    def _load_contacts(self):
        """Load contacts from file."""
        if not self.file_path.exists():
            logger.warning(f"Contact store file not found: {self.file_path}")
            return {}
        
        try:
            with open(self.file_path, "r") as f:
                return json.load(f)
        except json.JSONDecodeError:
            logger.error(f"Invalid JSON in contact store: {self.file_path}")
            return {}
    
    def get_contact(self, name: str) -> Optional[Contact]:
        """Get contact by name."""
        if name not in self.contacts:
            return None
        
        contact_data = self.contacts[name]
        return Contact(
            name=name,
            phone=contact_data.get("phone"),
            emails=contact_data.get("emails", [])
        )
    
    def save_contact(self, contact: Contact) -> None:
        """Save contact to store."""
        self.contacts[contact.name] = {
            "phone": contact.phone,
            "emails": contact.emails
        }
        
        with open(self.file_path, "w") as f:
            json.dump(self.contacts, f, indent=2)


def get_contact_info(name: str) -> Optional[Contact]:
    """Get contact information, prompting the user if needed."""
    contact_store = ContactStore(CONTACT_STORE_FILE)
    contact = contact_store.get_contact(name)
    
    if contact:
        logger.info(f"Found contact: {contact}")
        return contact
    
    # Contact not found, prompt user for information
    logger.info(f"Contact '{name}' not found in contacts.")
    phone = input(f"Please enter phone number for {name} (or 'cancel' to exit): ")
    
    if phone.lower() == "cancel":
        return None
    
    # Create new contact
    contact = Contact(name=name, phone=phone)
    
    # Ask for email
    email = input(f"Please enter email for {name} (optional, press Enter to skip): ")
    if email:
        contact.emails.append(email)
    
    # Save contact
    contact_store.save_contact(contact)
    logger.info(f"Saved new contact: {contact}")
    
    return contact


def parse_arguments():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Format iMessage history")
    parser.add_argument("-n", "--name", default="Phil", help="Contact name")
    parser.add_argument("-d", "--date", help="Start date (YYYY-MM-DD)")
    parser.add_argument("-e", "--end-date", help="End date (YYYY-MM-DD)")
    parser.add_argument("-s", "--size", type=float, help="Size per chunk in MB")
    parser.add_argument("-l", "--lines", type=int, help="Lines per chunk")
    parser.add_argument("-o", "--one-side", action="store_true", help="Only include messages from contact")
    return parser.parse_args()


async def main():
    """Main function that orchestrates the process."""
    # Parse arguments
    args = parse_arguments()
    logger.info(f"Starting with arguments: {args}")
    
    # Validate date if provided
    if args.date and is_date_in_future(args.date):
        print(f"Error: Date {args.date} is in the future")
        return 1
    
    # Get contact information
    contact = get_contact_info(args.name)
    if not contact:
        print(f"Error: Could not get contact information for {args.name}")
        return 1
    
    # TODO: Implement the rest of the functionality
    print(f"Contact information: {contact}")
    print("New formatter initialized. Implementation in progress.")
    return 0


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
