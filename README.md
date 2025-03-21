# Message History Formatter

This tool formats iMessage history into CSV and TXT files with specific formatting.

## Usage
```
cd ~/projects/cascade/CascadeProjects/txt-history
poetry install
poetry run format (args)
```

The output will look exactly like this (for the txt files, csv has no line between rows):
```
Jess, Jan 21, 2025 10:12:59 PM, I'm stuck on the toilet from trying to eat. I can't go to her if she wakes up. OMG this is the worst

Phil, Jan 21, 2025 10:14:26 PM, I got it, I'm keeping an eye on the monitor

Jess, Jan 21, 2025 10:15:29 PM, Was there a bag of clothes left on the porch?
```

## Options

- `-l`: num lines (this or chunk size, not both)
- `-s`: Maximum file size in MB for chunks (default: 5.0)
- `-d`: Start date in YYYY-MM-DD format
- `-e`: End date in YYYY-MM-DD format
- `-n`: Name to use for messages sent by the user (default: "Phil")

## Quickstart

Simply run:
```bash
cd ~/projects/cascade/CascadeProjects/txt-history
poetry install
poetry run format (args)
```

## Development Guidelines

When contributing to this project, please use the following template for your code requests:

```markdown
# Code Request

1. Documentation: [Reference relevant sections of this README]

2. Current Task:
   - What needs to be done?
   - Why is it needed?

3. Key Requirements:
   - Must have: [critical features]
   - Must not: [things to avoid/preserve]

4. Example: [if applicable, show sample input/output]

Additional Context: [only if something isn't covered in the README]
```

### Critical Requirements

1. **Interface Preservation**
   - CLI interface must remain consistent
   - Output format must match the example above exactly
   - Privacy handling (phone number protection) must be maintained

2. **Core Functionality**
   - iMessage exporter integration must not be modified
   - Virtual environment handling must be preserved
   - never change folder output structure:
        datetime_full/chunks_csv/chunk_1.csv, etc.
        datetime_full/chunks_txt/chunk_1.txt, etc.
   - Both CSV and TXT outputs must be generated

3. **Data Privacy**
   - Never modify or expose phone numbers
   - Always replace user's number with "Jess", default is always "Phil"
   - Maintain message privacy and security

4. **Performance**
   - Optimize for efficient processing
   - Handle large message histories gracefully
   - Clean up resources after execution