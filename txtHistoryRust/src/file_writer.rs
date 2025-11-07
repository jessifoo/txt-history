//! File writing utilities for message export.
//!
//! This module provides functions for writing messages to files in various formats
//! (TXT, CSV, JSON) with consistent formatting, matching the Python script's output structure.

use crate::error::Result;
use crate::models::{Message, OutputFormat};
use csv::Writer;
use serde_json;
use std::fs::{File, create_dir_all};
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

/// Write messages to files with timestamp-based directory structure.
///
/// Creates directory structure: `output_dir/timestamp/chunks_txt/` and `output_dir/timestamp/chunks_csv/`
/// This matches the Python script's output format.
///
/// # Arguments
///
/// * `messages` - Slice of messages to write
/// * `format` - Output format (TXT, CSV, or JSON)
/// * `output_dir` - Base output directory
/// * `timestamp` - Timestamp string for directory name (e.g., "2025-01-15_14-30-00")
///
/// # Returns
///
/// Vector of paths to created files
pub fn write_messages_to_timestamped_dir(
    messages: &[Message],
    format: OutputFormat,
    output_dir: &Path,
    timestamp: &str,
) -> Result<Vec<PathBuf>> {
    if messages.is_empty() {
        return Ok(Vec::new());
    }

    // Create timestamp-based directory structure
    let date_dir = output_dir.join(timestamp);
    create_dir_all(&date_dir)?;

    let mut output_files = Vec::new();

    match format {
        OutputFormat::Txt => {
            let txt_dir = date_dir.join("chunks_txt");
            create_dir_all(&txt_dir)?;
            let file_path = txt_dir.join("chunk_1.txt");
            write_txt_file(messages, &file_path)?;
            output_files.push(file_path);
        }
        OutputFormat::Csv => {
            let csv_dir = date_dir.join("chunks_csv");
            create_dir_all(&csv_dir)?;
            let file_path = csv_dir.join("chunk_1.csv");
            write_csv_file(messages, &file_path)?;
            output_files.push(file_path);
        }
        OutputFormat::Json => {
            let file_path = date_dir.join("chunk_1.json");
            write_json_file(messages, &file_path)?;
            output_files.push(file_path);
        }
    }

    Ok(output_files)
}

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
/// Includes header row: `ID, Sender, Datetime, Message`
fn write_csv_file(messages: &[Message], file_path: &Path) -> Result<()> {
    let file = File::create(file_path)?;
    let mut writer = Writer::from_writer(file);

    // Write header (matching Python format: ID, Sender, Datetime, Message)
    writer.write_record(&["ID", "Sender", "Datetime", "Message"])?;

    // Write data with ID column (starting from 1)
    for (i, message) in messages.iter().enumerate() {
        writer.write_record(&[
            &(i + 1).to_string(), // ID column
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
