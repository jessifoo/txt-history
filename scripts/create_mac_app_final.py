#!/usr/bin/env python3
"""
Create a Mac .app bundle - this script should be run on a Mac.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_mac_app():
    """Create a Mac .app bundle using PyInstaller."""
    print("🍎 Creating Mac .app bundle...")
    
    # Use the existing packaged application
    packaged_dir = Path.home() / "iMessageExporter"
    if not packaged_dir.exists():
        print("❌ Packaged application not found. Please run package_app.py first.")
        return False
    
    # Create a Mac-specific launcher script
    launcher_script = packaged_dir / "launch_mac_app.py"
    launcher_content = '''#!/usr/bin/env python3
"""
Mac app launcher for iMessage Exporter.
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

# Set up the environment for Mac
os.environ['PYTHONPATH'] = str(scripts_dir)

try:
    # Import and run the GUI
    from imessage_gui import main
    main()
except ImportError as e:
    print(f"Error: Missing required modules. Please run install_dependencies.py first.")
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error running application: {e}")
    sys.exit(1)
'''
    
    launcher_script.write_text(launcher_content)
    launcher_script.chmod(0o755)
    
    # Create PyInstaller command for Mac
    cmd = [
        "pyinstaller",
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--name", "iMessage Exporter",
        "--add-data", f"{packaged_dir}/scripts:scripts",
        "--add-data", f"{packaged_dir}/data:data",
        "--hidden-import", "tkinter",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pandas",
        "--hidden-import", "pytz",
        "--hidden-import", "aiofiles",
        "--hidden-import", "asyncio",
        "--hidden-import", "pathlib",
        "--hidden-import", "datetime",
        "--hidden-import", "logging",
        str(launcher_script)
    ]
    
    print("Running PyInstaller...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, cwd=packaged_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller completed successfully")
            
            # Check if the .app was created
            app_path = packaged_dir / "dist" / "iMessage Exporter.app"
            if app_path.exists():
                print(f"✅ Mac app created: {app_path}")
                return True
            else:
                print("❌ .app bundle not found")
                print("PyInstaller output:", result.stdout)
                return False
        else:
            print(f"❌ PyInstaller failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running PyInstaller: {e}")
        return False

def create_mac_installer():
    """Create a Mac installer script."""
    packaged_dir = Path.home() / "iMessageExporter"
    installer_script = packaged_dir / "install_mac_app.sh"
    
    installer_content = f'''#!/bin/bash
# iMessage Exporter Mac App Installer

echo "🍎 Installing iMessage Exporter Mac App..."
echo "=========================================="

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only"
    exit 1
fi

# Check if the app exists
if [ ! -d "dist/iMessage Exporter.app" ]; then
    echo "❌ iMessage Exporter.app not found. Please run create_mac_app_final.py first."
    exit 1
fi

# Create Applications directory if it doesn't exist
mkdir -p ~/Applications

# Copy the app to Applications
echo "📦 Copying app to Applications folder..."
cp -R "dist/iMessage Exporter.app" ~/Applications/

# Make it executable
chmod +x ~/Applications/"iMessage Exporter.app"/Contents/MacOS/*

echo "✅ Installation complete!"
echo ""
echo "To run the app:"
echo "1. Open Finder"
echo "2. Go to Applications"
echo "3. Double-click 'iMessage Exporter'"
echo ""
echo "Or run from Terminal:"
echo "open ~/Applications/iMessage\\ Exporter.app"
echo ""
echo "Note: You may need to allow the app in System Preferences > Security & Privacy"
echo "The app will request access to your Messages database when you first run it."
'''
    
    installer_script.write_text(installer_content)
    installer_script.chmod(0o755)
    
    print(f"✅ Mac installer script created: {installer_script}")

def create_mac_readme():
    """Create a Mac-specific README."""
    packaged_dir = Path.home() / "iMessageExporter"
    readme_file = packaged_dir / "MAC_README.md"
    
    readme_content = '''# iMessage Exporter - Mac App

This is a Mac application for exporting your iMessage conversations.

## Quick Start

1. **Install Dependencies** (one time only):
   ```bash
   python3 install_dependencies.py
   ```

2. **Create Mac App**:
   ```bash
   python3 create_mac_app_final.py
   ```

3. **Install the App**:
   ```bash
   ./install_mac_app.sh
   ```

4. **Run the App**:
   - Open Finder
   - Go to Applications
   - Double-click "iMessage Exporter"

## Features

- ✅ **Direct iMessage Database Access** - No external tools required
- ✅ **Contact Management** - Add, edit, and manage your contacts
- ✅ **Date Filtering** - Export specific date ranges
- ✅ **Multiple Formats** - CSV, TXT, or both
- ✅ **Chunking Options** - Handle large exports efficiently
- ✅ **User-Friendly GUI** - No command line needed

## Requirements

- macOS (for iMessage access)
- Python 3.7+ (for building the app)
- PyInstaller (installed automatically)

## Troubleshooting

**If you get permission errors:**
- The app needs access to your Messages database at `~/Library/Messages/chat.db`
- Allow access when prompted by macOS

**If the app won't open:**
- Right-click the app and select "Open"
- Or run: `xattr -d com.apple.quarantine ~/Applications/iMessage\\ Exporter.app`

**If contacts aren't found:**
- Add your contacts in the "Manage Contacts" tab
- Make sure phone numbers are in the correct format

## Privacy & Safety

- ✅ Everything stays on your computer
- ✅ No data uploaded anywhere
- ✅ Only reads your Messages (can't send or delete)
- ✅ Uses Apple's official Messages database

---

*Made with ❤️ for easy iMessage history access*
'''
    
    readme_file.write_text(readme_content)
    print(f"✅ Mac README created: {readme_file}")

def main():
    """Main function."""
    print("🚀 Creating Mac .app bundle for iMessage Exporter")
    print("=" * 60)
    
    # Check if we're on macOS
    if sys.platform != "darwin":
        print("⚠️  Warning: This script is designed for macOS")
        print("   It will create the app structure, but PyInstaller may not work correctly on other platforms")
        print()
    
    # Create the Mac app
    if create_mac_app():
        # Create installer script
        create_mac_installer()
        
        # Create Mac-specific README
        create_mac_readme()
        
        print("=" * 60)
        print("🎉 Mac app creation completed successfully!")
        print()
        print("📁 Files created:")
        print("   - dist/iMessage Exporter.app (the Mac app)")
        print("   - install_mac_app.sh (installer script)")
        print("   - MAC_README.md (Mac-specific instructions)")
        print()
        print("📋 Next steps:")
        print("1. Copy the entire iMessageExporter folder to your Mac")
        print("2. Run: python3 install_dependencies.py")
        print("3. Run: python3 create_mac_app_final.py")
        print("4. Run: ./install_mac_app.sh")
        print("5. Double-click the app to run it!")
        return 0
    else:
        print("❌ Mac app creation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())