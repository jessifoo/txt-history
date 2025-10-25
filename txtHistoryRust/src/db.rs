use anyhow::{Context, Result};
use chrono::{NaiveDateTime, Utc};
use r2d2::Pool;
use rusqlite::{Connection, Row, params, OptionalExtension};
use std::path::Path;

use crate::models::{DbContact, DbMessage, DbProcessedMessage, NewContact, NewMessage, NewProcessedMessage};

// Custom connection manager for rusqlite
pub struct SqliteConnectionManager {
    path: String,
}

impl SqliteConnectionManager {
    pub fn file<P: AsRef<Path>>(path: P) -> Self {
        Self {
            path: path.as_ref().to_string_lossy().to_string(),
        }
    }
}

impl r2d2::ManageConnection for SqliteConnectionManager {
    type Connection = Connection;
    type Error = rusqlite::Error;

    fn connect(&self) -> std::result::Result<Connection, rusqlite::Error> {
        Connection::open(&self.path)
    }

    fn is_valid(&self, conn: &mut Connection) -> std::result::Result<(), rusqlite::Error> {
        conn.execute_batch("").map_err(Into::into)
    }

    fn has_broken(&self, _conn: &mut Connection) -> bool {
        false
    }
}

// Type alias for the database connection pool
pub type DbPool = Pool<SqliteConnectionManager>;
pub type DbConnection = r2d2::PooledConnection<SqliteConnectionManager>;

/// Database manager for handling connections and operations
#[derive(Clone)]
pub struct Database {
    pool: DbPool,
}

impl Database {
    /// Create a new database connection pool
    pub fn new(database_url: &str) -> Result<Self> {
        // Create parent directory if it doesn't exist
        if let Some(parent) = Path::new(database_url).parent() {
            std::fs::create_dir_all(parent)?;
        }

        // Set up connection manager and pool
        let manager = SqliteConnectionManager::file(database_url);
        let pool = Pool::builder()
            .build(manager)
            .context("Failed to create database connection pool")?;

        // Run migrations
        let conn = pool.get()?;
        Self::run_migrations(&conn)?;

        Ok(Self { pool })
    }

    /// Run database migrations
    fn run_migrations(conn: &Connection) -> Result<()> {
        // Create tables if they don't exist
        conn.execute_batch(include_str!("../migrations/2025-03-15-000000_create_tables/up.sql"))
            .context("Failed to run initial migration")?;

        // Run additional migrations
        conn.execute_batch(include_str!("../migrations/2025-03-15-000001_add_processed_messages/up.sql"))
            .context("Failed to run processed_messages migration")?;

        // Run contact linking migration with proper error handling
        if let Err(e) = conn.execute_batch(include_str!("../migrations/2025-03-19-000000_enhance_contact_linking/up.sql")) {
            // Check for specific SQLite error codes instead of string matching
            match e {
                rusqlite::Error::SqliteFailure(sqlite_err, _) => {
                    // SQLite error code 1 is SQLITE_ERROR, but we need to check the extended code
                    // SQLITE_CONSTRAINT_UNIQUE = 2067, but we'll check for constraint violations
                    if sqlite_err.code != rusqlite::ErrorCode::ConstraintViolation {
                        return Err(e.into());
                    }
                    // If it's a constraint violation, it might be a duplicate column, which is okay
                }
                _ => return Err(e.into()),
            }
        }

        // Create performance indexes
        Self::create_indexes(conn)?;

        Ok(())
    }

    /// Create database indexes for performance
    fn create_indexes(conn: &Connection) -> Result<()> {
        // Index on messages.sender for contact queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender)", [])?;
        
        // Index on messages.date_created for date range queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_date_created ON messages(date_created)", [])?;
        
        // Composite index for sender + date queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_sender_date ON messages(sender, date_created)", [])?;
        
        // Index on messages.imessage_id for duplicate detection
        conn.execute("CREATE INDEX IF NOT EXISTS idx_messages_imessage_id ON messages(imessage_id)", [])?;
        
        // Index on contacts.name for contact lookups
        conn.execute("CREATE INDEX IF NOT EXISTS idx_contacts_name ON contacts(name)", [])?;
        
        // Index on processed_messages for processing queries
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processed_messages_original_id ON processed_messages(original_message_id)", [])?;
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processed_messages_version ON processed_messages(processing_version)", [])?;
        conn.execute("CREATE INDEX IF NOT EXISTS idx_processed_messages_original_version ON processed_messages(original_message_id, processing_version)", [])?;

        Ok(())
    }

    /// Get a connection from the pool
    pub fn get_connection(&self) -> Result<DbConnection> {
        self.pool.get().context("Failed to get database connection")
    }

    /// Initialize the database with default settings
    pub fn initialize(&self) -> Result<()> {
        let conn = self.get_connection()?;

        // Add default contacts if they don't exist
        self.ensure_contact(&conn, "Jess", None, None, true)?;
        self.ensure_contact(&conn, "Phil", Some("+18673335566"), Some("apple@phil-g.com"), false)?;
        self.ensure_contact(&conn, "Robert", Some("+17806793467"), None, false)?;
        self.ensure_contact(&conn, "Rhonda", Some("+17803944504"), None, false)?;
        self.ensure_contact(&conn, "Sherry", Some("+17807223445"), None, false)?;

        Ok(())
    }

    /// Ensure a contact exists in the database
    fn ensure_contact(&self, conn: &Connection, name: &str, phone: Option<&str>, email: Option<&str>, is_me: bool) -> Result<DbContact> {
        // Check if contact exists using prepared statement
        let contact_exists: bool = conn.query_row(
            "SELECT EXISTS(SELECT 1 FROM contacts WHERE name = ?)",
            params![name],
            |row| row.get(0),
        )?;

        if !contact_exists {
            // Insert new contact using prepared statement
            conn.execute(
                "INSERT INTO contacts (name, phone, email, is_me) VALUES (?, ?, ?, ?)",
                params![name, phone.map(ToString::to_string), email.map(ToString::to_string), is_me],
            )?;
        }

        // Return the contact
        self.get_contact(name)?.ok_or_else(|| anyhow::anyhow!("Failed to retrieve contact"))
    }

    /// Add a new message to the database if it doesn't already exist
    pub fn add_message(&self, new_message: NewMessage) -> Result<DbMessage> {
        let conn = self.get_connection()?;

        // Check if message already exists using prepared statement
        let existing: Option<DbMessage> = conn
            .query_row(
                "SELECT * FROM messages WHERE imessage_id = ?",
                params![new_message.imessage_id],
                |row| self.map_db_message(row),
            )
            .optional()?;

        if let Some(message) = existing {
            // Message already exists, return it
            Ok(message)
        } else {
            // Insert new message
            let date_imported = new_message.date_imported.unwrap_or_else(|| Utc::now().naive_utc());

            conn.execute(
                "INSERT INTO messages (imessage_id, text, sender, is_from_me, date_created, date_imported, handle_id, service, thread_id, has_attachments, contact_id) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                params![
                    new_message.imessage_id,
                    new_message.text,
                    new_message.sender,
                    new_message.is_from_me,
                    new_message.date_created,
                    date_imported,
                    new_message.handle_id,
                    new_message.service,
                    new_message.thread_id,
                    new_message.has_attachments,
                    new_message.contact_id
                ],
            )?;

            // Get the last inserted ID
            let id: i64 = conn.last_insert_rowid();

            // Return the newly inserted message
            Ok(DbMessage {
                id: id as i32,
                imessage_id: new_message.imessage_id,
                text: new_message.text,
                sender: new_message.sender,
                is_from_me: new_message.is_from_me,
                date_created: new_message.date_created,
                date_imported,
                handle_id: new_message.handle_id,
                service: new_message.service,
                thread_id: new_message.thread_id,
                has_attachments: new_message.has_attachments,
                contact_id: new_message.contact_id,
            })
        }
    }

    /// Get messages for a contact within a date range
    pub fn get_messages(
        &self, contact_name: &str, start_date: Option<NaiveDateTime>, end_date: Option<NaiveDateTime>,
    ) -> Result<Vec<DbMessage>> {
        let conn = self.get_connection()?;

        // Build query with proper indexing hints
        let query = match (start_date, end_date) {
            (Some(_), Some(_)) => "SELECT * FROM messages WHERE sender = ? AND date_created >= ? AND date_created <= ? ORDER BY date_created ASC",
            (Some(_), None) => "SELECT * FROM messages WHERE sender = ? AND date_created >= ? ORDER BY date_created ASC",
            (None, Some(_)) => "SELECT * FROM messages WHERE sender = ? AND date_created <= ? ORDER BY date_created ASC",
            (None, None) => "SELECT * FROM messages WHERE sender = ? ORDER BY date_created ASC",
        };

        // Execute query with proper parameters
        let mut stmt = conn.prepare(query)?;
        let message_iter = match (start_date, end_date) {
            (Some(start), Some(end)) => stmt.query_map(params![contact_name, start, end], |row| self.map_db_message(row))?,
            (Some(start), None) => stmt.query_map(params![contact_name, start], |row| self.map_db_message(row))?,
            (None, Some(end)) => stmt.query_map(params![contact_name, end], |row| self.map_db_message(row))?,
            (None, None) => stmt.query_map(params![contact_name], |row| self.map_db_message(row))?,
        };

        let mut results = Vec::new();
        for message in message_iter {
            results.push(message?);
        }

        Ok(results)
    }

    /// Map a database row to a DbMessage
    fn map_db_message(&self, row: &Row<'_>) -> rusqlite::Result<DbMessage> {
        Ok(DbMessage {
            id: row.get(0)?,
            imessage_id: row.get(1)?,
            text: row.get(2)?,
            sender: row.get(3)?,
            is_from_me: row.get(4)?,
            date_created: row.get(5)?,
            date_imported: row.get(6)?,
            handle_id: row.get(7)?,
            service: row.get(8)?,
            thread_id: row.get(9)?,
            has_attachments: row.get(10)?,
            contact_id: row.get(11)?,
        })
    }

    /// Map a database row to a DbContact
    fn map_db_contact(&self, row: &Row<'_>) -> rusqlite::Result<DbContact> {
        Ok(DbContact {
            id: row.get(0)?,
            name: row.get(1)?,
            phone: row.get(2)?,
            email: row.get(3)?,
            is_me: row.get(4)?,
        })
    }

    /// Get a message by ID
    pub fn get_message_by_id(&self, message_id: i32) -> Result<Option<DbMessage>> {
        let conn = self.get_connection()?;

        let message = conn
            .query_row(
                "SELECT * FROM messages WHERE id = ?",
                params![message_id],
                |row| self.map_db_message(row),
            )
            .optional()?;

        Ok(message)
    }

    /// Get a contact by name
    pub fn get_contact(&self, name: &str) -> Result<Option<DbContact>> {
        let conn = self.get_connection()?;

        let contact = conn
            .query_row(
                "SELECT * FROM contacts WHERE name = ?",
                params![name],
                |row| self.map_db_contact(row),
            )
            .optional()?;

        Ok(contact)
    }

    /// Add a new contact or update an existing one with improved identifier handling
    pub fn add_or_update_contact(&self, new_contact: NewContact) -> Result<DbContact> {
        let conn = self.get_connection()?;

        // Check if contact already exists by name
        let existing: Option<DbContact> = conn
            .query_row(
                "SELECT * FROM contacts WHERE name = ? AND is_me = ?",
                params![new_contact.name, new_contact.is_me],
                |row| self.map_db_contact(row),
            )
            .optional()?;

        if let Some(contact) = existing {
            // Update existing contact if needed
            let mut update_fields = Vec::new();
            let mut update_params: Vec<Box<dyn rusqlite::ToSql>> = Vec::new();

            if let Some(phone) = &new_contact.phone {
                if contact.phone.as_ref() != Some(phone) {
                    update_fields.push(format!("{} = ?", "phone"));
                    update_params.push(Box::new(phone.clone()));
                }
            }

            if let Some(email) = &new_contact.email {
                if contact.email.as_ref() != Some(email) {
                    update_fields.push(format!("{} = ?", "email"));
                    update_params.push(Box::new(email.clone()));
                }
            }

            if !update_fields.is_empty() {
                // Add the contact ID for the WHERE clause
                update_params.push(Box::new(contact.id));

                let query = format!("UPDATE contacts SET {} WHERE id = ?", update_fields.join(", "));

                conn.execute(&query, rusqlite::params_from_iter(update_params.iter()))?;

                // Get the updated contact
                return self
                    .get_contact(&new_contact.name)?
                    .ok_or_else(|| anyhow::anyhow!("Failed to retrieve updated contact"));
            }

            Ok(contact)
        } else {
            // Insert new contact
            conn.execute(
                "INSERT INTO contacts (name, phone, email, is_me) VALUES (?, ?, ?, ?)",
                params![new_contact.name, new_contact.phone, new_contact.email, new_contact.is_me],
            )?;

            // Get the newly inserted contact
            self.get_contact(&new_contact.name)?
                .ok_or_else(|| anyhow::anyhow!("Failed to retrieve newly inserted contact"))
        }
    }

    /// Get all messages for a specific person, combining both phone and email conversations
    pub fn get_conversation_with_person(
        &self, person_name: &str, start_date: Option<NaiveDateTime>, end_date: Option<NaiveDateTime>,
    ) -> Result<Vec<DbMessage>> {
        let conn = self.get_connection()?;

        // Get the contact
        let _contact = self
            .get_contact(person_name)?
            .ok_or_else(|| anyhow::anyhow!("Contact not found: {}", person_name))?;

        // Get messages where the sender is the person or where I sent messages
        // Use a more efficient query with proper indexing
        let query = match (start_date, end_date) {
            (Some(_), Some(_)) => "SELECT * FROM messages WHERE (sender = ? OR is_from_me = ?) AND date_created >= ? AND date_created <= ? ORDER BY date_created ASC",
            (Some(_), None) => "SELECT * FROM messages WHERE (sender = ? OR is_from_me = ?) AND date_created >= ? ORDER BY date_created ASC",
            (None, Some(_)) => "SELECT * FROM messages WHERE (sender = ? OR is_from_me = ?) AND date_created <= ? ORDER BY date_created ASC",
            (None, None) => "SELECT * FROM messages WHERE (sender = ? OR is_from_me = ?) ORDER BY date_created ASC",
        };

        // Execute query with proper parameters
        let mut stmt = conn.prepare(query)?;
        let message_iter = match (start_date, end_date) {
            (Some(start), Some(end)) => stmt.query_map(params![person_name, true, start, end], |row| self.map_db_message(row))?,
            (Some(start), None) => stmt.query_map(params![person_name, true, start], |row| self.map_db_message(row))?,
            (None, Some(end)) => stmt.query_map(params![person_name, true, end], |row| self.map_db_message(row))?,
            (None, None) => stmt.query_map(params![person_name, true], |row| self.map_db_message(row))?,
        };

        let mut results = Vec::new();
        for message in message_iter {
            results.push(message?);
        }

        Ok(results)
    }

    /// Add a new processed message to the database
    pub fn add_processed_message(&self, new_processed: NewProcessedMessage) -> Result<DbProcessedMessage> {
        let conn = self.get_connection()?;

        // Check if processed message already exists
        let existing: Option<DbProcessedMessage> = conn
            .query_row(
                "SELECT * FROM processed_messages WHERE original_message_id = ? AND processing_version = ?",
                params![new_processed.original_message_id, new_processed.processing_version],
                |row| self.map_db_processed_message(row),
            )
            .optional()?;

        if let Some(processed) = existing {
            // Processed message already exists, return it
            Ok(processed)
        } else {
            // Insert new processed message
            let now = Utc::now().naive_utc();

            conn.execute(
                "INSERT INTO processed_messages (original_message_id, processed_text, tokens, lemmatized_text, named_entities, sentiment_score, processed_at, processing_version) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                params![
                    new_processed.original_message_id,
                    new_processed.processed_text,
                    new_processed.tokens,
                    new_processed.lemmatized_text,
                    new_processed.named_entities,
                    new_processed.sentiment_score,
                    now,
                    new_processed.processing_version
                ],
            )?;

            // Get the last inserted ID
            let id: i64 = conn.last_insert_rowid();

            // Return the newly inserted processed message
            Ok(DbProcessedMessage {
                id: id as i32,
                original_message_id: new_processed.original_message_id,
                processed_text: new_processed.processed_text,
                tokens: new_processed.tokens,
                lemmatized_text: new_processed.lemmatized_text,
                named_entities: new_processed.named_entities,
                sentiment_score: new_processed.sentiment_score,
                processed_at: now,
                processing_version: new_processed.processing_version,
            })
        }
    }

    /// Map a database row to a DbProcessedMessage
    fn map_db_processed_message(&self, row: &Row<'_>) -> rusqlite::Result<DbProcessedMessage> {
        Ok(DbProcessedMessage {
            id: row.get(0)?,
            original_message_id: row.get(1)?,
            processed_text: row.get(2)?,
            tokens: row.get(3)?,
            lemmatized_text: row.get(4)?,
            named_entities: row.get(5)?,
            sentiment_score: row.get(6)?,
            processed_at: row.get(7)?,
            processing_version: row.get(8)?,
        })
    }

    /// Get a processed message by original message ID and processing version
    pub fn get_processed_message(&self, message_id: i32, version: &str) -> Result<Option<DbProcessedMessage>> {
        let conn = self.get_connection()?;

        let processed = conn
            .query_row(
                "SELECT * FROM processed_messages WHERE original_message_id = ? AND processing_version = ?",
                params![message_id, version],
                |row| self.map_db_processed_message(row),
            )
            .optional()?;

        Ok(processed)
    }

    /// Get all processed messages for a specific processing version
    pub fn get_processed_messages_by_version(&self, version: &str) -> Result<Vec<DbProcessedMessage>> {
        let conn = self.get_connection()?;

        let mut stmt = conn.prepare("SELECT * FROM processed_messages WHERE processing_version = ?")?;

        let processed_iter = stmt.query_map(params![version], |row| self.map_db_processed_message(row))?;

        let mut results = Vec::new();
        for processed in processed_iter {
            results.push(processed?);
        }

        Ok(results)
    }

    /// Get all messages that have not been processed with a specific version
    pub fn get_unprocessed_message_ids(&self, version: &str) -> Result<Vec<i32>> {
        let conn = self.get_connection()?;

        let query = "SELECT m.id FROM messages m LEFT JOIN processed_messages p ON m.id = p.original_message_id AND p.processing_version = ? WHERE p.id IS NULL";

        let mut stmt = conn.prepare(&query)?;
        let id_iter = stmt.query_map(params![version], |row| row.get::<_, i32>(0))?;

        let mut results = Vec::new();
        for id in id_iter {
            results.push(id?);
        }

        Ok(results)
    }

    /// Get statistics about processed messages
    pub fn get_processing_stats(&self) -> Result<ProcessingStats> {
        let conn = self.get_connection()?;

        // Get total message count
        let total_messages: i64 = conn.query_row("SELECT COUNT(*) FROM messages", params![], |row| row.get(0))?;

        // Get processed message count
        let processed_messages: i64 = conn.query_row("SELECT COUNT(*) FROM processed_messages", params![], |row| {
            row.get(0)
        })?;

        // Get unique processing versions
        let mut stmt = conn.prepare("SELECT DISTINCT processing_version FROM processed_messages")?;

        let version_iter = stmt.query_map(params![], |row| row.get::<_, String>(0))?;

        let mut versions = Vec::new();
        for version in version_iter {
            versions.push(version?);
        }

        Ok(ProcessingStats {
            total_messages: total_messages as usize,
            processed_messages: processed_messages as usize,
            processing_versions: versions,
        })
    }

    /// Get messages for a contact by name within a date range
    pub fn get_messages_by_contact_name(
        &self, contact_name: &str, date_range: &crate::models::DateRange,
    ) -> Result<Vec<crate::models::Message>> {
        let start_date = date_range.start.map(|dt| dt.naive_local());
        let end_date = date_range.end.map(|dt| dt.naive_local());

        // Get the raw database messages
        let db_messages = self.get_messages(contact_name, start_date, end_date)?;

        // Convert to the original Message format
        let messages: Vec<_> = db_messages.into_iter().map(|m| m.to_message()).collect();

        Ok(messages)
    }
}

/// Statistics about message processing
#[derive(Debug)]
pub struct ProcessingStats {
    pub total_messages: usize,
    pub processed_messages: usize,
    pub processing_versions: Vec<String>,
}

/// Initialize the database connection
pub fn establish_connection() -> Result<Database> {
    // Get database URL from environment or use default
    let database_url = std::env::var("DATABASE_URL").unwrap_or_else(|_| "sqlite:data/messages.db".to_string());

    // Create database connection
    let database = Database::new(&database_url)?;

    // Initialize with default data
    database.initialize()?;

    Ok(database)
}

