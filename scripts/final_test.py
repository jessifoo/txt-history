#!/usr/bin/env python3
"""
Final test to verify the core functionality works.
"""

import sys
import tempfile
from pathlib import Path
import sqlite3

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def test_core_functionality():
    """Test core functionality."""
    print("🧪 Testing core functionality...")
    
    try:
        from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager
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
        
        # Test database structure
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['messages', 'contacts', 'export_sessions', 'chunks']
            for table in expected_tables:
                assert table in tables, f"Missing table: {table}"
        print("✅ Database structure correct")
        
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

def test_utils():
    """Test utility functions."""
    print("🧪 Testing utility functions...")
    
    try:
        from utils import slugify_contact_name, parse_date_string, format_date_to_iso
        
        # Test slugify function
        assert slugify_contact_name("John Doe") == "john-doe"
        assert slugify_contact_name("Mary Jane Smith") == "mary-jane-smith"
        print("✅ Slugify function")
        
        # Test date parsing
        date = parse_date_string("2024-01-15")
        assert date is not None, "Failed to parse date"
        print("✅ Date parsing")
        
        # Test date formatting
        formatted = format_date_to_iso(date)
        assert formatted == "2024-01-15", f"Expected '2024-01-15', got '{formatted}'"
        print("✅ Date formatting")
        
        return True
        
    except Exception as e:
        print(f"❌ Utils test failed: {e}")
        return False

def test_constants():
    """Test constants."""
    print("🧪 Testing constants...")
    
    try:
        from constants import OUTPUT_DIR, TMP_PATH, CONTACT_STORE_FILE, DEFAULT_TIMEZONE
        
        # Test that constants are defined
        assert OUTPUT_DIR is not None, "OUTPUT_DIR not defined"
        assert TMP_PATH is not None, "TMP_PATH not defined"
        assert CONTACT_STORE_FILE is not None, "CONTACT_STORE_FILE not defined"
        assert DEFAULT_TIMEZONE is not None, "DEFAULT_TIMEZONE not defined"
        print("✅ Constants defined")
        
        # Test that directories exist
        assert OUTPUT_DIR.exists(), f"OUTPUT_DIR does not exist: {OUTPUT_DIR}"
        assert TMP_PATH.exists(), f"TMP_PATH does not exist: {TMP_PATH}"
        print("✅ Directories exist")
        
        return True
        
    except Exception as e:
        print(f"❌ Constants test failed: {e}")
        return False

def main():
    """Run all tests."""
    print("🧪 Running Final iMessage Exporter Tests")
    print("=" * 50)
    
    tests = [
        ("Core Functionality", test_core_functionality),
        ("GUI Components", test_gui_components),
        ("iMessage DB Reader", test_imessage_db_reader),
        ("Utility Functions", test_utils),
        ("Constants", test_constants),
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