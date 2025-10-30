-- Create messages table
CREATE TABLE IF NOT EXISTS messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    imessage_id TEXT NOT NULL UNIQUE,
    text TEXT,
    sender TEXT NOT NULL,
    is_from_me BOOLEAN NOT NULL,
    date_created TIMESTAMP NOT NULL,
    date_imported TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    handle_id TEXT,
    service TEXT,
    thread_id TEXT,
    has_attachments BOOLEAN NOT NULL DEFAULT false
);

-- Create indexes for messages table
CREATE INDEX IF NOT EXISTS idx_messages_date ON messages(date_created);
CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender);
CREATE INDEX IF NOT EXISTS idx_messages_handle ON messages(handle_id);
CREATE INDEX IF NOT EXISTS idx_messages_imessage_id ON messages(imessage_id);

-- Create contacts table
CREATE TABLE IF NOT EXISTS contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    phone TEXT,
    email TEXT,
    is_me BOOLEAN NOT NULL DEFAULT false,
    UNIQUE(name)
);

-- Create indexes for contacts table
CREATE INDEX IF NOT EXISTS idx_contacts_phone ON contacts(phone);
CREATE INDEX IF NOT EXISTS idx_contacts_email ON contacts(email);

-- Create attachments table
CREATE TABLE IF NOT EXISTS attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    filename TEXT,
    mime_type TEXT,
    size_bytes INTEGER,
    created_at TIMESTAMP NOT NULL,
    FOREIGN KEY(message_id) REFERENCES messages(id)
);

-- Create index for attachments table
CREATE INDEX IF NOT EXISTS idx_attachments_message ON attachments(message_id);
