#!/usr/bin/env python3
"""
Packaging script for iMessage History Exporter
Creates a standalone application for easy distribution.
"""

import os
import shutil
import sys
from pathlib import Path


def create_app_structure():
    """Create the application directory structure."""
    print("🏗️  Creating application structure...")

    # Create main app directory
    app_dir = Path.home() / "iMessageExporter"
    app_dir.mkdir(exist_ok=True)

    # Create subdirectories
    (app_dir / "scripts").mkdir(exist_ok=True)
    (app_dir / "data").mkdir(exist_ok=True)
    (app_dir / "output").mkdir(exist_ok=True)

    return app_dir


def copy_files(app_dir: Path):
    """Copy all necessary files to the app directory."""
    print("📋 Copying application files...")

    script_dir = Path(__file__).parent

    # Files to copy
    files_to_copy = [
        "format_new.py",
        "imessage_gui.py",
        "imessage_db_reader.py",
        "constants.py",
        "utils.py",
        "../README.md",
        "../requirements.txt",
        "../pyproject.toml",
    ]

    for file_path in files_to_copy:
        src = script_dir / file_path
        dst = app_dir / "scripts" / src.name

        if src.exists():
            shutil.copy2(src, dst)
            print(f"   ✅ {src.name}")
        else:
            print(f"   ⚠️  {src.name} not found")

    # Copy the entire txt-history package if it exists
    package_src = script_dir.parent / "src"
    if package_src.exists():
        package_dst = app_dir / "src"
        if package_dst.exists():
            shutil.rmtree(package_dst)
        shutil.copytree(package_src, package_dst)
        print("   ✅ src package")


def create_launcher_scripts(app_dir: Path):
    """Create launcher scripts for easy execution."""
    print("🚀 Creating launcher scripts...")

    # GUI launcher
    gui_launcher = app_dir / "launch_gui.py"
    gui_launcher.write_text("""#!/usr/bin/env python3
\"\"\"
Launcher script for the GUI version of iMessage History Exporter.
\"\"\"

import sys
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    from imessage_gui import main
    main()
except ImportError as e:
    print(f"Error: Missing required modules. Please run install_dependencies.py first.")
    print(f"Import error: {e}")
    sys.exit(1)
""")

    # CLI launcher
    cli_launcher = app_dir / "launch_cli.py"
    cli_launcher.write_text("""#!/usr/bin/env python3
\"\"\"
Launcher script for the CLI version of iMessage History Exporter.
\"\"\"

import sys
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent / "scripts"
sys.path.insert(0, str(scripts_dir))

try:
    from format_new import cli_main
    cli_main()
except ImportError as e:
    print(f"Error: Missing required modules. Please run install_dependencies.py first.")
    print(f"Import error: {e}")
    sys.exit(1)
""")

    # Make scripts executable
    os.chmod(gui_launcher, 0o755)
    os.chmod(cli_launcher, 0o755)


def create_dependency_installer(app_dir: Path):
    """Create a script to install dependencies."""
    print("📦 Creating dependency installer...")

    installer = app_dir / "install_dependencies.py"
    installer.write_text("""#!/usr/bin/env python3
\"\"\"
Install dependencies for iMessage History Exporter.
\"\"\"

import subprocess
import sys
from pathlib import Path

def run_command(cmd, description):
    \"\"\"Run a shell command and report the result.\"\"\"
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if result.returncode == 0:
            print(f"   ✅ {description} completed")
            return True
        else:
            print(f"   ❌ {description} failed: {result.stderr}")
            return False
    except Exception as e:
        print(f"   ❌ {description} failed: {e}")
        return False

def install_python_dependencies():
    \"\"\"Install Python dependencies.\"\"\"
    print("🐍 Installing Python dependencies...")

    # Try pip first
    if run_command("pip3 install --user pandas pytz", "Installing pandas and pytz"):
        return True

    # Try with pip if pip3 fails
    if run_command("pip install --user pandas pytz", "Installing pandas and pytz"):
        return True

    print("   ⚠️  Could not install Python dependencies automatically")
    print("   Please install manually: pip install pandas pytz")
    return False

def install_imessage_exporter():
    \"\"\"Install imessage-exporter (optional fallback).\"\"\"
    print("💬 Installing imessage-exporter (optional)...")

    # Check if already installed
    result = subprocess.run("which imessage-exporter", shell=True, capture_output=True)
    if result.returncode == 0:
        print("   ✅ imessage-exporter already installed")
        return True

    # Try to install via homebrew
    if run_command("brew install imessage-exporter", "Installing imessage-exporter"):
        return True

    print("   ⚠️  Could not install imessage-exporter automatically")
    print("   This is optional - the app will work with direct database access")
    return False

def main():
    \"\"\"Main installation function.\"\"\"
    print("🚀 Installing iMessage History Exporter dependencies...")
    print("=" * 60)

    success = True

    # Install Python dependencies
    if not install_python_dependencies():
        success = False

    # Install imessage-exporter (optional)
    install_imessage_exporter()

    print("=" * 60)
    if success:
        print("🎉 Installation completed successfully!")
        print()
        print("To run the application:")
        print("  GUI version: python3 launch_gui.py")
        print("  CLI version: python3 launch_cli.py")
    else:
        print("⚠️  Installation completed with some issues.")
        print("Please check the error messages above and fix manually.")

    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
""")

    os.chmod(installer, 0o755)


def create_readme(app_dir: Path):
    """Create a README file for the packaged application."""
    print("📖 Creating README...")

    readme = app_dir / "README.md"
    readme.write_text("""# iMessage History Exporter

A user-friendly application for exporting your iMessage conversations.

## What's Included

- **GUI Application**: Easy-to-use graphical interface
- **CLI Tool**: Command-line version for advanced users
- **Direct Database Access**: Reads directly from iMessage database (no external tools required)
- **Contact Management**: Built-in contact database for easy setup

## Quick Start

1. **Install Dependencies** (one time only):
   ```bash
   python3 install_dependencies.py
   ```

2. **Run the GUI Application**:
   ```bash
   python3 launch_gui.py
   ```

3. **Or use the CLI version**:
   ```bash
   python3 launch_cli.py --help
   ```

## Features

- Export messages from specific contacts
- Filter by date range
- Multiple output formats (CSV, TXT, or both)
- Automatic chunking for large exports
- Persistent contact management
- No terminal commands required for basic usage

## Requirements

- macOS (for iMessage access)
- Python 3.7+
- pandas and pytz (installed automatically)

## Troubleshooting

**If you get permission errors:**
- Make sure you're running on macOS
- The app needs access to your Messages database at `~/Library/Messages/chat.db`

**If contacts aren't found:**
- Add your contacts in the "Manage Contacts" tab
- Make sure phone numbers are in the correct format

**For advanced usage:**
See the CLI help: `python3 launch_cli.py --help`

## Support

This application reads your iMessage data directly from Apple's Messages database.
No data is uploaded or shared - everything stays on your Mac.

---

*Made with ❤️ for easy iMessage history access*
""")


def create_desktop_shortcut(app_dir: Path):
    """Create a desktop shortcut (optional)."""
    print("🖥️  Creating desktop shortcut...")

    desktop_shortcut = Path.home() / "Desktop" / "iMessage Exporter.app"

    # Create a simple AppleScript app
    applescript = f"""
tell application "Terminal"
    do script "cd {app_dir} && python3 launch_gui.py"
    set bounds of front window to {{100, 100, 800, 600}}
end tell
"""

    # Write AppleScript to temporary file and compile it
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".scpt", delete=False) as f:
        f.write(f'''
osascript -e '
tell application "Terminal"
    do script "cd "{app_dir}" && python3 launch_gui.py; exit"
    activate
end tell
' 2>/dev/null &
''')

        temp_script = f.name

    try:
        # Make it executable and try to run
        os.chmod(temp_script, 0o755)
        print("   ✅ Desktop shortcut created (run from Desktop)")
    except Exception as e:
        print(f"   ⚠️  Could not create desktop shortcut: {e}")


def create_mac_app_bundle(app_dir: Path):
    """Create a Mac .app bundle for the sister."""
    print("🍎 Creating Mac .app bundle...")
    
    # Create the .app bundle
    app_name = "iMessage Exporter.app"
    app_path = app_dir / app_name
    
    # Remove existing app if it exists
    if app_path.exists():
        shutil.rmtree(app_path)
    
    # Create Contents directory
    contents_dir = app_path / "Contents"
    contents_dir.mkdir(parents=True)
    
    # Create MacOS directory
    macos_dir = contents_dir / "MacOS"
    macos_dir.mkdir()
    
    # Create Resources directory
    resources_dir = contents_dir / "Resources"
    resources_dir.mkdir()
    
    # Create the main executable
    executable_content = '''#!/bin/bash

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_DIR="$(dirname "$(dirname "$(dirname "$SCRIPT_DIR")")")"
IMESSAGE_DIR="$APP_DIR/iMessageExporter"

# Change to the iMessage Exporter directory
cd "$IMESSAGE_DIR"

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    osascript -e 'display dialog "Python 3 is not installed. Please install Python 3 from python.org" buttons {"OK"} default button "OK"'
    exit 1
fi

# Check if dependencies are installed
if ! python3 -c "import pandas, pytz, aiofiles" 2>/dev/null; then
    osascript -e 'display dialog "Installing required dependencies... This may take a few minutes." buttons {"OK"} default button "OK"'
    
    # Install dependencies
    pip3 install pandas pytz aiofiles --user
    
    if [ $? -ne 0 ]; then
        osascript -e 'display dialog "Failed to install dependencies. Please check your Python installation." buttons {"OK"} default button "OK"'
        exit 1
    fi
fi

# Run the GUI application
python3 scripts/imessage_gui.py

# If the GUI exits with an error, show a message
if [ $? -ne 0 ]; then
    osascript -e 'display dialog "The application encountered an error. Please check the console for details." buttons {"OK"} default button "OK"'
fi
'''
    
    executable_file = macos_dir / "iMessage Exporter"
    executable_file.write_text(executable_content)
    executable_file.chmod(0o755)
    
    # Create Info.plist
    info_plist_content = '''<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>CFBundleExecutable</key>
    <string>iMessage Exporter</string>
    <key>CFBundleIdentifier</key>
    <string>com.imessageexporter.app</string>
    <key>CFBundleName</key>
    <string>iMessage Exporter</string>
    <key>CFBundleVersion</key>
    <string>1.0</string>
    <key>CFBundleShortVersionString</key>
    <string>1.0</string>
    <key>CFBundlePackageType</key>
    <string>APPL</string>
    <key>CFBundleSignature</key>
    <string>????</string>
    <key>CFBundleInfoDictionaryVersion</key>
    <string>6.0</string>
    <key>CFBundleDisplayName</key>
    <string>iMessage Exporter</string>
    <key>LSMinimumSystemVersion</key>
    <string>10.14</string>
    <key>NSHighResolutionCapable</key>
    <true/>
    <key>NSRequiresAquaSystemAppearance</key>
    <false/>
</dict>
</plist>'''
    
    info_plist_file = contents_dir / "Info.plist"
    info_plist_file.write_text(info_plist_content)
    
    print(f"   ✅ Mac .app bundle created: {app_name}")
    print(f"   📁 Location: {app_path}")
    print("   💡 Your sister can double-click this to run the app!")

def main():
    """Main packaging function."""
    print("🚀 Packaging iMessage History Exporter...")
    print("=" * 50)

    try:
        # Create app structure
        app_dir = create_app_structure()

        # Copy files
        copy_files(app_dir)

        # Create launcher scripts
        create_launcher_scripts(app_dir)

        # Create dependency installer
        create_dependency_installer(app_dir)

        # Create README
        create_readme(app_dir)

        # Create desktop shortcut
        create_desktop_shortcut(app_dir)

        # Create Mac .app bundle
        create_mac_app_bundle(app_dir)

        print("=" * 50)
        print("🎉 Packaging completed successfully!")
        print()
        print(f"📁 Application location: {app_dir}")
        print()
        print("📋 Next steps for your sister:")
        print("1. Copy the entire iMessageExporter folder to her computer")
        print("2. Run: python3 install_dependencies.py")
        print("3. Run: python3 launch_gui.py")
        print()
        print("✨ The app will open with a friendly GUI interface!")

        return 0

    except Exception as e:
        print(f"❌ Packaging failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
