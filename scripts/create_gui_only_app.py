#!/usr/bin/env python3
"""
Create a GUI-only version of the iMessage Exporter (no CLI components).
"""

import shutil
from pathlib import Path

def create_gui_only_package():
    """Create a GUI-only package without CLI components."""
    print("🖥️ Creating GUI-only package...")
    
    # Create GUI-only package directory
    gui_dir = Path.home() / "iMessageExporter_GUI_Only"
    if gui_dir.exists():
        shutil.rmtree(gui_dir)
    gui_dir.mkdir()
    
    # Copy the existing packaged application
    packaged_dir = Path.home() / "iMessageExporter"
    if packaged_dir.exists():
        shutil.copytree(packaged_dir, gui_dir / "iMessageExporter")
        print("✅ Copied packaged application")
    else:
        print("❌ Packaged application not found. Please run package_app.py first.")
        return False
    
    # Remove CLI-related files
    cli_files_to_remove = [
        "launch_cli.py",
        "scripts/format_new.py",  # This contains CLI code
    ]
    
    for file_path in cli_files_to_remove:
        full_path = gui_dir / "iMessageExporter" / file_path
        if full_path.exists():
            full_path.unlink()
            print(f"✅ Removed CLI file: {file_path}")
    
    # Create a simplified format_new.py with only GUI components
    create_gui_only_format_new(gui_dir / "iMessageExporter" / "scripts")
    
    # Create a simple launcher that only runs the GUI
    create_gui_launcher(gui_dir)
    
    # Create a simplified README
    create_gui_readme(gui_dir)
    
    print(f"✅ GUI-only package created: {gui_dir}")
    return True

def create_gui_only_format_new(scripts_dir):
    """Create a GUI-only version of format_new.py without CLI components."""
    format_new_content = '''#!/usr/bin/env python3
"""
iMessage History Exporter - GUI Components Only
This version contains only the components needed for the GUI application.
"""

import asyncio
import logging
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union
import pandas as pd
import pytz

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Message:
    """Represents a single message."""
    
    def __init__(self, sender: str, timestamp: str, content: str, contact_name: str, source_file: str = ""):
        self.sender = sender
        self.timestamp = timestamp
        self.content = content
        self.contact_name = contact_name
        self.source_file = source_file

class ChunkStrategy:
    """Strategy for chunking messages."""
    
    def __init__(self, strategy: str, value: float):
        self.strategy = strategy
        self.value = value

class ChunkConfig:
    """Configuration for message chunking."""
    
    def __init__(self, strategy: Optional[ChunkStrategy] = None):
        self.strategy = strategy

class ExportConfig:
    """Configuration for message export."""
    
    def __init__(
        self,
        contact_names: List[str],
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
        chunk_config: Optional[ChunkConfig] = None,
        one_side_only: bool = False,
        output_format: str = "both"
    ):
        self.contact_names = contact_names
        self.start_date = start_date
        self.end_date = end_date
        self.chunk_config = chunk_config
        self.one_side_only = one_side_only
        self.output_format = output_format

class DatabaseManager:
    """Manages the SQLite database for storing messages and contacts."""
    
    def __init__(self, db_path: Path | None = None):
        if db_path is None:
            project_root = Path(__file__).parent.parent
            db_path = project_root / "data" / "messages.db"
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
                        chunk_index INTEGER,
                        file_path TEXT NOT NULL,
                        message_count INTEGER,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (session_id) REFERENCES export_sessions (id)
                    )
                """)

            logger.info(f"Database initialized successfully at {self.db_path}")
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            raise

class ContactManager:
    """Manages contact information."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def save_contact(self, name: str, phone: str, email: str) -> bool:
        """Save or update contact information."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO contacts (name, phone, email)
                    VALUES (?, ?, ?)
                """, (name, phone, email))
            return True
        except Exception as e:
            logger.error(f"Failed to save contact {name}: {e}")
            return False

    def get_contact(self, name: str) -> Optional[Dict]:
        """Get contact information by name."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, name, phone, email FROM contacts WHERE name = ?
                """, (name,))
                row = cursor.fetchone()
                if row:
                    return {
                        "id": row[0],
                        "name": row[1],
                        "phone": row[2],
                        "email": row[3]
                    }
            return None
        except Exception as e:
            logger.error(f"Failed to get contact {name}: {e}")
            return None

    def get_all_contacts(self) -> List[Dict]:
        """Get all contacts."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.execute("""
                    SELECT id, name, phone, email FROM contacts ORDER BY name
                """)
                return [
                    {"id": row[0], "name": row[1], "phone": row[2], "email": row[3]}
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get contacts: {e}")
            return []

class MessageProcessor:
    """Processes and stores messages."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db_manager = db_manager

    def store_messages(self, messages: List[Message]) -> int:
        """Store messages in the database."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                cursor = conn.executemany("""
                    INSERT INTO messages (sender, timestamp, content, contact_name, source_file)
                    VALUES (?, ?, ?, ?, ?)
                """, [
                    (msg.sender, msg.timestamp, msg.content, msg.contact_name, msg.source_file)
                    for msg in messages
                ])
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Failed to store messages: {e}")
            return 0

    def get_messages(self, contact_names: List[str], start_date: Optional[str] = None, 
                    end_date: Optional[str] = None) -> List[Message]:
        """Retrieve messages from the database."""
        try:
            with sqlite3.connect(self.db_manager.db_path) as conn:
                query = "SELECT sender, timestamp, content, contact_name, source_file FROM messages WHERE contact_name IN ({})".format(
                    ",".join("?" * len(contact_names))
                )
                params = contact_names
                
                if start_date:
                    query += " AND timestamp >= ?"
                    params.append(start_date)
                
                if end_date:
                    query += " AND timestamp <= ?"
                    params.append(end_date)
                
                query += " ORDER BY timestamp"
                
                cursor = conn.execute(query, params)
                return [
                    Message(row[0], row[1], row[2], row[3], row[4])
                    for row in cursor.fetchall()
                ]
        except Exception as e:
            logger.error(f"Failed to get messages: {e}")
            return []

class ExportManager:
    """Manages message export functionality."""
    
    def __init__(self, db_manager: DatabaseManager, processor: MessageProcessor):
        self.db_manager = db_manager
        self.processor = processor

    async def export_messages(self, config: ExportConfig) -> bool:
        """Export messages based on configuration."""
        try:
            # Get messages from database
            messages = self.processor.get_messages(
                config.contact_names,
                config.start_date,
                config.end_date
            )
            
            if not messages:
                logger.warning("No messages found for the specified criteria")
                return False
            
            # Filter messages if one_side_only is True
            if config.one_side_only:
                messages = [msg for msg in messages if msg.sender != "You"]
            
            # Create output directory
            output_dir = Path(__file__).parent.parent / "output"
            output_dir.mkdir(exist_ok=True)
            
            # Generate timestamp for this export
            timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
            export_dir = output_dir / timestamp
            export_dir.mkdir(exist_ok=True)
            
            # Export based on format
            if config.output_format in ["csv", "both"]:
                self._export_csv(messages, export_dir)
            
            if config.output_format in ["txt", "both"]:
                self._export_txt(messages, export_dir)
            
            logger.info(f"Export completed successfully: {export_dir}")
            return True
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return False

    def _export_csv(self, messages: List[Message], output_dir: Path):
        """Export messages to CSV format."""
        try:
            data = []
            for msg in messages:
                data.append({
                    "sender": msg.sender,
                    "timestamp": msg.timestamp,
                    "content": msg.content,
                    "contact_name": msg.contact_name
                })
            
            df = pd.DataFrame(data)
            csv_file = output_dir / f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(csv_file, index=False)
            logger.info(f"CSV export completed: {csv_file}")
            
        except Exception as e:
            logger.error(f"CSV export failed: {e}")

    def _export_txt(self, messages: List[Message], output_dir: Path):
        """Export messages to TXT format."""
        try:
            txt_file = output_dir / f"messages_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            with open(txt_file, 'w', encoding='utf-8') as f:
                for msg in messages:
                    f.write(f"[{msg.timestamp}] {msg.sender}: {msg.content}\\n")
            
            logger.info(f"TXT export completed: {txt_file}")
            
        except Exception as e:
            logger.error(f"TXT export failed: {e}")
'''
    
    format_new_file = scripts_dir / "format_new.py"
    format_new_file.write_text(format_new_content)
    print("✅ Created GUI-only format_new.py")

def create_gui_launcher(gui_dir):
    """Create a simple GUI launcher."""
    launcher_content = '''#!/usr/bin/env python3
"""
Simple GUI launcher for iMessage Exporter.
"""

import sys
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent / "iMessageExporter" / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    from imessage_gui import main
    main()
except ImportError as e:
    print(f"Error: Missing required modules. Please install dependencies first.")
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error running application: {e}")
    sys.exit(1)
'''
    
    launcher_file = gui_dir / "launch_gui.py"
    launcher_file.write_text(launcher_content)
    launcher_file.chmod(0o755)
    print("✅ Created GUI launcher")

def create_gui_readme(gui_dir):
    """Create a README for the GUI-only version."""
    readme_content = '''# iMessage Exporter - GUI Only Version

This is a simplified version of the iMessage Exporter that only includes the GUI components.

## What's Included

- ✅ **GUI Application** - Easy-to-use interface
- ✅ **Contact Management** - Add and manage contacts
- ✅ **Message Export** - Export to CSV and TXT formats
- ✅ **Date Filtering** - Filter messages by date range
- ✅ **No CLI** - Everything through the GUI

## What's Removed

- ❌ Command line interface
- ❌ CLI launcher scripts
- ❌ Complex configuration options

## Quick Start

1. **Install Dependencies:**
   ```bash
   cd iMessageExporter
   python3 install_dependencies.py
   ```

2. **Run the App:**
   ```bash
   python3 launch_gui.py
   ```

## Features

### Contact Management
- Add contacts with name, phone, and email
- Edit existing contacts
- Remove contacts you no longer need

### Message Export
- Select contacts to export
- Choose date ranges (or export all)
- Pick output format (CSV, TXT, or both)
- Set chunking options for large exports

### User-Friendly Interface
- Tabbed interface for easy navigation
- Progress windows for long operations
- Clear error messages and status updates
- No command line knowledge required

## Privacy & Safety

- ✅ Everything stays on your computer
- ✅ No data uploaded anywhere
- ✅ Only reads your Messages (can't send or delete)
- ✅ Uses Apple's official Messages database

---

*Simple, safe, and easy to use!*
'''
    
    readme_file = gui_dir / "README.md"
    readme_file.write_text(readme_content)
    print("✅ Created GUI README")

def main():
    """Main function."""
    print("🖥️ Creating GUI-only iMessage Exporter")
    print("=" * 50)
    
    if create_gui_only_package():
        gui_dir = Path.home() / "iMessageExporter_GUI_Only"
        
        print("=" * 50)
        print("🎉 GUI-only package created successfully!")
        print()
        print("📁 Package location:", gui_dir)
        print()
        print("📋 What's included:")
        print("   - GUI application only (no CLI)")
        print("   - Simplified format_new.py")
        print("   - Easy launcher script")
        print("   - User-friendly README")
        print()
        print("🚀 To use:")
        print("1. Copy the folder to your Mac")
        print("2. Run: python3 launch_gui.py")
        print("3. That's it! No CLI needed!")
        
        return 0
    else:
        print("❌ Failed to create GUI-only package")
        return 1

if __name__ == "__main__":
    main()