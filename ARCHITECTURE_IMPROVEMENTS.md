# Architecture Improvements for txt-history

## Overview

This document outlines the improved architecture for the txt-history project, addressing the key concerns about file management, database usage, and code maintainability.

## Key Problems Solved

### 1. **No More File Recreation**
- **Problem**: Original script recreates all files every time it runs
- **Solution**: Database-backed persistent storage with intelligent caching
- **Benefit**: Only fetch new data when needed, reuse existing exports

### 2. **Reduced File Clutter**
- **Problem**: Multiple chunk files for different people/dates create clutter
- **Solution**: Configurable chunking strategies and smart file naming
- **Benefit**: Generate only the files you need, when you need them

### 3. **Better Code Organization**
- **Problem**: Original code is tightly coupled and hard to maintain
- **Solution**: Layered architecture with clear separation of concerns
- **Benefit**: Easier to test, extend, and maintain

## Architecture Layers

```
┌─────────────────────────────────────┐
│           CLI Layer                 │
│  - Argument parsing                 │
│  - User interaction                 │
│  - Configuration management         │
├─────────────────────────────────────┤
│         Service Layer               │
│  - ExportManager                    │
│  - MessageProcessor                 │
│  - Business logic orchestration     │
├─────────────────────────────────────┤
│         Repository Layer            │
│  - DatabaseManager                  │
│  - ContactManager                   │
│  - Data access abstraction          │
├─────────────────────────────────────┤
│         Database Layer              │
│  - SQLite storage                   │
│  - Message persistence              │
│  - Contact management               │
└─────────────────────────────────────┘
```

## Core Components

### 1. **DatabaseManager**
- **Purpose**: Manages SQLite database for persistent storage
- **Features**:
  - Message storage and retrieval
  - Contact information management
  - Export session tracking
  - Intelligent caching (24-hour threshold)

### 2. **ContactManager**
- **Purpose**: Handles contact information
- **Features**:
  - Contact lookup and storage
  - Phone/email validation
  - Integration with existing contact store

### 3. **MessageProcessor**
- **Purpose**: Handles message processing and chunking
- **Features**:
  - Multiple chunking strategies (size, lines, count, date range)
  - Configurable chunking parameters
  - Efficient message sorting

### 4. **ExportManager**
- **Purpose**: Orchestrates the export process
- **Features**:
  - Intelligent data fetching (cache vs. fresh)
  - Multiple output formats (CSV, TXT, both)
  - Configurable file naming

## Chunking Strategies

### 1. **Size-based Chunking** (`-s 0.1`)
- Splits messages by approximate file size in MB
- Useful for managing file sizes for different systems

### 2. **Line-based Chunking** (`-l 1000`)
- Splits messages by line count
- Good for readability and processing limits

### 3. **Count-based Chunking** (`-c 500`)
- Splits messages by message count
- Useful for batch processing

### 4. **Date-range Chunking** (`--date-range 7`)
- Splits messages by date ranges (e.g., weekly chunks)
- Good for time-based analysis

## Database Schema

### Messages Table
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sender TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    content TEXT NOT NULL,
    contact_name TEXT NOT NULL,
    source_file TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Contacts Table
```sql
CREATE TABLE contacts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    phone TEXT,
    email TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Export Sessions Table
```sql
CREATE TABLE export_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    contact_names TEXT NOT NULL,
    start_date TEXT,
    end_date TEXT,
    chunk_strategy TEXT,
    chunk_value REAL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## Usage Examples

### Basic Usage
```bash
# Export messages for a single contact
poetry run format_new -n "Phil" -s 0.1

# Export messages for multiple contacts
poetry run format_new -n "Phil" "Alice" "Bob" -s 0.1

# Export with date range
poetry run format_new -n "Phil" -d "2024-01-01" -e "2024-01-31" -s 0.1

# Export with different chunking strategies
poetry run format_new -n "Phil" -l 1000          # Line-based
poetry run format_new -n "Phil" -c 500           # Count-based
poetry run format_new -n "Phil" --date-range 7   # Date-based
```

### Advanced Usage
```bash
# Export only contact messages (exclude your replies)
poetry run format_new -n "Phil" -o -s 0.1

# Export in specific format only
poetry run format_new -n "Phil" --format csv -s 0.1
poetry run format_new -n "Phil" --format txt -s 0.1
```

## Benefits

### 1. **Performance**
- Cached data retrieval (24-hour threshold)
- Only fetch new data when needed
- Efficient database queries with indexes

### 2. **Flexibility**
- Multiple chunking strategies
- Configurable output formats
- Support for multiple contacts

### 3. **Maintainability**
- Clear separation of concerns
- Testable components
- Extensible architecture

### 4. **Storage Efficiency**
- No duplicate file generation
- Intelligent file naming
- Configurable chunking to reduce clutter

## Migration Path

### Phase 1: New Architecture (Current)
- Implement new `format_new.py` with database backend
- Maintain compatibility with existing `format_txts.py`
- Test with existing workflows

### Phase 2: Integration
- Migrate existing contacts to new database
- Import existing message data if needed
- Update documentation and examples

### Phase 3: Deprecation
- Deprecate old `format_txts.py` after validation
- Remove old file-based contact storage
- Clean up legacy code

## Future Enhancements

### 1. **Rust Backend Integration**
- Use Rust for high-performance message processing
- Implement immutable data store
- Provide Python bindings for existing functionality

### 2. **Advanced Analytics**
- Message sentiment analysis
- Conversation flow analysis
- Contact interaction patterns

### 3. **Cloud Integration**
- Cloud storage for message archives
- Multi-device synchronization
- Collaborative features

### 4. **API Development**
- REST API for programmatic access
- Web interface for data exploration
- Integration with other tools

## Testing Strategy

### Unit Tests
- Test each component in isolation
- Mock external dependencies
- Validate data transformations

### Integration Tests
- Test component interactions
- Validate database operations
- Test end-to-end workflows

### Performance Tests
- Measure database query performance
- Test chunking efficiency
- Validate memory usage

## Conclusion

The new architecture addresses the core concerns about file management and code maintainability while providing a solid foundation for future enhancements. The database-backed approach eliminates unnecessary file recreation, while the layered architecture makes the code more maintainable and testable.

The configurable chunking strategies and intelligent caching provide flexibility for different use cases, while the clear separation of concerns makes it easier to extend and modify the functionality as needed.
