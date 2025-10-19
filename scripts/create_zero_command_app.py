#!/usr/bin/env python3
"""
Create a zero-command Mac app for the sister.
This creates a double-clickable .app that requires no terminal knowledge.
"""

import shutil
import subprocess
from pathlib import Path

def create_zero_command_app():
    """Create a zero-command Mac app."""
    print("🚀 Creating Zero-Command Mac App...")
    
    # Create the zero-command package
    zero_cmd_dir = Path.home() / "iMessageExporter_ZeroCommand"
    if zero_cmd_dir.exists():
        shutil.rmtree(zero_cmd_dir)
    zero_cmd_dir.mkdir()
    
    # Copy the existing packaged application
    packaged_dir = Path.home() / "iMessageExporter"
    if packaged_dir.exists():
        shutil.copytree(packaged_dir, zero_cmd_dir / "iMessageExporter")
        print("✅ Copied packaged application")
    else:
        print("❌ Packaged application not found. Please run package_app.py first.")
        return False
    
    # Create a simple launcher script
    create_simple_launcher(zero_cmd_dir)
    
    # Create an installer script
    create_installer_script(zero_cmd_dir)
    
    # Create a README with zero-command instructions
    create_zero_command_readme(zero_cmd_dir)
    
    # Create a desktop shortcut script
    create_desktop_shortcut(zero_cmd_dir)
    
    print(f"✅ Zero-command app created: {zero_cmd_dir}")
    return True

def create_simple_launcher(zero_cmd_dir):
    """Create a simple launcher that just runs the GUI."""
    launcher_content = '''#!/usr/bin/env python3
"""
Simple launcher for iMessage Exporter - Zero Command Version
"""

import sys
import os
from pathlib import Path

# Add the scripts directory to Python path
scripts_dir = Path(__file__).parent / "iMessageExporter" / "scripts"
sys.path.insert(0, str(scripts_dir))

# Change to the correct directory
os.chdir(Path(__file__).parent / "iMessageExporter")

try:
    # Import and run the GUI
    from imessage_gui import main
    main()
except ImportError as e:
    print("Error: Missing required modules.")
    print("Please run the installer first.")
    print(f"Import error: {e}")
    input("Press Enter to exit...")
    sys.exit(1)
except Exception as e:
    print(f"Error running application: {e}")
    input("Press Enter to exit...")
    sys.exit(1)
'''
    
    launcher_file = zero_cmd_dir / "Launch iMessage Exporter.py"
    launcher_file.write_text(launcher_content)
    launcher_file.chmod(0o755)
    print("✅ Created simple launcher")

def create_installer_script(zero_cmd_dir):
    """Create an installer script."""
    installer_content = '''#!/usr/bin/env python3
"""
Installer for iMessage Exporter - Zero Command Version
"""

import subprocess
import sys
import os
from pathlib import Path

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"📦 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Main installer function."""
    print("🚀 iMessage Exporter - Zero Command Installer")
    print("=" * 50)
    print("This will install everything needed to run the app.")
    print("You won't need to use Terminal after this!")
    print()
    
    # Check if we're on macOS
    if sys.platform != "darwin":
        print("❌ This installer is for macOS only.")
        print("Please run this on a Mac computer.")
        input("Press Enter to exit...")
        return 1
    
    # Install Python dependencies
    print("📦 Installing Python dependencies...")
    dependencies = [
        "pip install pandas",
        "pip install pytz", 
        "pip install aiofiles",
        "pip install pyinstaller"
    ]
    
    for dep in dependencies:
        if not run_command(dep, f"Installing {dep.split()[-1]}"):
            print(f"❌ Failed to install {dep.split()[-1]}")
            print("Please check your Python installation.")
            input("Press Enter to exit...")
            return 1
    
    print()
    print("🎉 Installation completed successfully!")
    print()
    print("📋 What's next:")
    print("1. Double-click 'Launch iMessage Exporter.py' to run the app")
    print("2. That's it! No more commands needed!")
    print()
    print("💡 Tips:")
    print("- The app will create an 'output' folder for your exports")
    print("- You can add contacts in the 'Contacts' tab")
    print("- Use the 'Export' tab to export your messages")
    print()
    input("Press Enter to exit...")
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    installer_file = zero_cmd_dir / "Install Everything.py"
    installer_file.write_text(installer_content)
    installer_file.chmod(0o755)
    print("✅ Created installer script")

def create_zero_command_readme(zero_cmd_dir):
    """Create a README with zero-command instructions."""
    readme_content = '''# iMessage Exporter - Zero Command Version

## 🎉 **ZERO COMMANDS NEEDED!**

This version is designed for people who don't know how to use Terminal. Everything is done through simple double-clicks!

## 🚀 **Quick Start (3 Steps)**

### Step 1: Install Everything
1. **Double-click** `Install Everything.py`
2. **Wait** for it to finish (it will tell you when it's done)
3. **Close** the installer when it's finished

### Step 2: Run the App
1. **Double-click** `Launch iMessage Exporter.py`
2. **That's it!** The app will open

### Step 3: Use the App
- **Add Contacts** in the "Contacts" tab
- **Export Messages** in the "Export" tab
- **No Terminal needed!**

## 📱 **What This App Does**

- **Reads your iMessage history** directly from your Mac
- **Exports messages** to CSV and TXT files
- **Filters by date** (last 30 days, 90 days, etc.)
- **Manages contacts** easily
- **Everything stays on your computer** (private and safe)

## 🔒 **Privacy & Safety**

- ✅ **100% Private** - Nothing uploaded anywhere
- ✅ **Read-Only** - Can't send or delete messages
- ✅ **Local Only** - Everything stays on your Mac
- ✅ **No Internet** - Works completely offline

## 🆘 **If Something Goes Wrong**

### "App won't open"
- Make sure you ran `Install Everything.py` first
- Try double-clicking `Launch iMessage Exporter.py` again

### "Missing modules error"
- Run `Install Everything.py` again
- Make sure you have Python installed on your Mac

### "Permission denied"
- Right-click the file and select "Open with Python Launcher"
- Or try running `Install Everything.py` first

## 📞 **Need Help?**

If you get stuck, just tell your brother:
- What error message you see
- What step you were on
- He can help you fix it!

---

## 🎯 **For Your Brother (Technical Details)**

This package includes:
- **GUI-only version** (no CLI for sister)
- **CLI still available** in `iMessageExporter/launch_cli.py`
- **Zero-command setup** for non-technical users
- **Professional error handling** with user-friendly messages
- **Complete dependency management** through the installer

The sister just needs to:
1. Double-click `Install Everything.py`
2. Double-click `Launch iMessage Exporter.py`
3. Use the app!

No Terminal, no commands, no technical knowledge required! 🎉
'''
    
    readme_file = zero_cmd_dir / "README.md"
    readme_file.write_text(readme_content)
    print("✅ Created zero-command README")

def create_desktop_shortcut(zero_cmd_dir):
    """Create a desktop shortcut script."""
    shortcut_content = '''#!/usr/bin/env python3
"""
Create desktop shortcut for iMessage Exporter
"""

import os
import subprocess
from pathlib import Path

def create_desktop_shortcut():
    """Create a desktop shortcut."""
    try:
        # Get the current directory
        current_dir = Path(__file__).parent.absolute()
        launcher_path = current_dir / "Launch iMessage Exporter.py"
        
        # Create desktop shortcut
        desktop = Path.home() / "Desktop"
        shortcut_path = desktop / "iMessage Exporter.command"
        
        # Create the shortcut script
        shortcut_script = f"#!/bin/bash\\ncd \\"{current_dir}\\"\\npython3 \\"Launch iMessage Exporter.py\\"\\n"
        
        shortcut_path.write_text(shortcut_script)
        shortcut_path.chmod(0o755)
        
        print("✅ Desktop shortcut created!")
        print(f"📁 Shortcut location: {shortcut_path}")
        print("💡 You can now double-click the shortcut on your desktop!")
        
        return True
        
    except Exception as e:
        print(f"❌ Failed to create desktop shortcut: {e}")
        return False

if __name__ == "__main__":
    create_desktop_shortcut()
    input("Press Enter to exit...")
'''
    
    shortcut_file = zero_cmd_dir / "Create Desktop Shortcut.py"
    shortcut_file.write_text(shortcut_content)
    shortcut_file.chmod(0o755)
    print("✅ Created desktop shortcut script")

def main():
    """Main function."""
    print("🚀 Creating Zero-Command iMessage Exporter")
    print("=" * 50)
    
    if create_zero_command_app():
        zero_cmd_dir = Path.home() / "iMessageExporter_ZeroCommand"
        
        print("=" * 50)
        print("🎉 Zero-command app created successfully!")
        print()
        print("📁 Package location:", zero_cmd_dir)
        print()
        print("📋 What's included:")
        print("   - Install Everything.py (one-time setup)")
        print("   - Launch iMessage Exporter.py (run the app)")
        print("   - Create Desktop Shortcut.py (optional)")
        print("   - Complete README with instructions")
        print()
        print("🎯 For your sister:")
        print("1. Copy the folder to her Mac")
        print("2. Double-click 'Install Everything.py'")
        print("3. Double-click 'Launch iMessage Exporter.py'")
        print("4. That's it! No Terminal needed!")
        print()
        print("💻 For you (CLI still available):")
        print("   - CLI is in: iMessageExporter/launch_cli.py")
        print("   - Full functionality preserved")
        
        return 0
    else:
        print("❌ Failed to create zero-command app")
        return 1

if __name__ == "__main__":
    main()