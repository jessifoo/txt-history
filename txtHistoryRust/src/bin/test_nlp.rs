use anyhow::Result;
use chrono::Local;
use txt_history_rust::{
    db,
    models::{DbMessage, NewMessage},
    nlp::NlpProcessor,
};

fn main() -> Result<()> {
    // Initialize database
    let db = db::establish_connection()?;
    db.initialize()?;

    println!("Testing NLP processing functionality...");

    // Create a test processor
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");

    // Create some test messages if they don't exist
    ensure_test_messages(&db)?;

    // Get unprocessed message IDs
    let unprocessed_ids = db.get_unprocessed_message_ids("test_v1")?;
    println!("Found {} unprocessed messages", unprocessed_ids.len());

    if unprocessed_ids.is_empty() {
        println!("No unprocessed messages found. All messages may have been processed already.");

        // Get processing stats
        let stats = db.get_processing_stats()?;
        println!("\nProcessing Statistics:");
        println!("Total messages in database: {}", stats.total_messages);
        println!("Total processed messages: {}", stats.processed_messages);
        println!("Processing versions: {:?}", stats.processing_versions);

        return Ok(());
    }

    // Process a batch of messages
    let batch_size = 10.min(unprocessed_ids.len());
    let batch_ids = &unprocessed_ids[0..batch_size];

    println!("Processing a batch of {} messages...", batch_ids.len());
    let processed = processor.process_messages(&db, batch_ids)?;

    // Print results
    println!("Successfully processed {} messages", processed.len());

    for (i, proc_msg) in processed.iter().enumerate() {
        // Get original message
        if let Some(orig_msg) = db.get_message_by_id(proc_msg.original_message_id)? {
            println!("\nMessage {}: ", i + 1);
            println!("Original: {}", orig_msg.text.as_deref().unwrap_or(""));
            println!("Processed: {}", proc_msg.processed_text);

            if let Some(tokens) = &proc_msg.tokens {
                println!("Tokens: {}", tokens);
            }

            if let Some(lemmatized) = &proc_msg.lemmatized_text {
                println!("Lemmatized: {}", lemmatized);
            }

            if let Some(entities) = &proc_msg.named_entities {
                println!("Named Entities: {}", entities);
            }

            if let Some(sentiment) = proc_msg.sentiment_score {
                println!("Sentiment Score: {:.2}", sentiment);
                let sentiment_label = match sentiment {
                    s if s > 0.3 => "Positive",
                    s if s < -0.3 => "Negative",
                    _ => "Neutral",
                };
                println!("Sentiment: {}", sentiment_label);
            }
        }
    }

    println!("\nTest completed successfully!");
    Ok(())
}

// Helper function to ensure we have some test messages in the database
fn ensure_test_messages(db: &db::Database) -> Result<()> {
    // Check if we already have messages
    let conn = &mut db.get_connection()?;
    let count: i64 = conn.query_row("SELECT COUNT(*) FROM messages", [], |row| row.get(0))?;

    if count > 0 {
        println!("Database already contains {} messages", count);
        return Ok(());
    }

    println!("Creating test messages...");

    // Sample test messages
    let test_messages = vec![
        (
            "Jess",
            "I'm so happy with the progress we've made on this project!",
            true,
        ),
        (
            "Phil",
            "I don't like how this feature is working. It's terrible.",
            false,
        ),
        (
            "Robert",
            "Can you meet me at the coffee shop on Main Street at 3pm?",
            false,
        ),
        (
            "Jess",
            "The weather is nice today, but I think it might rain tomorrow.",
            true,
        ),
        (
            "Rhonda",
            "I just finished reading that book you recommended. It was amazing!",
            false,
        ),
        (
            "Jess",
            "I'm having trouble with the code. Nothing is working right now.",
            true,
        ),
        (
            "Phil",
            "Let's discuss this issue with John and Sarah from the marketing team.",
            false,
        ),
        (
            "Jess",
            "https://example.com has some great resources on this topic! 😊",
            true,
        ),
        (
            "Sherry",
            "The meeting is scheduled for Tuesday at 10am in Conference Room A.",
            false,
        ),
        (
            "Jess",
            "I love working with this team! Everyone is so supportive and knowledgeable.",
            true,
        ),
    ];

    // Add messages to database
    for (sender, text, is_from_me) in test_messages {
        let now = Local::now().naive_local();
        let new_message = NewMessage {
            imessage_id: format!("test_{}", rand::random::<u64>()),
            text: Some(text.to_string()),
            sender: sender.to_string(),
            is_from_me,
            date_created: now,
            date_imported: Some(now),
            handle_id: Some("test_handle".to_string()),
            service: Some("iMessage".to_string()),
            thread_id: Some("test_thread".to_string()),
            has_attachments: false,
            contact_id: None,
        };

        db.add_message(new_message)?;
    }

    println!("Added 10 test messages to the database");
    Ok(())
}
