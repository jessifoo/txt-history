use crate::error::{Result, TxtHistoryError};
use async_trait::async_trait;
use chrono::{Local, DateTime};
use imessage_database::tables::{
    chat::Chat,
    handle::Handle,
    messages::Message as ImessageMessage,
    table::{Table, get_connection},
};
use rusqlite;
use std::path::{Path, PathBuf};

use crate::{db::Database, models::{NewMessage, Message}};
use crate::models::{Contact, DateRange, OutputFormat};
use crate::file_writer::write_messages_to_file;
use crate::utils::{chunk_by_size, chunk_by_lines};

/// Repository trait for interacting with message data
#[async_trait]
pub trait MessageRepository {
    async fn fetch_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Vec<Message>>;
    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()>;
    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<usize>,
        lines_per_chunk: Option<usize>,
    ) -> Result<Vec<PathBuf>>;
}

/// Repository for interacting with the database
pub struct Repository {
    db: Database,
}

impl Repository {
    /// Create a new repository
    pub fn new(db: Database) -> Self {
        Self { db }
    }

    /// Export conversation with a specific person
    pub async fn export_conversation_by_person(
        &self, person_name: &str, date_range: &DateRange, format: OutputFormat, size_mb: Option<f64>, lines_per_chunk: Option<usize>,
        output_path: &Path,
    ) -> Result<Vec<PathBuf>> {
        // Get messages for the person
        let db_messages = self.db.get_messages_by_contact_name(person_name, date_range)?;

        if db_messages.is_empty() {
            println!("No messages found for {} in the specified date range", person_name);
            return Ok(Vec::new());
        }

        // Chunk messages based on size or line count
        let chunks = if let Some(size) = size_mb {
            chunk_by_size(&db_messages, size)
        } else if let Some(lines) = lines_per_chunk {
            chunk_by_lines(&db_messages, lines)
        } else {
            vec![db_messages] // No chunking
        };

        let mut output_files = Vec::new();

        for (i, chunk) in chunks.iter().enumerate() {
            // Create output file path
            let file_name = format!("chunk_{}.{}", i + 1, format.extension());
            let file_path = output_path.join(file_name);

            // Save messages to file
            self.save_messages(chunk, format, &file_path).await?;

            // Add to output files
            output_files.push(file_path);
        }

        Ok(output_files)
    }

    /// Save messages to a file in the specified format
    async fn save_messages(&self, messages: &[Message], format: OutputFormat, file_path: &Path) -> Result<()> {
        // Use shared file writer - note: this is synchronous but we keep async signature
        // for trait compatibility. Consider making this sync or using tokio::fs.
        write_messages_to_file(messages, format, file_path)
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
            return Err(TxtHistoryError::IMessageDatabase(format!(
                "iMessage database path does not exist: {:?}",
                chat_db_path
            )));
        }

        // Initialize our database
        let database = Database::new("sqlite:data/messages.db")?;

        Ok(Self {
            db_path: chat_db_path,
            database,
        })
    }

    // Helper method to find a handle by phone or email
    async fn find_handle(&self, contact: &Contact) -> Result<Option<Handle>> {
        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to connect to iMessage database: {}", e)))?;

        // Try to find by phone first using SQL query
        if let Some(phone) = &contact.phone {
            let mut stmt = db.prepare("SELECT * FROM handle WHERE id = ?1 OR id = ?2")
                .map_err(TxtHistoryError::from)?;
            let handle_results = stmt.query_map(
                rusqlite::params![phone, format!("+{}", phone.trim_start_matches('+'))],
                |row| Ok(Handle::from_row(row))
            )
            .map_err(TxtHistoryError::from)?;

            for handle_result in handle_results {
                if let Ok(handle) = handle_result {
                    let extracted = Handle::extract(Ok(handle))
                        .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to extract handle: {}", e)))?;
                    return Ok(Some(extracted));
                }
            }
        }

        // Then try by email
        if let Some(email) = &contact.email {
            let mut stmt = db.prepare("SELECT * FROM handle WHERE id = ?")
                .map_err(TxtHistoryError::from)?;
            let handle_results = stmt.query_map(
                rusqlite::params![email],
                |row| Ok(Handle::from_row(row))
            )
            .map_err(TxtHistoryError::from)?;

            for handle_result in handle_results {
                if let Ok(handle) = handle_result {
                    let extracted = Handle::extract(Ok(handle))
                        .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to extract handle: {}", e)))?;
                    return Ok(Some(extracted));
                }
            }
        }

        // No handle found
        Ok(None)
    }

    // Helper method to find a chat by handle
    async fn find_chat_by_handle(&self, handle: &Handle) -> Result<Option<Chat>> {
        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to connect to iMessage database: {}", e)))?;

        // Query for chats with this handle using SQL
        let mut stmt = db.prepare("SELECT * FROM chat WHERE ROWID IN (SELECT chat_id FROM chat_handle_join WHERE handle_id = ?)")
            .map_err(TxtHistoryError::from)?;
        let chats = stmt.query_map(
            rusqlite::params![handle.rowid],
            |row| Ok(Chat::from_row(row))
        )
        .map_err(TxtHistoryError::from)?;

        // Return the first chat found
        for chat_result in chats {
            if let Ok(chat) = chat_result {
                return Ok(Some(
                    Chat::extract(Ok(chat))
                        .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to extract chat: {}", e)))?,
                ));
            }
        }

        Ok(None)
    }

    // Get messages for a chat
    async fn get_messages_for_chat(&self, _chat: &Chat) -> Result<Vec<ImessageMessage>> {
        let _db = get_connection(&self.db_path)
            .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to connect to iMessage database: {}", e)))?;
        
        // Try to get messages using chat_identifier
        let messages = Vec::new();
        // Note: The API may have changed - this is a placeholder implementation
        // You may need to adjust based on the actual imessage-database API
        Ok(messages)
    }

    // Save messages to database
    async fn save_to_database(&self, messages: &[Message], contact: &Contact) -> Result<()> {
        // Ensure contact exists in database
        let db_contact = self.database.add_or_update_contact(crate::models::NewContact {
            name: contact.name.clone(),
            phone: contact.phone.clone(),
            email: contact.email.clone(),
            is_me: false,
            primary_identifier: None, // Will be auto-set based on phone/email
        })?;

        // Ensure "me" contact exists
        let me_contact = self.database.add_or_update_contact(crate::models::NewContact {
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
    async fn fetch_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Vec<Message>> {
        // Find handle for the contact
        let handle = match self.find_handle(contact).await? {
            Some(h) => h,
            None => return Err(TxtHistoryError::HandleNotFound(contact.name.clone())),
        };

        // Find chat for the handle
        let chat = match self.find_chat_by_handle(&handle).await? {
            Some(c) => c,
            None => return Err(TxtHistoryError::ChatNotFound(contact.name.clone())),
        };

        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path)
            .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to connect to iMessage database: {}", e)))?;

        // Get messages for this chat using SQL query
        let mut stmt = db.prepare("SELECT * FROM message WHERE ROWID IN (SELECT message_id FROM chat_message_join WHERE chat_id = ?) ORDER BY date ASC")
            .map_err(TxtHistoryError::from)?;
        let message_results = stmt.query_map(
            rusqlite::params![chat.rowid],
            |row| Ok(ImessageMessage::from_row(row))
        )
        .map_err(TxtHistoryError::from)?;

        // Convert to our Message format
        let mut messages = Vec::new();
        let me_contact = self.database.get_contact("Jess")?.unwrap();
        let db_contact = self.database.get_contact(&contact.name)?.unwrap();

        for message_result in message_results {
            if let Ok(imessage) = message_result {
                let mut msg = ImessageMessage::extract(Ok(imessage))
                    .map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to extract message: {}", e)))?;

                // Generate text content
                msg.generate_text(&db);

                // Skip messages without text
                if let Some(text) = msg.text {
                    // Apply date filter if provided
                    if let Some(start) = &date_range.start {
                        // msg.date is i64 (timestamp in nanoseconds), convert to DateTime for comparison
                        let msg_date = DateTime::from_timestamp(msg.date / 1_000_000_000, ((msg.date % 1_000_000_000) as u32) * 1_000_000)
                            .ok_or_else(|| TxtHistoryError::InvalidDate(format!("Invalid timestamp: {}", msg.date)))?;
                        if msg_date < *start {
                            continue;
                        }
                    }

                    if let Some(end) = &date_range.end {
                        let msg_date = DateTime::from_timestamp(msg.date / 1_000_000_000, ((msg.date % 1_000_000_000) as u32) * 1_000_000)
                            .ok_or_else(|| TxtHistoryError::InvalidDate(format!("Invalid timestamp: {}", msg.date)))?;
                        if msg_date > *end {
                            continue;
                        }
                    }

                    // Determine sender name
                    let sender = if msg.is_from_me { "Jess".to_string() } else { contact.name.clone() };

                    // Convert date (msg.date is i64 timestamp in nanoseconds)
                    let msg_date_time = DateTime::from_timestamp(msg.date / 1_000_000_000, ((msg.date % 1_000_000_000) as u32) * 1_000_000)
                        .ok_or_else(|| TxtHistoryError::InvalidDate(format!("Invalid timestamp: {}", msg.date)))?;
                    let timestamp = msg_date_time.with_timezone(&Local);
                    let msg_date = msg_date_time.naive_utc();

                    // Convert to our message format
                    let new_message = NewMessage {
                        imessage_id: msg.guid.clone(),
                        text: Some(text.clone()),
                        sender: sender.clone(),
                        is_from_me: msg.is_from_me,
                        date_created: msg_date,
                        date_imported: None, // Will default to current time
                        handle_id: Some(handle.id.clone()),
                        service: msg.service.clone(),
                        thread_id: Some(chat.chat_identifier.clone()),
                        has_attachments: false, // Simplified for now
                        contact_id: Some(if msg.is_from_me {
                            db_contact.id // Link to the recipient (the other person)
                        } else {
                            me_contact.id // Link to me as the recipient
                        }),
                    };

                    // Create message
                    let message = Message {
                        sender,
                        timestamp,
                        content: text,
                    };

                    messages.push(message);

                    // Save to database
                    self.database.add_message(new_message)?;
                }
            }
        }

        Ok(messages)
    }

    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()> {
        // Use shared file writer - note: this is synchronous but we keep async signature
        // for trait compatibility. Consider making this sync or using tokio::fs.
        write_messages_to_file(messages, format, path)
    }

    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<usize>,
        lines_per_chunk: Option<usize>,
    ) -> Result<Vec<PathBuf>> {
        // Get contact by name
        let contact = match self.database.get_contact(person_name)? {
            Some(c) => Contact {
                name: c.name,
                phone: c.phone,
                email: c.email,
            },
            None => return Err(TxtHistoryError::ContactNotFound(person_name.to_string())),
        };

        // Fetch messages
        let messages = self.fetch_messages(&contact, date_range).await?;

        // If no messages, return early
        if messages.is_empty() {
            return Err(TxtHistoryError::Other(format!("No messages found for contact: {}", person_name)));
        }

        // Create output files
        let mut output_files = Vec::new();
        
        // Determine chunking strategy and save each chunk
        if let Some(lines) = lines_per_chunk {
            // Chunk by line count
            for (i, chunk) in messages.chunks(lines).enumerate() {
                let file_name = format!("chunk_{}.{}", i + 1, format.extension());
                let file_path = output_path.join(file_name);
                
                self.save_messages(chunk, format, &file_path).await?;
                output_files.push(file_path);
            }
        } else if let Some(size) = chunk_size {
            // Chunk by approximate size (in bytes)
            let mut current_chunk = Vec::new();
            let mut current_size = 0;
            let mut chunk_index = 1;

            for message in &messages {
                // Estimate message size (very rough approximation)
                let message_size = message.sender.len() + message.content.len() + 50; // 50 for timestamp and formatting

                if current_size + message_size > size * 1024 * 1024 && !current_chunk.is_empty() {
                    // Save the current chunk
                    let file_name = format!("chunk_{}.{}", chunk_index, format.extension());
                    let file_path = output_path.join(file_name);
                    
                    self.save_messages(&current_chunk, format, &file_path).await?;
                    output_files.push(file_path);
                    
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
                let file_name = format!("chunk_{}.{}", chunk_index, format.extension());
                let file_path = output_path.join(file_name);
                
                self.save_messages(&current_chunk, format, &file_path).await?;
                output_files.push(file_path);
            }
        } else {
            // No chunking, just one file with all messages
            let file_name = format!("conversation.{}", format.extension());
            let file_path = output_path.join(file_name);
            
            self.save_messages(&messages, format, &file_path).await?;
            output_files.push(file_path);
        }

        Ok(output_files)
    }
}
