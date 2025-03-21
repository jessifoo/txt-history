mod db;
mod models;
mod nlp;
mod repository;
mod schema;

use anyhow::{Context, Result};
use chrono::{DateTime, Local, NaiveDateTime};
use clap::{Parser, Subcommand};
use imessage_database::util::dirs;
use repository::IMessageDatabaseRepo;
use std::path::PathBuf;

use crate::db::Database;
use crate::models::{Contact, DateRange, OutputFormat};
use crate::nlp::NlpProcessor;

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
            start_date,
            end_date,
            format,
            size,
            lines,
            output_dir,
        } => import_messages(name, start_date, end_date, format, *size, *lines, output_dir),
        Commands::Query {
            name,
            start_date,
            end_date,
            format,
            size,
            lines,
            output_dir,
        } => query_messages(&db, name, start_date, end_date, format, *size, *lines, output_dir),
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
        } => process_messages(&db, version, name, start_date, end_date, *batch_size, *stats),
    }
}

/// Import messages from iMessage database
fn import_messages(
    name: &str, start_date: &Option<String>, end_date: &Option<String>, format: &str, size: Option<f64>, lines: Option<usize>,
    output_dir: &str,
) -> Result<()> {
    // Get iMessage database path
    let chat_db_path = dirs::get_imessage_chat_db_path().context("Failed to locate iMessage database")?;

    println!("Using iMessage database at: {}", chat_db_path.display());

    // Create repository
    let repo = IMessageDatabaseRepo::new(chat_db_path)?;

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

    // Fetch messages
    println!("Fetching messages...");
    let messages = repo.fetch_messages(&contact, &date_range).await?;
    println!("Found {} messages", messages.len());

    // Determine output format
    let output_format = match format.to_lowercase().as_str() {
        "csv" => OutputFormat::Csv,
        _ => OutputFormat::Txt,
    };

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Write messages to files
    write_messages_to_files(&messages, output_format, size, lines, output_dir)?;

    Ok(())
}

/// Query messages from the database
fn query_messages(
    db: &Database, name: &str, start_date: &Option<String>, end_date: &Option<String>, format: &str, size: Option<f64>,
    lines: Option<usize>, output_dir: &str,
) -> Result<()> {
    // Get contact
    let contact_info = match db.get_contact(name)? {
        Some(contact) => contact,
        None => return Err(anyhow::anyhow!("Contact not found: {}", name)),
    };

    println!("Looking up messages for: {}", contact_info.name);

    // Parse date range
    let date_range = parse_date_range(start_date, end_date)?;
    let start_naive = date_range.start.map(|dt| dt.naive_local());
    let end_naive = date_range.end.map(|dt| dt.naive_local());

    if let Some(start) = &date_range.start {
        println!("Start date: {}", start.format("%Y-%m-%d"));
    }
    if let Some(end) = &date_range.end {
        println!("End date: {}", end.format("%Y-%m-%d"));
    }

    // Fetch messages
    println!("Fetching messages...");
    let db_messages = db.get_messages(&contact_info.name, start_naive, end_naive)?;
    println!("Found {} messages", db_messages.len());

    // Convert to the original Message format
    let messages: Vec<_> = db_messages.into_iter().map(|m| m.to_message()).collect();

    // Determine output format
    let output_format = match format.to_lowercase().as_str() {
        "csv" => OutputFormat::Csv,
        _ => OutputFormat::Txt,
    };

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Write messages to files
    write_messages_to_files(&messages, output_format, size, lines, output_dir)?;

    Ok(())
}

/// Export conversation with a specific person
async fn export_conversation_by_person(
    db: &Database, name: &str, start_date: &Option<String>, end_date: &Option<String>, size_mb: Option<f64>,
    lines_per_chunk: Option<usize>, output_dir: &str,
) -> Result<()> {
    println!("Exporting conversation with {}", name);

    // Create output directory if it doesn't exist
    std::fs::create_dir_all(output_dir)?;

    // Parse date range
    let date_range = parse_date_range(start_date, end_date)?;

    // Create repository
    let chat_db_path = dirs::chat_db_path().context("Failed to get iMessage database path")?;
    let repo = IMessageDatabaseRepo::new(chat_db_path)?;

    // Create output path
    let output_path = std::path::Path::new(output_dir).join(format!("{}_conversation", name));

    // Export conversation
    let output_files = repo
        .export_conversation_by_person(
            name,
            OutputFormat::Txt, // This is ignored as both formats are created
            &output_path,
            &date_range,
            size_mb.map(|s| s as usize),
            lines_per_chunk,
        )
        .await?;

    if output_files.is_empty() {
        println!("No messages found for {} in the specified date range", name);
    } else {
        println!("Successfully exported conversation with {}:", name);
        for file in output_files {
            println!("  - {}", file.display());
        }
    }

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
            None => return Err(anyhow::anyhow!("Contact not found: {}", contact_name)),
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
    // In a real application, you might look up the contact in an address book
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
            return Err(anyhow::anyhow!(
                "Contact not found: {}. Available contacts: Jess, Phil, Robert, Rhonda, Sherry",
                name
            ));
        },
    };

    Ok(contact)
}

/// Parse date range from string options
fn parse_date_range(start_date: &Option<String>, end_date: &Option<String>) -> Result<DateRange> {
    let start = if let Some(date_str) = start_date {
        Some(
            DateTime::parse_from_str(&format!("{} 00:00:00 +0000", date_str), "%Y-%m-%d %H:%M:%S %z")
                .context("Invalid start date format, use YYYY-MM-DD")?
                .with_timezone(&Local),
        )
    } else {
        None
    };

    let end = if let Some(date_str) = end_date {
        Some(
            DateTime::parse_from_str(&format!("{} 23:59:59 +0000", date_str), "%Y-%m-%d %H:%M:%S %z")
                .context("Invalid end date format, use YYYY-MM-DD")?
                .with_timezone(&Local),
        )
    } else {
        None
    };

    Ok(DateRange { start, end })
}

/// Write messages to files with chunking
fn write_messages_to_files(
    messages: &[models::Message], format: OutputFormat, size_mb: Option<f64>, lines_per_chunk: Option<usize>, output_dir: &str,
) -> Result<()> {
    if messages.is_empty() {
        println!("No messages to write");
        return Ok(());
    }

    // Determine chunking strategy
    let chunk_size = if let Some(size) = size_mb {
        // Estimate bytes per message and calculate chunk size
        let avg_msg_size = messages
            .iter()
            .map(|m| m.content.len() + m.sender.len() + 50) // Add some overhead for formatting
            .sum::<usize>() as f64
            / messages.len() as f64;

        let bytes_per_mb = 1024.0 * 1024.0;
        let msgs_per_chunk = (size * bytes_per_mb / avg_msg_size).ceil() as usize;
        msgs_per_chunk.max(1) // Ensure at least one message per chunk
    } else if let Some(lines) = lines_per_chunk {
        lines
    } else {
        // Default to all messages in one file
        messages.len()
    };

    // Create chunks
    let chunks: Vec<_> = messages.chunks(chunk_size).collect();
    println!("Writing {} chunks", chunks.len());

    // Process each chunk
    for (i, chunk) in chunks.iter().enumerate() {
        let chunk_num = i + 1;
        let file_base = format!("{}/chunk_{}", output_dir, chunk_num);

        match format {
            OutputFormat::Txt => {
                let file_path = format!("{}.txt", file_base);
                write_txt_file(chunk, &file_path)?;
                println!("Wrote {} messages to {}", chunk.len(), file_path);
            },
            OutputFormat::Csv => {
                let file_path = format!("{}.csv", file_base);
                write_csv_file(chunk, &file_path)?;
                println!("Wrote {} messages to {}", chunk.len(), file_path);
            },
        }
    }

    Ok(())
}

/// Write messages to a text file
fn write_txt_file(messages: &[models::Message], file_path: &str) -> Result<()> {
    use std::fs::File;
    use std::io::{BufWriter, Write};

    let file = File::create(file_path)?;
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

    Ok(())
}

/// Write messages to a CSV file
fn write_csv_file(messages: &[models::Message], file_path: &str) -> Result<()> {
    use std::fs::File;
    use std::io::BufWriter;

    let file = File::create(file_path)?;
    let mut writer = csv::Writer::from_writer(BufWriter::new(file));

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
