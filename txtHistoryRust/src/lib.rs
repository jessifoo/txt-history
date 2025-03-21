pub mod db;
pub mod models;
pub mod nlp;
pub mod repository;
pub mod schema;

// Re-export key components for easier access
pub use db::Database;
pub use models::{Contact, DateRange, Message, OutputFormat};
pub use nlp::NlpProcessor;
