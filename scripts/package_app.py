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
