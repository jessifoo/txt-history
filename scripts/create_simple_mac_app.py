#!/usr/bin/env python3
"""
Create a simple Mac app using PyInstaller with the existing packaged files.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

def create_simple_mac_app():
    """Create a simple Mac app using the existing packaged files."""
    print("🍎 Creating simple Mac .app bundle...")
    
    # Use the existing packaged application
    packaged_dir = Path.home() / "iMessageExporter"
    if not packaged_dir.exists():
        print("❌ Packaged application not found. Please run package_app.py first.")
        return False
    
    # Create a simple launcher script that works on Mac
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
    
    # Create PyInstaller spec file
    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

block_cipher = None

a = Analysis(
    ['{launcher_script}'],
    pathex=['{packaged_dir}'],
    binaries=[],
    datas=[
        ('{packaged_dir}/scripts', 'scripts'),
        ('{packaged_dir}/data', 'data'),
    ],
    hiddenimports=[
        'tkinter',
        'sqlite3',
        'pandas',
        'pytz',
        'aiofiles',
        'asyncio',
        'pathlib',
        'datetime',
        'logging',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='iMessage Exporter',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
'''
    
    spec_file = packaged_dir / "iMessageExporter.spec"
    spec_file.write_text(spec_content)
    
    # Run PyInstaller
    print("Running PyInstaller...")
    pyinstaller_path = "/home/ubuntu/.local/bin/pyinstaller"
    cmd = [pyinstaller_path, "--clean", str(spec_file)]
    
    try:
        result = subprocess.run(cmd, cwd=packaged_dir, capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ PyInstaller completed successfully")
            
            # Check if the app was created
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
    echo "❌ iMessage Exporter.app not found. Please run create_simple_mac_app.py first."
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

def main():
    """Main function."""
    print("🚀 Creating Mac .app bundle for iMessage Exporter")
    print("=" * 60)
    
    # Create the Mac app
    if create_simple_mac_app():
        # Create installer script
        create_mac_installer()
        
        print("=" * 60)
        print("🎉 Mac app creation completed successfully!")
        print()
        print("📁 Files created:")
        print("   - dist/iMessage Exporter.app (the Mac app)")
        print("   - install_mac_app.sh (installer script)")
        print()
        print("📋 Next steps:")
        print("1. Copy the entire iMessageExporter folder to your Mac")
        print("2. Run: ./install_mac_app.sh")
        print("3. The app will be installed in ~/Applications")
        print("4. Double-click the app to run it!")
        return 0
    else:
        print("❌ Mac app creation failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())