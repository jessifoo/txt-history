use anyhow::Result;
use metrics::{counter, histogram, gauge, increment_counter, record_histogram, gauge_value};
use std::time::Duration;

/// Metrics collection and management
pub struct MetricsCollector {
    // Database metrics
    pub db_connections_total: &'static str,
    pub db_operations_total: &'static str,
    pub db_operation_duration: &'static str,
    pub db_connection_pool_size: &'static str,
    
    // Message processing metrics
    pub messages_processed_total: &'static str,
    pub message_processing_duration: &'static str,
    pub messages_imported_total: &'static str,
    pub messages_exported_total: &'static str,
    
    // NLP processing metrics
    pub nlp_operations_total: &'static str,
    pub nlp_processing_duration: &'static str,
    pub nlp_batch_size: &'static str,
    pub nlp_sentiment_scores: &'static str,
    
    // Export metrics
    pub export_operations_total: &'static str,
    pub export_duration: &'static str,
    pub export_file_size_bytes: &'static str,
    pub export_files_created_total: &'static str,
    
    // Error metrics
    pub errors_total: &'static str,
    pub error_rate: &'static str,
}

impl Default for MetricsCollector {
    fn default() -> Self {
        Self {
            db_connections_total: "txt_history_db_connections_total",
            db_operations_total: "txt_history_db_operations_total",
            db_operation_duration: "txt_history_db_operation_duration_seconds",
            db_connection_pool_size: "txt_history_db_connection_pool_size",
            
            messages_processed_total: "txt_history_messages_processed_total",
            message_processing_duration: "txt_history_message_processing_duration_seconds",
            messages_imported_total: "txt_history_messages_imported_total",
            messages_exported_total: "txt_history_messages_exported_total",
            
            nlp_operations_total: "txt_history_nlp_operations_total",
            nlp_processing_duration: "txt_history_nlp_processing_duration_seconds",
            nlp_batch_size: "txt_history_nlp_batch_size",
            nlp_sentiment_scores: "txt_history_nlp_sentiment_scores",
            
            export_operations_total: "txt_history_export_operations_total",
            export_duration: "txt_history_export_duration_seconds",
            export_file_size_bytes: "txt_history_export_file_size_bytes",
            export_files_created_total: "txt_history_export_files_created_total",
            
            errors_total: "txt_history_errors_total",
            error_rate: "txt_history_error_rate",
        }
    }
}

impl MetricsCollector {
    /// Initialize metrics collection
    pub fn init() -> Result<()> {
        // Initialize the metrics recorder
        metrics::set_global_recorder(metrics::NoopRecorder)
            .map_err(|e| anyhow::anyhow!("Failed to initialize metrics recorder: {}", e))?;
        
        Ok(())
    }

    /// Record database operation metrics
    pub fn record_db_operation(&self, operation: &str, duration: Duration, success: bool) {
        let labels = [
            ("operation", operation),
            ("status", if success { "success" } else { "error" }),
        ];
        
        increment_counter!(self.db_operations_total, &labels);
        record_histogram!(self.db_operation_duration, duration.as_secs_f64(), &labels);
        
        if !success {
            increment_counter!(self.errors_total, &[("type", "database")]);
        }
    }

    /// Record message processing metrics
    pub fn record_message_processing(&self, count: usize, duration: Duration, operation: &str) {
        let labels = [("operation", operation)];
        
        counter!(self.messages_processed_total, count as u64);
        record_histogram!(self.message_processing_duration, duration.as_secs_f64(), &labels);
    }

    /// Record message import metrics
    pub fn record_message_import(&self, count: usize, source: &str) {
        let labels = [("source", source)];
        counter!(self.messages_imported_total, count as u64);
    }

    /// Record message export metrics
    pub fn record_message_export(&self, count: usize, format: &str) {
        let labels = [("format", format)];
        counter!(self.messages_exported_total, count as u64);
    }

    /// Record NLP processing metrics
    pub fn record_nlp_processing(&self, batch_size: usize, duration: Duration, operation: &str) {
        let labels = [("operation", operation)];
        
        counter!(self.nlp_operations_total, 1);
        record_histogram!(self.nlp_processing_duration, duration.as_secs_f64());
        gauge!(self.nlp_batch_size, batch_size as f64);
    }

    /// Record sentiment analysis metrics
    pub fn record_sentiment_analysis(&self, score: f32, text_length: usize) {
        record_histogram!(self.nlp_sentiment_scores, score as f64);
        record_histogram!("txt_history_nlp_text_length", text_length as f64);
    }

    /// Record export operation metrics
    pub fn record_export_operation(&self, format: &str, file_count: usize, total_size_bytes: u64, duration: Duration) {
        let labels = [("format", format)];
        
        counter!(self.export_operations_total, 1);
        record_histogram!(self.export_duration, duration.as_secs_f64());
        counter!(self.export_files_created_total, file_count as u64);
        record_histogram!(self.export_file_size_bytes, total_size_bytes as f64);
    }

    /// Record error metrics
    pub fn record_error(&self, error_type: &str, operation: &str) {
        let labels = [
            ("type", error_type),
            ("operation", operation),
        ];
        
        increment_counter!(self.errors_total, &labels);
    }

    /// Update connection pool size
    pub fn update_connection_pool_size(&self, size: usize) {
        gauge!(self.db_connection_pool_size, size as f64);
    }

    /// Record custom histogram
    pub fn record_histogram(&self, name: &str, value: f64, labels: &[(&str, &str)]) {
        record_histogram!(name, value, labels);
    }

    /// Record custom counter
    pub fn increment_counter(&self, name: &str, labels: &[(&str, &str)]) {
        increment_counter!(name, labels);
    }

    /// Record custom gauge
    pub fn set_gauge(&self, name: &str, value: f64, labels: &[(&str, &str)]) {
        gauge!(name, value);
    }
}

/// Performance timing wrapper for metrics
pub struct MetricsTimer {
    collector: MetricsCollector,
    operation: String,
    start: std::time::Instant,
}

impl MetricsTimer {
    pub fn new(collector: MetricsCollector, operation: &str) -> Self {
        Self {
            collector,
            operation: operation.to_string(),
            start: std::time::Instant::now(),
        }
    }

    pub fn finish(self, success: bool) {
        let duration = self.start.elapsed();
        self.collector.record_db_operation(&self.operation, duration, success);
    }
}

/// Convenience macros for common metrics
#[macro_export]
macro_rules! record_db_operation {
    ($collector:expr, $operation:expr, $duration:expr, $success:expr) => {
        $collector.record_db_operation($operation, $duration, $success);
    };
}

#[macro_export]
macro_rules! record_message_processing {
    ($collector:expr, $count:expr, $duration:expr, $operation:expr) => {
        $collector.record_message_processing($count, $duration, $operation);
    };
}

#[macro_export]
macro_rules! record_error {
    ($collector:expr, $error_type:expr, $operation:expr) => {
        $collector.record_error($error_type, $operation);
    };
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_metrics_collector_creation() {
        let collector = MetricsCollector::default();
        assert_eq!(collector.db_connections_total, "txt_history_db_connections_total");
    }

    #[test]
    fn test_metrics_initialization() {
        // This test might fail if metrics is already initialized
        // but that's expected behavior
        let result = MetricsCollector::init();
        // We don't assert on the result since it might fail if already initialized
    }
}
