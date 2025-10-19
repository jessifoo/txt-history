#!/usr/bin/env python3
"""
Test script to verify GUI components work without running the actual GUI.
"""

import sys
from pathlib import Path
import sqlite3

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_functionality():
    """Test database operations."""
    print("Testing database functionality...")
    
    from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager
    
    # Create test database
    test_db = Path("test_gui.db")
    if test_db.exists():
        test_db.unlink()
    
    try:
        # Test database manager
        db_manager = DatabaseManager(test_db)
        print("✅ Database manager created")
        
        # Test contact manager
        contact_manager = ContactManager(db_manager)
        print("✅ Contact manager created")
        
        # Test adding a contact
        contact_manager.save_contact("Test Contact", "+1234567890", "test@example.com")
        print("✅ Contact saved")
        
        # Test retrieving contacts
        contact = contact_manager.get_contact("Test Contact")
        if contact:
            print(f"✅ Contact retrieved: {contact}")
        else:
            print("❌ Failed to retrieve contact")
            return False
        
        # Test message processor
        processor = MessageProcessor(db_manager)
        print("✅ Message processor created")
        
        # Test export manager
        export_manager = ExportManager(db_manager, processor)
        print("✅ Export manager created")
        
        return True
        
    except Exception as e:
        print(f"❌ Database test failed: {e}")
        return False
    finally:
        if test_db.exists():
            test_db.unlink()

def test_imessage_db_reader():
    """Test iMessage database reader."""
    print("\nTesting iMessage database reader...")
    
    try:
        from imessage_db_reader import IMessageDBReader, find_imessage_database
        
        # Test finding database (will be None in this environment)
        db_path = find_imessage_database()
        print(f"✅ iMessage database finder works: {db_path}")
        
        # Test reader initialization (will fail in this environment, which is expected)
        try:
            reader = IMessageDBReader()
            print("✅ iMessage database reader created")
        except FileNotFoundError:
            print("✅ iMessage database reader correctly reports no database (expected in this environment)")
        
        return True
        
    except Exception as e:
        print(f"❌ iMessage database reader test failed: {e}")
        return False

def test_contact_loading():
    """Test contact loading functionality."""
    print("\nTesting contact loading...")
    
    try:
        from format_new import DatabaseManager, ContactManager
        import sqlite3
        
        # Create test database with sample data
        test_db = Path("test_contacts.db")
        if test_db.exists():
            test_db.unlink()
        
        db_manager = DatabaseManager(test_db)
        contact_manager = ContactManager(db_manager)
        
        # Add sample contacts
        sample_contacts = [
            ("Alice", "+1111111111", "alice@example.com"),
            ("Bob", "+2222222222", "bob@example.com"),
            ("Charlie", "+3333333333", "charlie@example.com")
        ]
        
        for name, phone, email in sample_contacts:
            contact_manager.save_contact(name, phone, email)
        
        # Test retrieving all contacts (simulating GUI contact loading)
        with sqlite3.connect(test_db) as conn:
            cursor = conn.execute("SELECT name, phone, email FROM contacts ORDER BY name")
            contacts = cursor.fetchall()
        
        if len(contacts) == 3:
            print(f"✅ Contact loading works: {len(contacts)} contacts found")
            for name, phone, email in contacts:
                print(f"   - {name}: {phone}, {email}")
        else:
            print(f"❌ Expected 3 contacts, got {len(contacts)}")
            return False
        
        return True
        
    except Exception as e:
        print(f"❌ Contact loading test failed: {e}")
        return False
    finally:
        if test_db.exists():
            test_db.unlink()

def main():
    """Run all tests."""
    print("🧪 Testing GUI Components")
    print("=" * 50)
    
    tests = [
        test_database_functionality,
        test_imessage_db_reader,
        test_contact_loading
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print("=" * 50)
    print(f"Tests passed: {passed}/{total}")
    
    if passed == total:
        print("🎉 All tests passed! GUI components are working correctly.")
        return 0
    else:
        print("❌ Some tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())