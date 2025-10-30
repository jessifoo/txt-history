//! Database schema definitions
//!
//! This module provides constants for table and column names used with rusqlite.
//! It replaces auto-generated diesel schema with rusqlite-compatible definitions.

/// Contacts table schema
pub mod contacts {
    /// Table name
    pub const TABLE: &str = "contacts";
    /// Primary key column
    pub const ID: &str = "id";
    /// Contact name column
    pub const NAME: &str = "name";
    /// Phone number column
    pub const PHONE: &str = "phone";
    /// Email address column
    pub const EMAIL: &str = "email";
    /// Flag indicating if this is the current user
    pub const IS_ME: &str = "is_me";
}

/// Messages table schema
pub mod messages {
    /// Table name
    pub const TABLE: &str = "messages";
    /// Primary key column
    pub const ID: &str = "id";
    /// iMessage unique identifier column
    pub const IMESSAGE_ID: &str = "imessage_id";
    /// Message text content column
    pub const TEXT: &str = "text";
    /// Sender name column
    pub const SENDER: &str = "sender";
    /// Flag indicating if message is from current user
    pub const IS_FROM_ME: &str = "is_from_me";
    /// Message creation timestamp column
    pub const DATE_CREATED: &str = "date_created";
    /// Message import timestamp column
    pub const DATE_IMPORTED: &str = "date_imported";
    /// Handle identifier column
    pub const HANDLE_ID: &str = "handle_id";
    /// Service type column (iMessage, SMS, etc.)
    pub const SERVICE: &str = "service";
    /// Thread identifier column
    pub const THREAD_ID: &str = "thread_id";
    /// Flag indicating if message has attachments
    pub const HAS_ATTACHMENTS: &str = "has_attachments";
}

/// Attachments table schema
pub mod attachments {
    /// Table name
    pub const TABLE: &str = "attachments";
    /// Primary key column
    pub const ID: &str = "id";
    /// Foreign key to messages table
    pub const MESSAGE_ID: &str = "message_id";
    /// Attachment filename column
    pub const FILENAME: &str = "filename";
    /// MIME type column
    pub const MIME_TYPE: &str = "mime_type";
    /// File size in bytes column
    pub const SIZE_BYTES: &str = "size_bytes";
    /// Creation timestamp column
    pub const CREATED_AT: &str = "created_at";
}

/// Processed messages table schema
pub mod processed_messages {
    /// Table name
    pub const TABLE: &str = "processed_messages";
    /// Primary key column
    pub const ID: &str = "id";
    /// Foreign key to messages table
    pub const ORIGINAL_MESSAGE_ID: &str = "original_message_id";
    /// Processed text content column
    pub const PROCESSED_TEXT: &str = "processed_text";
    /// Tokenized text column
    pub const TOKENS: &str = "tokens";
    /// Lemmatized text column
    pub const LEMMATIZED_TEXT: &str = "lemmatized_text";
    /// Named entities JSON column
    pub const NAMED_ENTITIES: &str = "named_entities";
    /// Sentiment score column
    pub const SENTIMENT_SCORE: &str = "sentiment_score";
    /// Processing timestamp column
    pub const PROCESSED_AT: &str = "processed_at";
    /// Processing version identifier column
    pub const PROCESSING_VERSION: &str = "processing_version";
}
