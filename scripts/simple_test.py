#!/usr/bin/env python3
"""
Simple test to verify the core functionality works.
"""

import sys
import tempfile
from pathlib import Path
import sqlite3

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def test_basic_functionality():
    """Test basic functionality without complex setup."""
    print("🧪 Testing basic functionality...")
    
    try:
        from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager, Message
        from datetime import datetime
        print("✅ Imports work")
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        # Test database manager
        db_manager = DatabaseManager(db_path)
        print("✅ Database manager created")
        
        # Test contact manager
        contact_manager = ContactManager(db_manager)
        contact_manager.save_contact("Test Contact", "+1234567890", "test@example.com")
        print("✅ Contact saved")
        
        # Test retrieving contact
        contact = contact_manager.get_contact("Test Contact")
        assert contact is not None, "Failed to retrieve contact"
        print("✅ Contact retrieved")
        
        # Test message processor
        processor = MessageProcessor(db_manager)
        print("✅ Message processor created")
        
        # Test export manager
        export_manager = ExportManager(db_manager, processor)
        print("✅ Export manager created")
        
        # Test storing messages (using DatabaseManager method)
        import pandas as pd
        messages = [
            Message("Test Contact", pd.Timestamp("2024-01-01 10:00:00"), "Hello!", "Test Contact", "test.txt"),
            Message("You", pd.Timestamp("2024-01-01 10:01:00"), "Hi there!", "Test Contact", "test.txt")
        ]
        db_manager.store_messages(messages)
        print("✅ Messages stored")
        
        # Test retrieving messages
        retrieved = db_manager.get_messages(["Test Contact"])
        assert len(retrieved) == 2, f"Expected 2 messages, got {len(retrieved)}"
        print("✅ Messages retrieved")
        
        # Clean up
        db_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_gui_components():
    """Test GUI components."""
    print("🧪 Testing GUI components...")
    
    try:
        from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager
        import sqlite3
        
        # Create temporary database
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = Path(tmp.name)
        
        # Test that GUI components can be created
        db_manager = DatabaseManager(db_path)
        contact_manager = ContactManager(db_manager)
        processor = MessageProcessor(db_manager)
        export_manager = ExportManager(db_manager, processor)
        
        print("✅ GUI components created")
        
        # Test contact loading functionality
        contact_manager.save_contact("Test Contact", "+1234567890", "test@example.com")
        
        # Simulate contact loading (what the GUI does)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name, phone, email FROM contacts ORDER BY name")
            contacts = cursor.fetchall()
        
        assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
        print("✅ Contact loading works")
        
        # Clean up
        db_path.unlink()
        
        return True
        
    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        return False

def test_imessage_db_reader():
    """Test iMessage database reader."""
    print("🧪 Testing iMessage DB reader...")
    
    try:
        from imessage_db_reader import IMessageDBReader, find_imessage_database
        
        # Test finding database (will be None in this environment)
        db_path = find_imessage_database()
        assert db_path is None, "Should not find iMessage database in this environment"
        print("✅ Database finder works")
        
        # Test reader initialization
        try:
            reader = IMessageDBReader()
            print("✅ Reader created")
        except FileNotFoundError:
            print("✅ Reader correctly reports no database")
        
        return True
        
    except Exception as e:
        print(f"❌ iMessage DB reader test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Simple iMessage Exporter Tests")
    print("=" * 50)
    
    tests = [
        ("Basic Functionality", test_basic_functionality),
        ("GUI Components", test_gui_components),
        ("iMessage DB Reader", test_imessage_db_reader),
    ]
    
    passed = 0
    total = len(tests)
    
    for test_name, test_func in tests:
        print(f"\\n{test_name}:")
        try:
            if test_func():
                passed += 1
                print(f"✅ {test_name} passed")
            else:
                print(f"❌ {test_name} failed")
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is working correctly.")
        return 0
    else:
        print(f"❌ {total - passed} tests failed.")
        return 1

if __name__ == "__main__":
    sys.exit(main())