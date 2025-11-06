# How We're Using `imessage-database`

## Overview

The project uses `imessage-database` v2.4.0 to read messages directly from the macOS iMessage database, replacing the need for the external `imessage-exporter` command-line tool used in the Python version.

> **See also**: [Comparison with `imessage-exporter`](./IMESSAGE_EXPORTER_VS_IMESSAGE_DATABASE.md) for a detailed analysis of why `imessage-database` is more powerful.

## Usage Pattern

### 1. **Direct Database Access** (`IMessageDatabaseRepo`)

Instead of calling an external tool, we:
- Connect directly to the iMessage SQLite database
- Query tables using SQL
- Extract data using the crate's `Table` trait

### 2. **Key Components Used**

```rust
use imessage_database::tables::{
    chat::Chat,           // Chat/conversation data
    handle::Handle,       // Contact identifiers (phone/email)
    messages::Message,    // Individual messages
    table::{Table, get_connection},  // Database connection
};
```

### 3. **Current Implementation Flow**

1. **Find Handle** (phone/email → Handle)
   - Query `handle` table by phone number or email
   - Extract `Handle` struct using `Handle::extract()`

2. **Find Chat** (Handle → Chat)
   - Query `chat` table via `chat_handle_join`
   - Extract `Chat` struct

3. **Fetch Messages** (Chat → Messages)
   - Query `message` table via `chat_message_join`
   - Extract `Message` structs
   - Call `msg.generate_text()` to get message content

4. **Convert & Store**
   - Convert to our internal `Message` format
   - Store in local SQLite database (`db.rs`)
   - Apply date filtering
   - Export to files

## Current Issues

### ⚠️ **Not Using the Crate's API Properly**

We're bypassing the crate's intended API and using raw SQL:

```rust
// Current: Raw SQL queries
db.prepare("SELECT * FROM handle WHERE id = ?")?;
db.prepare("SELECT * FROM chat WHERE ROWID IN (...)")?;
db.prepare("SELECT * FROM message WHERE ROWID IN (...)")?;
```

### ✅ **What We Should Be Using**

The crate provides a `Table` trait with methods like:
- `Handle::get_by_id()` - but this doesn't exist in v2.4.0
- `Chat::get_by_handle_id()` - also doesn't exist
- `Message::get_by_chat_id()` - also doesn't exist

**The API has changed** - we're working around missing methods by using SQL directly.

## Recommendations

### Option 1: Continue with Raw SQL (Current Approach)
- ✅ Works and is explicit
- ✅ More control over queries
- ❌ Bypasses crate abstractions
- ❌ May break if schema changes

### Option 2: Investigate Actual API
- Check what methods ARE available in v2.4.0
- Use crate's intended patterns
- More maintainable long-term

### Option 3: Use Lower-Level Access
- The crate provides `get_connection()` which gives us a `rusqlite::Connection`
- We're already doing this, which is fine
- Consider wrapping in a helper module

## Current Architecture

```
IMessageDatabaseRepo
├── Connects to iMessage DB via get_connection()
├── Queries handle table (raw SQL)
│   └── Uses Handle::from_row() → Handle::extract()
├── Queries chat table (raw SQL)  
│   └── Uses Chat::from_row() → Chat::extract()
├── Queries message table (raw SQL)
│   └── Uses ImessageMessage::from_row() → ImessageMessage::extract()
├── Calls msg.generate_text(&db) to populate text field
└── Converts to internal Message format
```

## Actual Usage Details

### 1. **Connection**
```rust
use imessage_database::tables::table::get_connection;
let db = get_connection(&self.db_path)?;
```

### 2. **Handle Lookup** (Phone/Email → Handle)
```rust
// Query: SELECT * FROM handle WHERE id = ?1 OR id = ?2
let handle = Handle::from_row(row)?;
let extracted = Handle::extract(Ok(handle))?;
// Fields used: handle.id, handle.rowid
```

### 3. **Chat Lookup** (Handle → Chat)
```rust
// Query: SELECT * FROM chat WHERE ROWID IN 
//        (SELECT chat_id FROM chat_handle_join WHERE handle_id = ?)
let chat = Chat::from_row(row)?;
let extracted = Chat::extract(Ok(chat))?;
// Fields used: chat.rowid
```

### 4. **Message Fetching** (Chat → Messages)
```rust
// Query: SELECT * FROM message WHERE ROWID IN 
//        (SELECT message_id FROM chat_message_join WHERE chat_id = ?)
let msg = ImessageMessage::from_row(row)?;
let mut extracted = ImessageMessage::extract(Ok(msg))?;

// Generate text content (populates msg.text)
extracted.generate_text(&db);

// Fields used:
// - msg.date (i64 nanoseconds timestamp)
// - msg.is_from_me (bool)
// - msg.text (Option<String>)
```

## Key Insight

**We're using `imessage-database` primarily for:**
1. ✅ Database connection (`get_connection()`)
2. ✅ Table structs (`Handle`, `Chat`, `Message`)
3. ✅ Row extraction (`from_row()` → `extract()`)
4. ✅ Text generation (`generate_text()`)
5. ✅ Table trait (for `extract()` method)

**We're NOT using:**
- ❌ High-level query methods (they don't exist in v2.4.0)
- ❌ The crate's intended query patterns
- ❌ Any ORM-like features

**This is essentially a low-level wrapper** around the iMessage database, using the crate mainly for:
- Struct definitions (Handle, Chat, Message)
- Connection management
- Row-to-struct conversion
- Text content generation

The actual querying is done via raw SQL, which gives us full control but bypasses any abstractions the crate might provide.
