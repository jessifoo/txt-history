//! Utility functions for message processing.
//!
//! This module provides shared utilities for chunking and processing messages.

use crate::models::Message;

/// Chunk messages by approximate size in MB.
///
/// # Arguments
///
/// * `messages` - Slice of messages to chunk
/// * `size_mb` - Target size per chunk in megabytes
///
/// # Returns
///
/// Vector of message chunks, where each chunk is approximately `size_mb` MB.
pub fn chunk_by_size(messages: &[Message], size_mb: f64) -> Vec<Vec<Message>> {
    let size_bytes = (size_mb * 1024.0 * 1024.0) as usize;
    let mut chunks = Vec::new();
    let mut current_chunk = Vec::new();
    let mut current_size = 0;

    for message in messages {
        // Estimate size of message in bytes
        // Approximate: sender + content + timestamp formatting + overhead
        let message_size = message.sender.len() + message.content.len() + 50;

        if current_size + message_size > size_bytes && !current_chunk.is_empty() {
            chunks.push(current_chunk);
            current_chunk = Vec::new();
            current_size = 0;
        }

        current_chunk.push(message.clone());
        current_size += message_size;
    }

    if !current_chunk.is_empty() {
        chunks.push(current_chunk);
    }

    chunks
}

/// Chunk messages by line count.
///
/// # Arguments
///
/// * `messages` - Slice of messages to chunk
/// * `lines_per_chunk` - Number of messages per chunk
///
/// # Returns
///
/// Vector of message chunks, where each chunk contains at most
/// `lines_per_chunk` messages.
pub fn chunk_by_lines(messages: &[Message], lines_per_chunk: usize) -> Vec<Vec<Message>> {
    messages.chunks(lines_per_chunk).map(|chunk| chunk.to_vec()).collect()
}
