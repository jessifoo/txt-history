#!/usr/bin/env python3
"""
Migration script to update the contacts database structure.
"""

import sqlite3
from pathlib import Path

def migrate_contacts_database(db_path: Path):
    """Migrate the contacts database to the new structure."""
    print(f"Migrating database: {db_path}")
    
    # Backup the original database
    backup_path = db_path.with_suffix('.db.backup')
    if not backup_path.exists():
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"Backup created: {backup_path}")
    
    with sqlite3.connect(db_path) as conn:
        # Check current structure
        cursor = conn.execute("PRAGMA table_info(contacts)")
        columns = [row[1] for row in cursor.fetchall()]
        print(f"Current columns: {columns}")
        
        if 'phone' not in columns or 'email' not in columns:
            print("Adding missing columns...")
            
            # Add phone and email columns if they don't exist
            try:
                conn.execute("ALTER TABLE contacts ADD COLUMN phone TEXT")
                print("Added phone column")
            except sqlite3.OperationalError:
                print("Phone column already exists")
            
            try:
                conn.execute("ALTER TABLE contacts ADD COLUMN email TEXT")
                print("Added email column")
            except sqlite3.OperationalError:
                print("Email column already exists")
            
            try:
                conn.execute("ALTER TABLE contacts ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
                print("Added created_at column")
            except sqlite3.OperationalError:
                print("Created_at column already exists")
            
            conn.commit()
            print("Migration completed successfully")
        else:
            print("Database already has the correct structure")

if __name__ == "__main__":
    # Migrate the original database
    original_db = Path("contacts.db")
    if original_db.exists():
        migrate_contacts_database(original_db)
    
    # Migrate the packaged database
    packaged_db = Path("/home/ubuntu/iMessageExporter/data/messages.db")
    if packaged_db.exists():
        migrate_contacts_database(packaged_db)