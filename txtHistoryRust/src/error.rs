//! Error types for the txt-history-rust library.
//!
//! This module provides custom error types using `thiserror` for better error handling
//! and more specific error messages throughout the application.

use thiserror::Error;

/// Errors that can occur in the txt-history-rust application.
#[derive(Error, Debug)]
pub enum TxtHistoryError {
    /// Database-related errors
    #[error("Database error: {0}")]
    Database(#[from] rusqlite::Error),

    /// Error connecting to or querying the iMessage database
    #[error("iMessage database error: {0}")]
    IMessageDatabase(String),

    /// Contact not found
    #[error("Contact not found: {0}")]
    ContactNotFound(String),

    /// Handle not found for contact
    #[error("No handle found for contact: {0}")]
    HandleNotFound(String),

    /// Chat not found for handle
    #[error("No chat found for contact: {0}")]
    ChatNotFound(String),

    /// File I/O errors
    #[error("File I/O error: {0}")]
    Io(#[from] std::io::Error),

    /// Invalid date format
    #[error("Invalid date format: {0}")]
    InvalidDate(String),

    /// Invalid configuration
    #[error("Invalid configuration: {0}")]
    InvalidConfig(String),

    /// Serialization/deserialization errors
    #[error("Serialization error: {0}")]
    Serialization(#[from] serde_json::Error),

    /// Binary serialization errors
    #[error("Binary serialization error: {0}")]
    Bincode(#[from] bincode::Error),

    /// Cache errors
    #[error("Cache error: {0}")]
    Cache(String),

    /// General error with context
    #[error("{0}")]
    Other(String),
}

/// Convenience type alias for Result with TxtHistoryError
pub type Result<T> = std::result::Result<T, TxtHistoryError>;

impl From<anyhow::Error> for TxtHistoryError {
    fn from(err: anyhow::Error) -> Self {
        TxtHistoryError::Other(err.to_string())
    }
}

impl From<sled::Error> for TxtHistoryError {
    fn from(err: sled::Error) -> Self {
        TxtHistoryError::Cache(err.to_string())
    }
}
