# txt-history-rust

A Rust implementation of the txt-history message processor using the `imessage_database` crate and SQLite database for message storage, analysis, and export.

## Overview

This application allows you to:

1. Import messages from your iMessage database into a local SQLite database (source of truth)
2. Pre-process messages using NLP techniques and store them in a separate table
3. Query and analyze messages using various filters and processing techniques
4. Export messages in TXT, CSV, and JSON formats for further analysis

The application maintains an immutable record of original messages and provides a flexible framework for processing and analyzing message content.

## Architecture

The application follows a multi-layered architecture:

1. **Data Acquisition Layer**: Extracts messages from iMessage database using the `imessage_database` crate
2. **Storage Layer**: Stores messages in SQLite tables using direct SQL (without ORM)
3. **Processing Layer**: Applies NLP techniques to messages and stores results
4. **Export Layer**: Formats and exports messages in various formats

## Database Schema

The application uses a SQLite database with the following schema:

### Messages Table (Source of Truth)
- `id`: Primary key
- `imessage_id`: Original ID from iMessage (unique)
- `text`: Message content
- `sender`: Sender name (normalized)
- `is_from_me`: Flag for messages sent by you
- `date_created`: Original timestamp from iMessage
- `date_imported`: Timestamp when the message was imported
- `handle_id`: Original handle ID (phone/email)
- `service`: Service type (iMessage, SMS, etc.)
- `thread_id`: Original thread ID
- `has_attachments`: Flag indicating if the message has attachments
- `contact_id`: Foreign key to contacts table

### Processed Messages Table
- `id`: Primary key
- `original_message_id`: Foreign key to messages table
- `processed_text`: Cleaned and normalized text
- `tokens`: Tokenized text (words)
- `lemmatized_text`: Stemmed/lemmatized text
- `named_entities`: JSON array of extracted entities
- `sentiment_score`: Calculated sentiment (-1.0 to 1.0)
- `processed_at`: Timestamp of processing
- `processing_version`: Version of processing algorithm used

### Contacts Table
- `id`: Primary key
- `name`: Contact name (unique)
- `phone`: Phone number (optional)
- `email`: Email address (optional)
- `is_me`: Flag for your own contact

### Attachments Table
- `id`: Primary key
- `message_id`: Foreign key to messages table
- `filename`: Attachment filename
- `mime_type`: MIME type of the attachment
- `size_bytes`: Size of the attachment in bytes
- `created_at`: Timestamp when the attachment was created

## NLP Processing Features

The application includes several NLP processing capabilities:

1. **Text Cleaning**: Remove URLs, emojis, and normalize whitespace
2. **Tokenization**: Split text into meaningful tokens
3. **Lemmatization/Stemming**: Reduce words to their base forms
4. **Named Entity Recognition**: Identify people, places, organizations (simplified implementation)
5. **Sentiment Analysis**: Calculate sentiment scores for messages
6. **Language Detection**: Identify the language of messages

## Usage

### Import Messages (to Source of Truth)

```bash
cargo run -- import --name "Phil" --start-date "2023-01-01" --end-date "2023-12-31"
```

Options:
- `--name`: Name of the contact (required)
- `--start-date`: Start date for message range (YYYY-MM-DD)
- `--end-date`: End date for message range (YYYY-MM-DD)

### Process Messages

```bash
cargo run -- process --version "v1" --name "Phil"
```

Options:
- `--version`: Processing version identifier (for tracking different processing methods)
- `--name`: Name of the contact (optional, processes all contacts if omitted)
- `--unprocessed-only`: Only process messages that haven't been processed with this version

### Export Messages

```bash
cargo run -- export --name "Phil" --format txt,csv --output-dir "output" --lines-per-chunk 500
```

Options:
- `--name`: Name of the contact (required)
- `--format`: Output formats (comma-separated: txt,csv,json)
- `--output-dir`: Output directory for message files (default: "output")
- `--lines-per-chunk`: Maximum number of messages per chunk
- `--size-per-chunk`: Maximum size per chunk in MB
- `--processed`: Export processed messages instead of original

### Analyze Messages

```bash
cargo run -- analyze --name "Phil" --metric sentiment --output-file "sentiment_analysis.json"
```

Options:
- `--name`: Name of the contact (required)
- `--metric`: Analysis metric (sentiment, entities, language)
- `--output-file`: Output file for analysis results

## Output Format

The application generates files for each chunk of messages in the requested formats:

1. `chunk_N.txt`: Plain text format with one message per line, separated by blank lines
2. `chunk_N.csv`: CSV format with columns for sender, timestamp, and content
3. `chunk_N.json`: JSON format with full message details

Example TXT format:
```
Phil, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier

Jess, Jan 20, 2025 12:22:28 PM, When she's healthy, she doesn't wake up
```

## Dependencies

- `imessage_database`: For accessing the iMessage SQLite database
- `rusqlite`: For SQLite database operations
- `r2d2`: For connection pooling
- `chrono`: For date/time handling
- `clap`: For command-line argument parsing
- `serde` and `serde_json`: For JSON serialization/deserialization
- `regex`: For text processing
- `rust_stemmers`: For word stemming
- `stop_words`: For filtering common words
- `whatlang`: For language detection
- `unicode_normalization`: For text normalization
- `anyhow` and `thiserror`: For error handling

## Development

### Database Migrations

The application uses embedded SQL migrations to manage the database schema. The migrations are run automatically when the application starts.

### Adding New Contacts

Contacts are defined in the `db.rs` file. To add a new contact, update the `initialize` method.

### Future Improvements

- Implement chunking by conversation threads
- Add support for attachments
- Add more sophisticated NLP processing techniques
- Create a web interface for browsing and analyzing messages
- Support for exporting to pandas DataFrames
- Integration with machine learning pipelines
- Support for group chats
- Visualization of message patterns and sentiment over time
