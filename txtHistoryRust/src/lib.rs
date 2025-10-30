//! Text History - Message Management and Export
//!
//! A Rust library for managing, processing, and exporting message histories
//! from iMessage and other sources.
//!
//! # Features
//!
//! - Import messages from iMessage database
//! - Export to multiple formats (TXT, CSV, JSON)
//! - NLP processing and analysis
//! - Contact management
//! - Configurable chunking and batching

/// Configuration management
pub mod config;
/// Database operations and connection pooling
pub mod db;
/// Logging setup and utilities
pub mod logging;
/// Metrics collection
pub mod metrics;
/// Data models and structures
pub mod models;
/// NLP processing
pub mod nlp;
/// Repository pattern for data access
pub mod repository;
/// Database schema definitions
pub mod schema;
/// Input validation and sanitization
pub mod validation;

// Re-export key components for easier access
pub use db::Database;
pub use models::{Contact, DateRange, Message, OutputFormat};
pub use nlp::NlpProcessor;
