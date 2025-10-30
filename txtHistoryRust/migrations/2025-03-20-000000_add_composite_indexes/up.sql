-- Add composite indexes for common query patterns
-- These optimize multi-condition queries that filter by multiple columns

-- Composite index for querying messages by sender and date
-- Used heavily in: get_messages(), get_messages_by_contact_name()
CREATE INDEX IF NOT EXISTS idx_messages_sender_date ON messages(sender, date_created);

-- Composite index for querying messages by sender and date (reverse for descending queries)
CREATE INDEX IF NOT EXISTS idx_messages_sender_date_desc ON messages(sender, date_created DESC);

-- Composite index for querying contacts by name and is_me flag
-- Used in: add_or_update_contact(), ensure_contact()
CREATE INDEX IF NOT EXISTS idx_contacts_name_is_me ON contacts(name, is_me);

-- Composite index for filtering messages by from_me status and date
-- Useful for export operations that filter by sender type
CREATE INDEX IF NOT EXISTS idx_messages_from_me_date ON messages(is_from_me, date_created);

-- Add chat_id composite index for iMessage queries (if contact_id column exists)
-- This assumes the enhance_contact_linking migration has run
CREATE INDEX IF NOT EXISTS idx_messages_contact_date ON messages(contact_id, date_created) WHERE contact_id IS NOT NULL;

-- Composite index for handle queries (if present in iMessage database integration)
CREATE INDEX IF NOT EXISTS idx_messages_handle_date ON messages(handle_id, date_created) WHERE handle_id IS NOT NULL;
