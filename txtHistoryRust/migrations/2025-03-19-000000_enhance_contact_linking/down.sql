-- Drop the indexes
DROP INDEX IF EXISTS idx_messages_contact_id;
DROP INDEX IF EXISTS idx_contacts_primary_identifier;

-- Remove the columns
ALTER TABLE messages DROP COLUMN contact_id;
ALTER TABLE contacts DROP COLUMN primary_identifier;
