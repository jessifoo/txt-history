//! File writing utilities for message export.
//!
//! This module provides functions for writing messages to files in various formats
//! (TXT, CSV, JSON) with consistent formatting.

use crate::error::{Result, TxtHistoryError};
use crate::models::{Message, OutputFormat};
use chrono::Local;
use csv::Writer;
use serde_json;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::Path;

/// Write messages to a file in the specified format.
///
/// # Arguments
///
/// * `messages` - Slice of messages to write
/// * `format` - Output format (TXT, CSV, or JSON)
/// * `file_path` - Path to the output file
///
/// # Errors
///
/// Returns an error if file creation or writing fails.
pub fn write_messages_to_file(messages: &[Message], format: OutputFormat, file_path: &Path) -> Result<()> {
    match format {
        OutputFormat::Txt => write_txt_file(messages, file_path),
        OutputFormat::Csv => write_csv_file(messages, file_path),
        OutputFormat::Json => write_json_file(messages, file_path),
    }
}

/// Write messages to a text file.
///
/// Format: `sender, timestamp, content\n\n` (blank line between messages)
fn write_txt_file(messages: &[Message], file_path: &Path) -> Result<()> {
    let file = File::create(file_path)?;
    let mut writer = BufWriter::new(file);

    for message in messages {
        writeln!(
            writer,
            "{}, {}, {}",
            message.sender,
            message.timestamp.format("%b %d, %Y %r"),
            message.content
        )?;
        writeln!(writer)?; // Add blank line between messages
    }

    writer.flush()?;
    Ok(())
}

/// Write messages to a CSV file.
///
/// Includes header row: `Sender, Timestamp, Content`
fn write_csv_file(messages: &[Message], file_path: &Path) -> Result<()> {
    let file = File::create(file_path)?;
    let mut writer = Writer::from_writer(file);

    // Write header
    writer.write_record(&["Sender", "Timestamp", "Content"])?;

    // Write data
    for message in messages {
        writer.write_record(&[
            &message.sender,
            &message.timestamp.format("%b %d, %Y %r").to_string(),
            &message.content,
        ])?;
    }

    writer.flush()?;
    Ok(())
}

/// Write messages to a JSON file.
///
/// Outputs a JSON array of message objects.
fn write_json_file(messages: &[Message], file_path: &Path) -> Result<()> {
    let file = File::create(file_path)?;
    let writer = BufWriter::new(file);

    let json_messages: Vec<serde_json::Value> = messages
        .iter()
        .map(|m| {
            serde_json::json!({
                "sender": m.sender,
                "timestamp": m.timestamp.format("%b %d, %Y %r").to_string(),
                "content": m.content,
            })
        })
        .collect();

    serde_json::to_writer_pretty(writer, &json_messages)?;
    Ok(())
}
