-- Create processed_messages table
CREATE TABLE processed_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    original_message_id INTEGER NOT NULL,
    processed_text TEXT NOT NULL,
    tokens TEXT,                      -- Tokenized text (JSON array)
    lemmatized_text TEXT,             -- Lemmatized version
    named_entities TEXT,              -- Named entities (JSON)
    sentiment_score REAL,             -- Sentiment analysis score
    processed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    processing_version TEXT NOT NULL, -- Version of processing pipeline
    FOREIGN KEY(original_message_id) REFERENCES messages(id),
    UNIQUE(original_message_id, processing_version)
);

-- Create indexes for processed_messages table
CREATE INDEX idx_processed_messages_original ON processed_messages(original_message_id);
CREATE INDEX idx_processed_messages_sentiment ON processed_messages(sentiment_score);
CREATE INDEX idx_processed_messages_version ON processed_messages(processing_version);
