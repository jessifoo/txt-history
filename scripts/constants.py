"""Constants used throughout the application."""
from pathlib import Path

# Directory paths
OUTPUT_DIR = Path.home() / "txt_history_output"
TMP_PATH = Path.home() / "imessage-export"
CONTACT_STORE_FILE = Path(__file__).parent / "contacts.json"

# Ensure directories exist
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TMP_PATH.mkdir(parents=True, exist_ok=True)