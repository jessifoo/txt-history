//! Comprehensive unit tests for metrics.rs module

use std::time::Duration;
use txt_history_rust::metrics::{MetricsCollector, MetricsTimer};

#[test]
fn test_metrics_collector_default() {
    let collector = MetricsCollector::default();
    assert_eq!(collector.db_operations_total, 0);
    assert_eq!(collector.messages_processed_total, 0);
    assert_eq!(collector.messages_imported_total, 0);
    assert_eq!(collector.messages_exported_total, 0);
    assert_eq!(collector.nlp_operations_total, 0);
    assert_eq!(collector.export_operations_total, 0);
    assert_eq!(collector.errors_total, 0);
}

#[test]
fn test_metrics_initialization() {
    let result = MetricsCollector::init();
    assert!(result.is_ok());
}

#[test]
fn test_record_db_operation_success() {
    let mut collector = MetricsCollector::default();
    collector.record_db_operation("select", Duration::from_millis(100), true);
    assert_eq!(collector.db_operations_total, 1);
    assert_eq!(collector.errors_total, 0);
}

#[test]
fn test_record_db_operation_failure() {
    let mut collector = MetricsCollector::default();
    collector.record_db_operation("select", Duration::from_millis(100), false);
    assert_eq!(collector.db_operations_total, 1);
    assert_eq!(collector.errors_total, 1);
}

#[test]
fn test_record_multiple_db_operations() {
    let mut collector = MetricsCollector::default();
    collector.record_db_operation("select", Duration::from_millis(50), true);
    collector.record_db_operation("insert", Duration::from_millis(100), true);
    collector.record_db_operation("update", Duration::from_millis(75), false);
    
    assert_eq!(collector.db_operations_total, 3);
    assert_eq!(collector.errors_total, 1);
}

#[test]
fn test_record_message_processing() {
    let mut collector = MetricsCollector::default();
    collector.record_message_processing(10, Duration::from_secs(1), "parse");
    assert_eq!(collector.messages_processed_total, 10);
}

#[test]
fn test_record_message_processing_multiple() {
    let mut collector = MetricsCollector::default();
    collector.record_message_processing(10, Duration::from_secs(1), "parse");
    collector.record_message_processing(20, Duration::from_secs(2), "filter");
    collector.record_message_processing(15, Duration::from_millis(500), "transform");
    
    assert_eq!(collector.messages_processed_total, 45);
}

#[test]
fn test_record_message_import() {
    let mut collector = MetricsCollector::default();
    collector.record_message_import(100, "imessage");
    assert_eq!(collector.messages_imported_total, 100);
}

#[test]
fn test_record_message_import_multiple_sources() {
    let mut collector = MetricsCollector::default();
    collector.record_message_import(100, "imessage");
    collector.record_message_import(50, "csv");
    collector.record_message_import(75, "json");
    
    assert_eq!(collector.messages_imported_total, 225);
}

#[test]
fn test_record_message_export() {
    let mut collector = MetricsCollector::default();
    collector.record_message_export(50, "txt");
    assert_eq!(collector.messages_exported_total, 50);
}

#[test]
fn test_record_message_export_multiple_formats() {
    let mut collector = MetricsCollector::default();
    collector.record_message_export(50, "txt");
    collector.record_message_export(30, "csv");
    collector.record_message_export(20, "json");
    
    assert_eq!(collector.messages_exported_total, 100);
}

#[test]
fn test_record_nlp_processing() {
    let mut collector = MetricsCollector::default();
    collector.record_nlp_processing(10, Duration::from_millis(500), "sentiment");
    assert_eq!(collector.nlp_operations_total, 1);
}

#[test]
fn test_record_nlp_processing_multiple() {
    let mut collector = MetricsCollector::default();
    collector.record_nlp_processing(10, Duration::from_millis(500), "sentiment");
    collector.record_nlp_processing(20, Duration::from_secs(1), "ner");
    collector.record_nlp_processing(15, Duration::from_millis(300), "language");
    
    assert_eq!(collector.nlp_operations_total, 3);
}

#[test]
fn test_record_sentiment_analysis() {
    let collector = MetricsCollector::default();
    // Should not panic or error
    collector.record_sentiment_analysis(0.75, 100);
}

#[test]
fn test_record_sentiment_analysis_negative() {
    let collector = MetricsCollector::default();
    collector.record_sentiment_analysis(-0.5, 50);
}

#[test]
fn test_record_sentiment_analysis_positive() {
    let collector = MetricsCollector::default();
    collector.record_sentiment_analysis(0.9, 200);
}

#[test]
fn test_record_export_operation() {
    let mut collector = MetricsCollector::default();
    collector.record_export_operation("txt", 5, 102400, Duration::from_secs(2));
    assert_eq!(collector.export_operations_total, 1);
}

#[test]
fn test_record_export_operation_multiple() {
    let mut collector = MetricsCollector::default();
    collector.record_export_operation("txt", 5, 102400, Duration::from_secs(2));
    collector.record_export_operation("csv", 3, 51200, Duration::from_secs(1));
    collector.record_export_operation("json", 2, 25600, Duration::from_millis(500));
    
    assert_eq!(collector.export_operations_total, 3);
}

#[test]
fn test_record_error() {
    let mut collector = MetricsCollector::default();
    collector.record_error("database", "connection");
    assert_eq!(collector.errors_total, 1);
}

#[test]
fn test_record_multiple_errors() {
    let mut collector = MetricsCollector::default();
    collector.record_error("database", "connection");
    collector.record_error("network", "timeout");
    collector.record_error("validation", "input");
    
    assert_eq!(collector.errors_total, 3);
}

#[test]
fn test_get_summary_default() {
    let collector = MetricsCollector::default();
    let summary = collector.get_summary();
    
    assert!(summary.contains("Database operations: 0"));
    assert!(summary.contains("Messages processed: 0"));
    assert!(summary.contains("Errors: 0"));
}

#[test]
fn test_get_summary_with_metrics() {
    let mut collector = MetricsCollector::default();
    collector.record_db_operation("select", Duration::from_millis(100), true);
    collector.record_message_processing(10, Duration::from_secs(1), "parse");
    collector.record_message_import(50, "imessage");
    collector.record_message_export(25, "txt");
    collector.record_nlp_processing(5, Duration::from_millis(200), "sentiment");
    collector.record_export_operation("txt", 2, 10240, Duration::from_secs(1));
    collector.record_error("test", "error");
    
    let summary = collector.get_summary();
    
    assert!(summary.contains("Database operations: 1"));
    assert!(summary.contains("Messages processed: 10"));
    assert!(summary.contains("Messages imported: 50"));
    assert!(summary.contains("Messages exported: 25"));
    assert!(summary.contains("NLP operations: 1"));
    assert!(summary.contains("Export operations: 1"));
    assert!(summary.contains("Errors: 1"));
}

#[test]
fn test_metrics_timer_creation() {
    let timer = MetricsTimer::new("test_operation");
    assert_eq!(timer.operation, "test_operation");
}

#[test]
fn test_metrics_timer_finish_success() {
    let mut collector = MetricsCollector::default();
    let timer = MetricsTimer::new("test_op");
    
    std::thread::sleep(Duration::from_millis(10));
    timer.finish(&mut collector, true);
    
    assert_eq!(collector.db_operations_total, 1);
    assert_eq!(collector.errors_total, 0);
}

#[test]
fn test_metrics_timer_finish_failure() {
    let mut collector = MetricsCollector::default();
    let timer = MetricsTimer::new("test_op");
    
    timer.finish(&mut collector, false);
    
    assert_eq!(collector.db_operations_total, 1);
    assert_eq!(collector.errors_total, 1);
}

#[test]
fn test_metrics_zero_counts() {
    let collector = MetricsCollector::default();
    let summary = collector.get_summary();
    
    assert!(summary.contains(": 0"));
}

#[test]
fn test_metrics_large_counts() {
    let mut collector = MetricsCollector::default();
    
    for _ in 0..1000 {
        collector.record_message_processing(1, Duration::from_millis(1), "test");
    }
    
    assert_eq!(collector.messages_processed_total, 1000);
}

#[test]
fn test_metrics_concurrent_updates() {
    let mut collector = MetricsCollector::default();
    
    // Simulate concurrent-like updates
    for i in 0..10 {
        collector.record_db_operation("query", Duration::from_millis(i * 10), true);
        collector.record_message_processing(i as usize, Duration::from_millis(i * 5), "proc");
    }
    
    assert_eq!(collector.db_operations_total, 10);
    assert_eq!(collector.messages_processed_total, 45); // 0+1+2+...+9
}

#[test]
fn test_record_export_with_zero_files() {
    let mut collector = MetricsCollector::default();
    collector.record_export_operation("txt", 0, 0, Duration::from_secs(0));
    assert_eq!(collector.export_operations_total, 1);
}

#[test]
fn test_record_export_with_large_size() {
    let mut collector = MetricsCollector::default();
    collector.record_export_operation("txt", 100, u64::MAX, Duration::from_secs(10));
    assert_eq!(collector.export_operations_total, 1);
}

#[test]
fn test_metrics_summary_format() {
    let collector = MetricsCollector::default();
    let summary = collector.get_summary();
    
    assert!(summary.starts_with("Metrics Summary:"));
    assert!(summary.contains("\n"));
    assert!(summary.contains("- "));
}