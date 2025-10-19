# iMessage History Exporter - Setup Guide for Jessica

Hi Sis! Here's how to use the iMessage export tool I made for you. It's super easy - no scary terminal commands needed!

## What This Does

This app lets you:
- Export your text message conversations with specific people
- Save them as CSV or text files
- Filter by date (like "just the last year")
- Choose exactly which contacts you want

## Quick Setup (5 minutes)

### Step 1: Get the App
I already ran the packaging script, so you should have an `iMessageExporter` folder. If not, ask me and I'll send it to you.

### Step 2: Install Dependencies
1. Open Terminal (spotlight search for "Terminal")
2. Navigate to the iMessageExporter folder:
   ```bash
   cd ~/iMessageExporter
   ```
3. Run the installer:
   ```bash
   python3 install_dependencies.py
   ```

That's it! It will install a couple of Python packages automatically.

### Step 3: Run the App
```bash
python3 launch_gui.py
```

A friendly window will pop up with buttons and options!

## How to Use the App

### First Time Setup
1. Click on the **"Manage Contacts"** tab
2. Click **"Add Contact"**
3. Enter your contact's name (like "Mom" or "John Doe")
4. Enter their phone number (with country code if needed)
5. Click **"Save"**

### Exporting Messages
1. Go to the **"Export Messages"** tab
2. Select contacts from the list (hold Ctrl to select multiple)
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
python3 launch_cli.py --help
```

**Need to export a lot of messages?** Use chunking:
- By size: Split into 10MB files
- By count: Split every 1000 messages
- By date: Split every 30 days

That's it! The app is designed to be simple and safe. If you run into any issues, just let me know! 💕

---

*Made with ❤️ by your favorite developer sister*
