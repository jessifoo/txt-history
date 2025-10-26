use anyhow::Result;
use std::path::Path;
use tracing::info;
use tracing_appender::{non_blocking, rolling};
use tracing_subscriber::{layer::SubscriberExt, util::SubscriberInitExt, EnvFilter, Registry};

/// Initialize structured logging system
pub fn init_logging(log_level: Option<&str>, log_file: Option<&Path>) -> Result<()> {
    // Set up environment filter
    let env_filter = EnvFilter::try_from_default_env()
        .or_else(|_| {
            let level = log_level.unwrap_or("info");
            EnvFilter::try_new(level)
        })
        .map_err(|e| anyhow::anyhow!("Failed to create log filter: {}", e))?;

    // Create registry
    let registry = Registry::default().with(env_filter);

    // Add console layer
    let console_layer = tracing_subscriber::fmt::layer()
        .with_writer(std::io::stderr)
        .with_ansi(true)
        .with_target(true)
        .with_thread_ids(true)
        .with_thread_names(true);

    // Add file layer if log file is specified
    if let Some(log_path) = log_file {
        let file_appender = rolling::daily(log_path.parent().unwrap_or(Path::new(".")), "app.log");
        let (non_blocking_appender, _guard) = non_blocking(file_appender);

        let file_layer = tracing_subscriber::fmt::layer()
            .with_writer(non_blocking_appender)
            .with_ansi(false)
            .with_target(true)
            .with_thread_ids(true)
            .with_thread_names(true)
            .json();

        registry.with(console_layer).with(file_layer).init();
    } else {
        registry.with(console_layer).init();
    }

    info!("Logging system initialized");
    Ok(())
}

/// Performance timing utilities
pub struct OperationTimer {
    operation: String,
    start: std::time::Instant,
}

impl OperationTimer {
    pub fn new(operation: &str) -> Self {
        Self {
            operation: operation.to_string(),
            start: std::time::Instant::now(),
        }
    }

    pub fn finish(self) -> u128 {
        let duration = self.start.elapsed().as_millis();
        tracing::info!(
            operation = self.operation,
            duration_ms = duration,
            "Operation completed"
        );
        duration
    }
}

impl Drop for OperationTimer {
    fn drop(&mut self) {
        if !std::thread::panicking() {
            let duration = self.start.elapsed().as_millis();
            tracing::debug!(
                operation = self.operation,
                duration_ms = duration,
                "Operation finished"
            );
        }
    }
}
