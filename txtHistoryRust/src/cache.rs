use crate::models::{Contact, DateRange, Message};
use anyhow::{Context, Result};
use chrono::{DateTime, Local};
use serde::{Deserialize, Serialize};
use std::path::PathBuf;

#[derive(Serialize, Deserialize)]
struct CacheEntry {
    contact_name: String,
    date_range: DateRange,
    messages: Vec<Message>,
    timestamp: DateTime<Local>,
}

pub struct MessageCache {
    db: sled::Db,
}

impl MessageCache {
    pub fn new() -> Result<Self> {
        // Create cache directory if it doesn't exist
        let cache_dir = PathBuf::from(".message_cache");
        std::fs::create_dir_all(&cache_dir)?;
        
        let db = sled::open(&cache_dir)
            .context("Failed to open cache database")?;
        
        Ok(Self { db })
    }

    fn make_key(contact: &Contact, date_range: &DateRange) -> Vec<u8> {
        // Create a unique key based on contact and date range
        let key = format!(
            "{}:{}:{}",
            contact.name,
            date_range.start.map_or("".to_string(), |d| d.to_rfc3339()),
            date_range.end.map_or("".to_string(), |d| d.to_rfc3339())
        );
        key.into_bytes()
    }

    pub fn get_cached_messages(&self, contact: &Contact, date_range: &DateRange) -> Result<Option<Vec<Message>>> {
        let key = Self::make_key(contact, date_range);
        
        if let Some(data) = self.db.get(&key)? {
            let entry: CacheEntry = bincode::deserialize(&data)?;
            Ok(Some(entry.messages))
        } else {
            Ok(None)
        }
    }

    pub fn cache_messages(&self, contact: &Contact, date_range: &DateRange, messages: &[Message]) -> Result<()> {
        let key = Self::make_key(contact, date_range);
        
        let entry = CacheEntry {
            contact_name: contact.name.clone(),
            date_range: date_range.clone(),
            messages: messages.to_vec(),
            timestamp: Local::now(),
        };

        let data = bincode::serialize(&entry)?;
        self.db.insert(key, data)?;
        self.db.flush()?;
        
        Ok(())
    }

    pub fn clear_cache(&self) -> Result<()> {
        self.db.clear()?;
        self.db.flush()?;
        Ok(())
    }
}
