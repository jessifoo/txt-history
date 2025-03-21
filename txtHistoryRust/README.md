# txt-history-rust

A Rust implementation of the txt-history message processor using the `imessage_database` crate and Diesel ORM.

## Overview

This application allows you to:

1. Import messages from your iMessage database into a local SQLite database
2. Query messages from the local database
3. Export messages in both TXT and CSV formats

The application maintains an immutable record of messages, ensuring that once a message is stored, it cannot be modified.

## Database Schema

The application uses a SQLite database with the following schema:

### Messages Table
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

## Usage

### Import Messages

```bash
cargo run -- import --name "Phil" --start-date "2023-01-01" --end-date "2023-12-31" --output-dir "output" --lines-per-chunk 500
```

Options:
- `--name`: Name of the contact (required)
- `--start-date`: Start date for message range (YYYY-MM-DD)
- `--end-date`: End date for message range (YYYY-MM-DD)
- `--output-dir`: Output directory for message files (default: "output")
- `--lines-per-chunk`: Maximum number of messages per chunk
- `--size-per-chunk`: Maximum size per chunk in MB

### Query Messages

```bash
cargo run -- query --name "Phil" --start-date "2023-01-01" --end-date "2023-12-31" --output-dir "output" --lines-per-chunk 500
```

Options are the same as for the import command.

## Output Format

The application generates two files for each chunk of messages:

1. `chunk_N.txt`: Plain text format with one message per line, separated by blank lines
2. `chunk_N.csv`: CSV format with columns for sender, timestamp, and content

Example TXT format:
```
Phil, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier

Jess, Jan 20, 2025 12:22:28 PM, When she's healthy, she doesn't wake up
```

## Dependencies

- `imessage_database`: For accessing the iMessage SQLite database
- `diesel`: ORM for database operations
- `chrono`: For date/time handling
- `clap`: For command-line argument parsing
- `tokio`: For async support
- `anyhow` and `thiserror`: For error handling

## Development

### Database Migrations

The application uses Diesel migrations to manage the database schema. The migrations are embedded in the application and run automatically when the application starts.

### Adding New Contacts

Contacts are currently hardcoded in the application. To add a new contact, update the `get_contact_info` function in `main.rs` and the `initialize` method in `db.rs`.

### Future Improvements

- Add support for attachments
- Implement a configuration file for contacts
- Add support for group chats
- Implement a web interface for browsing messages
