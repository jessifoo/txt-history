use chrono::NaiveDateTime;
use std::path::{Path, PathBuf};
use std::fs;
use tempfile::tempdir;
use tokio::runtime::Runtime;

// Import the necessary modules from the crate
use txtHistoryRust::db::Database;
use txtHistoryRust::models::{NewContact, DbContact, NewMessage, DbMessage, Contact, DateRange, OutputFormat, Message};
use txtHistoryRust::repository::{MessageRepository, IMessageDatabaseRepo};

#[test]
fn test_export_conversation_by_person() {
    // Create a runtime for async tests
    let rt = Runtime::new().unwrap();
    
    // Create a temporary directory for the test
    let temp_dir = tempdir().expect("Failed to create temp directory");
    let db_path = temp_dir.path().join("test.db");
    let db_url = format!("sqlite://{}", db_path.display());
    
    // Create a database and populate it with test data
    let db = Database::new(&db_url).expect("Failed to create database");
    
    // Create test contacts
    let person_contact = NewContact {
        name: "Phil".to_string(),
        phone: Some("+15551234567".to_string()),
        email: None,
        is_me: false,
        primary_identifier: None,
    };
    
    let me_contact = NewContact {
        name: "Jess".to_string(),
        phone: None,
        email: None,
        is_me: true,
        primary_identifier: Some("Jess".to_string()),
    };
    
    let person = db.add_or_update_contact(person_contact).expect("Failed to add person contact");
    let me = db.add_or_update_contact(me_contact).expect("Failed to add me contact");
    
    // Create test messages with realistic timestamps
    let timestamp1 = NaiveDateTime::parse_from_str("2025-01-20 12:21:19", "%Y-%m-%d %H:%M:%S").unwrap();
    let timestamp2 = NaiveDateTime::parse_from_str("2025-01-20 12:22:28", "%Y-%m-%d %H:%M:%S").unwrap();
    let timestamp3 = NaiveDateTime::parse_from_str("2025-01-20 14:26:27", "%Y-%m-%d %H:%M:%S").unwrap();
    
    // Message from Phil to Jess
    let message1 = NewMessage {
        imessage_id: "test1".to_string(),
        text: Some("Yea, I'll have to go to bed earlier".to_string()),
        sender: "Phil".to_string(),
        is_from_me: false,
        date_created: timestamp1,
        handle_id: None,
        service: Some("iMessage".to_string()),
        thread_id: None,
        has_attachments: false,
        contact_id: Some(me.id),
    };
    
    // Message from Jess to Phil
    let message2 = NewMessage {
        imessage_id: "test2".to_string(),
        text: Some("When she's healthy, she doesn't wake up, I don't know if she's getting sick, but in general let her work on falling back to sleep herself. Robert and Roxanne did it, I'm sure we can too".to_string()),
        sender: "Jess".to_string(),
        is_from_me: true,
        date_created: timestamp2,
        handle_id: None,
        service: Some("iMessage".to_string()),
        thread_id: None,
        has_attachments: false,
        contact_id: Some(person.id),
    };
    
    // Another message from Phil to Jess
    let message3 = NewMessage {
        imessage_id: "test3".to_string(),
        text: Some("Are you picking up Everly?".to_string()),
        sender: "Phil".to_string(),
        is_from_me: false,
        date_created: timestamp3,
        handle_id: None,
        service: Some("iMessage".to_string()),
        thread_id: None,
        has_attachments: false,
        contact_id: Some(me.id),
    };
    
    db.add_message(message1).expect("Failed to add message 1");
    db.add_message(message2).expect("Failed to add message 2");
    db.add_message(message3).expect("Failed to add message 3");
    
    // Create a mock repository for testing
    struct MockRepo {
        db: Database,
    }
    
    impl MockRepo {
        fn new(db: Database) -> Self {
            Self { db }
        }
    }
    
    #[async_trait::async_trait]
    impl MessageRepository for MockRepo {
        async fn fetch_messages(&self, _contact: &Contact, _date_range: &DateRange) -> anyhow::Result<Vec<Message>> {
            Ok(Vec::new())
        }
        
        async fn save_messages(&self, messages: &[Message], format: OutputFormat, path: &Path) -> anyhow::Result<()> {
            // Simple implementation for testing
            let content = messages.iter()
                .map(|m| format!("{}, {}, {}", 
                    m.sender,
                    m.timestamp.format("%b %d, %Y %I:%M:%S %p"),
                    m.content
                ))
                .collect::<Vec<_>>()
                .join("\n\n");
                
            if format == OutputFormat::Txt {
                fs::write(path, content)?;
            } else {
                // For CSV, just write the same content for simplicity in testing
                fs::write(path, content)?;
            }
            
            Ok(())
        }
        
        async fn export_conversation_by_person(
            &self, 
            person_name: &str, 
            format: OutputFormat, 
            output_path: &Path,
            date_range: &DateRange,
            chunk_size: Option<usize>,
            lines_per_chunk: Option<usize>
        ) -> anyhow::Result<Vec<PathBuf>> {
            // Get all messages with this person
            let messages = self.db.get_conversation_with_person(
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
                    timestamp: chrono::DateTime::<chrono::Local>::from_naive_local(&db_msg.date_created)
                        .expect("Invalid timestamp"),
                })
                .collect();
            
            // For simplicity in testing, just create one file
            let txt_path = output_path.with_extension("txt");
            let csv_path = output_path.with_extension("csv");
            
            self.save_messages(&messages, OutputFormat::Txt, &txt_path).await?;
            self.save_messages(&messages, OutputFormat::Csv, &csv_path).await?;
            
            Ok(vec![txt_path, csv_path])
        }
    }
    
    // Run the export test
    rt.block_on(async {
        let output_dir = temp_dir.path().join("output");
        fs::create_dir_all(&output_dir).expect("Failed to create output directory");
        
        let repo = MockRepo::new(db);
        let date_range = DateRange {
            start: None,
            end: None,
        };
        
        let output_path = output_dir.join("phil_conversation");
        let result = repo.export_conversation_by_person(
            "Phil",
            OutputFormat::Txt,
            &output_path,
            &date_range,
            None,
            None
        ).await.expect("Export failed");
        
        // Verify files were created
        assert_eq!(result.len(), 2);
        assert!(result[0].exists());
        assert!(result[1].exists());
        
        // Check content of the TXT file
        let txt_content = fs::read_to_string(&result[0]).expect("Failed to read TXT file");
        assert!(txt_content.contains("Phil, Jan 20, 2025 12:21:19 PM, Yea, I'll have to go to bed earlier"));
        assert!(txt_content.contains("Jess, Jan 20, 2025 12:22:28 PM, When she's healthy"));
        assert!(txt_content.contains("Phil, Jan 20, 2025 02:26:27 PM, Are you picking up Everly?"));
        
        // Verify chronological order
        let lines: Vec<&str> = txt_content.split("\n\n").collect();
        assert_eq!(lines.len(), 3);
        assert!(lines[0].contains("12:21:19"));
        assert!(lines[1].contains("12:22:28"));
        assert!(lines[2].contains("02:26:27"));
    });
}
