use anyhow::{Context, Result};
use async_trait::async_trait;
use chrono::{Local, TimeZone};
use csv::Writer;
use imessage_database::tables::{chat::Chat, handle::Handle, table::get_connection};
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};
use tracing::{error, info};

use crate::db::Database;
use crate::models::{Contact, DateRange, Message, NewMessage, OutputFormat};

/// Repository trait for interacting with message data
#[allow(clippy::too_many_arguments)]
#[async_trait]
pub trait MessageRepository {
    async fn fetch_messages(
        &self,
        contact: &Contact,
        date_range: &DateRange,
    ) -> Result<Vec<Message>>;
    async fn save_messages(
        &self,
        messages: &[Message],
        format: OutputFormat,
        path: &Path,
    ) -> Result<()>;
    async fn export_conversation_by_person(
        &self,
        person_name: &str,
        format: OutputFormat,
        output_path: &Path,
        date_range: &DateRange,
        chunk_size: Option<f64>,
        lines_per_chunk: Option<usize>,
        only_contact: bool,
    ) -> Result<Vec<PathBuf>>;
}

/// Repository for interacting with the database
pub struct Repository {
    db: Database,
}

impl Repository {
    /// Create a new repository
    #[must_use]
    pub const fn new(db: Database) -> Self {
        Self { db }
    }

    /// Export conversation with a specific person
    #[allow(clippy::too_many_arguments)]
    pub async fn export_conversation_by_person(
        &self,
        person_name: &str,
        date_range: &DateRange,
        format: OutputFormat,
        size_mb: Option<f64>,
        lines_per_chunk: Option<usize>,
        output_path: &Path,
        only_contact: bool,
    ) -> Result<Vec<PathBuf>> {
        // Get messages for the person
        let _start_date = date_range.start.map(|dt| dt.naive_local());
        let _end_date = date_range.end.map(|dt| dt.naive_local());

        let mut db_messages = self
            .db
            .get_messages_by_contact_name(person_name, date_range)?;

        if db_messages.is_empty() {
            info!(
                "No messages found for {} in the specified date range",
                person_name
            );
            return Ok(Vec::new());
        }

        // Filter to only show contact's messages if requested
        if only_contact {
            db_messages.retain(|msg| msg.sender == person_name);
            info!(
                "Filtered to {} messages from {} only",
                db_messages.len(),
                person_name
            );
        }

        // db_messages are already in Message format
        let messages = db_messages;

        // Generate date range string for file naming
        let date_range_str =
            if let (Some(first_msg), Some(last_msg)) = (messages.first(), messages.last()) {
                let start_date = first_msg.timestamp.format("%Y-%m-%d").to_string();
                let end_date = last_msg.timestamp.format("%Y-%m-%d").to_string();
                format!("{start_date}_{end_date}")
            } else {
                "no_messages".to_string()
            };

        // Chunk messages based on size or line count
        let chunks = if let Some(size) = size_mb {
            self.chunk_by_size(&messages, size)
        } else if let Some(lines) = lines_per_chunk {
            self.chunk_by_lines(&messages, lines)
        } else {
            vec![messages] // No chunking
        };

        let mut output_files = Vec::new();

        for (i, chunk) in chunks.iter().enumerate() {
            let chunk_num = i + 1;

            // Generate file names with contact name and date range
            let base_name = if chunks.len() == 1 {
                format!("{person_name}_{date_range_str}")
            } else {
                format!("{person_name}_{date_range_str}_chunk_{chunk_num}")
            };

            let base_path = output_path.join(base_name);

            // Save messages to file
            self.save_messages(chunk, format, &base_path).await?;

            // Add to output files
            output_files.push(base_path);
        }

        Ok(output_files)
    }

    /// Save messages to a file in the specified format
    async fn save_messages(
        &self,
        messages: &[Message],
        format: OutputFormat,
        file_path: &Path,
    ) -> Result<()> {
        match format {
            OutputFormat::Txt => self
                .save_txt(messages, file_path)
                .await
                .with_context(|| format!("Failed to save TXT file: {file_path:?}"))?,
            OutputFormat::Csv => self
                .save_csv(messages, file_path)
                .await
                .with_context(|| format!("Failed to save CSV file: {file_path:?}"))?,
            OutputFormat::Json => self
                .save_json(messages, file_path)
                .await
                .with_context(|| format!("Failed to save JSON file: {file_path:?}"))?,
        }

        Ok(())
    }

    /// Save messages to a text file
    async fn save_txt(&self, messages: &[Message], file_path: &Path) -> Result<()> {
        let file = File::create(file_path)
            .with_context(|| format!("Failed to create TXT file: {file_path:?}"))?;
        let mut writer = BufWriter::new(file);

        for message in messages {
            // Format like Python script: sender,date,content (no ID column for TXT)
            writeln!(
                writer,
                "{},{},{}",
                message.sender,
                message.timestamp.format("%b %d, %Y %r"),
                message.content
            )?;
        }

        Ok(())
    }

    /// Save messages to a CSV file
    async fn save_csv(&self, messages: &[Message], file_path: &Path) -> Result<()> {
        let file = File::create(file_path)
            .with_context(|| format!("Failed to create CSV file: {file_path:?}"))?;
        let mut writer = Writer::from_writer(file);

        // Write header row like Python script
        writer.write_record(["ID", "Sender", "Datetime", "Message"])?;

        // Add ID column with autoincrementing values starting from 1
        for (i, message) in messages.iter().enumerate() {
            writer.write_record([
                &(i + 1).to_string(), // ID column
                &message.sender,
                &message.timestamp.format("%b %d, %Y %r").to_string(),
                &message.content,
            ])?;
        }

        writer.flush()?;
        Ok(())
    }

    /// Save messages to a JSON file
    async fn save_json(&self, messages: &[Message], file_path: &Path) -> Result<()> {
        let file = File::create(file_path)
            .with_context(|| format!("Failed to create JSON file: {file_path:?}"))?;
        let writer = BufWriter::new(file);

        // Write JSON directly using serde streaming to avoid intermediate vector
        use serde::ser::SerializeSeq;
        use serde::Serializer;
        let mut ser = serde_json::Serializer::new(writer);
        let mut seq = ser.serialize_seq(Some(messages.len()))?;

        for message in messages {
            seq.serialize_element(&serde_json::json!({
                "sender": message.sender,
                "timestamp": message.timestamp.format("%b %d, %Y %r").to_string(),
                "content": message.content,
            }))?;
        }
        seq.end()?;

        Ok(())
    }

    /// Chunk messages by approximate size in MB
    fn chunk_by_size(&self, messages: &[Message], size_mb: f64) -> Vec<Vec<Message>> {
        let size_bytes = (size_mb * 1024.0 * 1024.0) as usize;
        let mut chunks = Vec::new();
        let mut current_chunk = Vec::new();
        let mut current_size = 0;

        for message in messages {
            // Estimate size of message in bytes
            let message_size = message.sender.len() + message.content.len() + 50; // 50 bytes for timestamp and overhead

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

    /// Chunk messages by line count
    fn chunk_by_lines(&self, messages: &[Message], lines_per_chunk: usize) -> Vec<Vec<Message>> {
        let mut chunks = Vec::new();
        let mut current_chunk = Vec::new();

        for (i, message) in messages.iter().enumerate() {
            current_chunk.push(message.clone());

            if (i + 1) % lines_per_chunk == 0 && !current_chunk.is_empty() {
                chunks.push(current_chunk);
                current_chunk = Vec::new();
            }
        }

        if !current_chunk.is_empty() {
            chunks.push(current_chunk);
        }

        chunks
    }
}

#[async_trait::async_trait]
impl MessageRepository for Repository {
    async fn fetch_messages(
        &self,
        contact: &Contact,
        date_range: &DateRange,
    ) -> Result<Vec<Message>> {
        // Get messages from our database for this contact
        let db_messages = self
            .db
            .get_messages_by_contact_name(&contact.name, date_range)
            .with_context(|| format!("Failed to fetch messages for contact: {}", contact.name))?;

        // db_messages is already Vec<Message>, no conversion needed
        Ok(db_messages)
    }

    async fn save_messages(
        &self,
        messages: &[Message],
        format: OutputFormat,
        path: &Path,
    ) -> Result<()> {
        use std::fs::File;
        use std::io::{BufWriter, Write};

        let file = File::create(path)?;
        let mut writer = BufWriter::new(file);

        match format {
            OutputFormat::Txt => {
                for message in messages {
                    writeln!(
                        writer,
                        "{}, {}, {}\n",
                        message.sender,
                        message.timestamp.format("%b %d, %Y %r"),
                        message.content
                    )?;
                }
            }
            OutputFormat::Csv => {
                let mut csv_writer = Writer::from_writer(writer);
                csv_writer.write_record(["Sender", "Timestamp", "Content"])?;

                for message in messages {
                    csv_writer.write_record([
                        &message.sender,
                        &message.timestamp.format("%b %d, %Y %r").to_string(),
                        &message.content,
                    ])?;
                }
                csv_writer.flush()?;
            }
            OutputFormat::Json => {
                // Write JSON directly using serde streaming to avoid intermediate vector
                use serde::ser::SerializeSeq;
                use serde::Serializer;
                let mut ser = serde_json::Serializer::new(writer);
                let mut seq = ser.serialize_seq(Some(messages.len()))?;

                for message in messages {
                    seq.serialize_element(&serde_json::json!({
                        "sender": message.sender,
                        "timestamp": message.timestamp.format("%b %d, %Y %r").to_string(),
                        "content": message.content,
                    }))?;
                }
                seq.end()?;
            }
        }

        Ok(())
    }

    async fn export_conversation_by_person(
        &self,
        person_name: &str,
        _format: OutputFormat,
        output_path: &Path,
        date_range: &DateRange,
        chunk_size: Option<f64>,
        lines_per_chunk: Option<usize>,
        only_contact: bool,
    ) -> Result<Vec<PathBuf>> {
        // Get messages for the person
        let start_date = date_range.start.map(|dt| dt.naive_local());
        let end_date = date_range.end.map(|dt| dt.naive_local());

        let db_messages =
            self.db
                .get_conversation_with_person(person_name, start_date, end_date)?;

        if db_messages.is_empty() {
            info!(
                "No messages found for {} in the specified date range",
                person_name
            );
            return Ok(Vec::new());
        }

        // Convert DbMessage to Message format
        let mut messages: Vec<Message> = db_messages
            .into_iter()
            .map(|db_msg| Message {
                content: db_msg.text.unwrap_or_default(),
                sender: db_msg.sender,
                timestamp: chrono::Utc
                    .from_utc_datetime(&db_msg.date_created)
                    .with_timezone(&Local),
            })
            .collect();

        // Filter to only show contact's messages if requested
        if only_contact {
            messages.retain(|msg| msg.sender == person_name);
            info!(
                "Filtered to {} messages from {} only",
                messages.len(),
                person_name
            );
        }
        // Chunk messages based on size or line count
        // Default to 0.1 MB if no chunk size is specified
        let default_chunk_size_mb = 0.1;
        let chunks = if let Some(size_mb) = chunk_size {
            self.chunk_by_size(&messages, size_mb)
        } else if let Some(lines) = lines_per_chunk {
            self.chunk_by_lines(&messages, lines)
        } else {
            // Default chunking by size (0.1 MB)
            self.chunk_by_size(&messages, default_chunk_size_mb)
        };

        let mut output_files = Vec::new();

        // Generate date range string for file naming
        let date_range_str =
            if let (Some(first_msg), Some(last_msg)) = (messages.first(), messages.last()) {
                let start_date = first_msg.timestamp.format("%Y-%m-%d").to_string();
                let end_date = last_msg.timestamp.format("%Y-%m-%d").to_string();
                format!("{start_date}_{end_date}")
            } else {
                "no_messages".to_string()
            };

        for (i, chunk) in chunks.iter().enumerate() {
            let chunk_num = i + 1;

            // Generate file names with contact name and date range
            let base_name = if chunks.len() == 1 {
                format!("{person_name}_{date_range_str}")
            } else {
                format!("{person_name}_{date_range_str}_chunk_{chunk_num}")
            };

            let base_path = output_path
                .parent()
                .ok_or_else(|| anyhow::anyhow!("Invalid output path: no parent directory"))?
                .join(base_name);

            // Save CSV file
            let csv_path = base_path.with_extension("csv");
            self.save_messages(chunk, OutputFormat::Csv, &csv_path)
                .await?;
            output_files.push(csv_path);

            // Save TXT file
            let txt_path = base_path.with_extension("txt");
            self.save_messages(chunk, OutputFormat::Txt, &txt_path)
                .await?;
            output_files.push(txt_path);
        }

        Ok(output_files)
    }
}

/// Repository for interacting with the iMessage database
pub struct IMessageDatabaseRepo {
    db_path: PathBuf,
    database: Database,
}

impl IMessageDatabaseRepo {
    pub fn new(chat_db_path: PathBuf) -> Result<Self> {
        // Validate that the path exists
        if !chat_db_path.exists() {
            return Err(anyhow::anyhow!(
                "iMessage database path does not exist: {chat_db_path:?}"
            ));
        }

        // Initialize our database using environment variable or platform-appropriate default
        let database = crate::db::establish_connection()?;

        Ok(Self {
            db_path: chat_db_path,
            database,
        })
    }

    // Helper method to find a handle by phone or email using indexed query
    async fn find_handle(&self, contact: &Contact) -> Result<Option<Handle>> {
        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {e}"))?;

        // Use direct SQL query with index instead of full table scan
        // The handle table has an id column which contains phone/email
        use rusqlite::OptionalExtension;

        // Try to find by phone first
        if let Some(phone) = &contact.phone {
            let query = "SELECT ROWID, id FROM handle WHERE id = ? LIMIT 1";
            let handle: Option<Handle> = db
                .query_row(query, [phone], |row| {
                    Ok(Handle {
                        rowid: row.get(0)?,
                        id: row.get(1)?,
                        person_centric_id: None,
                    })
                })
                .optional()
                .map_err(|e| anyhow::anyhow!("Failed to query handle: {e}"))?;

            if handle.is_some() {
                return Ok(handle);
            }
        }

        // Then try by email
        if let Some(email) = &contact.email {
            let query = "SELECT ROWID, id FROM handle WHERE id = ? LIMIT 1";
            let handle: Option<Handle> = db
                .query_row(query, [email], |row| {
                    Ok(Handle {
                        rowid: row.get(0)?,
                        id: row.get(1)?,
                        person_centric_id: None,
                    })
                })
                .optional()
                .map_err(|e| anyhow::anyhow!("Failed to query handle: {e}"))?;

            if handle.is_some() {
                return Ok(handle);
            }
        }

        // No handle found
        Ok(None)
    }

    // Helper method to find a chat by handle using indexed query
    async fn find_chat_by_handle(&self, handle: &Handle) -> Result<Option<Chat>> {
        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {e}"))?;

        // Use direct SQL query with index instead of full table scan
        use rusqlite::OptionalExtension;

        let query = "SELECT ROWID, chat_identifier FROM chat WHERE chat_identifier = ? LIMIT 1";

        let chat: Option<Chat> = db
            .query_row(query, [&handle.id], |row| {
                Ok(Chat {
                    rowid: row.get(0)?,
                    chat_identifier: row.get(1)?,
                    service_name: None,
                    display_name: None,
                })
            })
            .optional()
            .map_err(|e| anyhow::anyhow!("Failed to query chat: {e}"))?;

        Ok(chat)
    }

    // Save messages to database
    #[allow(dead_code)]
    async fn save_to_database(&self, messages: &[Message], contact: &Contact) -> Result<()> {
        // Ensure contact exists in database
        let db_contact = self
            .database
            .add_or_update_contact(crate::models::NewContact {
                name: contact.name.clone(),
                phone: contact.phone.clone(),
                email: contact.email.clone(),
                is_me: false,
                primary_identifier: None, // Will be auto-set based on phone/email
            })?;

        // Ensure "me" contact exists
        let me_contact = self
            .database
            .add_or_update_contact(crate::models::NewContact {
                name: "Jess".to_string(),
                phone: None,
                email: None,
                is_me: true,
                primary_identifier: Some("Jess".to_string()),
            })?;

        // Save messages
        for message in messages {
            let new_message = NewMessage {
                imessage_id: format!("generated_{}", message.timestamp.timestamp()),
                text: Some(message.content.clone()),
                sender: message.sender.clone(),
                is_from_me: message.sender == "Jess",
                date_created: message.timestamp.naive_local(),
                date_imported: None, // Will default to current time
                handle_id: None,
                service: Some("iMessage".to_string()),
                thread_id: None,
                has_attachments: false,
                contact_id: Some(if message.sender == "Jess" {
                    db_contact.id // Link to the recipient (the other person)
                } else {
                    me_contact.id // Link to me as the recipient
                }),
            };

            self.database.add_message(new_message)?;
        }

        Ok(())
    }
}

#[async_trait]
impl MessageRepository for IMessageDatabaseRepo {
    async fn fetch_messages(
        &self,
        contact: &Contact,
        date_range: &DateRange,
    ) -> Result<Vec<Message>> {
        // Find the handle for this contact
        let handle = if let Some(h) = self.find_handle(contact).await? {
            h
        } else {
            error!("No handle found for contact: {:?}", contact);
            return Ok(Vec::new());
        };

        // Find the chat for this handle
        let chat = if let Some(c) = self.find_chat_by_handle(&handle).await? {
            c
        } else {
            error!("No chat found for handle: {:?}", handle);
            return Ok(Vec::new());
        };

        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {e}"))?;

        // Use indexed query instead of full table scan
        // Query messages by chat_id with date filtering using SQL
        let mut query = "SELECT ROWID, guid, text, service, handle_id, subject, date, date_read, \
                                date_delivered, is_from_me, is_read, item_type, group_title, \
                                group_action_type, associated_message_guid, associated_message_type, \
                                balloon_bundle_id, expressive_send_style_id, thread_originator_guid, \
                                thread_originator_part, chat_id, num_attachments, deleted_from, \
                                num_replies \
                         FROM message WHERE chat_id = ?".to_string();

        let mut params: Vec<Box<dyn rusqlite::ToSql>> = vec![Box::new(chat.rowid)];

        // Add date range filters to the SQL query for better performance
        if let Some(start_dt) = date_range.start {
            query.push_str(" AND date >= ?");
            // Convert DateTime to Apple's epoch (nanoseconds since 2001-01-01)
            let apple_epoch =
                start_dt.timestamp_nanos_opt().unwrap_or(0) / 1_000_000_000 - 978_307_200; // Offset from 2001-01-01 to 1970-01-01
            params.push(Box::new(apple_epoch));
        }

        if let Some(end_dt) = date_range.end {
            query.push_str(" AND date <= ?");
            let apple_epoch =
                end_dt.timestamp_nanos_opt().unwrap_or(0) / 1_000_000_000 - 978_307_200;
            params.push(Box::new(apple_epoch));
        }

        query.push_str(" ORDER BY date ASC");

        let mut stmt = db
            .prepare(&query)
            .map_err(|e| anyhow::anyhow!("Failed to prepare query: {e}"))?;

        let message_iter = stmt
            .query_map(rusqlite::params_from_iter(params.iter()), |row| {
                // Parse row into ImessageMessage manually for performance
                let is_from_me: bool = row.get(9)?;
                let date: i64 = row.get(6)?;
                let text: Option<String> = row.get(2)?;

                Ok((is_from_me, date, text))
            })
            .map_err(|e| anyhow::anyhow!("Failed to execute query: {e}"))?;

        let mut messages = Vec::new();
        for result in message_iter {
            match result {
                Ok((is_from_me, date_value, text_opt)) => {
                    // Convert Apple epoch to DateTime
                    use chrono::TimeZone;
                    let timestamp = if let chrono::LocalResult::Single(dt) =
                        chrono::Utc.timestamp_opt(date_value + 978307200, 0)
                    {
                        dt.with_timezone(&Local)
                    } else {
                        error!("Failed to parse message date: {}, skipping", date_value);
                        continue;
                    };

                    if let Some(text) = text_opt {
                        let message = Message {
                            sender: if is_from_me {
                                "Me".to_string()
                            } else {
                                contact.name.clone()
                            },
                            timestamp,
                            content: text,
                        };
                        messages.push(message);
                    }
                }
                Err(e) => {
                    error!("Error processing message row: {:?}", e);
                }
            }
        }

        Ok(messages)
    }

    async fn save_messages(
        &self,
        messages: &[Message],
        format: OutputFormat,
        path: &Path,
    ) -> Result<()> {
        match format {
            OutputFormat::Txt => {
                let file = File::create(path)?;
                let mut writer = BufWriter::new(file);

                for message in messages {
                    writeln!(
                        &mut writer,
                        "{}, {}, {}",
                        message.sender,
                        message.timestamp.format("%b %d, %Y %l:%M:%S %p"),
                        message.content
                    )?;
                    writeln!(&mut writer)?; // Add blank line between messages
                }

                Ok(())
            }
            OutputFormat::Csv => {
                let file = File::create(path)?;
                let mut writer = Writer::from_writer(file);

                for message in messages {
                    writer.write_record([
                        &message.sender,
                        &message
                            .timestamp
                            .format("%b %d, %Y %l:%M:%S %p")
                            .to_string(),
                        &message.content,
                    ])?;
                }

                writer.flush()?;
                Ok(())
            }
            OutputFormat::Json => {
                let file = File::create(path)?;
                let writer = BufWriter::new(file);

                // Write JSON directly using serde streaming to avoid intermediate vector
                use serde::ser::SerializeSeq;
                use serde::Serializer;
                let mut ser = serde_json::Serializer::pretty(writer);
                let mut seq = ser.serialize_seq(Some(messages.len()))?;

                for msg in messages {
                    seq.serialize_element(&serde_json::json!({
                        "sender": msg.sender,
                        "timestamp": msg.timestamp.to_rfc3339(),
                        "content": msg.content
                    }))?;
                }
                seq.end()?;
                Ok(())
            }
        }
    }

    async fn export_conversation_by_person(
        &self,
        person_name: &str,
        format: OutputFormat,
        output_path: &Path,
        date_range: &DateRange,
        chunk_size: Option<f64>,
        lines_per_chunk: Option<usize>,
        only_contact: bool,
    ) -> Result<Vec<PathBuf>> {
        // Get contact by name
        let contact = match self.database.get_contact(person_name)? {
            Some(c) => Contact {
                name: c.name,
                phone: c.phone,
                email: c.email,
                emails: vec![], // Initialize empty emails vector
            },
            None => return Err(anyhow::anyhow!("Contact not found: {person_name}")),
        };

        // Fetch messages
        let mut messages = self.fetch_messages(&contact, date_range).await?;

        // Filter to only show contact's messages if requested
        if only_contact {
            messages.retain(|msg| msg.sender == person_name);
            info!(
                "Filtered to {} messages from {} only",
                messages.len(),
                person_name
            );
        }

        // If no messages, return early
        if messages.is_empty() {
            return Err(anyhow::anyhow!(
                "No messages found for contact: {person_name}"
            ));
        }

        // Generate date range string for file naming
        let date_range_str =
            if let (Some(first_msg), Some(last_msg)) = (messages.first(), messages.last()) {
                let start_date = first_msg.timestamp.format("%Y-%m-%d").to_string();
                let end_date = last_msg.timestamp.format("%Y-%m-%d").to_string();
                format!("{start_date}_{end_date}")
            } else {
                "no_messages".to_string()
            };

        // Create output files
        let mut output_files = Vec::new();

        // Determine chunking strategy and save each chunk
        if let Some(lines) = lines_per_chunk {
            // Chunk by line count
            for (i, chunk) in messages.chunks(lines).enumerate() {
                let chunk_num = i + 1;
                let base_name = if messages.len() <= lines {
                    format!("{person_name}_{date_range_str}")
                } else {
                    format!("{person_name}_{date_range_str}_chunk_{chunk_num}")
                };
                let base_path = output_path.join(base_name);

                self.save_messages(chunk, format, &base_path).await?;
                output_files.push(base_path);
            }
        } else if let Some(size) = chunk_size {
            // Chunk by approximate size (in bytes)
            let mut current_chunk = Vec::new();
            let mut current_size = 0;
            let mut chunk_index = 1;

            for message in &messages {
                // Estimate message size (very rough approximation)
                let message_size = message.sender.len() + message.content.len() + 50; // 50 for timestamp and formatting

                if current_size + message_size > (size * 1024.0 * 1024.0) as usize
                    && !current_chunk.is_empty()
                {
                    // Save the current chunk
                    let base_name = format!("{person_name}_{date_range_str}_chunk_{chunk_index}");
                    let base_path = output_path.join(base_name);

                    self.save_messages(&current_chunk, format, &base_path)
                        .await?;
                    output_files.push(base_path);

                    // Start a new chunk
                    current_chunk = Vec::new();
                    current_size = 0;
                    chunk_index += 1;
                }

                current_chunk.push(message.clone());
                current_size += message_size;
            }

            // Save the last chunk if not empty
            if !current_chunk.is_empty() {
                let base_name = if chunk_index == 1 {
                    format!("{person_name}_{date_range_str}")
                } else {
                    format!("{person_name}_{date_range_str}_chunk_{chunk_index}")
                };
                let base_path = output_path.join(base_name);

                self.save_messages(&current_chunk, format, &base_path)
                    .await?;
                output_files.push(base_path);
            }
        } else {
            // No chunking, just one file with all messages
            let base_name = format!("{person_name}_{date_range_str}");
            let base_path = output_path.join(base_name);

            self.save_messages(&messages, format, &base_path).await?;
            output_files.push(base_path);
        }

        Ok(output_files)
    }
}
