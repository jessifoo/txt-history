//! Data models for message handling and storage
//!
//! This module contains all data structures used throughout the application,
//! including messages, contacts, and database models.

use chrono::{DateTime, Local, NaiveDateTime, TimeZone};
use serde::{Deserialize, Serialize};

/// A message with sender, timestamp, and content
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    /// Name of the message sender
    pub sender: String,
    /// Timestamp when the message was sent
    pub timestamp: DateTime<Local>,
    /// Message text content
    pub content: String,
}

/// Contact information for a person
#[derive(Debug, Clone)]
pub struct Contact {
    /// Contact's display name
    pub name: String,
    /// Contact's phone number (optional)
    pub phone: Option<String>,
    /// Contact's primary email address (optional)
    pub email: Option<String>,
    /// List of all email addresses for this contact
    pub emails: Vec<String>,
}

impl Contact {
    /// Get the contact identifiers for iMessage export filter
    ///
    /// Returns a comma-separated string of phone and emails
    #[must_use]
    pub fn get_identifiers(&self) -> String {
        let mut identifiers = Vec::new();

        if let Some(phone) = &self.phone {
            identifiers.push(phone.clone());
        }

        for email in &self.emails {
            identifiers.push(email.clone());
        }

        identifiers.join(",")
    }
}

/// Date range for filtering messages
#[derive(Debug)]
pub struct DateRange {
    /// Start date (inclusive, optional)
    pub start: Option<DateTime<Local>>,
    /// End date (inclusive, optional)
    pub end: Option<DateTime<Local>>,
}

/// Output format for exported messages
#[derive(Debug, Clone, Copy)]
pub enum OutputFormat {
    /// Comma-separated values format
    Csv,
    /// Plain text format
    Txt,
    /// JSON format
    Json,
}

impl OutputFormat {
    /// Get the file extension for this format
    #[must_use]
    pub const fn extension(&self) -> &'static str {
        match self {
            Self::Csv => "csv",
            Self::Txt => "txt",
            Self::Json => "json",
        }
    }
}

/// Metadata about a message chunk
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkMetadata {
    /// Chunk sequence number
    pub chunk_number: usize,
    /// Number of messages in this chunk
    pub message_count: usize,
    /// Timestamp of first message in chunk
    pub start_date: DateTime<Local>,
    /// Timestamp of last message in chunk
    pub end_date: DateTime<Local>,
}

/// Database representation of a message
#[derive(Debug, Clone)]
pub struct DbMessage {
    /// Database primary key
    pub id: i32,
    /// iMessage unique identifier
    pub imessage_id: String,
    /// Message text content
    pub text: Option<String>,
    /// Sender name
    pub sender: String,
    /// True if message was sent by current user
    pub is_from_me: bool,
    /// Timestamp when message was created
    pub date_created: NaiveDateTime,
    /// Timestamp when message was imported
    pub date_imported: NaiveDateTime,
    /// Handle identifier for the sender
    pub handle_id: Option<String>,
    /// Service used (iMessage, SMS, etc.)
    pub service: Option<String>,
    /// Thread identifier for grouped messages
    pub thread_id: Option<String>,
    /// True if message has attachments
    pub has_attachments: bool,
    /// Foreign key to contacts table
    pub contact_id: Option<i32>,
}

/// NLP analysis results for a message
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NlpAnalysis {
    /// Tokenized words from the message
    pub tokens: Vec<String>,
    /// Named entities found in the message
    pub entities: Vec<NamedEntity>,
    /// Sentiment score (-1.0 to 1.0, if available)
    pub sentiment_score: Option<f32>,
    /// Detected language code
    pub language: Option<String>,
    /// Cleaned and normalized text
    pub processed_text: String,
    /// Lemmatized version of the text
    pub lemmatized_text: Option<String>,
}

/// A named entity extracted from text
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NamedEntity {
    /// The entity text as it appears in the message
    pub text: String,
    /// Type of entity (PERSON, LOCATION, ORGANIZATION, etc.)
    pub entity_type: String,
    /// Character offset where entity starts
    pub start: usize,
    /// Character offset where entity ends
    pub end: usize,
}

impl NlpAnalysis {
    /// Convert NLP analysis to a database record
    #[must_use]
    pub fn to_new_processed_message(&self, message_id: i32, version: &str) -> NewProcessedMessage {
        NewProcessedMessage {
            original_message_id: message_id,
            processed_text: self.processed_text.clone(),
            tokens: Some(self.tokens.join(" ")),
            lemmatized_text: self.lemmatized_text.clone(),
            named_entities: Some(serde_json::to_string(&self.entities).unwrap_or_default()),
            sentiment_score: self.sentiment_score,
            processing_version: version.to_string(),
        }
    }
}

impl DbMessage {
    /// Convert database message to application message format
    #[must_use]
    pub fn to_message(&self) -> Message {
        Message {
            sender: self.sender.clone(),
            timestamp: Local.from_utc_datetime(&self.date_created),
            content: self.text.clone().unwrap_or_default(),
        }
    }
}

/// Database representation of a contact
#[derive(Debug, Clone)]
pub struct DbContact {
    /// Database primary key
    pub id: i32,
    /// Contact's display name
    pub name: String,
    /// Contact's phone number
    pub phone: Option<String>,
    /// Contact's email address
    pub email: Option<String>,
    /// True if this contact represents the current user
    pub is_me: bool,
}

/// Database representation of a processed message
#[derive(Debug, Clone)]
pub struct DbProcessedMessage {
    /// Database primary key
    pub id: i32,
    /// Foreign key to original message
    pub original_message_id: i32,
    /// Cleaned and normalized text
    pub processed_text: String,
    /// Space-separated tokens
    pub tokens: Option<String>,
    /// Lemmatized version of text
    pub lemmatized_text: Option<String>,
    /// JSON-encoded named entities
    pub named_entities: Option<String>,
    /// Sentiment score (-1.0 to 1.0)
    pub sentiment_score: Option<f32>,
    /// Timestamp when processing occurred
    pub processed_at: NaiveDateTime,
    /// Processing version identifier
    pub processing_version: String,
}

/// Data for creating a new contact
#[derive(Debug, Clone)]
pub struct NewContact {
    /// Contact's display name
    pub name: String,
    /// Contact's phone number
    pub phone: Option<String>,
    /// Contact's email address
    pub email: Option<String>,
    /// True if this contact represents the current user
    pub is_me: bool,
    /// Primary identifier (phone or email)
    pub primary_identifier: Option<String>,
}

/// Data for creating a new message
#[derive(Debug, Clone)]
pub struct NewMessage {
    /// iMessage unique identifier
    pub imessage_id: String,
    /// Message text content
    pub text: Option<String>,
    /// Sender name
    pub sender: String,
    /// True if message was sent by current user
    pub is_from_me: bool,
    /// Timestamp when message was created
    pub date_created: NaiveDateTime,
    /// Timestamp when message was imported (optional, defaults to now)
    pub date_imported: Option<NaiveDateTime>,
    /// Handle identifier for the sender
    pub handle_id: Option<String>,
    /// Service used (iMessage, SMS, etc.)
    pub service: Option<String>,
    /// Thread identifier for grouped messages
    pub thread_id: Option<String>,
    /// True if message has attachments
    pub has_attachments: bool,
    /// Foreign key to contacts table
    pub contact_id: Option<i32>,
}

/// Data for creating a new processed message
#[derive(Debug, Clone)]
pub struct NewProcessedMessage {
    /// Foreign key to original message
    pub original_message_id: i32,
    /// Cleaned and normalized text
    pub processed_text: String,
    /// Space-separated tokens
    pub tokens: Option<String>,
    /// Lemmatized version of text
    pub lemmatized_text: Option<String>,
    /// JSON-encoded named entities
    pub named_entities: Option<String>,
    /// Sentiment score (-1.0 to 1.0)
    pub sentiment_score: Option<f32>,
    /// Processing version identifier
    pub processing_version: String,
}

/// Query builder for constructing database queries
#[derive(Debug, Default)]
pub struct QueryBuilder {
    /// List of filters to apply
    pub filters: Vec<Filter>,
    /// Column to order results by
    pub order_by: Option<String>,
    /// Maximum number of results to return
    pub limit: Option<usize>,
    /// Number of results to skip
    pub offset: Option<usize>,
}

/// A filter condition for database queries
#[derive(Debug)]
pub struct Filter {
    /// Column name to filter on
    pub field: String,
    /// Comparison operator
    pub operator: Operator,
    /// Value to compare against
    pub value: FilterType,
}

/// Comparison operators for filters
#[derive(Debug, Copy, Clone)]
pub enum Operator {
    /// Equality (=)
    Equal,
    /// Inequality (!=)
    NotEqual,
    /// Greater than (>)
    GreaterThan,
    /// Greater than or equal (>=)
    GreaterThanOrEqual,
    /// Less than (<)
    LessThan,
    /// Less than or equal (<=)
    LessThanOrEqual,
    /// Pattern matching (LIKE)
    Like,
    /// Set membership (IN)
    In,
}

/// Value types for filter conditions
#[derive(Debug)]
pub enum FilterType {
    /// Text value
    Text(String),
    /// Integer value
    Integer(i64),
    /// Floating point value
    Float(f64),
    /// Boolean value
    Boolean(bool),
    /// Date/time value
    Date(NaiveDateTime),
    /// NULL value
    Null,
    /// Array of text values
    TextArray(Vec<String>),
    /// Array of integer values
    IntegerArray(Vec<i64>),
}

impl QueryBuilder {
    /// Create a new empty query builder
    #[must_use]
    pub fn new() -> Self {
        Self::default()
    }

    /// Add a filter condition to the query
    pub fn add_filter(&mut self, filter: Filter) {
        self.filters.push(filter);
    }

    /// Set the column to order results by
    pub fn set_order_by(&mut self, order_by: String) {
        self.order_by = Some(order_by);
    }

    /// Set the maximum number of results to return
    pub const fn set_limit(&mut self, limit: usize) {
        self.limit = Some(limit);
    }

    /// Set the number of results to skip
    pub const fn set_offset(&mut self, offset: usize) {
        self.offset = Some(offset);
    }
}

/// Message item wrapper
#[derive(Debug)]
pub enum MessageItem {
    /// A database message
    Message(DbMessage),
}
