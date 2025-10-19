#!/usr/bin/env python3
"""
Create a Mac .app bundle using PyInstaller.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_mac_app():
    """Create a Mac .app bundle."""
    print("🍎 Creating Mac .app bundle...")
    
    # Get the scripts directory
    scripts_dir = Path(__file__).parent
    
    # Create a temporary directory for the build
    build_dir = scripts_dir / "build"
    dist_dir = scripts_dir / "dist"
    
    # Clean up previous builds
    if build_dir.exists():
        shutil.rmtree(build_dir)
    if dist_dir.exists():
        shutil.rmtree(dist_dir)
    
    # Create the PyInstaller command
    cmd = [
        "pyinstaller",
        "--windowed",  # No console window
        "--onefile",   # Single executable
        "--name", "iMessage Exporter",
        "--icon", "icon.icns",  # We'll create a simple icon
        "--add-data", f"{scripts_dir / 'constants.py'}:.",
        "--add-data", f"{scripts_dir / 'utils.py'}:.",
        "--add-data", f"{scripts_dir / 'imessage_db_reader.py'}:.",
        "--add-data", f"{scripts_dir / 'format_new.py'}:.",
        "--hidden-import", "tkinter",
        "--hidden-import", "sqlite3",
        "--hidden-import", "pandas",
        "--hidden-import", "pytz",
        "--hidden-import", "aiofiles",
        "--hidden-import", "asyncio",
        str(scripts_dir / "imessage_gui.py")
    ]
    
    print("Running PyInstaller...")
    print("Command:", " ".join(cmd))
    
    try:
        result = subprocess.run(cmd, cwd=scripts_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller completed successfully")
            
            # Check if the .app was created
            app_path = dist_dir / "iMessage Exporter.app"
            if app_path.exists():
                print(f"✅ Mac app created: {app_path}")
                
                # Create a simple installer script
                create_installer_script(app_path)
                
                return True
            else:
                print("❌ .app bundle not found")
                return False
        else:
            print(f"❌ PyInstaller failed: {result.stderr}")
            return False
            
    except Exception as e:
        print(f"❌ Error running PyInstaller: {e}")
        return False

def create_installer_script(app_path):
    """Create an installer script for the Mac app."""
    installer_script = app_path.parent / "install_mac_app.sh"
    
    installer_content = f"""#!/bin/bash
# iMessage Exporter Mac App Installer

echo "🍎 Installing iMessage Exporter Mac App..."
echo "=========================================="

# Check if we're on macOS
if [[ "$OSTYPE" != "darwin"* ]]; then
    echo "❌ This installer is for macOS only"
    exit 1
fi

# Create Applications directory if it doesn't exist
mkdir -p ~/Applications

# Copy the app to Applications
echo "📦 Copying app to Applications folder..."
cp -R "iMessage Exporter.app" ~/Applications/

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
"""
    
    installer_script.write_text(installer_content)
    installer_script.chmod(0o755)
    
    print(f"✅ Installer script created: {installer_script}")

def create_simple_icon():
    """Create a simple icon for the app."""
    # For now, we'll skip the icon creation since it requires additional tools
    # In a real scenario, you'd create a proper .icns file
    print("ℹ️  Skipping icon creation (would need additional tools)")

def main():
    """Main function."""
    print("🚀 Creating Mac .app bundle for iMessage Exporter")
    print("=" * 60)
    
    # Create a simple icon placeholder
    create_simple_icon()
    
    # Create the Mac app
    if create_mac_app():
        print("=" * 60)
        print("🎉 Mac app creation completed successfully!")
        print()
        print("📁 Files created:")
        print("   - dist/iMessage Exporter.app (the Mac app)")
        print("   - dist/install_mac_app.sh (installer script)")
        print()
        print("📋 Next steps:")
        print("1. Copy the 'dist' folder to your Mac")
        print("2. Run: ./install_mac_app.sh")
        print("3. The app will be installed in ~/Applications")
        return 0
    else:
        print("❌ Mac app creation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())