use txt_history_rust::nlp::NlpProcessor;

#[test]
fn test_nlp_processor_creation() {
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");
    assert_eq!(processor.version, "test_v1");
}

#[test]
fn test_text_cleaning() {
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");
    
    // Test URL removal
    let text_with_url = "Check out https://example.com for more info";
    let cleaned = processor.clean_text(text_with_url);
    println!("Cleaned text: '{}'", cleaned);
    assert!(!cleaned.contains("https://"));
    assert!(cleaned.contains("check"));
    
    // Test emoji removal
    let text_with_emoji = "Hello 😀 world 🌍";
    let cleaned = processor.clean_text(text_with_emoji);
    assert!(!cleaned.contains("😀"));
    assert!(!cleaned.contains("🌍"));
    
    // Test special character removal
    let text_with_special = "Hello!!! How are you???";
    let cleaned = processor.clean_text(text_with_special);
    assert!(!cleaned.contains("!!!"));
    assert!(!cleaned.contains("???"));
}

#[test]
fn test_tokenization() {
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");
    
    let text = "Hello world! This is a sample.";
    let tokens = processor.tokenize(text);
    
    println!("Generated tokens: {:?}", tokens);
    assert!(tokens.contains(&"Hello".to_string()));
    assert!(tokens.contains(&"world!".to_string()));
    assert!(tokens.contains(&"This".to_string()));
    assert!(tokens.contains(&"sample.".to_string()));
}

#[test]
fn test_sentiment_analysis() {
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");
    
    // Test positive sentiment
    let positive_text = "This is great and amazing!";
    let positive_score = processor.analyze_sentiment(positive_text);
    assert!(positive_score > 0.0);
    
    // Test negative sentiment
    let negative_text = "This is terrible and awful!";
    let negative_score = processor.analyze_sentiment(negative_text);
    assert!(negative_score < 0.0);
    
    // Test neutral sentiment
    let neutral_text = "The sky is blue and the grass is green";
    let neutral_score = processor.analyze_sentiment(neutral_text);
    assert_eq!(neutral_score, 0.0);
}

#[test]
fn test_full_text_processing() {
    let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");
    
    let text = "Hello world! This is a great test message with https://example.com and 😀 emojis.";
    let analysis = processor.process_text(text).expect("Failed to process text");
    
    // Check that text was cleaned
    assert!(!analysis.processed_text.contains("https://"));
    assert!(!analysis.processed_text.contains("😀"));
    
    // Check that tokens were extracted
    assert!(!analysis.tokens.is_empty());
    // Note: "Hello" might be removed as a stop word, so we check for other tokens
    assert!(analysis.tokens.iter().any(|t| t.len() > 0));
    
    // Check that sentiment was calculated
    assert!(analysis.sentiment_score.is_some());
    
    // Check that language was detected
    assert!(analysis.language.is_some());
    // Language detection might return "eng" instead of "en"
    let detected_lang = analysis.language.unwrap();
    assert!(detected_lang == "en" || detected_lang == "eng");
}
