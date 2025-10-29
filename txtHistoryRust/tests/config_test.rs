//! Comprehensive unit tests for config.rs module

use txt_history_rust::config::{
    AppConfig, DatabaseConfig, ExportConfig, IMessageConfig, LoggingConfig, NlpConfig,
};

#[test]
fn test_default_config_values() {
    let config = AppConfig::default();

    assert_eq!(config.database.url, "sqlite:data/messages.db");
    assert_eq!(config.database.max_connections, 10);
    assert_eq!(config.database.connection_timeout_secs, 30);
    assert_eq!(config.database.migration_timeout_secs, 60);
}

#[test]
fn test_default_logging_config() {
    let config = AppConfig::default();

    assert_eq!(config.logging.level, "info");
    assert_eq!(config.logging.file_path, None);
    assert_eq!(config.logging.max_file_size_mb, 100);
    assert_eq!(config.logging.max_files, 5);
    assert_eq!(config.logging.format, "text");
}

#[test]
fn test_default_nlp_config() {
    let config = AppConfig::default();

    assert_eq!(config.nlp.batch_size, 100);
    assert_eq!(config.nlp.max_text_length, 10000);
    assert!(config.nlp.enable_sentiment);
    assert!(config.nlp.enable_ner);
    assert!(config.nlp.enable_language_detection);
    assert_eq!(config.nlp.processing_timeout_secs, 300);
}

#[test]
fn test_default_export_config() {
    let config = AppConfig::default();

    assert_eq!(config.export.default_format, "txt");
    assert_eq!(config.export.max_chunk_size_mb, 10.0);
    assert_eq!(config.export.max_lines_per_chunk, 10000);
    assert_eq!(config.export.output_directory, "./output");
    assert!(!config.export.enable_compression);
}

#[test]
fn test_default_imessage_config() {
    let config = AppConfig::default();

    assert_eq!(config.imessage.database_path, "");
    assert_eq!(config.imessage.connection_timeout_secs, 30);
    assert_eq!(config.imessage.read_timeout_secs, 60);
    assert_eq!(config.imessage.max_retries, 3);
}

#[test]
fn test_config_validation_success() {
    let config = AppConfig::default();
    assert!(config.validate().is_ok());
}

#[test]
fn test_config_validation_zero_max_connections() {
    let mut config = AppConfig::default();
    config.database.max_connections = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_zero_connection_timeout() {
    let mut config = AppConfig::default();
    config.database.connection_timeout_secs = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_invalid_log_level() {
    let mut config = AppConfig::default();
    config.logging.level = "invalid".to_string();
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_valid_log_levels() {
    let valid_levels = vec!["trace", "debug", "info", "warn", "error"];
    for level in valid_levels {
        let mut config = AppConfig::default();
        config.logging.level = level.to_string();
        assert!(config.validate().is_ok(), "Failed for level: {}", level);
    }
}

#[test]
fn test_config_validation_invalid_log_format() {
    let mut config = AppConfig::default();
    config.logging.format = "xml".to_string();
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_valid_log_formats() {
    let valid_formats = vec!["text", "json"];
    for format in valid_formats {
        let mut config = AppConfig::default();
        config.logging.format = format.to_string();
        assert!(config.validate().is_ok(), "Failed for format: {}", format);
    }
}

#[test]
fn test_config_validation_zero_batch_size() {
    let mut config = AppConfig::default();
    config.nlp.batch_size = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_zero_max_text_length() {
    let mut config = AppConfig::default();
    config.nlp.max_text_length = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_invalid_export_format() {
    let mut config = AppConfig::default();
    config.export.default_format = "pdf".to_string();
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_valid_export_formats() {
    let valid_formats = vec!["txt", "csv", "json"];
    for format in valid_formats {
        let mut config = AppConfig::default();
        config.export.default_format = format.to_string();
        assert!(config.validate().is_ok(), "Failed for format: {}", format);
    }
}

#[test]
fn test_config_validation_negative_chunk_size() {
    let mut config = AppConfig::default();
    config.export.max_chunk_size_mb = -1.0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_zero_chunk_size() {
    let mut config = AppConfig::default();
    config.export.max_chunk_size_mb = 0.0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_zero_lines_per_chunk() {
    let mut config = AppConfig::default();
    config.export.max_lines_per_chunk = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_config_validation_zero_max_retries() {
    let mut config = AppConfig::default();
    config.imessage.max_retries = 0;
    assert!(config.validate().is_err());
}

#[test]
fn test_get_database_url_default() {
    let config = AppConfig::default();
    let url = config.get_database_url();
    assert_eq!(url, "sqlite:data/messages.db");
}

#[test]
fn test_get_database_url_from_env() {
    std::env::set_var("DATABASE_URL", "sqlite:test.db");
    let config = AppConfig::default();
    let url = config.get_database_url();
    assert_eq!(url, "sqlite:test.db");
    std::env::remove_var("DATABASE_URL");
}

#[test]
fn test_get_log_level_default() {
    let config = AppConfig::default();
    let level = config.get_log_level();
    assert_eq!(level, "info");
}

#[test]
fn test_get_log_level_from_env() {
    std::env::set_var("RUST_LOG", "debug");
    let config = AppConfig::default();
    let level = config.get_log_level();
    assert_eq!(level, "debug");
    std::env::remove_var("RUST_LOG");
}

#[test]
fn test_database_config_clone() {
    let config = DatabaseConfig {
        url: "sqlite:test.db".to_string(),
        max_connections: 5,
        connection_timeout_secs: 15,
        migration_timeout_secs: 30,
    };
    let cloned = config.clone();
    assert_eq!(config.url, cloned.url);
    assert_eq!(config.max_connections, cloned.max_connections);
}

#[test]
fn test_logging_config_with_file_path() {
    let config = LoggingConfig {
        level: "debug".to_string(),
        file_path: Some("/var/log/app.log".to_string()),
        max_file_size_mb: 50,
        max_files: 3,
        format: "json".to_string(),
    };
    assert!(config.file_path.is_some());
}

#[test]
fn test_nlp_config_all_features_disabled() {
    let config = NlpConfig {
        batch_size: 50,
        max_text_length: 5000,
        enable_sentiment: false,
        enable_ner: false,
        enable_language_detection: false,
        processing_timeout_secs: 120,
    };
    assert!(!config.enable_sentiment);
    assert!(!config.enable_ner);
    assert!(!config.enable_language_detection);
}

#[test]
fn test_export_config_with_compression() {
    let config = ExportConfig {
        default_format: "json".to_string(),
        max_chunk_size_mb: 25.5,
        max_lines_per_chunk: 50000,
        output_directory: "/tmp/output".to_string(),
        enable_compression: true,
    };
    assert!(config.enable_compression);
}

#[test]
fn test_imessage_config_with_custom_path() {
    let config = IMessageConfig {
        database_path: "/custom/path/chat.db".to_string(),
        connection_timeout_secs: 45,
        read_timeout_secs: 90,
        max_retries: 5,
    };
    assert_eq!(config.database_path, "/custom/path/chat.db");
}

#[test]
fn test_config_validation_boundary_values() {
    let mut config = AppConfig::default();
    config.database.max_connections = 1;
    config.database.connection_timeout_secs = 1;
    config.nlp.batch_size = 1;
    config.nlp.max_text_length = 1;
    config.export.max_chunk_size_mb = 0.1;
    config.export.max_lines_per_chunk = 1;
    config.imessage.max_retries = 1;

    assert!(config.validate().is_ok());
}

#[test]
fn test_config_validation_large_values() {
    let mut config = AppConfig::default();
    config.database.max_connections = 1000;
    config.database.connection_timeout_secs = 3600;
    config.nlp.batch_size = 10000;
    config.nlp.max_text_length = 1000000;
    config.export.max_chunk_size_mb = 1000.0;
    config.export.max_lines_per_chunk = 1000000;
    config.imessage.max_retries = 100;

    assert!(config.validate().is_ok());
}

#[test]
fn test_get_imessage_db_path_empty_default() {
    let config = AppConfig::default();
    let path = config.get_imessage_db_path();
    // On non-macOS or without HOME, should be empty
    #[cfg(not(target_os = "macos"))]
    assert_eq!(path, "");
}

#[test]
fn test_get_imessage_db_path_from_config() {
    let mut config = AppConfig::default();
    config.imessage.database_path = "/custom/chat.db".to_string();
    let path = config.get_imessage_db_path();
    assert_eq!(path, "/custom/chat.db");
}

#[test]
fn test_config_debug_format() {
    let config = AppConfig::default();
    let debug_str = format!("{:?}", config);
    assert!(debug_str.contains("AppConfig"));
}

#[test]
fn test_config_clone() {
    let config = AppConfig::default();
    let cloned = config.clone();
    assert_eq!(config.database.url, cloned.database.url);
    assert_eq!(config.logging.level, cloned.logging.level);
}