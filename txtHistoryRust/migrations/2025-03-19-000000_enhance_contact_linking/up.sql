-- Add contact_id to messages table to link messages to contacts (if not exists)
ALTER TABLE messages ADD COLUMN contact_id INTEGER;

-- Create foreign key constraint
CREATE INDEX IF NOT EXISTS idx_messages_contact_id ON messages(contact_id);

-- Add primary_identifier to contacts table to help identify the same person across different methods
ALTER TABLE contacts ADD COLUMN primary_identifier TEXT;
CREATE INDEX IF NOT EXISTS idx_contacts_primary_identifier ON contacts(primary_identifier);
