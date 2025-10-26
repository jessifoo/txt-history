use chrono::{DateTime, Local, NaiveDateTime, TimeZone};
use serde::{Deserialize, Serialize};
use serde_json;

// Original models for compatibility with existing code
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Message {
    pub sender: String,
    pub timestamp: DateTime<Local>,
    pub content: String,
}

#[derive(Debug, Clone)]
pub struct Contact {
    pub name: String,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub emails: Vec<String>,
}

impl Contact {
    /// Get the contact identifiers for iMessage export filter
    /// Returns a comma-separated string of phone and emails
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

#[derive(Debug)]
pub struct DateRange {
    pub start: Option<DateTime<Local>>,
    pub end: Option<DateTime<Local>>,
}

#[derive(Debug, Clone, Copy)]
pub enum OutputFormat {
    Csv,
    Txt,
    Json,
}

impl OutputFormat {
    pub fn extension(&self) -> &'static str {
        match self {
            OutputFormat::Csv => "csv",
            OutputFormat::Txt => "txt",
            OutputFormat::Json => "json",
        }
    }
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ChunkMetadata {
    pub chunk_number: usize,
    pub message_count: usize,
    pub start_date: DateTime<Local>,
    pub end_date: DateTime<Local>,
}

// Simple database models without Diesel
#[derive(Debug, Clone)]
pub struct DbMessage {
    pub id: i32,
    pub imessage_id: String,
    pub text: Option<String>,
    pub sender: String,
    pub is_from_me: bool,
    pub date_created: NaiveDateTime,
    pub date_imported: NaiveDateTime,
    pub handle_id: Option<String>,
    pub service: Option<String>,
    pub thread_id: Option<String>,
    pub has_attachments: bool,
    pub contact_id: Option<i32>,
}

// Struct to hold NLP analysis results
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NlpAnalysis {
    pub tokens: Vec<String>,
    pub entities: Vec<NamedEntity>,
    pub sentiment_score: Option<f32>,
    pub language: Option<String>,
    pub processed_text: String,
    pub lemmatized_text: Option<String>,
}

// Named entity representation
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NamedEntity {
    pub text: String,
    pub entity_type: String,
    pub start: usize,
    pub end: usize,
}

// Conversion methods
impl NlpAnalysis {
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
    // Convert to the original Message format for compatibility
    pub fn to_message(&self) -> Message {
        Message {
            sender: self.sender.clone(),
            timestamp: Local.from_utc_datetime(&self.date_created),
            content: self.text.clone().unwrap_or_default(),
        }
    }
}

// Database models for rusqlite
#[derive(Debug, Clone)]
pub struct DbContact {
    pub id: i32,
    pub name: String,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub is_me: bool,
}

#[derive(Debug, Clone)]
pub struct DbProcessedMessage {
    pub id: i32,
    pub original_message_id: i32,
    pub processed_text: String,
    pub tokens: Option<String>,
    pub lemmatized_text: Option<String>,
    pub named_entities: Option<String>,
    pub sentiment_score: Option<f32>,
    pub processed_at: NaiveDateTime,
    pub processing_version: String,
}

// Structs for inserting new records
#[derive(Debug, Clone)]
pub struct NewContact {
    pub name: String,
    pub phone: Option<String>,
    pub email: Option<String>,
    pub is_me: bool,
    pub primary_identifier: Option<String>,
}

#[derive(Debug, Clone)]
pub struct NewMessage {
    pub imessage_id: String,
    pub text: Option<String>,
    pub sender: String,
    pub is_from_me: bool,
    pub date_created: NaiveDateTime,
    pub date_imported: Option<NaiveDateTime>,
    pub handle_id: Option<String>,
    pub service: Option<String>,
    pub thread_id: Option<String>,
    pub has_attachments: bool,
    pub contact_id: Option<i32>,
}

#[derive(Debug, Clone)]
pub struct NewProcessedMessage {
    pub original_message_id: i32,
    pub processed_text: String,
    pub tokens: Option<String>,
    pub lemmatized_text: Option<String>,
    pub named_entities: Option<String>,
    pub sentiment_score: Option<f32>,
    pub processing_version: String,
}

// Query builder for rusqlite
#[derive(Debug, Default)]
pub struct QueryBuilder {
    pub filters: Vec<Filter>,
    pub order_by: Option<String>,
    pub limit: Option<usize>,
    pub offset: Option<usize>,
}

#[derive(Debug)]
pub struct Filter {
    pub field: String,
    pub operator: Operator,
    pub value: FilterType,
}

#[derive(Debug)]
pub enum Operator {
    Equal,
    NotEqual,
    GreaterThan,
    GreaterThanOrEqual,
    LessThan,
    LessThanOrEqual,
    Like,
    In,
}

#[derive(Debug)]
pub enum FilterType {
    Text(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    Date(NaiveDateTime),
    Null,
    TextArray(Vec<String>),
    IntegerArray(Vec<i64>),
}

impl QueryBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn add_filter(&mut self, filter: Filter) {
        self.filters.push(filter);
    }

    pub fn set_order_by(&mut self, order_by: String) {
        self.order_by = Some(order_by);
    }

    pub fn set_limit(&mut self, limit: usize) {
        self.limit = Some(limit);
    }

    pub fn set_offset(&mut self, offset: usize) {
        self.offset = Some(offset);
    }
}

// Enum for message items
#[derive(Debug)]
pub enum MessageItem {
    Message(DbMessage),
}
