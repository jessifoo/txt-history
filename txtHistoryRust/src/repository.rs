use anyhow::Result;
use async_trait::async_trait;
use tracing::{info, error};
use chrono::{Local, TimeZone};
use csv::Writer;
use imessage_database::tables::{
    chat::Chat,
    handle::Handle,
    messages::Message as ImessageMessage,
    table::{Table, get_connection},
};
use serde_json;
use std::fs::File;
use std::io::{BufWriter, Write};
use std::path::{Path, PathBuf};

use crate::{db::Database, models::{NewMessage, Message}};
use crate::models::{Contact, DateRange, OutputFormat};

/// Repository trait for interacting with message data
#[async_trait]
pub trait MessageRepository {
    async fn fetch_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Vec<Message>>;
    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()>;
    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<f64>,
        lines_per_chunk: Option<usize>, only_contact: bool,
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
        output_path: &Path, only_contact: bool,
    ) -> Result<Vec<PathBuf>> {
        // Get messages for the person
        let _start_date = date_range.start.map(|dt| dt.naive_local());
        let _end_date = date_range.end.map(|dt| dt.naive_local());

        let mut db_messages = self.db.get_messages_by_contact_name(person_name, date_range)?;

        if db_messages.is_empty() {
            info!("No messages found for {} in the specified date range", person_name);
            return Ok(Vec::new());
        }

        // Filter to only show contact's messages if requested
        if only_contact {
            db_messages.retain(|msg| msg.sender == person_name);
            info!("Filtered to {} messages from {} only", db_messages.len(), person_name);
        }

        // Chunk messages based on size or line count
        let chunks = if let Some(size) = size_mb {
            self.chunk_by_size(&db_messages, size)
        } else if let Some(lines) = lines_per_chunk {
            self.chunk_by_lines(&db_messages, lines)
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
        match format {
            OutputFormat::Txt => self.save_txt(messages, file_path).await?,
            OutputFormat::Csv => self.save_csv(messages, file_path).await?,
            OutputFormat::Json => self.save_json(messages, file_path).await?,
        }

        Ok(())
    }

    /// Save messages to a text file
    async fn save_txt(&self, messages: &[Message], file_path: &Path) -> Result<()> {
        let file = File::create(file_path)?;
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
        let file = File::create(file_path)?;
        let mut writer = Writer::from_writer(file);

        // Write header row like Python script
        writer.write_record(&["ID", "Sender", "Datetime", "Message"])?;

        // Add ID column with autoincrementing values starting from 1
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

    /// Save messages to a JSON file
    async fn save_json(&self, messages: &[Message], file_path: &Path) -> Result<()> {
        let file = File::create(file_path)?;
        let mut writer = BufWriter::new(file);

        let json_messages: Vec<_> = messages
            .iter()
            .map(|m| {
                serde_json::json!({
                    "sender": m.sender,
                    "timestamp": m.timestamp.format("%b %d, %Y %r").to_string(),
                    "content": m.content,
                })
            })
            .collect();

        writeln!(writer, "[")?;
        for (i, json_message) in json_messages.iter().enumerate() {
            if i > 0 {
                writeln!(writer, ",")?;
            }
            writeln!(writer, "{}", json_message)?;
        }
        writeln!(writer, "]")?;

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
    async fn fetch_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Vec<Message>> {
        // Get messages from our database for this contact
        let db_messages = self.db.get_messages_by_contact_name(&contact.name, date_range)?;
        
        // db_messages is already Vec<Message>, no conversion needed
        Ok(db_messages)
    }

    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()> {
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
                csv_writer.write_record(&["Sender", "Timestamp", "Content"])?;
                
                for message in messages {
                    csv_writer.write_record(&[
                        &message.sender,
                        &message.timestamp.format("%b %d, %Y %r").to_string(),
                        &message.content,
                    ])?;
                }
                csv_writer.flush()?;
            }
            OutputFormat::Json => {
                let json_messages: Vec<_> = messages
                    .iter()
                    .map(|m| {
                        serde_json::json!({
                            "sender": m.sender,
                            "timestamp": m.timestamp.format("%b %d, %Y %r").to_string(),
                            "content": m.content,
                        })
                    })
                    .collect();

                writeln!(writer, "[")?;
                for (i, json_message) in json_messages.iter().enumerate() {
                    if i > 0 {
                        writeln!(writer, ",")?;
                    }
                    writeln!(writer, "{}", json_message)?;
                }
                writeln!(writer, "]")?;
            }
        }

        Ok(())
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
        // Get messages for the person
        let start_date = date_range.start.map(|dt| dt.naive_local());
        let end_date = date_range.end.map(|dt| dt.naive_local());

        let db_messages = self.db.get_conversation_with_person(
            person_name,
            start_date,
            end_date,
        )?;

        if db_messages.is_empty() {
            info!("No messages found for {} in the specified date range", person_name);
            return Ok(Vec::new());
        }

        // Convert DbMessage to Message format
        let mut messages: Vec<Message> = db_messages
            .into_iter()
            .map(|db_msg| Message {
                content: db_msg.text.unwrap_or_default(),
                sender: db_msg.sender,
                timestamp: chrono::Utc.from_utc_datetime(&db_msg.date_created)
                    .with_timezone(&Local),
            })
            .collect();

        // Filter to only show contact's messages if requested
        if only_contact {
            messages.retain(|msg| msg.sender == person_name);
            info!("Filtered to {} messages from {} only", messages.len(), person_name);
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

        for (i, chunk) in chunks.iter().enumerate() {
            let chunk_num = i + 1;
            
            // Generate both CSV and TXT files like the Python script
            let base_path = if chunks.len() == 1 {
                output_path.parent().unwrap().join(output_path.file_stem().unwrap())
            } else {
                output_path.parent().unwrap().join(format!("{}_chunk_{}", 
                    output_path.file_stem().unwrap().to_string_lossy(), chunk_num))
            };

            // Save CSV file
            let csv_path = base_path.with_extension("csv");
            self.save_messages(chunk, OutputFormat::Csv, &csv_path).await?;
            output_files.push(csv_path);

            // Save TXT file
            let txt_path = base_path.with_extension("txt");
            self.save_messages(chunk, OutputFormat::Txt, &txt_path).await?;
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
            return Err(anyhow::anyhow!("iMessage database path does not exist: {:?}", chat_db_path));
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
        let db = get_connection(&self.db_path).map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {}", e))?;

        // Try to find by phone first
        if let Some(phone) = &contact.phone {
            let mut found_handle: Option<Handle> = None;
            
            Handle::stream(&db, |handle_result| {
                match handle_result {
                    Ok(handle) => {
                        if handle.id == *phone {
                            found_handle = Some(handle);
                            return Ok::<(), anyhow::Error>(());
                        }
                    }
                    Err(e) => {
                        error!("Error processing handle: {:?}", e);
                    }
                }
                Ok(())
            }).map_err(|e| anyhow::anyhow!("Failed to stream handles: {}", e))?;

            if found_handle.is_some() {
                return Ok(found_handle);
            }
        }

        // Then try by email
        if let Some(email) = &contact.email {
            let mut found_handle: Option<Handle> = None;
            
            Handle::stream(&db, |handle_result| {
                match handle_result {
                    Ok(handle) => {
                        if handle.id == *email {
                            found_handle = Some(handle);
                            return Ok::<(), anyhow::Error>(());
                        }
                    }
                    Err(e) => {
                        error!("Error processing handle: {:?}", e);
                    }
                }
                Ok(())
            }).map_err(|e| anyhow::anyhow!("Failed to stream handles: {}", e))?;

            if found_handle.is_some() {
                return Ok(found_handle);
            }
        }

        // No handle found
        Ok(None)
    }

    // Helper method to find a chat by handle
    async fn find_chat_by_handle(&self, handle: &Handle) -> Result<Option<Chat>> {
        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path).map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {}", e))?;

        // Query for chats with this handle - look for chat_identifier matching handle.id
        let mut found_chat: Option<Chat> = None;
        
        Chat::stream(&db, |chat_result| {
            match chat_result {
                Ok(chat) => {
                    if chat.chat_identifier == handle.id {
                        found_chat = Some(chat);
                        return Ok::<(), anyhow::Error>(());
                    }
                }
                Err(e) => {
                    error!("Error processing chat: {:?}", e);
                }
            }
            Ok(())
        }).map_err(|e| anyhow::anyhow!("Failed to stream chats: {}", e))?;

        Ok(found_chat)
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
        // Find the handle for this contact
        let handle = match self.find_handle(contact).await? {
            Some(h) => h,
            None => {
                error!("No handle found for contact: {:?}", contact);
                return Ok(Vec::new());
            }
        };

        // Find the chat for this handle
        let chat = match self.find_chat_by_handle(&handle).await? {
            Some(c) => c,
            None => {
                error!("No chat found for handle: {:?}", handle);
                return Ok(Vec::new());
            }
        };

        // Create a connection to the iMessage database
        let db = get_connection(&self.db_path).map_err(|e| anyhow::anyhow!("Failed to connect to iMessage database: {}", e))?;

        // Get the time offset for date conversion
        let offset = imessage_database::util::dates::get_offset();

        // Collect messages from the chat
        let mut messages = Vec::new();
        
        ImessageMessage::stream(&db, |message_result| {
            match message_result {
                Ok(mut imessage) => {
                    // Check if this message belongs to our chat
                    if let Some(chat_id) = imessage.chat_id {
                        if chat_id == chat.rowid {
                            // Check date range if specified
                            if let Some(start_date) = date_range.start {
                                if let Ok(msg_date) = imessage.date(&offset) {
                                    if msg_date < start_date {
                                        return Ok::<(), anyhow::Error>(());
                                    }
                                }
                            }
                            
                            if let Some(end_date) = date_range.end {
                                if let Ok(msg_date) = imessage.date(&offset) {
                                    if msg_date > end_date {
                                        return Ok::<(), anyhow::Error>(());
                                    }
                                }
                            }

                            // Store the values we need before calling generate_text
                            let is_from_me = imessage.is_from_me;
                            let timestamp = imessage.date(&offset).unwrap_or_else(|_| Local::now());
                            
                            // Generate text for the message
                            if let Ok(text) = imessage.generate_text(&db) {
                                // Convert to our Message format
                                let message = Message {
                                    sender: if is_from_me {
                                        "Me".to_string()
                                    } else {
                                        contact.name.clone()
                                    },
                                    timestamp,
                                    content: text.to_string(),
                                };
                                messages.push(message);
                            }
                        }
                    }
                }
                Err(e) => {
                    error!("Error processing message: {:?}", e);
                }
            }
            Ok::<(), anyhow::Error>(())
        }).map_err(|e| anyhow::anyhow!("Failed to stream messages: {}", e))?;

        Ok(messages)
    }

    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()> {
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
            },
            OutputFormat::Csv => {
                let file = File::create(path)?;
                let mut writer = Writer::from_writer(file);

                for message in messages {
                    writer.write_record(&[
                        &message.sender,
                        &message.timestamp.format("%b %d, %Y %l:%M:%S %p").to_string(),
                        &message.content,
                    ])?;
                }

                writer.flush()?;
                Ok(())
            },
            OutputFormat::Json => {
                let file = File::create(path)?;
                let writer = BufWriter::new(file);

                // Convert messages to serializable format
                let json_messages: Vec<serde_json::Value> = messages
                    .iter()
                    .map(|msg| {
                        serde_json::json!({
                            "sender": msg.sender,
                            "timestamp": msg.timestamp.to_rfc3339(),
                            "content": msg.content
                        })
                    })
                    .collect();

                serde_json::to_writer_pretty(writer, &json_messages)?;
                Ok(())
            },
        }
    }

    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<f64>,
        lines_per_chunk: Option<usize>, only_contact: bool,
    ) -> Result<Vec<PathBuf>> {
        // Get contact by name
        let contact = match self.database.get_contact(person_name)? {
            Some(c) => Contact {
                name: c.name,
                phone: c.phone,
                email: c.email,
                emails: vec![], // Initialize empty emails vector
            },
            None => return Err(anyhow::anyhow!("Contact not found: {}", person_name)),
        };

        // Fetch messages
        let mut messages = self.fetch_messages(&contact, date_range).await?;

        // Filter to only show contact's messages if requested
        if only_contact {
            messages.retain(|msg| msg.sender == person_name);
            info!("Filtered to {} messages from {} only", messages.len(), person_name);
        }

        // If no messages, return early
        if messages.is_empty() {
            return Err(anyhow::anyhow!("No messages found for contact: {}", person_name));
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

                if current_size + message_size > (size * 1024.0 * 1024.0) as usize && !current_chunk.is_empty() {
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
