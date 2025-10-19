use anyhow::{Context, Result};
use regex::Regex;
use rust_stemmers::{Algorithm, Stemmer};
// use serde::{Deserialize, Serialize}; // Unused for now
use std::collections::HashSet;
use stop_words::{LANGUAGE, get};
use unicode_normalization::UnicodeNormalization;
use whatlang::{Lang, detect};

use crate::db::Database;
use crate::models::{DbProcessedMessage, NamedEntity, NlpAnalysis};

/// NLP processor for text analysis
pub struct NlpProcessor {
    version: String,
    url_regex: Regex,
    emoji_regex: Regex,
    special_chars_regex: Regex,
    extra_spaces_regex: Regex,
    stopwords: HashSet<String>,
    stemmer: Stemmer,
}

impl NlpProcessor {
    /// Create a new NLP processor with the specified version
    pub fn new(version: &str) -> Self {
        // Initialize regular expressions for text cleaning
        let url_regex = Regex::new(r"https?://\S+|www\.\S+").unwrap();
        let emoji_regex = Regex::new(r"[\p{Emoji}]").unwrap();
        let special_chars_regex = Regex::new(r"[^\w\s]").unwrap();
        let extra_spaces_regex = Regex::new(r"\s+").unwrap();

        // Initialize stopwords for English
        let stopwords: HashSet<String> = get(LANGUAGE::English).iter().map(|s| s.to_string()).collect();

        // Initialize stemmer for English
        let stemmer = Stemmer::create(Algorithm::English);

        Self {
            version: version.to_string(),
            url_regex,
            emoji_regex,
            special_chars_regex,
            extra_spaces_regex,
            stopwords,
            stemmer,
        }
    }

    /// Process a message and return NLP analysis
    pub fn process_text(&self, text: &str) -> Result<NlpAnalysis> {
        // Clean the text
        let processed_text = self.clean_text(text);

        // Tokenize the text
        let tokens = self.tokenize(&processed_text);

        // Lemmatize/stem the text
        let lemmatized_text = self.lemmatize(&tokens);

        // Extract named entities (simplified implementation)
        let entities = self.extract_entities(&processed_text);

        // Calculate sentiment score (simplified implementation)
        let sentiment_score = self.analyze_sentiment(&processed_text);

        // Detect language
        let language = detect(text).map(|info| info.lang().code().to_string());

        Ok(NlpAnalysis {
            processed_text,
            tokens,
            entities,
            lemmatized_text: Some(lemmatized_text),
            sentiment_score: Some(sentiment_score),
            language,
        })
    }

    /// Clean the text by removing URLs, emojis, and normalizing whitespace
    fn clean_text(&self, text: &str) -> String {
        // Normalize Unicode characters
        let normalized = text.nfc().collect::<String>();

        // Remove URLs
        let no_urls = self.url_regex.replace_all(&normalized, " ").to_string();

        // Remove emojis
        let no_emojis = self.emoji_regex.replace_all(&no_urls, " ").to_string();

        // Replace special characters with space
        let no_special = self.special_chars_regex.replace_all(&no_emojis, " ").to_string();

        // Normalize whitespace
        let normalized_spaces = self.extra_spaces_regex.replace_all(&no_special, " ").to_string();

        // Trim and convert to lowercase
        normalized_spaces.trim().to_lowercase()
    }

    /// Tokenize the text into words
    fn tokenize(&self, text: &str) -> Vec<String> {
        text.split_whitespace()
            .map(|s| s.to_string())
            .filter(|s| !s.is_empty() && !self.stopwords.contains(s))
            .collect()
    }

    /// Lemmatize/stem the tokens
    fn lemmatize(&self, tokens: &[String]) -> String {
        tokens.iter().map(|token| self.stemmer.stem(token)).collect::<Vec<_>>().join(" ")
    }

    /// Extract named entities from text (simplified implementation)
    fn extract_entities(&self, text: &str) -> Vec<NamedEntity> {
        // This is a very simplified implementation
        // In a real-world scenario, you would use a proper NER model
        let mut entities = Vec::new();

        // Detect language
        if let Some(info) = detect(text) {
            if info.lang() == Lang::Eng && info.confidence() > 0.5 {
                // Simple rule-based entity extraction for demonstration
                // Look for capitalized words that might be names
                let words: Vec<&str> = text.split_whitespace().collect();

                for (i, word) in words.iter().enumerate() {
                    if !word.is_empty() && word.chars().next().unwrap().is_uppercase() {
                        // Skip common sentence starters
                        if i > 0 || !["I", "The", "A", "An", "This", "That"].contains(word) {
                            let start = text.find(word).unwrap_or(0);
                            let end = start + word.len();

                            entities.push(NamedEntity {
                                text: word.to_string(),
                                entity_type: "PERSON".to_string(), // Simplified
                                start,
                                end,
                            });
                        }
                    }
                }
            }
        }

        entities
    }

    /// Analyze sentiment of text (simplified implementation)
    fn analyze_sentiment(&self, text: &str) -> f32 {
        // This is a very simplified implementation
        // In a real-world scenario, you would use a proper sentiment analysis model

        // Define simple positive and negative word lists
        let positive_words = [
            "good",
            "great",
            "excellent",
            "amazing",
            "wonderful",
            "fantastic",
            "happy",
            "joy",
            "love",
            "like",
            "best",
            "better",
            "awesome",
        ];

        let negative_words = [
            "bad",
            "terrible",
            "awful",
            "horrible",
            "worst",
            "hate",
            "dislike",
            "poor",
            "disappointing",
            "sad",
            "angry",
            "upset",
        ];

        // Count positive and negative words
        let words: Vec<&str> = text.split_whitespace().collect();
        let positive_count = words.iter().filter(|w| positive_words.contains(w)).count() as f32;
        let negative_count = words.iter().filter(|w| negative_words.contains(w)).count() as f32;

        // Calculate sentiment score (-1.0 to 1.0)
        if positive_count == 0.0 && negative_count == 0.0 {
            0.0 // Neutral
        } else {
            (positive_count - negative_count) / (positive_count + negative_count)
        }
    }

    /// Process a batch of messages and store results in the database
    pub fn process_messages(&self, db: &Database, message_ids: &[i32]) -> Result<Vec<DbProcessedMessage>> {
        let mut processed_messages = Vec::new();
        let _conn = &mut db.get_connection()?;

        for &message_id in message_ids {
            // Check if message has already been processed with this version
            let existing = db.get_processed_message(message_id, &self.version)?;
            if existing.is_some() {
                processed_messages.push(existing.unwrap());
                continue;
            }

            // Get the message from the database
            let message = db
                .get_message_by_id(message_id)?
                .context(format!("Message with ID {} not found", message_id))?;

            // Skip messages without text
            if message.text.is_none() {
                continue;
            }

            // Process the message text
            let analysis = self.process_text(&message.text.unwrap())?;

            // Convert to database model
            let new_processed = analysis.to_new_processed_message(message_id, &self.version);

            // Save to database
            let processed_message = db.add_processed_message(new_processed)?;
            processed_messages.push(processed_message);
        }

        Ok(processed_messages)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_clean_text() {
        let processor = NlpProcessor::new("test_v1");

        // Test URL removal
        let text_with_url = "Check out https://example.com for more info";
        let cleaned = processor.clean_text(text_with_url);
        assert!(!cleaned.contains("https://"));

        // Test emoji removal
        let text_with_emoji = "I love this 😍";
        let cleaned = processor.clean_text(text_with_emoji);
        assert!(!cleaned.contains("😍"));

        // Test special character handling
        let text_with_special = "Hello, world! How are you?";
        let cleaned = processor.clean_text(text_with_special);
        assert!(!cleaned.contains(","));
        assert!(!cleaned.contains("!"));
        assert!(!cleaned.contains("?"));

        // Test whitespace normalization
        let text_with_spaces = "  Too   many    spaces   ";
        let cleaned = processor.clean_text(text_with_spaces);
        assert_eq!(cleaned, "too many spaces");
    }

    #[test]
    fn test_tokenize() {
        let processor = NlpProcessor::new("test_v1");

        let text = "this is a test sentence with stopwords";
        let tokens = processor.tokenize(text);

        // Stopwords like "this", "is", "a", "with" should be removed
        assert!(!tokens.contains(&"this".to_string()));
        assert!(!tokens.contains(&"is".to_string()));
        assert!(!tokens.contains(&"a".to_string()));
        assert!(!tokens.contains(&"with".to_string()));

        // Content words should remain
        assert!(tokens.contains(&"test".to_string()));
        assert!(tokens.contains(&"sentence".to_string()));
        assert!(tokens.contains(&"stopwords".to_string()));
    }

    #[test]
    fn test_sentiment_analysis() {
        let processor = NlpProcessor::new("test_v1");

        // Positive text
        let positive_text = "I love this product it's amazing and wonderful";
        let positive_score = processor.analyze_sentiment(positive_text);
        assert!(positive_score > 0.0);

        // Negative text
        let negative_text = "This is terrible and I hate it";
        let negative_score = processor.analyze_sentiment(negative_text);
        assert!(negative_score < 0.0);

        // Neutral text
        let neutral_text = "The sky is blue and the grass is green";
        let neutral_score = processor.analyze_sentiment(neutral_text);
        assert_eq!(neutral_score, 0.0);
    }
}
