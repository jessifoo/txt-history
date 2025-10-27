use anyhow::{Context, Result};
use regex::Regex;
use rust_stemmers::{Algorithm, Stemmer};
// use serde::{Deserialize, Serialize}; // Unused for now
use std::collections::HashSet;
use stop_words::{get, LANGUAGE};
use unicode_normalization::UnicodeNormalization;
use whatlang::{detect, Lang};

use crate::db::Database;
use crate::models::{DbProcessedMessage, NamedEntity, NlpAnalysis};

/// NLP processor for text analysis
pub struct NlpProcessor {
    pub version: String,
    url_regex: Regex,
    emoji_regex: Regex,
    special_chars_regex: Regex,
    extra_spaces_regex: Regex,
    stopwords: HashSet<String>,
    stemmer: Stemmer,
}

impl NlpProcessor {
    /// Create a new NLP processor with the specified version
    pub fn new(version: &str) -> Result<Self> {
        // Initialize regular expressions for text cleaning
        let url_regex = Regex::new(r"https?://\S+|www\.\S+")
            .map_err(|e| anyhow::anyhow!("Failed to compile URL regex: {e}"))?;
        let emoji_regex = Regex::new(r"[\p{Emoji}]")
            .map_err(|e| anyhow::anyhow!("Failed to compile emoji regex: {e}"))?;
        let special_chars_regex = Regex::new(r"[^\w\s]")
            .map_err(|e| anyhow::anyhow!("Failed to compile special chars regex: {e}"))?;
        let extra_spaces_regex = Regex::new(r"\s+")
            .map_err(|e| anyhow::anyhow!("Failed to compile spaces regex: {e}"))?;

        // Initialize stopwords for English
        let stopwords: HashSet<String> = get(LANGUAGE::English)
            .iter()
            .map(ToString::to_string)
            .collect();

        // Initialize stemmer for English
        let stemmer = Stemmer::create(Algorithm::English);

        Ok(Self {
            version: version.to_string(),
            url_regex,
            emoji_regex,
            special_chars_regex,
            extra_spaces_regex,
            stopwords,
            stemmer,
        })
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
    #[must_use]
    pub fn clean_text(&self, text: &str) -> String {
        // Normalize Unicode characters
        let normalized = text.nfc().collect::<String>();

        // Remove URLs
        let no_urls = self.url_regex.replace_all(&normalized, " ").to_string();

        // Remove emojis
        let no_emojis = self.emoji_regex.replace_all(&no_urls, " ").to_string();

        // Replace special characters with space
        let no_special = self
            .special_chars_regex
            .replace_all(&no_emojis, " ")
            .to_string();

        // Normalize whitespace
        let normalized_spaces = self
            .extra_spaces_regex
            .replace_all(&no_special, " ")
            .to_string();

        // Trim and convert to lowercase
        normalized_spaces.trim().to_lowercase()
    }

    /// Tokenize the text into words
    #[must_use]
    pub fn tokenize(&self, text: &str) -> Vec<String> {
        text.split_whitespace()
            .map(ToString::to_string)
            .filter(|s| !s.is_empty() && !self.stopwords.contains(s))
            .collect()
    }

    /// Lemmatize/stem the tokens
    fn lemmatize(&self, tokens: &[String]) -> String {
        tokens
            .iter()
            .map(|token| self.stemmer.stem(token))
            .collect::<Vec<_>>()
            .join(" ")
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
                    if !word.is_empty() && word.chars().next().is_some_and(char::is_uppercase) {
                        // Skip common sentence starters
                        if i > 0 || !["I", "The", "A", "An", "This", "That"].contains(word) {
                            let start = text.find(word).unwrap_or(0);
                            let end = start + word.len();

                            entities.push(NamedEntity {
                                text: (*word).to_string(),
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

    /// Analyze sentiment of text using enhanced word-based analysis
    #[must_use]
    pub fn analyze_sentiment(&self, text: &str) -> f32 {
        // Enhanced sentiment analysis with weighted words and context awareness
        let positive_words = [
            ("good", 1.0),
            ("great", 1.5),
            ("excellent", 2.0),
            ("amazing", 2.0),
            ("wonderful", 1.8),
            ("fantastic", 1.8),
            ("happy", 1.2),
            ("joy", 1.5),
            ("love", 2.0),
            ("like", 1.0),
            ("best", 1.5),
            ("better", 1.2),
            ("awesome", 1.8),
            ("perfect", 2.0),
            ("brilliant", 1.8),
            ("outstanding", 1.8),
            ("superb", 1.8),
            ("marvelous", 1.8),
            ("delightful", 1.5),
            ("pleased", 1.2),
            ("satisfied", 1.0),
            ("excited", 1.5),
            ("thrilled", 1.8),
            ("grateful", 1.5),
            ("blessed", 1.5),
            ("fortunate", 1.2),
            ("lucky", 1.0),
            ("successful", 1.5),
            ("victory", 1.8),
            ("win", 1.5),
            ("achievement", 1.5),
        ];

        let negative_words = [
            ("bad", -1.0),
            ("terrible", -2.0),
            ("awful", -2.0),
            ("horrible", -2.0),
            ("worst", -2.0),
            ("hate", -2.0),
            ("dislike", -1.0),
            ("poor", -1.2),
            ("disappointing", -1.5),
            ("sad", -1.2),
            ("angry", -1.5),
            ("upset", -1.2),
            ("frustrated", -1.5),
            ("annoyed", -1.2),
            ("irritated", -1.2),
            ("disgusted", -1.8),
            ("furious", -2.0),
            ("devastated", -2.0),
            ("depressed", -1.8),
            ("miserable", -1.8),
            ("hopeless", -1.8),
            ("desperate", -1.5),
            ("worried", -1.2),
            ("anxious", -1.2),
            ("scared", -1.5),
            ("afraid", -1.2),
            ("disgusting", -1.8),
            ("revolting", -1.8),
            ("pathetic", -1.5),
            ("useless", -1.5),
            ("worthless", -1.8),
        ];

        // Intensifiers that modify sentiment
        let intensifiers = [
            ("very", 1.5),
            ("extremely", 2.0),
            ("incredibly", 2.0),
            ("absolutely", 2.0),
            ("completely", 1.8),
            ("totally", 1.8),
            ("really", 1.3),
            ("so", 1.2),
            ("quite", 1.2),
            ("rather", 1.1),
            ("somewhat", 0.8),
            ("slightly", 0.7),
            ("barely", 0.5),
            ("hardly", 0.5),
        ];

        // Negation words that flip sentiment
        let negations = [
            "not", "no", "never", "none", "nothing", "nobody", "nowhere", "neither", "nor",
        ];

        let words: Vec<&str> = text.split_whitespace().collect();
        let mut total_sentiment = 0.0;
        let mut word_count = 0.0;

        for (i, word) in words.iter().enumerate() {
            let lower_word = word.to_lowercase();

            // Check for positive words
            if let Some((_, weight)) = positive_words.iter().find(|(w, _)| *w == lower_word) {
                let mut sentiment = *weight;

                // Check for intensifiers before this word
                if i > 0 {
                    let prev_word = words[i - 1].to_lowercase();
                    if let Some((_, intensity)) = intensifiers.iter().find(|(w, _)| *w == prev_word)
                    {
                        sentiment *= *intensity;
                    }
                }

                // Check for negations before this word
                let has_negation = (i >= 1
                    && negations.contains(&words[i - 1].to_lowercase().as_str()))
                    || (i >= 2 && negations.contains(&words[i - 2].to_lowercase().as_str()));

                if has_negation {
                    sentiment = -sentiment * 0.8; // Flip and reduce intensity
                }

                total_sentiment += sentiment;
                word_count += 1.0;
            }

            // Check for negative words
            if let Some((_, weight)) = negative_words.iter().find(|(w, _)| *w == lower_word) {
                let mut sentiment = *weight;

                // Check for intensifiers before this word
                if i > 0 {
                    let prev_word = words[i - 1].to_lowercase();
                    if let Some((_, intensity)) = intensifiers.iter().find(|(w, _)| *w == prev_word)
                    {
                        sentiment *= *intensity;
                    }
                }

                // Check for negations before this word
                let has_negation = (i >= 1
                    && negations.contains(&words[i - 1].to_lowercase().as_str()))
                    || (i >= 2 && negations.contains(&words[i - 2].to_lowercase().as_str()));

                if has_negation {
                    sentiment = -sentiment * 0.8; // Flip and reduce intensity
                }

                total_sentiment += sentiment;
                word_count += 1.0;
            }
        }

        // Normalize sentiment score to -1.0 to 1.0 range
        if word_count == 0.0 {
            0.0 // Neutral if no sentiment words found
        } else {
            let normalized: f32 = total_sentiment / word_count;
            // Clamp to [-1.0, 1.0] range
            normalized.max(-1.0_f32).min(1.0_f32)
        }
    }

    /// Process a batch of messages and store results in the database
    pub fn process_messages(
        &self,
        db: &Database,
        message_ids: &[i32],
    ) -> Result<Vec<DbProcessedMessage>> {
        let mut processed_messages = Vec::new();
        let _conn = &mut db.get_connection()?;

        for &message_id in message_ids {
            // Check if message has already been processed with this version
            let existing = db.get_processed_message(message_id, &self.version)?;
            if existing.is_some() {
                processed_messages.push(
                    existing.ok_or_else(|| {
                        anyhow::anyhow!("Failed to get existing processed message")
                    })?,
                );
                continue;
            }

            // Get the message from the database
            let message = db
                .get_message_by_id(message_id)?
                .context(format!("Message with ID {message_id} not found"))?;

            // Skip messages without text
            if message.text.is_none() {
                continue;
            }

            // Process the message text
            let analysis = self.process_text(
                &message
                    .text
                    .ok_or_else(|| anyhow::anyhow!("Message has no text content"))?,
            )?;

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
        let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");

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
        let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");

        let text = "this is a sample sentence with stopwords";
        let tokens = processor.tokenize(text);

        // Stopwords like "this", "is", "a", "with" should be removed
        assert!(!tokens.contains(&"this".to_string()));
        assert!(!tokens.contains(&"is".to_string()));
        assert!(!tokens.contains(&"a".to_string()));
        assert!(!tokens.contains(&"with".to_string()));

        // Content words should remain
        assert!(tokens.contains(&"sample".to_string()));
        assert!(tokens.contains(&"sentence".to_string()));
        assert!(tokens.contains(&"stopwords".to_string()));
    }

    #[test]
    fn test_sentiment_analysis() {
        let processor = NlpProcessor::new("test_v1").expect("Failed to create NLP processor");

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
