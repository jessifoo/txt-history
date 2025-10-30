-- Rollback composite indexes

DROP INDEX IF EXISTS idx_messages_sender_date;
DROP INDEX IF EXISTS idx_messages_sender_date_desc;
DROP INDEX IF EXISTS idx_contacts_name_is_me;
DROP INDEX IF EXISTS idx_messages_from_me_date;
DROP INDEX IF EXISTS idx_messages_contact_date;
DROP INDEX IF EXISTS idx_messages_handle_date;
