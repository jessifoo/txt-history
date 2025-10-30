use anyhow::{anyhow, Result};
use chrono::{DateTime, Local};
use std::path::Path;

/// Validation utilities for input sanitization and edge case handling
#[derive(Debug, Copy, Clone)]
pub struct InputValidator;

impl InputValidator {
    /// Validate contact name
    pub fn validate_contact_name(name: &str) -> Result<()> {
        if name.trim().is_empty() {
            return Err(anyhow!("Contact name cannot be empty"));
        }

        if name.len() > 100 {
            return Err(anyhow!("Contact name too long (max 100 characters)"));
        }

        // Check for potentially dangerous characters
        if name.contains('\0') || name.contains('\r') || name.contains('\n') {
            return Err(anyhow!("Contact name contains invalid characters"));
        }

        Ok(())
    }

    /// Validate phone number format
    pub fn validate_phone(phone: &str) -> Result<()> {
        if phone.trim().is_empty() {
            return Err(anyhow!("Phone number cannot be empty"));
        }

        // Remove common formatting characters
        let cleaned = phone
            .chars()
            .filter(|c| {
                c.is_ascii_digit() || *c == '+' || *c == '-' || *c == '(' || *c == ')' || *c == ' '
            })
            .collect::<String>();

        // Check if it contains only digits and + at the start
        let digits_only = cleaned.chars().filter(char::is_ascii_digit).count();

        if !(7..=15).contains(&digits_only) {
            return Err(anyhow!("Phone number must be between 7 and 15 digits"));
        }

        if !cleaned.starts_with('+') && !cleaned.chars().all(|c| c.is_ascii_digit()) {
            return Err(anyhow!(
                "Phone number must start with + or contain only digits"
            ));
        }

        Ok(())
    }

    /// Validate email format
    pub fn validate_email(email: &str) -> Result<()> {
        if email.trim().is_empty() {
            return Err(anyhow!("Email cannot be empty"));
        }

        if email.len() > 254 {
            return Err(anyhow!("Email too long (max 254 characters)"));
        }

        // Basic email validation
        if !email.contains('@') {
            return Err(anyhow!("Email must contain @ symbol"));
        }

        let parts: Vec<&str> = email.split('@').collect();
        if parts.len() != 2 {
            return Err(anyhow!("Email must have exactly one @ symbol"));
        }

        let local_part = parts[0];
        let domain_part = parts[1];

        if local_part.is_empty() || local_part.len() > 64 {
            return Err(anyhow!("Email local part invalid"));
        }

        if domain_part.is_empty() || !domain_part.contains('.') {
            return Err(anyhow!("Email domain invalid"));
        }

        Ok(())
    }

    /// Validate file path
    pub fn validate_file_path(path: &Path) -> Result<()> {
        if path.to_string_lossy().is_empty() {
            return Err(anyhow!("File path cannot be empty"));
        }

        // Check for path traversal attempts
        let path_str = path.to_string_lossy();
        if path_str.contains("..") || path_str.contains('~') {
            return Err(anyhow!(
                "File path contains potentially dangerous characters"
            ));
        }

        // Check path length
        if path_str.len() > 4096 {
            return Err(anyhow!("File path too long (max 4096 characters)"));
        }

        Ok(())
    }

    /// Validate date range
    pub fn validate_date_range(
        start: Option<DateTime<Local>>,
        end: Option<DateTime<Local>>,
    ) -> Result<()> {
        if let (Some(start_date), Some(end_date)) = (start, end) {
            if start_date > end_date {
                return Err(anyhow!("Start date cannot be after end date"));
            }

            // Check if date range is not too far in the future
            let now = Local::now();
            if start_date > now || end_date > now {
                return Err(anyhow!("Dates cannot be in the future"));
            }

            // Check if date range is not too far in the past (more than 20 years for messages)
            let twenty_years_ago = now - chrono::Duration::days(365 * 20);
            if start_date < twenty_years_ago {
                tracing::warn!("Start date is more than 20 years in the past");
            }

            // Warn about very large date ranges that may impact performance
            let days = (end_date - start_date).num_days();
            if days > 365 * 5 {
                tracing::warn!(
                    "Large date range ({} days / {:.1} years) may impact performance and memory usage",
                    days,
                    days as f64 / 365.0
                );
            }

            // Error on extremely large ranges
            if days > 365 * 10 {
                return Err(anyhow!(
                    "Date range too large ({days} days / {} years). Maximum supported range is 10 years. \
                    Please split into smaller queries.",
                    days / 365
                ));
            }
        }

        Ok(())
    }

    /// Validate chunk size
    pub fn validate_chunk_size(size: f64) -> Result<()> {
        if size <= 0.0 {
            return Err(anyhow!("Chunk size must be positive"));
        }

        if size > 1000.0 {
            return Err(anyhow!("Chunk size too large (max 1000 MB)"));
        }

        Ok(())
    }

    /// Validate lines per chunk
    pub fn validate_lines_per_chunk(lines: usize) -> Result<()> {
        if lines == 0 {
            return Err(anyhow!("Lines per chunk must be greater than 0"));
        }

        if lines > 1_000_000 {
            return Err(anyhow!("Lines per chunk too large (max 1,000,000)"));
        }

        Ok(())
    }

    /// Validate batch size for processing
    pub fn validate_batch_size(batch_size: usize) -> Result<()> {
        if batch_size == 0 {
            return Err(anyhow!("Batch size must be greater than 0"));
        }

        if batch_size > 10000 {
            return Err(anyhow!("Batch size too large (max 10,000)"));
        }

        Ok(())
    }

    /// Validate processing version
    pub fn validate_processing_version(version: &str) -> Result<()> {
        if version.trim().is_empty() {
            return Err(anyhow!("Processing version cannot be empty"));
        }

        if version.len() > 50 {
            return Err(anyhow!("Processing version too long (max 50 characters)"));
        }

        // Check for valid characters (alphanumeric, dots, dashes, underscores)
        if !version
            .chars()
            .all(|c| c.is_ascii_alphanumeric() || c == '.' || c == '-' || c == '_')
        {
            return Err(anyhow!("Processing version contains invalid characters"));
        }

        Ok(())
    }

    /// Sanitize text input
    #[must_use]
    pub fn sanitize_text(text: &str) -> String {
        text.chars()
            .filter(|c| !c.is_control() || *c == '\n' || *c == '\t' || *c == '\r')
            .collect::<String>()
            .trim()
            .to_string()
    }

    /// Validate database URL
    pub fn validate_database_url(url: &str) -> Result<()> {
        if url.trim().is_empty() {
            return Err(anyhow!("Database URL cannot be empty"));
        }

        if !url.starts_with("sqlite:") {
            return Err(anyhow!("Only SQLite databases are supported"));
        }

        if url.len() > 1000 {
            return Err(anyhow!("Database URL too long"));
        }

        Ok(())
    }

    /// Validate iMessage database path
    pub fn validate_imessage_db_path(path: &Path) -> Result<()> {
        if !path.exists() {
            return Err(anyhow!("iMessage database path does not exist: {path:?}"));
        }

        if !path.is_file() {
            return Err(anyhow!("iMessage database path is not a file: {path:?}"));
        }

        // Check file permissions (readable)
        if std::fs::metadata(path)
            .map_err(|e| anyhow!("Cannot access iMessage database: {e}"))?
            .permissions()
            .readonly()
        {
            // This is actually what we want for iMessage database
        }

        Ok(())
    }
}
