mod db;
mod error;
mod file_writer;
mod models;
mod nlp;
mod repository;
mod schema;
mod utils;

use std::path::PathBuf;

use chrono::{DateTime, Local};
use clap::{Parser, Subcommand};
use imessage_database::util::dirs;

use crate::{
    db::Database,
    error::{Result, TxtHistoryError},
    file_writer::{write_messages_to_file, write_messages_to_timestamped_dir},
    models::{Contact, DateRange, OutputFormat},
    nlp::NlpProcessor,
    repository::IMessageDatabaseRepo,
    utils::{chunk_by_lines, chunk_by_size},
};

#[derive(Parser)]
#[command(author, version, about, long_about = None)]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Import messages from iMessage database
    Import {
        /// Name of the contact (default: "Phil")
        #[arg(short, long, default_value = "Phil")]
        name: String,

        /// Start date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        date: Option<String>,

        /// End date for message range (YYYY-MM-DD)
        #[arg(short = 'e', long)]
        end_date: Option<String>,

        /// Size of each chunk in MB
        #[arg(short = 's', long)]
        size: Option<f64>,

        /// Number of lines per chunk
        #[arg(short, long)]
        lines: Option<usize>,

        /// Output directory
        #[arg(short, long, default_value = "./output")]
        output: Option<String>,

        /// Export only the contact's messages, excluding your replies
        #[arg(long)]
        one_side: bool,
    },
    /// Query messages from the database
    Query {
        /// Name of the contact
        #[arg(short, long)]
        name: String,

        /// Start date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        start_date: Option<String>,

        /// End date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        end_date: Option<String>,

        /// Output format (txt or csv)
        #[arg(short, long, default_value = "txt")]
        format: String,

        /// Size of each chunk in MB
        #[arg(short, long)]
        size: Option<f64>,

        /// Number of lines per chunk
        #[arg(short, long)]
        lines: Option<usize>,

        /// Output directory
        #[arg(short, long, default_value = "./output")]
        output_dir: String,
    },
    /// Export conversation with a specific person
    ExportByPerson {
        /// Name of the person
        #[arg(short, long, default_value = "Phil")]
        name: String,

        /// Start date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        start_date: Option<String>,

        /// End date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        end_date: Option<String>,

        /// Size of each chunk in MB
        #[arg(short, long)]
        size: Option<f64>,

        /// Number of lines per chunk
        #[arg(short, long)]
        lines: Option<usize>,

        /// Output directory
        #[arg(short, long, default_value = "./output")]
        output_dir: String,
    },
    /// Process messages with NLP
    Process {
        /// Processing version identifier
        #[arg(short, long, default_value = "v1.0")]
        version: String,

        /// Name of the contact (optional, process all if not specified)
        #[arg(short, long)]
        name: Option<String>,

        /// Start date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        start_date: Option<String>,

        /// End date for message range (YYYY-MM-DD)
        #[arg(short, long)]
        end_date: Option<String>,

        /// Batch size for processing
        #[arg(short, long, default_value = "100")]
        batch_size: usize,

        /// Show processing statistics
        #[arg(short, long)]
        stats: bool,
    },
}

#[tokio::main]
async fn main() -> Result<()> {
    // Parse command line arguments
    let cli = Cli::parse();

    // Initialize database
    let db = db::establish_connection()?;
    db.initialize()?;

    // Process command
    match &cli.command {
        Commands::Import {
            name,
            date,
            end_date,
            size,
            lines,
            output,
            one_side,
        } => import_messages(name, date, end_date, size, *lines, output.as_deref(), *one_side).await?,
        Commands::Query {
            name,
            start_date,
            end_date,
            format,
            size,
            lines,
            output_dir,
        } => query_messages(&db, name, start_date, end_date, format, *size, *lines, output_dir)?,
        Commands::ExportByPerson {
            name,
            start_date,
            end_date,
            size,
            lines,
            output_dir,
        } => export_conversation_by_person(&db, name, start_date, end_date, *size, *lines, output_dir).await?,
        Commands::Process {
            version,
            name,
            start_date,
            end_date,
            batch_size,
            stats,
        } => process_messages(&db, version, name, start_date, end_date, *batch_size, *stats)?,
    }

    Ok(())
}

/// Import messages from iMessage database (matches Python script behavior)
async fn import_messages(
    name: &str, date: &Option<String>, end_date: &Option<String>, size: Option<f64>, lines: Option<usize>, output_dir: Option<&str>,
    only_contact: bool,
) -> Result<()> {
    // Get iMessage database path
    let chat_db_path =
        dirs::get_chat_db().map_err(|e| TxtHistoryError::IMessageDatabase(format!("Failed to locate iMessage database: {}", e)))?;

    println!("Using iMessage database at: {}", chat_db_path.display());

    // Create repository
    let repo = IMessageDatabaseRepo::new(chat_db_path)?;

    // Parse date range
    let date_range = parse_date_range(date, end_date)?;

    // Get contact information
    let contact = get_contact_info(name)?;

    // Fetch messages
    println!("Fetching messages for contact: {}", contact.name);
    let mut messages = repo.fetch_messages(&contact, &date_range, only_contact).await?;

    // Ensure messages are sorted chronologically (ascending)
    messages.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));

    println!("Found {} messages", messages.len());

    if messages.is_empty() {
        println!("No messages found for {} in the specified date range", contact.name);
        return Ok(());
    }

    // Determine output directory
    let output_path = output_dir.map(PathBuf::from).unwrap_or_else(|| PathBuf::from("./output"));

    // Generate timestamp for directory structure
    let timestamp = Local::now().format("%Y-%m-%d_%H-%M-%S").to_string();

    // Chunk messages
    let chunks = if let Some(size_mb) = size {
        chunk_by_size(&messages, size_mb)
    } else if let Some(lines_count) = lines {
        chunk_by_lines(&messages, lines_count)
    } else {
        vec![messages] // No chunking
    };

    println!("Writing {} chunks", chunks.len());

    // Write chunks to timestamped directories (matching Python structure)
    let mut all_files = Vec::new();
    for (i, chunk) in chunks.iter().enumerate() {
        let chunk_num = i + 1;

        // Write TXT format
        let txt_dir = output_path.join(&timestamp).join("chunks_txt");
        std::fs::create_dir_all(&txt_dir)?;
        let txt_file = txt_dir.join(format!("chunk_{}.txt", chunk_num));
        write_messages_to_file(chunk, OutputFormat::Txt, &txt_file)?;
        all_files.push(txt_file.clone());
        println!("Wrote {} messages to {}", chunk.len(), txt_file.display());

        // Write CSV format
        let csv_dir = output_path.join(&timestamp).join("chunks_csv");
        std::fs::create_dir_all(&csv_dir)?;
        let csv_file = csv_dir.join(format!("chunk_{}.csv", chunk_num));
        write_messages_to_file(chunk, OutputFormat::Csv, &csv_file)?;
        all_files.push(csv_file.clone());
        println!("Wrote {} messages to {}", chunk.len(), csv_file.display());
    }

    println!("Export complete! Files written to: {}", output_path.join(&timestamp).display());
    Ok(())
}

/// Query messages from the database
fn query_messages(
    db: &Database, name: &str, start_date: &Option<String>, end_date: &Option<String>, format: &str, size: Option<f64>,
    lines: Option<usize>, output_dir: &str,
) -> Result<()> {
    // Get contact info
    let contact = get_contact_info(name)?;
    println!("Looking up messages for: {}", contact.name);

    // Parse date range
    let date_range = parse_date_range(start_date, end_date)?;
    if let Some(start) = &date_range.start {
        println!("Start date: {}", start.format("%Y-%m-%d"));
    }
    if let Some(end) = &date_range.end {
        println!("End date: {}", end.format("%Y-%m-%d"));
    }

    // Determine output format
    let output_format = match format.to_lowercase().as_str() {
        "txt" => OutputFormat::Txt,
        "csv" => OutputFormat::Csv,
        "json" => OutputFormat::Json,
        _ => {
            println!("Invalid format: {}. Using txt as default.", format);
            OutputFormat::Txt
        },
    };

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Query messages
    println!("Querying messages...");
    let messages = db.get_messages_by_contact_name(&contact.name, &date_range)?;
    println!("Found {} messages", messages.len());

    // Write messages to files
    write_messages_to_files(&messages, output_format, size, lines, output_dir)?;

    Ok(())
}

/// Export conversation with a specific person
async fn export_conversation_by_person(
    db: &Database, name: &str, start_date: &Option<String>, end_date: &Option<String>, size_mb: Option<f64>,
    lines_per_chunk: Option<usize>, output_dir: &str,
) -> Result<()> {
    // Parse date range
    let date_range = parse_date_range(start_date, end_date)?;

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Create output path
    let output_path = std::path::Path::new(output_dir);

    // Create repository
    let repo = crate::repository::Repository::new(db.clone());

    // Export conversation
    println!("Exporting conversation with: {}", name);

    // Export in both TXT and CSV formats
    let txt_files = repo
        .export_conversation_by_person(name, &date_range, OutputFormat::Txt, size_mb, lines_per_chunk, output_path)
        .await?;
    println!("Exported {} TXT files", txt_files.len());

    let csv_files = repo
        .export_conversation_by_person(name, &date_range, OutputFormat::Csv, size_mb, lines_per_chunk, output_path)
        .await?;
    println!("Exported {} CSV files", csv_files.len());

    Ok(())
}

/// Process messages with NLP
fn process_messages(
    db: &Database, version: &str, name: &Option<String>, start_date: &Option<String>, end_date: &Option<String>, batch_size: usize,
    show_stats: bool,
) -> Result<()> {
    // Create NLP processor
    let processor = NlpProcessor::new(version);
    println!("Using NLP processor version: {}", version);

    // Parse date range
    let date_range = parse_date_range(start_date, end_date)?;
    let start_naive = date_range.start.map(|dt| dt.naive_local());
    let end_naive = date_range.end.map(|dt| dt.naive_local());

    // Get message IDs to process
    let message_ids = if let Some(contact_name) = name {
        // Get contact
        let contact_info = match db.get_contact(contact_name)? {
            Some(contact) => contact,
            None => return Err(TxtHistoryError::ContactNotFound(format!("Contact not found: {}", contact_name))),
        };

        println!("Processing messages for: {}", contact_info.name);

        // Fetch messages
        let db_messages = db.get_messages(&contact_info.name, start_naive, end_naive)?;
        println!("Found {} messages to process", db_messages.len());

        // Get message IDs
        db_messages.into_iter().map(|m| m.id).collect::<Vec<_>>()
    } else {
        // Get all unprocessed message IDs
        let unprocessed_ids = db.get_unprocessed_message_ids(version)?;
        println!("Found {} unprocessed messages", unprocessed_ids.len());
        unprocessed_ids
    };

    // Process messages in batches
    let total_messages = message_ids.len();
    let mut processed_count = 0;

    for chunk in message_ids.chunks(batch_size) {
        let batch_ids = chunk.to_vec();
        let batch_size = batch_ids.len();

        println!("Processing batch of {} messages...", batch_size);
        let processed = processor.process_messages(db, &batch_ids)?;

        processed_count += processed.len();
        println!("Processed {}/{} messages", processed_count, total_messages);
    }

    // Show statistics if requested
    if show_stats {
        let stats = db.get_processing_stats()?;
        println!("\nProcessing Statistics:");
        println!("Total messages in database: {}", stats.total_messages);
        println!("Total processed messages: {}", stats.processed_messages);
        println!("Processing versions: {:?}", stats.processing_versions);
    }

    println!("\nProcessing complete!");
    Ok(())
}

/// Get contact information by name
fn get_contact_info(name: &str) -> Result<Contact> {
    // For now, we'll just create a contact with the given name
    // TODO: Implement contact store with JSON persistence (like Python's
    // ContactStore)
    let contact = match name {
        "Jess" => Contact {
            name: "Jess".to_string(),
            phone: None,
            email: None,
        },
        "Phil" => Contact {
            name: "Phil".to_string(),
            phone: Some("+18673335566".to_string()),
            email: Some("apple@phil-g.com".to_string()),
        },
        "Robert" => Contact {
            name: "Robert".to_string(),
            phone: Some("+17806793467".to_string()),
            email: None,
        },
        "Rhonda" => Contact {
            name: "Rhonda".to_string(),
            phone: Some("+17803944504".to_string()),
            email: None,
        },
        "Sherry" => Contact {
            name: "Sherry".to_string(),
            phone: Some("+17807223445".to_string()),
            email: None,
        },
        _ => {
            return Err(TxtHistoryError::ContactNotFound(format!(
                "Contact not found: {}. Available contacts: Jess, Phil, Robert, Rhonda, Sherry",
                name
            )));
        },
    };

    Ok(contact)
}

/// Parse date range from string options
fn parse_date_range(start_date: &Option<String>, end_date: &Option<String>) -> Result<DateRange> {
    let start = if let Some(date_str) = start_date {
        Some(
            DateTime::parse_from_str(&format!("{} 00:00:00 +0000", date_str), "%Y-%m-%d %H:%M:%S %z")
                .map_err(|e| TxtHistoryError::InvalidDate(format!("Invalid start date format, use YYYY-MM-DD: {}", e)))?
                .with_timezone(&Local),
        )
    } else {
        None
    };

    let end = if let Some(date_str) = end_date {
        Some(
            DateTime::parse_from_str(&format!("{} 23:59:59 +0000", date_str), "%Y-%m-%d %H:%M:%S %z")
                .map_err(|e| TxtHistoryError::InvalidDate(format!("Invalid end date format, use YYYY-MM-DD: {}", e)))?
                .with_timezone(&Local),
        )
    } else {
        None
    };

    Ok(DateRange {
        start,
        end,
    })
}

/// Write messages to files with chunking (legacy function, kept for
/// compatibility)
fn write_messages_to_files(
    messages: &[crate::models::Message], format: OutputFormat, size_mb: Option<f64>, lines_per_chunk: Option<usize>, output_dir: &str,
) -> Result<()> {
    if messages.is_empty() {
        println!("No messages to write");
        return Ok(());
    }

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Chunk messages using shared utilities
    let chunks = if let Some(size) = size_mb {
        chunk_by_size(messages, size)
    } else if let Some(lines) = lines_per_chunk {
        chunk_by_lines(messages, lines)
    } else {
        vec![messages.to_vec()] // No chunking
    };

    println!("Writing {} chunks", chunks.len());

    // Process each chunk
    for (i, chunk) in chunks.iter().enumerate() {
        let chunk_num = i + 1;
        let file_base = format!("{}/chunk_{}", output_dir, chunk_num);

        match format {
            OutputFormat::Txt => {
                let file_path = format!("{}.txt", file_base);
                write_messages_to_file(chunk, format, std::path::Path::new(&file_path))?;
                println!("Wrote {} messages to {}", chunk.len(), file_path);
            },
            OutputFormat::Csv => {
                let file_path = format!("{}.csv", file_base);
                write_messages_to_file(chunk, format, std::path::Path::new(&file_path))?;
                println!("Wrote {} messages to {}", chunk.len(), file_path);
            },
            OutputFormat::Json => {
                let file_path = format!("{}.json", file_base);
                write_messages_to_file(chunk, format, std::path::Path::new(&file_path))?;
                println!("Wrote {} messages to {}", chunk.len(), file_path);
            },
        }
    }

    Ok(())
}
