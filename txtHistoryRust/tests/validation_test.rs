//! Comprehensive unit tests for validation.rs module

use chrono::{Duration, Local};
use std::path::Path;
use txt_history_rust::validation::InputValidator;

#[test]
fn test_validate_contact_name_valid() {
    assert!(InputValidator::validate_contact_name("John Doe").is_ok());
}

#[test]
fn test_validate_contact_name_empty() {
    assert!(InputValidator::validate_contact_name("").is_err());
}

#[test]
fn test_validate_contact_name_whitespace_only() {
    assert!(InputValidator::validate_contact_name("   ").is_err());
}

#[test]
fn test_validate_contact_name_too_long() {
    let long_name = "a".repeat(101);
    assert!(InputValidator::validate_contact_name(&long_name).is_err());
}

#[test]
fn test_validate_contact_name_exactly_100_chars() {
    let name = "a".repeat(100);
    assert!(InputValidator::validate_contact_name(&name).is_ok());
}

#[test]
fn test_validate_contact_name_with_null_byte() {
    assert!(InputValidator::validate_contact_name("John\0Doe").is_err());
}

#[test]
fn test_validate_contact_name_with_newline() {
    assert!(InputValidator::validate_contact_name("John\nDoe").is_err());
}

#[test]
fn test_validate_contact_name_with_carriage_return() {
    assert!(InputValidator::validate_contact_name("John\rDoe").is_err());
}

#[test]
fn test_validate_contact_name_with_special_chars() {
    assert!(InputValidator::validate_contact_name("O'Brien-Smith").is_ok());
}

#[test]
fn test_validate_contact_name_unicode() {
    assert!(InputValidator::validate_contact_name("José García").is_ok());
}

#[test]
fn test_validate_phone_valid_us() {
    assert!(InputValidator::validate_phone("+1234567890").is_ok());
}

#[test]
fn test_validate_phone_valid_international() {
    assert!(InputValidator::validate_phone("+442012345678").is_ok());
}

#[test]
fn test_validate_phone_with_formatting() {
    assert!(InputValidator::validate_phone("+1 (555) 123-4567").is_ok());
}

#[test]
fn test_validate_phone_empty() {
    assert!(InputValidator::validate_phone("").is_err());
}

#[test]
fn test_validate_phone_too_short() {
    assert!(InputValidator::validate_phone("123456").is_err());
}

#[test]
fn test_validate_phone_too_long() {
    assert!(InputValidator::validate_phone("12345678901234567").is_err());
}

#[test]
fn test_validate_phone_min_length() {
    assert!(InputValidator::validate_phone("1234567").is_ok());
}

#[test]
fn test_validate_phone_max_length() {
    assert!(InputValidator::validate_phone("123456789012345").is_ok());
}

#[test]
fn test_validate_phone_digits_only() {
    assert!(InputValidator::validate_phone("1234567890").is_ok());
}

#[test]
fn test_validate_phone_with_invalid_chars() {
    assert!(InputValidator::validate_phone("+1234567890abc").is_err());
}

#[test]
fn test_validate_email_valid() {
    assert!(InputValidator::validate_email("test@example.com").is_ok());
}

#[test]
fn test_validate_email_valid_subdomain() {
    assert!(InputValidator::validate_email("user@mail.example.com").is_ok());
}

#[test]
fn test_validate_email_empty() {
    assert!(InputValidator::validate_email("").is_err());
}

#[test]
fn test_validate_email_no_at_symbol() {
    assert!(InputValidator::validate_email("testexample.com").is_err());
}

#[test]
fn test_validate_email_multiple_at_symbols() {
    assert!(InputValidator::validate_email("test@@example.com").is_err());
}

#[test]
fn test_validate_email_no_local_part() {
    assert!(InputValidator::validate_email("@example.com").is_err());
}

#[test]
fn test_validate_email_no_domain() {
    assert!(InputValidator::validate_email("test@").is_err());
}

#[test]
fn test_validate_email_no_domain_extension() {
    assert!(InputValidator::validate_email("test@example").is_err());
}

#[test]
fn test_validate_email_too_long() {
    let long_email = format!("{}@example.com", "a".repeat(250));
    assert!(InputValidator::validate_email(&long_email).is_err());
}

#[test]
fn test_validate_email_local_part_too_long() {
    let long_local = format!("{}@example.com", "a".repeat(65));
    assert!(InputValidator::validate_email(&long_local).is_err());
}

#[test]
fn test_validate_email_exactly_254_chars() {
    let email = format!("{}@example.com", "a".repeat(242));
    assert!(InputValidator::validate_email(&email).is_ok());
}

#[test]
fn test_validate_file_path_valid() {
    let path = Path::new("test/file.txt");
    assert!(InputValidator::validate_file_path(path).is_ok());
}

#[test]
fn test_validate_file_path_empty() {
    let path = Path::new("");
    assert!(InputValidator::validate_file_path(path).is_err());
}

#[test]
fn test_validate_file_path_with_parent_traversal() {
    let path = Path::new("../test/file.txt");
    assert!(InputValidator::validate_file_path(path).is_err());
}

#[test]
fn test_validate_file_path_with_tilde() {
    let path = Path::new("~/test/file.txt");
    assert!(InputValidator::validate_file_path(path).is_err());
}

#[test]
fn test_validate_file_path_absolute() {
    let path = Path::new("/absolute/path/file.txt");
    assert!(InputValidator::validate_file_path(path).is_ok());
}

#[test]
fn test_validate_file_path_too_long() {
    let long_path = "a".repeat(5000);
    let path = Path::new(&long_path);
    assert!(InputValidator::validate_file_path(path).is_err());
}

#[test]
fn test_validate_date_range_valid() {
    let start = Local::now() - Duration::days(10);
    let end = Local::now() - Duration::days(5);
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_ok());
}

#[test]
fn test_validate_date_range_start_after_end() {
    let start = Local::now() - Duration::days(5);
    let end = Local::now() - Duration::days(10);
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_err());
}

#[test]
fn test_validate_date_range_future_start() {
    let start = Local::now() + Duration::days(1);
    let end = Local::now() + Duration::days(2);
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_err());
}

#[test]
fn test_validate_date_range_future_end() {
    let start = Local::now() - Duration::days(1);
    let end = Local::now() + Duration::days(1);
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_err());
}

#[test]
fn test_validate_date_range_none_values() {
    assert!(InputValidator::validate_date_range(None, None).is_ok());
}

#[test]
fn test_validate_date_range_only_start() {
    let start = Local::now() - Duration::days(10);
    assert!(InputValidator::validate_date_range(Some(start), None).is_ok());
}

#[test]
fn test_validate_date_range_only_end() {
    let end = Local::now() - Duration::days(5);
    assert!(InputValidator::validate_date_range(None, Some(end)).is_ok());
}

#[test]
fn test_validate_date_range_too_large() {
    let start = Local::now() - Duration::days(365 * 11);
    let end = Local::now();
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_err());
}

#[test]
fn test_validate_date_range_one_year() {
    let start = Local::now() - Duration::days(365);
    let end = Local::now();
    assert!(InputValidator::validate_date_range(Some(start), Some(end)).is_ok());
}

#[test]
fn test_validate_chunk_size_valid() {
    assert!(InputValidator::validate_chunk_size(10.0).is_ok());
}

#[test]
fn test_validate_chunk_size_zero() {
    assert!(InputValidator::validate_chunk_size(0.0).is_err());
}

#[test]
fn test_validate_chunk_size_negative() {
    assert!(InputValidator::validate_chunk_size(-5.0).is_err());
}

#[test]
fn test_validate_chunk_size_too_large() {
    assert!(InputValidator::validate_chunk_size(1001.0).is_err());
}

#[test]
fn test_validate_chunk_size_exactly_1000() {
    assert!(InputValidator::validate_chunk_size(1000.0).is_ok());
}

#[test]
fn test_validate_chunk_size_small() {
    assert!(InputValidator::validate_chunk_size(0.1).is_ok());
}

#[test]
fn test_validate_lines_per_chunk_valid() {
    assert!(InputValidator::validate_lines_per_chunk(1000).is_ok());
}

#[test]
fn test_validate_lines_per_chunk_zero() {
    assert!(InputValidator::validate_lines_per_chunk(0).is_err());
}

#[test]
fn test_validate_lines_per_chunk_too_large() {
    assert!(InputValidator::validate_lines_per_chunk(1_000_001).is_err());
}

#[test]
fn test_validate_lines_per_chunk_exactly_max() {
    assert!(InputValidator::validate_lines_per_chunk(1_000_000).is_ok());
}

#[test]
fn test_validate_lines_per_chunk_one() {
    assert!(InputValidator::validate_lines_per_chunk(1).is_ok());
}

#[test]
fn test_validate_batch_size_valid() {
    assert!(InputValidator::validate_batch_size(100).is_ok());
}

#[test]
fn test_validate_batch_size_zero() {
    assert!(InputValidator::validate_batch_size(0).is_err());
}

#[test]
fn test_validate_batch_size_too_large() {
    assert!(InputValidator::validate_batch_size(10001).is_err());
}

#[test]
fn test_validate_batch_size_exactly_max() {
    assert!(InputValidator::validate_batch_size(10000).is_ok());
}

#[test]
fn test_validate_batch_size_one() {
    assert!(InputValidator::validate_batch_size(1).is_ok());
}

#[test]
fn test_validate_processing_version_valid() {
    assert!(InputValidator::validate_processing_version("v1.0.0").is_ok());
}

#[test]
fn test_validate_processing_version_empty() {
    assert!(InputValidator::validate_processing_version("").is_err());
}

#[test]
fn test_validate_processing_version_whitespace() {
    assert!(InputValidator::validate_processing_version("   ").is_err());
}

#[test]
fn test_validate_processing_version_too_long() {
    let long_version = "v".repeat(51);
    assert!(InputValidator::validate_processing_version(&long_version).is_err());
}

#[test]
fn test_validate_processing_version_exactly_50_chars() {
    let version = "v".repeat(50);
    assert!(InputValidator::validate_processing_version(&version).is_ok());
}

#[test]
fn test_validate_processing_version_with_invalid_chars() {
    assert!(InputValidator::validate_processing_version("v1.0@beta").is_err());
}

#[test]
fn test_validate_processing_version_alphanumeric() {
    assert!(InputValidator::validate_processing_version("version123").is_ok());
}

#[test]
fn test_validate_processing_version_with_dashes_dots() {
    assert!(InputValidator::validate_processing_version("v1.0-beta.1").is_ok());
}

#[test]
fn test_sanitize_text_clean() {
    let text = "Clean text";
    let sanitized = InputValidator::sanitize_text(text);
    assert_eq!(sanitized, "Clean text");
}

#[test]
fn test_sanitize_text_with_control_chars() {
    let text = "Text\x00with\x01control";
    let sanitized = InputValidator::sanitize_text(text);
    assert!(!sanitized.contains('\x00'));
    assert!(!sanitized.contains('\x01'));
}

#[test]
fn test_sanitize_text_preserves_newlines() {
    let text = "Line1\nLine2";
    let sanitized = InputValidator::sanitize_text(text);
    assert!(sanitized.contains('\n'));
}

#[test]
fn test_sanitize_text_preserves_tabs() {
    let text = "Col1\tCol2";
    let sanitized = InputValidator::sanitize_text(text);
    assert!(sanitized.contains('\t'));
}

#[test]
fn test_sanitize_text_trims_whitespace() {
    let text = "  Text with spaces  ";
    let sanitized = InputValidator::sanitize_text(text);
    assert_eq!(sanitized, "Text with spaces");
}

#[test]
fn test_sanitize_text_empty() {
    let sanitized = InputValidator::sanitize_text("");
    assert_eq!(sanitized, "");
}

#[test]
fn test_validate_database_url_valid() {
    assert!(InputValidator::validate_database_url("sqlite:data/messages.db").is_ok());
}

#[test]
fn test_validate_database_url_empty() {
    assert!(InputValidator::validate_database_url("").is_err());
}

#[test]
fn test_validate_database_url_not_sqlite() {
    assert!(InputValidator::validate_database_url("postgres://localhost/db").is_err());
}

#[test]
fn test_validate_database_url_too_long() {
    let long_url = format!("sqlite:{}", "a".repeat(1000));
    assert!(InputValidator::validate_database_url(&long_url).is_err());
}

#[test]
fn test_validate_database_url_memory() {
    assert!(InputValidator::validate_database_url("sqlite::memory:").is_ok());
}