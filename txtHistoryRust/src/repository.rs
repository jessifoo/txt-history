use anyhow::Result;
use async_trait::async_trait;
use chrono::{Local, TimeZone};
use imessage_database::{
    IMessageChat, IMessageDb,
    tables::{chat::Chat, handle::Handle, message::Message as ImessageMessage},
};
use std::path::{Path, PathBuf};

use crate::models::{Contact, DateRange, Message, OutputFormat};

#[async_trait]
pub trait MessageRepository {
    async fn fetch_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Vec<Message>>;
    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()>;
    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<usize>,
        lines_per_chunk: Option<usize>,
    ) -> Result<Vec<PathBuf>>;
}

pub struct IMessageDatabaseRepo {
    db: IMessageDb,
    database: Database,
}

impl IMessageDatabaseRepo {
    pub fn new(chat_db_path: PathBuf) -> Result<Self> {
        // Initialize iMessage database
        let db = IMessageDb::new(chat_db_path).map_err(|e| anyhow::anyhow!("Failed to initialize iMessage database: {}", e))?;

        // Initialize our database
        let database = Database::new("sqlite:data/messages.db")?;

        Ok(Self { db, database })
    }

    // Helper method to find a handle by phone or email
    async fn find_handle(&self, contact: &Contact) -> Result<Option<Handle>> {
        // Try to find by phone first
        if let Some(phone) = &contact.phone {
            let handle = self
                .db
                .get_handle_by_id(phone)
                .await
                .map_err(|e| anyhow::anyhow!("Failed to get handle by phone: {}", e))?;

            if handle.is_some() {
                return Ok(handle);
            }
        }

        // Then try by email
        if let Some(email) = &contact.email {
            let handle = self
                .db
                .get_handle_by_id(email)
                .await
                .map_err(|e| anyhow::anyhow!("Failed to get handle by email: {}", e))?;

            return Ok(handle);
        }

        // No handle found
        Ok(None)
    }

    // Helper method to find a chat by handle
    async fn find_chat_by_handle(&self, handle: &Handle) -> Result<Option<Chat>> {
        let chats = self
            .db
            .get_chats_by_handle_id(handle.rowid)
            .await
            .map_err(|e| anyhow::anyhow!("Failed to get chats by handle: {}", e))?;

        // Just return the first chat for now
        Ok(chats.into_iter().next())
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
            None => return Err(anyhow::anyhow!("No handle found for contact: {}", contact.name)),
        };

        // Find chat for the handle
        let chat = match self.find_chat_by_handle(&handle).await? {
            Some(c) => c,
            None => return Err(anyhow::anyhow!("No chat found for contact: {}", contact.name)),
        };

        // Build query
        let mut query = QueryBuilder::new();

        // Add chat filter
        query.add_filter(Filter {
            field: "message.cache_roomnames".to_string(),
            operator: Operator::Equal,
            value: FilterType::Text(chat.chat_identifier.clone()),
        });

        // Add date filters if provided
        if let Some(start) = &date_range.start {
            query.add_filter(Filter {
                field: "message.date".to_string(),
                operator: Operator::GreaterThanOrEqual,
                value: FilterType::Date(start.naive_utc()),
            });
        }

        if let Some(end) = &date_range.end {
            query.add_filter(Filter {
                field: "message.date".to_string(),
                operator: Operator::LessThanOrEqual,
                value: FilterType::Date(end.naive_utc()),
            });
        }

        // Execute query
        let message_items = self
            .db
            .get_messages_by_query(query)
            .await
            .map_err(|e| anyhow::anyhow!("Failed to get messages: {}", e))?;

        // Convert to our Message format
        let mut messages = Vec::new();

        for item in message_items {
            if let MessageItem::Message(msg) = item {
                // Skip messages without text
                if let Some(text) = msg.text {
                    // Determine sender name
                    let sender = if msg.is_from_me { "Jess".to_string() } else { contact.name.clone() };

                    // Convert date
                    let timestamp = Local.from_utc_datetime(&msg.date);

                    // Create message
                    let message = Message {
                        sender,
                        timestamp,
                        content: text,
                    };

                    messages.push(message);

                    // Save to database
                    let new_message = NewMessage {
                        imessage_id: msg.guid,
                        text: msg.text,
                        sender: if msg.is_from_me { "Jess".to_string() } else { contact.name.clone() },
                        is_from_me: msg.is_from_me,
                        date_created: msg.date,
                        handle_id: Some(handle.id.clone()),
                        service: msg.service,
                        thread_id: Some(chat.chat_identifier.clone()),
                        has_attachments: !msg.attachments.is_empty(),
                        contact_id: if msg.is_from_me { Some(me_contact.id) } else { Some(db_contact.id) },
                    };

                    // Add to database
                    self.database.add_message(new_message)?;
                }
            }
        }

        // Sort by date
        messages.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));

        Ok(messages)
    }

    async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> Result<()> {
        match format {
            OutputFormat::Txt => {
                use std::fs::File;
                use std::io::{BufWriter, Write};

                let file = File::create(path)?;
                let mut writer = BufWriter::new(file);

                for message in messages {
                    writeln!(
                        writer,
                        "{}, {}, {}\n",
                        message.sender,
                        message.timestamp.format("%b %d, %Y %r"),
                        message.content
                    )?;
                }
            },
            OutputFormat::Csv => {
                let file = std::fs::File::create(path)?;
                let mut writer = csv::Writer::from_writer(file);

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
            },
        }

        Ok(())
    }

    // Export conversation with a person in the specified format
    async fn export_conversation_by_person(
        &self, person_name: &str, format: OutputFormat, output_path: &Path, date_range: &DateRange, chunk_size: Option<usize>,
        lines_per_chunk: Option<usize>,
    ) -> Result<Vec<PathBuf>> {
        // Get all messages with this person
        let messages = self.database.get_conversation_with_person(
            person_name,
            date_range.start.map(|dt| dt.naive_local()),
            date_range.end.map(|dt| dt.naive_local()),
        )?;

        if messages.is_empty() {
            return Ok(Vec::new());
        }

        // Convert database messages to the Message format
        let messages: Vec<Message> = messages
            .into_iter()
            .map(|db_msg| Message {
                content: db_msg.text.unwrap_or_default(),
                sender: db_msg.sender,
                timestamp: Local.from_utc_datetime(&db_msg.date_created),
            })
            .collect();

        // Determine how to chunk the messages
        let chunks = if let Some(lines) = lines_per_chunk {
            // Chunk by number of messages
            messages.chunks(lines).map(|chunk| chunk.to_vec()).collect::<Vec<_>>()
        } else if let Some(size_mb) = chunk_size {
            // Chunk by approximate size in MB
            let bytes_per_mb = 1024 * 1024;
            let target_bytes = size_mb as usize * bytes_per_mb;

            let mut chunks = Vec::new();
            let mut current_chunk = Vec::new();
            let mut current_size = 0;

            for msg in messages {
                // Estimate size of this message (content + metadata)
                let msg_size = msg.content.len() + msg.sender.len() + 50; // 50 bytes for timestamp and formatting

                if current_size + msg_size > target_bytes && !current_chunk.is_empty() {
                    chunks.push(current_chunk);
                    current_chunk = Vec::new();
                    current_size = 0;
                }

                current_chunk.push(msg);
                current_size += msg_size;
            }

            if !current_chunk.is_empty() {
                chunks.push(current_chunk);
            }

            chunks
        } else {
            // No chunking, just one file
            vec![messages]
        };

        // Create output files for each chunk
        let mut output_files = Vec::new();

        for (i, chunk) in chunks.iter().enumerate() {
            let chunk_number = i + 1;
            let file_stem = output_path.file_stem().and_then(|s| s.to_str()).unwrap_or("conversation");

            let file_name = if chunks.len() > 1 {
                format!("{}_chunk_{}", file_stem, chunk_number)
            } else {
                file_stem.to_string()
            };

            // Create both TXT and CSV files
            let txt_path = output_path.with_file_name(format!("{}.txt", file_name));
            let csv_path = output_path.with_file_name(format!("{}.csv", file_name));

            // Format and save the messages
            self.save_messages(chunk, OutputFormat::Txt, &txt_path).await?;
            self.save_messages(chunk, OutputFormat::Csv, &csv_path).await?;

            output_files.push(txt_path);
            output_files.push(csv_path);
        }

        Ok(output_files)
    }
}
