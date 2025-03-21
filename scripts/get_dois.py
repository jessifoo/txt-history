#!/usr/bin/env python3

"""
Script to extract DOIs from BibTeX format text, either from clipboard or file input.
Supports multiple BibTeX entries and provides a more user-friendly paste experience.
"""

import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

import pyperclip


def extract_dois(text):
    """Extract DOIs from text using regex pattern matching."""
    # DOI pattern: 10.xxxx/any.chars
    doi_pattern = r'(?:doi|DOI)?\s*[=:]\s*["{]?(10\.\d{4,}/[-._;()/:\w]+)["}]?'
    matches = re.finditer(doi_pattern, text)
    return [match.group(1) for match in matches]


def get_text_from_editor():
    """Open a temporary file in the default text editor for pasting multiple entries."""
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".bib", delete=False) as tf:
        tf.write("# Paste your BibTeX entries here and save the file\n\n")
        tf.flush()
        editor = os.environ.get("EDITOR", "nano")  # Default to nano if no EDITOR is set
        try:
            subprocess.call([editor, tf.name])
            with open(tf.name) as f:
                return f.read()
        finally:
            Path(tf.name).unlink()  # Clean up temporary file


def main() -> None:
    # If a file is provided as argument, read from it
    if len(sys.argv) > 1:
        input_file = Path(sys.argv[1])
        if not input_file.exists():
            sys.exit(1)
        text = input_file.read_text()
    else:
        # If no file provided, offer interactive input option
        choice = input("Enter choice (1/2): ").strip()

        if choice == "1":
            try:
                text = pyperclip.paste()
                if not text:
                    sys.exit(1)
            except Exception:
                sys.exit(1)
        elif choice == "2":
            text = get_text_from_editor()
            if not text or text.strip() == "# Paste your BibTeX entries here and save the file":
                sys.exit(1)
        else:
            sys.exit(1)

    dois = extract_dois(text)
    if not dois:
        sys.exit(0)

    for _doi in dois:
        pass

    # Copy DOIs to clipboard for convenience
    pyperclip.copy("\n".join(dois))


if __name__ == "__main__":
    main()
