pub mod db;
pub mod error;
pub mod file_writer;
pub mod models;
pub mod nlp;
pub mod repository;
pub mod schema;
pub mod utils;

// Re-export key components for easier access
pub use db::Database;
pub use error::{Result, TxtHistoryError};
pub use models::{Contact, DateRange, Message, OutputFormat};
pub use nlp::NlpProcessor;
