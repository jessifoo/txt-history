# How We Get All Messages from One Conversation and Format Them

## Overview

This document explains the complete flow from fetching messages from a single iMessage conversation to formatting and writing them to files.

## Step-by-Step Flow

### 1. **Entry Point: `import_messages()`** (`src/main.rs:199`)

```rust
// User runs: cargo run -- import -n Phil -d 2025-01-01
async fn import_messages(name: &str, date: &Option<String>, ...) -> Result<()>
```

**What happens:**
- Gets iMessage database path (macOS: `~/Library/Messages/chat.db`)
- Creates `IMessageDatabaseRepo`
- Parses date range
- Gets contact info (name, phone, email)
- Calls `repo.fetch_messages()` to get all messages

---

### 2. **Finding the Conversation** (`src/repository.rs:272`)

#### Step 2a: Find Handle (Phone/Email → Handle ID)

```rust
// src/repository.rs:138-181
async fn find_handle(&self, contact: &Contact) -> Result<Option<Handle>>
```

**Process:**
1. **Try phone number first:**
   ```sql
   SELECT * FROM handle 
   WHERE id = ?1 OR id = ?2
   -- ?1 = "+18673335566"
   -- ?2 = "18673335566" (normalized version)
   ```
   - Searches for exact phone match
   - Also tries normalized version (with/without +)
   - Returns first matching `Handle` struct

2. **If phone fails, try email:**
   ```sql
   SELECT * FROM handle 
   WHERE id = ?
   -- ? = "apple@phil-g.com"
   ```
   - Searches for email match
   - Returns first matching `Handle` struct

**Result:** `Handle` struct containing:
- `id`: The phone/email identifier
- `rowid`: Database row ID

#### Step 2b: Find Chat (Handle → Chat)

```rust
// src/repository.rs:184-207
async fn find_chat_by_handle(&self, handle: &Handle) -> Result<Option<Chat>>
```

**Process:**
```sql
SELECT * FROM chat 
WHERE ROWID IN (
    SELECT chat_id 
    FROM chat_handle_join 
    WHERE handle_id = ?
)
-- ? = handle.rowid
```

**What this does:**
- `chat_handle_join` is a join table linking handles to chats
- Finds all chats associated with this handle
- Returns the first chat found

**Result:** `Chat` struct containing:
- `chat_identifier`: Unique chat identifier
- `rowid`: Database row ID (used for message lookup)

---

### 3. **Fetching All Messages from the Conversation** (`src/repository.rs:289-295`)

```rust
// Get ALL messages for this chat
let mut stmt = db.prepare(
    "SELECT * FROM message 
     WHERE ROWID IN (
         SELECT message_id 
         FROM chat_message_join 
         WHERE chat_id = ?
     ) 
     ORDER BY date ASC"
)?;
```

**What this SQL does:**
1. **`chat_message_join`** is a join table linking chats to messages
2. Finds all `message_id`s for this `chat_id`
3. Selects all messages with those ROWIDs
4. **Orders by date ASC** (oldest first)

**Result:** Iterator of all messages in the conversation, chronologically ordered

---

### 4. **Processing Each Message** (`src/repository.rs:329-400`)

For each message in the conversation:

#### Step 4a: Extract Message Data
```rust
let mut msg = ImessageMessage::extract(Ok(imessage))?;
```

#### Step 4b: Generate Text Content
```rust
msg.generate_text(&db);
```
- Calls `imessage-database` crate's method
- Populates `msg.text` field
- Handles attachments, links, etc.

#### Step 4c: Filter by Date Range
```rust
// Convert timestamp (nanoseconds → DateTime)
let seconds = msg.date / 1_000_000_000;
let nanoseconds = (msg.date % 1_000_000_000) as u32;
let msg_date_time = DateTime::from_timestamp(seconds, nanoseconds)?;

// Filter if before start date
if let Some(start) = &date_range.start {
    if msg_date_time < *start {
        continue; // Skip this message
    }
}

// Filter if after end date
if let Some(end) = &date_range.end {
    if msg_date_time > *end {
        continue; // Skip this message
    }
}
```

#### Step 4d: Determine Sender Name
```rust
let sender = if msg.is_from_me { 
    "Jess".to_string()  // Message from me
} else { 
    contact.name.clone()  // Message from contact
};
```

#### Step 4e: Filter by `only_contact` (if enabled)
```rust
if only_contact && sender == "Jess" {
    continue; // Skip messages from "Jess"
}
```

#### Step 4f: Convert to Our Message Format
```rust
let message = Message {
    sender: sender.clone(),
    timestamp: msg_date_time.with_timezone(&Local),
    content: text,
};
messages.push(message);
```

#### Step 4g: Save to Local Database (Optional)
```rust
self.database.add_message(new_message)?;
```
- Saves message to our local SQLite database
- For future queries without accessing iMessage DB

---

### 5. **Sorting Messages** (`src/repository.rs:404-405`)

```rust
// Ensure messages are sorted chronologically after filtering
messages.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
```

**Why:** After filtering by date range and `only_contact`, we ensure chronological order.

---

### 6. **Chunking Messages** (`src/main.rs:239-246`)

```rust
let chunks = if let Some(size_mb) = size {
    chunk_by_size(&messages, size_mb)  // Split by file size
} else if let Some(lines_count) = lines {
    chunk_by_lines(&messages, lines_count)  // Split by message count
} else {
    vec![messages]  // No chunking - all in one file
};
```

**Purpose:** Split large conversations into manageable files

---

### 7. **Formatting and Writing Messages** (`src/file_writer.rs`)

For each chunk, we write in **both TXT and CSV formats**:

#### TXT Format (`write_txt_file`)
```
Phil, Jan 15, 2025 02:30:00 PM, Hello there!

Jess, Jan 15, 2025 02:31:00 PM, Hi Phil!

Phil, Jan 15, 2025 02:32:00 PM, How are you?
```

**Format:** `sender, timestamp, content\n\n` (blank line between messages)

#### CSV Format (`write_csv_file`)
```csv
ID,Sender,Datetime,Message
1,Phil,Jan 15, 2025 02:30:00 PM,Hello there!
2,Jess,Jan 15, 2025 02:31:00 PM,Hi Phil!
3,Phil,Jan 15, 2025 02:32:00 PM,How are you?
```

**Format:** Header row + data rows with ID column

#### JSON Format (`write_json_file`)
```json
[
  {
    "sender": "Phil",
    "timestamp": "Jan 15, 2025 02:30:00 PM",
    "content": "Hello there!"
  },
  ...
]
```

---

## Complete Flow Diagram

```
User Command
    ↓
import_messages()
    ↓
IMessageDatabaseRepo::fetch_messages()
    ↓
┌─────────────────────────────────────┐
│ Step 1: Find Handle                │
│ Contact (phone/email) → Handle      │
│ SQL: SELECT * FROM handle WHERE...  │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 2: Find Chat                   │
│ Handle → Chat                        │
│ SQL: SELECT * FROM chat WHERE...    │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 3: Get ALL Messages            │
│ Chat → All Messages                 │
│ SQL: SELECT * FROM message WHERE... │
│ ORDER BY date ASC                   │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 4: Process Each Message        │
│ - Generate text                     │
│ - Filter by date range              │
│ - Filter by only_contact            │
│ - Convert to Message struct         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 5: Sort Messages               │
│ messages.sort_by(timestamp)         │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 6: Chunk Messages              │
│ Split into chunks by size/lines     │
└─────────────────────────────────────┘
    ↓
┌─────────────────────────────────────┐
│ Step 7: Format & Write              │
│ - Write TXT format                  │
│ - Write CSV format                  │
│ Output: timestamp/chunks_txt/       │
│         timestamp/chunks_csv/       │
└─────────────────────────────────────┘
```

## Key Points

1. **Single SQL Query Gets All Messages**: One query retrieves all messages from the conversation using the join table
2. **Chronological Order**: Messages are ordered by date (oldest first) from SQL, then re-sorted after filtering
3. **Filtering Happens In-Memory**: Date range and `only_contact` filtering happens after fetching all messages
4. **Dual Format Output**: Both TXT and CSV files are written for each chunk
5. **Timestamp-Based Directories**: Files are organized in `timestamp/chunks_txt/` and `timestamp/chunks_csv/`

## Database Schema Understanding

### iMessage Database Tables:
- **`handle`**: Contact identifiers (phone numbers, emails)
- **`chat`**: Conversation threads
- **`message`**: Individual messages
- **`chat_handle_join`**: Links handles to chats (many-to-many)
- **`chat_message_join`**: Links chats to messages (many-to-many)

### Our Flow:
1. `handle` table → Find contact's handle ID
2. `chat_handle_join` → Find chat(s) for that handle
3. `chat_message_join` → Find all messages for that chat
4. `message` table → Get full message data

This is why we can get **all messages from one conversation** with a single SQL query!
