use crate::models::{Contact, DateRange, Message, OutputFormat};
use crate::repository::MessageRepository;
use crate::cache::MessageCache;
use anyhow::Result;
use std::path::Path;

pub struct MessageService {
    repository: Box<dyn MessageRepository>,
    cache: MessageCache,
}

impl MessageService {
    pub fn new(repository: Box<dyn MessageRepository>) -> Result<Self> {
        let cache = MessageCache::new()?;
        Ok(Self { repository, cache })
    }

    pub async fn process_messages(
        &self,
        contact: Contact,
        date_range: DateRange,
        output_format: OutputFormat,
        output_path: &Path,
        chunk_size_mb: Option<f64>,
        chunk_rows: Option<usize>,
    ) -> Result<()> {
        // Try to get messages from cache first
        let messages = if let Some(cached_messages) = self.cache.get_cached_messages(&contact, &date_range)? {
            println!("Using cached messages for {} in date range", contact.name);
            cached_messages
        } else {
            // If not in cache, fetch from database
            println!("Fetching messages for {} from database", contact.name);
            let mut messages = self.repository.fetch_messages(&contact, &date_range).await?;
            messages.sort_by_key(|m| m.timestamp);
            
            // Cache the fetched messages
            self.cache.cache_messages(&contact, &date_range, &messages)?;
            messages
        };

        // If no chunking is requested, save all messages to a single file
        if chunk_size_mb.is_none() && chunk_rows.is_none() {
            return self.repository.save_messages(&messages, output_format, output_path).await;
        }

        // Split messages into chunks
        let chunks = if let Some(size_mb) = chunk_size_mb {
            self.chunk_by_size(&messages, size_mb)
        } else if let Some(rows) = chunk_rows {
            self.chunk_by_rows(&messages, rows)
        } else {
            vec![messages]
        };

        // Save each chunk with an index
        for (i, chunk) in chunks.iter().enumerate() {
            let chunk_path = output_path.with_file_name(format!(
                "chunk_{}.{}",
                i + 1,
                output_format.to_string().to_lowercase()
            ));
            self.repository.save_messages(chunk, output_format, &chunk_path).await?;
        }

        Ok(())
    }

    fn chunk_by_size(&self, messages: &[Message], size_mb: f64) -> Vec<Vec<Message>> {
        let size_bytes = (size_mb * 1024.0 * 1024.0) as usize;
        let mut chunks = Vec::new();
        let mut current_chunk = Vec::new();
        let mut current_size = 0;

        for message in messages {
            let msg_size = message.sender.len() + 
                          20 + // Approximate size for formatted timestamp
                          message.content.len() + 
                          2;  // Newline characters

            if current_size + msg_size > size_bytes && !current_chunk.is_empty() {
                chunks.push(current_chunk);
                current_chunk = Vec::new();
                current_size = 0;
            }

            current_chunk.push(message.clone());
            current_size += msg_size;
        }

        if !current_chunk.is_empty() {
            chunks.push(current_chunk);
        }

        chunks
    }

    fn chunk_by_rows(&self, messages: &[Message], rows: usize) -> Vec<Vec<Message>> {
        messages.chunks(rows)
            .map(|chunk| chunk.to_vec())
            .collect()
    }
}
