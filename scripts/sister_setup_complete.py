#!/usr/bin/env python3
"""
Complete setup script for your sister's Mac.
This creates everything she needs to run the iMessage Exporter app.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_sister_package():
    """Create a complete package for your sister."""
    print("👩‍💻 Creating complete package for your sister...")
    
    # Create sister package directory
    sister_dir = Path.home() / "iMessageExporter_ForSister"
    if sister_dir.exists():
        shutil.rmtree(sister_dir)
    sister_dir.mkdir()
    
    # Copy the existing packaged application
    packaged_dir = Path.home() / "iMessageExporter"
    if packaged_dir.exists():
        shutil.copytree(packaged_dir, sister_dir / "iMessageExporter")
        print("✅ Copied packaged application")
    else:
        print("❌ Packaged application not found. Please run package_app.py first.")
        return False
    
    # Create a simple setup script for Mac
    setup_script = sister_dir / "setup_for_mac.py"
    setup_content = '''#!/usr/bin/env python3
"""
Setup script for Mac - run this on your Mac to set up the iMessage Exporter app.
"""

import os
import subprocess
import sys
from pathlib import Path

def check_mac():
    """Check if we're running on macOS."""
    if sys.platform != "darwin":
        print("❌ This script is for macOS only")
        return False
    return True

def install_dependencies():
    """Install Python dependencies."""
    print("📦 Installing Python dependencies...")
    
    try:
        # Install required packages
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", 
                       "pandas", "pytz", "aiofiles"], check=True)
        print("✅ Dependencies installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install dependencies: {e}")
        return False

def install_pyinstaller():
    """Install PyInstaller for creating the Mac app."""
    print("🔧 Installing PyInstaller...")
    
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "--user", 
                       "pyinstaller"], check=True)
        print("✅ PyInstaller installed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install PyInstaller: {e}")
        return False

def create_mac_app():
    """Create the Mac .app bundle."""
    print("🍎 Creating Mac app...")
    
    try:
        # Run the Mac app creation script
        subprocess.run([sys.executable, "create_mac_app_final.py"], 
                      cwd="iMessageExporter", check=True)
        print("✅ Mac app created successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to create Mac app: {e}")
        return False

def install_app():
    """Install the app to Applications folder."""
    print("📱 Installing app to Applications...")
    
    try:
        subprocess.run(["./install_mac_app.sh"], cwd="iMessageExporter", check=True)
        print("✅ App installed to Applications folder")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Failed to install app: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 Setting up iMessage Exporter for Mac")
    print("=" * 50)
    
    if not check_mac():
        return 1
    
    # Change to the script directory
    script_dir = Path(__file__).parent
    os.chdir(script_dir)
    
    steps = [
        ("Installing dependencies", install_dependencies),
        ("Installing PyInstaller", install_pyinstaller),
        ("Creating Mac app", create_mac_app),
        ("Installing app", install_app),
    ]
    
    for step_name, step_func in steps:
        print(f"\\n{step_name}...")
        if not step_func():
            print(f"❌ {step_name} failed")
            return 1
        print(f"✅ {step_name} completed")
    
    print("\\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print()
    print("📱 Your iMessage Exporter app is now installed!")
    print("   Location: ~/Applications/iMessage Exporter.app")
    print()
    print("🚀 To run the app:")
    print("   1. Open Finder")
    print("   2. Go to Applications")
    print("   3. Double-click 'iMessage Exporter'")
    print()
    print("💡 Tips:")
    print("   - The app will ask for permission to access your Messages")
    print("   - Add your contacts in the 'Manage Contacts' tab first")
    print("   - Choose your export options and click 'Start Export'")
    print()
    print("🆘 Need help? Check the MAC_README.md file for detailed instructions")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
'''
    
    setup_script.write_text(setup_content)
    setup_script.chmod(0o755)
    
    # Create a simple README for your sister
    readme_file = sister_dir / "README_FOR_SISTER.md"
    readme_content = '''# iMessage Exporter - For Your Sister! 💕

Hi! I made this app for you so you can easily export your text messages without using scary terminal commands.

## What This Does

This app lets you:
- Export your text message conversations with specific people
- Save them as CSV or text files (great for Excel!)
- Filter by date (like "just the last year")
- Choose exactly which contacts you want
- All with a friendly, easy-to-use interface!

## Super Easy Setup (5 minutes)

### Step 1: Run the Setup Script
1. Open Terminal (spotlight search for "Terminal")
2. Navigate to this folder:
   ```bash
   cd ~/Downloads/iMessageExporter_ForSister
   ```
3. Run the setup script:
   ```bash
   python3 setup_for_mac.py
   ```

That's it! The script will:
- Install all the required software
- Create a Mac app for you
- Install it in your Applications folder

### Step 2: Run the App
1. Open Finder
2. Go to Applications
3. Double-click "iMessage Exporter"

## How to Use the App

### First Time Setup
1. Click on the **"Manage Contacts"** tab
2. Click **"Add Contact"**
3. Enter your contact's name (like "Mom" or "John Doe")
4. Enter their phone number (with country code if needed)
5. Click **"Save"**

### Exporting Messages
1. Go to the **"Export Messages"** tab
2. Select contacts from the list (hold Cmd to select multiple)
3. Choose date range (or leave blank for all time)
4. Pick your options:
   - **Format**: "both" for CSV and text files
   - **Mode**: "All messages" includes your replies
   - **Chunking**: Leave as "No chunking" unless you have tons of messages
5. Click **"Start Export"** 🚀

The app will show a progress window, then tell you where to find your files!

## Tips & Troubleshooting

**Contacts not showing up?**
- Make sure you added them in the "Manage Contacts" tab first
- Phone numbers should be in this format: `+1234567890` (with +1 for US numbers)

**Getting permission errors?**
- This is normal! The app reads directly from your Messages, which macOS protects
- Just click "Allow" when the security prompt appears

**Files not appearing?**
- Check the output folder location shown in the success message
- Look for folders with timestamps like `2024-01-15_14-30-45`

**Need help?**
- Check the status bar at the bottom for messages
- The app shows helpful error messages in popup windows
- If something's really wrong, take a screenshot and send it to me!

## What You Get

The app creates organized files:
- **CSV files**: Great for Excel or data analysis
- **TXT files**: Simple text format for reading
- **Organized by date**: Each export gets its own timestamped folder

Example output structure:
```
txt_history_output/
└── 2024-01-15_14-30-45/
    ├── Mom_2023-01-01_to_2024-01-15.csv
    ├── Mom_2023-01-01_to_2024-01-15.txt
    └── John_2023-01-01_to_2024-01-15.csv
```

## Privacy & Safety

- ✅ Everything stays on your computer
- ✅ No data uploaded anywhere
- ✅ Only reads your Messages (can't send or delete)
- ✅ Uses Apple's official Messages database

## Advanced Features

**Want more control?** Use the CLI version:
```bash
cd ~/Applications/iMessageExporter.app/Contents/MacOS
./iMessage\ Exporter --help
```

**Need to export a lot of messages?** Use chunking:
- By size: Split into 10MB files
- By count: Split every 1000 messages
- By date: Split every 30 days

That's it! The app is designed to be simple and safe. If you run into any issues, just let me know! 💕

---

*Made with ❤️ by your favorite developer sister*
'''
    
    readme_file.write_text(readme_content)
    
    # Create a simple launcher script
    launcher_script = sister_dir / "launch_app.py"
    launcher_content = '''#!/usr/bin/env python3
"""
Simple launcher for the iMessage Exporter app.
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
    print(f"Error: Missing required modules. Please run setup_for_mac.py first.")
    print(f"Import error: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error running application: {e}")
    sys.exit(1)
'''
    
    launcher_script.write_text(launcher_content)
    launcher_script.chmod(0o755)
    
    print(f"✅ Sister package created: {sister_dir}")
    return True

def main():
    """Main function."""
    print("👩‍💻 Creating complete package for your sister")
    print("=" * 60)
    
    if create_sister_package():
        sister_dir = Path.home() / "iMessageExporter_ForSister"
        
        print("=" * 60)
        print("🎉 Sister package created successfully!")
        print()
        print("📁 Package location:", sister_dir)
        print()
        print("📋 What's included:")
        print("   - Complete iMessage Exporter application")
        print("   - setup_for_mac.py (easy setup script)")
        print("   - README_FOR_SISTER.md (simple instructions)")
        print("   - launch_app.py (backup launcher)")
        print()
        print("📤 Next steps:")
        print("1. Copy the 'iMessageExporter_ForSister' folder to your sister's Mac")
        print("2. Have her run: python3 setup_for_mac.py")
        print("3. The app will be installed and ready to use!")
        print()
        print("💡 The setup script will:")
        print("   - Install all dependencies")
        print("   - Create a Mac .app bundle")
        print("   - Install it in Applications")
        print("   - Make it super easy to use!")
        
        return 0
    else:
        print("❌ Failed to create sister package")
        return 1

if __name__ == "__main__":
    sys.exit(main())