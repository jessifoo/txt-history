use chrono::NaiveDateTime;
use std::fs;
use std::path::Path;
use tempfile::tempdir;

// Import the necessary modules from the crate
use txtHistoryRust::db::Database;
use txtHistoryRust::models::{DbContact, DbMessage, NewContact, NewMessage};

#[test]
fn test_add_or_update_contact() {
    // Create a temporary database for testing
    let temp_dir = tempdir().expect("Failed to create temp directory");
    let db_path = temp_dir.path().join("test.db");
    let db_url = format!("sqlite://{}", db_path.display());

    let db = Database::new(&db_url).expect("Failed to create database");

    // Test adding a new contact
    let new_contact = NewContact {
        name: "Test Person".to_string(),
        phone: Some("+15551234567".to_string()),
        email: None,
        is_me: false,
        primary_identifier: None,
    };

    let contact = db.add_or_update_contact(new_contact).expect("Failed to add contact");

    // Verify the contact was added correctly
    assert_eq!(contact.name, "Test Person");
    assert_eq!(contact.phone, Some("+15551234567".to_string()));
    assert_eq!(contact.is_me, false);
    assert!(contact.primary_identifier.is_some());
    assert_eq!(contact.primary_identifier, Some("+15551234567".to_string()));

    // Test updating the contact with an email
    let updated_contact = NewContact {
        name: "Test Person".to_string(),
        phone: Some("+15551234567".to_string()),
        email: Some("test@example.com".to_string()),
        is_me: false,
        primary_identifier: None,
    };

    let updated = db.add_or_update_contact(updated_contact).expect("Failed to update contact");

    // Verify the contact was updated correctly
    assert_eq!(updated.id, contact.id); // Same ID means it's the same contact
    assert_eq!(updated.email, Some("test@example.com".to_string()));
    assert_eq!(updated.primary_identifier, Some("+15551234567".to_string())); // Primary identifier shouldn't change
}

#[test]
fn test_get_conversation_with_person() {
    // Create a temporary database for testing
    let temp_dir = tempdir().expect("Failed to create temp directory");
    let db_path = temp_dir.path().join("test.db");
    let db_url = format!("sqlite://{}", db_path.display());

    let db = Database::new(&db_url).expect("Failed to create database");

    // Create test contacts
    let person_contact = NewContact {
        name: "Test Person".to_string(),
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

    // Create test messages
    let timestamp1 = NaiveDateTime::parse_from_str("2025-01-01 10:00:00", "%Y-%m-%d %H:%M:%S").unwrap();
    let timestamp2 = NaiveDateTime::parse_from_str("2025-01-01 10:05:00", "%Y-%m-%d %H:%M:%S").unwrap();
    let timestamp3 = NaiveDateTime::parse_from_str("2025-01-01 10:10:00", "%Y-%m-%d %H:%M:%S").unwrap();

    // Message from person to me
    let message1 = NewMessage {
        imessage_id: "test1".to_string(),
        text: Some("Hello from person".to_string()),
        sender: "Test Person".to_string(),
        is_from_me: false,
        date_created: timestamp1,
        handle_id: None,
        service: Some("iMessage".to_string()),
        thread_id: None,
        has_attachments: false,
        contact_id: Some(me.id),
    };

    // Message from me to person
    let message2 = NewMessage {
        imessage_id: "test2".to_string(),
        text: Some("Hello from me".to_string()),
        sender: "Jess".to_string(),
        is_from_me: true,
        date_created: timestamp2,
        handle_id: None,
        service: Some("iMessage".to_string()),
        thread_id: None,
        has_attachments: false,
        contact_id: Some(person.id),
    };

    // Another message from person to me
    let message3 = NewMessage {
        imessage_id: "test3".to_string(),
        text: Some("How are you?".to_string()),
        sender: "Test Person".to_string(),
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

    // Test retrieving the conversation
    let conversation = db
        .get_conversation_with_person("Test Person", None, None)
        .expect("Failed to get conversation");

    // Verify we got all messages in chronological order
    assert_eq!(conversation.len(), 3);
    assert_eq!(conversation[0].text, Some("Hello from person".to_string()));
    assert_eq!(conversation[1].text, Some("Hello from me".to_string()));
    assert_eq!(conversation[2].text, Some("How are you?".to_string()));

    // Test date filtering
    let filtered_conversation = db
        .get_conversation_with_person("Test Person", Some(timestamp2), None)
        .expect("Failed to get filtered conversation");

    // Should only include messages from timestamp2 onwards
    assert_eq!(filtered_conversation.len(), 2);
    assert_eq!(filtered_conversation[0].text, Some("Hello from me".to_string()));
    assert_eq!(filtered_conversation[1].text, Some("How are you?".to_string()));
}
