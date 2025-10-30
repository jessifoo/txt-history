use anyhow::Result;
use config::{Config, Environment, File};
use serde::{Deserialize, Serialize};

/// Application configuration structure
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AppConfig {
    pub database: DatabaseConfig,
    pub logging: LoggingConfig,
    pub nlp: NlpConfig,
    pub export: ExportConfig,
    pub imessage: IMessageConfig,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct DatabaseConfig {
    pub url: String,
    pub max_connections: u32,
    pub connection_timeout_secs: u64,
    pub migration_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct LoggingConfig {
    pub level: String,
    pub file_path: Option<String>,
    pub max_file_size_mb: u64,
    pub max_files: u32,
    pub format: String, // "json" or "text"
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct NlpConfig {
    pub batch_size: usize,
    pub max_text_length: usize,
    pub enable_sentiment: bool,
    pub enable_ner: bool,
    pub enable_language_detection: bool,
    pub processing_timeout_secs: u64,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ExportConfig {
    pub default_format: String,
    pub max_chunk_size_mb: f64,
    pub max_lines_per_chunk: usize,
    pub output_directory: String,
    pub enable_compression: bool,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct IMessageConfig {
    pub database_path: String,
    pub connection_timeout_secs: u64,
    pub read_timeout_secs: u64,
    pub max_retries: u32,
}

impl Default for AppConfig {
    fn default() -> Self {
        Self {
            database: DatabaseConfig {
                url: "sqlite:data/messages.db".to_string(),
                max_connections: 10,
                connection_timeout_secs: 30,
                migration_timeout_secs: 60,
            },
            logging: LoggingConfig {
                level: "info".to_string(),
                file_path: None,
                max_file_size_mb: 100,
                max_files: 5,
                format: "text".to_string(),
            },
            nlp: NlpConfig {
                batch_size: 100,
                max_text_length: 10000,
                enable_sentiment: true,
                enable_ner: true,
                enable_language_detection: true,
                processing_timeout_secs: 300,
            },
            export: ExportConfig {
                default_format: "txt".to_string(),
                max_chunk_size_mb: 10.0,
                max_lines_per_chunk: 10000,
                output_directory: "./output".to_string(),
                enable_compression: false,
            },
            imessage: IMessageConfig {
                database_path: String::new(), // Will be dynamically detected
                connection_timeout_secs: 30,
                read_timeout_secs: 60,
                max_retries: 3,
            },
        }
    }
}

impl AppConfig {
    /// Load configuration from multiple sources with precedence
    pub fn load() -> Result<Self> {
        let config = Config::builder()
            // Add config file if it exists
            .add_source(File::with_name("config/default").required(false))
            .add_source(File::with_name("config/local").required(false))
            .add_source(File::with_name("config").required(false))
            // Add environment variables with prefix
            .add_source(Environment::with_prefix("TXT_HISTORY").separator("_"))
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to load configuration: {e}"))?;

        let app_config: Self = config
            .try_deserialize()
            .map_err(|e| anyhow::anyhow!("Failed to deserialize configuration: {e}"))?;

        // Validate configuration
        app_config.validate()?;

        Ok(app_config)
    }

    /// Validate configuration values
    pub fn validate(&self) -> Result<()> {
        // Validate database config
        if self.database.max_connections == 0 {
            return Err(anyhow::anyhow!("max_connections must be greater than 0"));
        }
        if self.database.connection_timeout_secs == 0 {
            return Err(anyhow::anyhow!(
                "connection_timeout_secs must be greater than 0"
            ));
        }

        // Validate logging config
        let valid_levels = ["trace", "debug", "info", "warn", "error"];
        if !valid_levels.contains(&self.logging.level.as_str()) {
            return Err(anyhow::anyhow!(
                "Invalid log level: {}. Must be one of: {valid_levels:?}",
                self.logging.level
            ));
        }

        let valid_formats = ["text", "json"];
        if !valid_formats.contains(&self.logging.format.as_str()) {
            return Err(anyhow::anyhow!(
                "Invalid log format: {}. Must be one of: {valid_formats:?}",
                self.logging.format
            ));
        }

        // Validate NLP config
        if self.nlp.batch_size == 0 {
            return Err(anyhow::anyhow!("batch_size must be greater than 0"));
        }
        if self.nlp.max_text_length == 0 {
            return Err(anyhow::anyhow!("max_text_length must be greater than 0"));
        }

        // Validate export config
        let valid_formats = ["txt", "csv", "json"];
        if !valid_formats.contains(&self.export.default_format.as_str()) {
            return Err(anyhow::anyhow!(
                "Invalid export format: {}. Must be one of: {valid_formats:?}",
                self.export.default_format
            ));
        }

        if self.export.max_chunk_size_mb <= 0.0 {
            return Err(anyhow::anyhow!("max_chunk_size_mb must be greater than 0"));
        }

        if self.export.max_lines_per_chunk == 0 {
            return Err(anyhow::anyhow!(
                "max_lines_per_chunk must be greater than 0"
            ));
        }

        // Validate iMessage config
        if self.imessage.max_retries == 0 {
            return Err(anyhow::anyhow!("max_retries must be greater than 0"));
        }

        Ok(())
    }

    /// Get database URL from environment or config
    #[must_use]
    pub fn get_database_url(&self) -> String {
        std::env::var("DATABASE_URL").unwrap_or_else(|_| self.database.url.clone())
    }

    /// Get iMessage database path from environment or config
    #[must_use]
    pub fn get_imessage_db_path(&self) -> String {
        std::env::var("IMESSAGE_DB_PATH").unwrap_or_else(|_| {
            if self.imessage.database_path.is_empty() {
                // Use platform-agnostic approach - only default to macOS path on macOS
                #[cfg(target_os = "macos")]
                {
                    if let Ok(home) = std::env::var("HOME") {
                        format!("{}/Library/Messages/chat.db", home)
                    } else {
                        // No default on macOS without HOME
                        String::new()
                    }
                }
                #[cfg(not(target_os = "macos"))]
                {
                    // No default iMessage path on non-macOS systems
                    String::new()
                }
            } else {
                self.imessage.database_path.clone()
            }
        })
    }

    /// Get log level from environment or config
    #[must_use]
    pub fn get_log_level(&self) -> String {
        std::env::var("RUST_LOG").unwrap_or_else(|_| self.logging.level.clone())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_config() {
        let config = AppConfig::default();
        assert_eq!(config.database.url, "sqlite:data/messages.db");
        assert_eq!(config.logging.level, "info");
        assert_eq!(config.nlp.batch_size, 100);
    }

    #[test]
    fn test_config_validation() {
        let config = AppConfig::default();
        assert!(config.validate().is_ok());
    }

    #[test]
    fn test_invalid_config() {
        let mut config = AppConfig::default();
        config.database.max_connections = 0;
        assert!(config.validate().is_err());
    }
}
