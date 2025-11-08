# Code Review: Logic Issues and Cut Corners

## Issues Found

### 1. **Duplicate Date Conversion (Inefficiency)**
**Location**: `src/repository.rs:318-320, 328-330, 346-348`

**Problem**: The same date (`msg.date`) is converted from nanoseconds to DateTime three times:
- Once for start date filtering
- Once for end date filtering  
- Once for creating the Message struct

**Impact**: Unnecessary computation, potential for inconsistency if conversion logic differs

**Fix**: Convert once and reuse

### 2. **Missing Sorting After Filtering**
**Location**: `src/repository.rs:387`

**Problem**: `IMessageDatabaseRepo::fetch_messages` filters messages but doesn't sort them after filtering. While SQL orders them initially, after filtering by date range and `only_contact`, the order should be guaranteed.

**Impact**: Messages might not be in chronological order after filtering

**Fix**: Sort messages before returning

### 3. **Chicken-and-Egg Problem: Contacts Must Exist**
**Location**: `src/repository.rs:299-302`

**Problem**: `fetch_messages` requires contacts ("Jess" and the contact) to already exist in the local database, but we're fetching from iMessage. If contacts don't exist, the operation fails.

**Impact**: First-time imports will fail if contacts aren't pre-initialized

**Fix**: Auto-create contacts if they don't exist

### 4. **Inconsistent Empty Message Handling**
**Location**: `src/repository.rs:415` vs `src/repository.rs:84`

**Problem**: 
- `IMessageDatabaseRepo::export_conversation_by_person` returns an error for empty messages
- `Repository::export_conversation_by_person` returns empty Vec

**Impact**: Inconsistent API behavior

**Fix**: Make both return empty Vec (more consistent with "no results" pattern)

### 5. **Hardcoded "Jess" Name**
**Location**: Multiple locations

**Problem**: "Jess" is hardcoded throughout the codebase. Should be configurable or derived from system.

**Impact**: Not portable, requires code changes for different users

**Fix**: Make configurable (can be addressed later, but noted)

### 6. **Missing Date Range Validation**
**Location**: `src/main.rs:parse_date_range`

**Problem**: No validation that start_date < end_date

**Impact**: Invalid date ranges could cause confusion

**Fix**: Add validation
