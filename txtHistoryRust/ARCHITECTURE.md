# txt-history-rust Architecture

## Project Overview

`txt-history-rust` is a Rust implementation of a message history processor for iMessage data. It extracts messages from the macOS iMessage database, processes them, and outputs them in both TXT and CSV formats with specific formatting.

## Core Components

### 1. Data Access Layer

- **imessage_database**: Uses the `imessage_database` crate to access the macOS iMessage database
- **db.rs**: Manages the local SQLite database for storing processed messages
- **repository.rs**: Provides a repository pattern for data access operations

### 2. Domain Model

- **models.rs**: Defines the core data structures and types
- **schema.rs**: Defines the database schema

### 3. Business Logic

- **service.rs**: Contains the core business logic for processing messages
- **nlp.rs**: Natural language processing utilities for message analysis
- **cache.rs**: Caching mechanisms for performance optimization

### 4. User Interface

- **main.rs**: Command-line interface and application entry point
- **bin/test_nlp.rs**: Testing utility for NLP functionality

## Data Flow

1. User provides input parameters (contact name, date range, output options)
2. Application connects to the iMessage database
3. Messages are extracted and filtered based on user criteria
4. Messages are processed and normalized
5. Output is generated in TXT and CSV formats, chunked as specified

## Configuration

- **.cargo/config.toml**: Rust compiler and Clippy configuration
- **.rustfmt.toml**: Code formatting rules
- **clippy.toml**: Linter configuration

## Key Features

1. **Message Extraction**: Extract messages from the macOS iMessage database
2. **Contact Normalization**: Map phone numbers and email addresses to contact names
3. **Message Formatting**: Format messages consistently
4. **Output Generation**: Generate TXT and CSV output with specific formatting
5. **Chunking**: Split output into chunks based on size or line count

## Implementation Notes

- The application uses a repository pattern to abstract data access
- Error handling is done with `anyhow` for propagation and `thiserror` for definition
- The CLI is implemented using `clap` with derive macros
- Date handling uses the `chrono` crate
