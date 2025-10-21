use chrono::NaiveDateTime;
use std::env;
use txt_history_rust::db::Database;
use txt_history_rust::models::{NewContact, NewMessage, NewProcessedMessage};

#[test]
fn test_database_creation_and_initialization() {
    let temp_dir = env::temp_dir().join("txt_history_db_test");
    std::fs::create_dir_all(&temp_dir).expect("Failed to create temp directory");
    let db_path = temp_dir.join("test.db");
    let db_url = format!("sqlite://{}", db_path.display());

    // Test database creation
    let db = Database::new(&db_url).expect("Failed to create database");
    
    // Test that we can get a connection
    let _conn = db.get_connection().expect("Failed to get database connection");
}

#[test]
fn test_contact_management() {
    let temp_dir = env::temp_dir().join("txt_history_contact_test");
    std::fs::create_dir_all(&temp_dir).expect("Failed to create temp directory");
    let db_path = temp_dir.join("test.db");
    let db_url = format!("sqlite://{}", db_path.display());

    let db = Database::new(&db_url).expect("Failed to create database");

    // Test adding a new contact
    let new_contact = NewContact {
        name: "Test User".to_string(),
        phone: Some("+1234567890".to_string()),
        email: Some("test@example.com".to_string()),
        is_me: false,
        primary_identifier: Some("test_user".to_string()),
    };

    let contact = db.add_or_update_contact(new_contact).expect("Failed to add contact");
    assert_eq!(contact.name, "Test User");
    assert_eq!(contact.phone, Some("+1234567890".to_string()));

    // Test retrieving the contact
    let retrieved = db.get_contact("Test User").expect("Failed to get contact");
    assert!(retrieved.is_some());
    assert_eq!(retrieved.unwrap().name, "Test User");
}
