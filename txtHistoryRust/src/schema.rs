// Schema definitions for database tables
// This file replaces the auto-generated diesel schema with rusqlite-compatible table definitions

// These constants represent table and column names for use with rusqlite
pub mod contacts {
    pub const TABLE: &str = "contacts";
    pub const ID: &str = "id";
    pub const NAME: &str = "name";
    pub const PHONE: &str = "phone";
    pub const EMAIL: &str = "email";
    pub const IS_ME: &str = "is_me";
}

pub mod messages {
    pub const TABLE: &str = "messages";
    pub const ID: &str = "id";
    pub const IMESSAGE_ID: &str = "imessage_id";
    pub const TEXT: &str = "text";
    pub const SENDER: &str = "sender";
    pub const IS_FROM_ME: &str = "is_from_me";
    pub const DATE_CREATED: &str = "date_created";
    pub const DATE_IMPORTED: &str = "date_imported";
    pub const HANDLE_ID: &str = "handle_id";
    pub const SERVICE: &str = "service";
    pub const THREAD_ID: &str = "thread_id";
    pub const HAS_ATTACHMENTS: &str = "has_attachments";
}

pub mod attachments {
    pub const TABLE: &str = "attachments";
    pub const ID: &str = "id";
    pub const MESSAGE_ID: &str = "message_id";
    pub const FILENAME: &str = "filename";
    pub const MIME_TYPE: &str = "mime_type";
    pub const SIZE_BYTES: &str = "size_bytes";
    pub const CREATED_AT: &str = "created_at";
}

pub mod processed_messages {
    pub const TABLE: &str = "processed_messages";
    pub const ID: &str = "id";
    pub const ORIGINAL_MESSAGE_ID: &str = "original_message_id";
    pub const PROCESSED_TEXT: &str = "processed_text";
    pub const TOKENS: &str = "tokens";
    pub const LEMMATIZED_TEXT: &str = "lemmatized_text";
    pub const NAMED_ENTITIES: &str = "named_entities";
    pub const SENTIMENT_SCORE: &str = "sentiment_score";
    pub const PROCESSED_AT: &str = "processed_at";
    pub const PROCESSING_VERSION: &str = "processing_version";
}
