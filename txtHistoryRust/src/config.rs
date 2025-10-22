use anyhow::Result;
use serde::{Deserialize, Serialize};
use std::path::Path;
use config::{Config, ConfigError, Environment, File};

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
                database_path: "/Users/jessica/Library/Messages/chat.db".to_string(),
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
            // Start with default values
            .set_defaults(AppConfig::default().into_iter())?
            // Add config file if it exists
            .add_source(File::with_name("config/default").required(false))
            .add_source(File::with_name("config/local").required(false))
            .add_source(File::with_name("config").required(false))
            // Add environment variables with prefix
            .add_source(Environment::with_prefix("TXT_HISTORY").separator("_"))
            .build()
            .map_err(|e| anyhow::anyhow!("Failed to load configuration: {}", e))?;

        let app_config: AppConfig = config
            .try_deserialize()
            .map_err(|e| anyhow::anyhow!("Failed to deserialize configuration: {}", e))?;

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
            return Err(anyhow::anyhow!("connection_timeout_secs must be greater than 0"));
        }

        // Validate logging config
        let valid_levels = ["trace", "debug", "info", "warn", "error"];
        if !valid_levels.contains(&self.logging.level.as_str()) {
            return Err(anyhow::anyhow!(
                "Invalid log level: {}. Must be one of: {:?}",
                self.logging.level,
                valid_levels
            ));
        }

        let valid_formats = ["text", "json"];
        if !valid_formats.contains(&self.logging.format.as_str()) {
            return Err(anyhow::anyhow!(
                "Invalid log format: {}. Must be one of: {:?}",
                self.logging.format,
                valid_formats
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
                "Invalid export format: {}. Must be one of: {:?}",
                self.export.default_format,
                valid_formats
            ));
        }

        if self.export.max_chunk_size_mb <= 0.0 {
            return Err(anyhow::anyhow!("max_chunk_size_mb must be greater than 0"));
        }

        if self.export.max_lines_per_chunk == 0 {
            return Err(anyhow::anyhow!("max_lines_per_chunk must be greater than 0"));
        }

        // Validate iMessage config
        if self.imessage.max_retries == 0 {
            return Err(anyhow::anyhow!("max_retries must be greater than 0"));
        }

        Ok(())
    }

    /// Get database URL from environment or config
    pub fn get_database_url(&self) -> String {
        std::env::var("DATABASE_URL")
            .unwrap_or_else(|_| self.database.url.clone())
    }

    /// Get iMessage database path from environment or config
    pub fn get_imessage_db_path(&self) -> String {
        std::env::var("IMESSAGE_DB_PATH")
            .unwrap_or_else(|_| self.imessage.database_path.clone())
    }

    /// Get log level from environment or config
    pub fn get_log_level(&self) -> String {
        std::env::var("RUST_LOG")
            .unwrap_or_else(|_| self.logging.level.clone())
    }
}

impl IntoIterator for AppConfig {
    type Item = (String, config::Value);
    type IntoIter = std::collections::HashMap<String, config::Value>;

    fn into_iter(self) -> Self::IntoIter {
        let mut map = std::collections::HashMap::new();
        
        // Flatten the configuration into key-value pairs
        map.insert("database.url".to_string(), config::Value::from(self.database.url));
        map.insert("database.max_connections".to_string(), config::Value::from(self.database.max_connections));
        map.insert("database.connection_timeout_secs".to_string(), config::Value::from(self.database.connection_timeout_secs));
        map.insert("database.migration_timeout_secs".to_string(), config::Value::from(self.database.migration_timeout_secs));
        
        map.insert("logging.level".to_string(), config::Value::from(self.logging.level));
        if let Some(file_path) = self.logging.file_path {
            map.insert("logging.file_path".to_string(), config::Value::from(file_path));
        }
        map.insert("logging.max_file_size_mb".to_string(), config::Value::from(self.logging.max_file_size_mb));
        map.insert("logging.max_files".to_string(), config::Value::from(self.logging.max_files));
        map.insert("logging.format".to_string(), config::Value::from(self.logging.format));
        
        map.insert("nlp.batch_size".to_string(), config::Value::from(self.nlp.batch_size));
        map.insert("nlp.max_text_length".to_string(), config::Value::from(self.nlp.max_text_length));
        map.insert("nlp.enable_sentiment".to_string(), config::Value::from(self.nlp.enable_sentiment));
        map.insert("nlp.enable_ner".to_string(), config::Value::from(self.nlp.enable_ner));
        map.insert("nlp.enable_language_detection".to_string(), config::Value::from(self.nlp.enable_language_detection));
        map.insert("nlp.processing_timeout_secs".to_string(), config::Value::from(self.nlp.processing_timeout_secs));
        
        map.insert("export.default_format".to_string(), config::Value::from(self.export.default_format));
        map.insert("export.max_chunk_size_mb".to_string(), config::Value::from(self.export.max_chunk_size_mb));
        map.insert("export.max_lines_per_chunk".to_string(), config::Value::from(self.export.max_lines_per_chunk));
        map.insert("export.output_directory".to_string(), config::Value::from(self.export.output_directory));
        map.insert("export.enable_compression".to_string(), config::Value::from(self.export.enable_compression));
        
        map.insert("imessage.database_path".to_string(), config::Value::from(self.imessage.database_path));
        map.insert("imessage.connection_timeout_secs".to_string(), config::Value::from(self.imessage.connection_timeout_secs));
        map.insert("imessage.read_timeout_secs".to_string(), config::Value::from(self.imessage.read_timeout_secs));
        map.insert("imessage.max_retries".to_string(), config::Value::from(self.imessage.max_retries));
        
        map.into_iter()
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
