#!/usr/bin/env python3
"""
Comprehensive test suite for iMessage Exporter.
"""

import sys
import tempfile
import shutil
from pathlib import Path
import sqlite3
import asyncio

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent))

def test_database_manager():
    """Test DatabaseManager functionality."""
    print("🧪 Testing DatabaseManager...")
    
    from format_new import DatabaseManager
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Test initialization
        db_manager = DatabaseManager(db_path)
        assert db_manager.db_path == db_path
        assert db_path.exists()
        print("✅ Database initialization")
        
        # Test database structure
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [row[0] for row in cursor.fetchall()]
            expected_tables = ['messages', 'contacts', 'export_sessions', 'chunks']
            for table in expected_tables:
                assert table in tables, f"Missing table: {table}"
        print("✅ Database structure")
        
        return True
        
    except Exception as e:
        print(f"❌ DatabaseManager test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def test_contact_manager():
    """Test ContactManager functionality."""
    print("🧪 Testing ContactManager...")
    
    from format_new import DatabaseManager, ContactManager
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        db_manager = DatabaseManager(db_path)
        contact_manager = ContactManager(db_manager)
        
        # Test saving contact
        success = contact_manager.save_contact("Test Contact", "+1234567890", "test@example.com")
        assert success, "Failed to save contact"
        print("✅ Save contact")
        
        # Test retrieving contact
        contact = contact_manager.get_contact("Test Contact")
        assert contact is not None, "Failed to retrieve contact"
        assert contact["name"] == "Test Contact"
        assert contact["phone"] == "+1234567890"
        assert contact["email"] == "test@example.com"
        print("✅ Retrieve contact")
        
        # Test getting all contacts
        contacts = contact_manager.get_all_contacts()
        assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
        print("✅ Get all contacts")
        
        return True
        
    except Exception as e:
        print(f"❌ ContactManager test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def test_message_processor():
    """Test MessageProcessor functionality."""
    print("🧪 Testing MessageProcessor...")
    
    from format_new import DatabaseManager, MessageProcessor, Message
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        db_manager = DatabaseManager(db_path)
        processor = MessageProcessor(db_manager)
        
        # Create test messages
        messages = [
            Message("Alice", "2024-01-01 10:00:00", "Hello!", "Alice", "test.txt"),
            Message("You", "2024-01-01 10:01:00", "Hi there!", "Alice", "test.txt"),
            Message("Bob", "2024-01-02 11:00:00", "How are you?", "Bob", "test.txt")
        ]
        
        # Test storing messages
        count = processor.store_messages(messages)
        assert count == 3, f"Expected to store 3 messages, stored {count}"
        print("✅ Store messages")
        
        # Test retrieving messages
        retrieved = processor.get_messages(["Alice"])
        assert len(retrieved) == 2, f"Expected 2 messages from Alice, got {len(retrieved)}"
        print("✅ Retrieve messages")
        
        # Test date filtering
        retrieved = processor.get_messages(["Alice"], start_date="2024-01-01", end_date="2024-01-01")
        assert len(retrieved) == 2, f"Expected 2 messages on 2024-01-01, got {len(retrieved)}"
        print("✅ Date filtering")
        
        return True
        
    except Exception as e:
        print(f"❌ MessageProcessor test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def test_export_manager():
    """Test ExportManager functionality."""
    print("🧪 Testing ExportManager...")
    
    from format_new import DatabaseManager, MessageProcessor, ExportManager, ExportConfig, Message
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        db_manager = DatabaseManager(db_path)
        processor = MessageProcessor(db_manager)
        export_manager = ExportManager(db_manager, processor)
        
        # Add test messages
        messages = [
            Message("Alice", "2024-01-01 10:00:00", "Hello!", "Alice", "test.txt"),
            Message("You", "2024-01-01 10:01:00", "Hi there!", "Alice", "test.txt")
        ]
        processor.store_messages(messages)
        
        # Test export configuration
        config = ExportConfig(
            contact_names=["Alice"],
            output_format="csv"
        )
        
        # Test export (this will create files)
        result = asyncio.run(export_manager.export_messages(config))
        assert result, "Export should succeed"
        print("✅ Export messages")
        
        return True
        
    except Exception as e:
        print(f"❌ ExportManager test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def test_imessage_db_reader():
    """Test IMessageDBReader functionality."""
    print("🧪 Testing IMessageDBReader...")
    
    from imessage_db_reader import IMessageDBReader, find_imessage_database
    
    # Test finding database (will be None in this environment)
    db_path = find_imessage_database()
    assert db_path is None, "Should not find iMessage database in this environment"
    print("✅ Database finder (expected no database)")
    
    # Test reader initialization
    try:
        reader = IMessageDBReader()
        print("✅ Reader initialization")
    except FileNotFoundError:
        print("✅ Reader correctly reports no database")
    
    return True

def test_gui_components():
    """Test GUI components without actually running the GUI."""
    print("🧪 Testing GUI components...")
    
    from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager
    from imessage_gui import IMessageExporterGUI
    import tkinter as tk
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Test GUI initialization (without showing window)
        root = tk.Tk()
        root.withdraw()  # Hide the window
        
        # Test that GUI components can be created
        db_manager = DatabaseManager(db_path)
        contact_manager = ContactManager(db_manager)
        processor = MessageProcessor(db_manager)
        export_manager = ExportManager(db_manager, processor)
        
        print("✅ GUI components initialization")
        
        # Test contact loading functionality
        contact_manager.save_contact("Test Contact", "+1234567890", "test@example.com")
        
        # Simulate contact loading (what the GUI does)
        with sqlite3.connect(db_path) as conn:
            cursor = conn.execute("SELECT name, phone, email FROM contacts ORDER BY name")
            contacts = cursor.fetchall()
        
        assert len(contacts) == 1, f"Expected 1 contact, got {len(contacts)}"
        print("✅ Contact loading simulation")
        
        root.destroy()
        return True
        
    except Exception as e:
        print(f"❌ GUI components test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def test_utils():
    """Test utility functions."""
    print("🧪 Testing utility functions...")
    
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

def test_constants():
    """Test constants and configuration."""
    print("🧪 Testing constants...")
    
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

def run_integration_test():
    """Run a full integration test."""
    print("🧪 Running integration test...")
    
    from format_new import DatabaseManager, ContactManager, MessageProcessor, ExportManager, ExportConfig, Message
    import asyncio
    
    # Create temporary database
    with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
        db_path = Path(tmp.name)
    
    try:
        # Initialize all components
        db_manager = DatabaseManager(db_path)
        contact_manager = ContactManager(db_manager)
        processor = MessageProcessor(db_manager)
        export_manager = ExportManager(db_manager, processor)
        
        # Add a contact
        contact_manager.save_contact("Test User", "+1234567890", "test@example.com")
        
        # Add some messages
        messages = [
            Message("Test User", "2024-01-01 10:00:00", "Hello!", "Test User", "test.txt"),
            Message("You", "2024-01-01 10:01:00", "Hi there!", "Test User", "test.txt"),
            Message("Test User", "2024-01-01 10:02:00", "How are you?", "Test User", "test.txt")
        ]
        processor.store_messages(messages)
        
        # Export messages
        config = ExportConfig(
            contact_names=["Test User"],
            output_format="both"
        )
        
        result = asyncio.run(export_manager.export_messages(config))
        assert result, "Integration test should succeed"
        print("✅ Full integration test")
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False
    finally:
        if db_path.exists():
            db_path.unlink()

def main():
    """Run all tests."""
    print("🧪 Running iMessage Exporter Test Suite")
    print("=" * 60)
    
    tests = [
        ("Database Manager", test_database_manager),
        ("Contact Manager", test_contact_manager),
        ("Message Processor", test_message_processor),
        ("Export Manager", test_export_manager),
        ("iMessage DB Reader", test_imessage_db_reader),
        ("GUI Components", test_gui_components),
        ("Utility Functions", test_utils),
        ("Constants", test_constants),
        ("Integration Test", run_integration_test),
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
    
    print("=" * 60)
    print(f"Test Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! The application is working correctly.")
        return 0
    else:
        print(f"❌ {total - passed} tests failed. Please check the errors above.")
        return 1

if __name__ == "__main__":
    sys.exit(main())