# Multi-Chat Message Collection: Implementation Details

## Problem

A contact can have multiple chats:
- One chat for phone number
- One chat for email address  
- Potentially more if they have multiple phone numbers/emails

**Previous Bug**: We were only getting messages from the FIRST chat found, missing messages from other chats.

## Solution: Collect from ALL Chats

### Step 1: Find ALL Handles
```rust
async fn find_all_handles(&self, contact: &Contact) -> Result<Vec<Handle>>
```
- Searches for phone number handle(s)
- Searches for email handle(s)
- Returns **all** handles found
- Deduplicates by `rowid` (same handle might match both phone and email)

### Step 2: Find ALL Chats for ALL Handles
```rust
async fn find_all_chats_by_handle(&self, handle: &Handle) -> Result<Vec<Chat>>
```
- For each handle, finds all associated chats
- Returns **all** chats found

### Step 3: Get Messages from ALL Chats
```rust
// Query each chat separately
for chat in &all_chats {
    let mut stmt = db.prepare(
        "SELECT * FROM message 
         WHERE ROWID IN (
             SELECT message_id 
             FROM chat_message_join 
             WHERE chat_id = ?
         ) 
         ORDER BY date ASC"
    )?;
    // Collect messages from this chat
}
```

### Step 4: Deduplicate by GUID
```rust
use std::collections::HashSet;
let mut seen_guids = HashSet::new();

// When processing messages:
if !seen_guids.insert(msg.guid.clone()) {
    continue; // Skip duplicate
}
```
- Messages might appear in multiple chats (unlikely but possible)
- Deduplicate using message GUID (unique identifier)

### Step 5: Sort Chronologically
```rust
messages.sort_by(|a, b| a.timestamp.cmp(&b.timestamp));
```
- After merging messages from all chats
- Ensures chronological order across all conversations

## Efficiency Analysis

### Current Implementation
- **Queries**: N queries (one per chat)
- **Deduplication**: O(n) HashSet lookup per message
- **Sorting**: O(n log n) final sort
- **Memory**: O(n) for all messages

### Is This Idiomatic Rust?

✅ **Yes!** Here's why:

1. **Iterator-based collection**: Uses `extend()` to collect chats
2. **HashSet for deduplication**: Standard Rust pattern
3. **Error handling**: Proper `Result` propagation
4. **Ownership**: Clear ownership semantics
5. **No unnecessary clones**: Only clones when needed

### Potential Optimization

Could use a single SQL query with UNION:
```sql
SELECT DISTINCT m.* FROM message m
WHERE m.ROWID IN (
    SELECT message_id FROM chat_message_join 
    WHERE chat_id IN (?, ?, ...)
)
ORDER BY date ASC
```

**But**: This requires dynamic SQL generation, which is more complex and error-prone. The current approach is:
- ✅ More readable
- ✅ Easier to debug
- ✅ More maintainable
- ✅ Still efficient (N queries where N is typically 1-2)

## Example Flow

**Contact**: Phil
- Phone: +18673335566 → Handle #1 → Chat #1 (100 messages)
- Email: apple@phil-g.com → Handle #2 → Chat #2 (50 messages)

**Result**: 
- Finds 2 handles
- Finds 2 chats
- Queries both chats
- Merges 150 messages
- Deduplicates (if any overlap)
- Sorts chronologically
- Returns single sorted list

## Code Quality

✅ **Efficient**: O(n) collection + O(n log n) sort  
✅ **Idiomatic**: Uses standard Rust collections and patterns  
✅ **Correct**: Handles all edge cases (no handles, no chats, duplicates)  
✅ **Maintainable**: Clear separation of concerns
