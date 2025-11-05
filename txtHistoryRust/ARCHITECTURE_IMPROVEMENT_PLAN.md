# Architecture & Code Quality Improvement Plan

## Overview

This document outlines the plan to improve the architecture and code quality of the Rust project to make it more idiomatic and maintainable.

## Current State Assessment

**Score: 7.5/10** - Good foundation but needs architectural improvements

### Critical Architectural Issues

1. ✅ **Unused Module** - `service.rs` removed
2. ⚠️ **Repository Pattern Duplication** - Two overlapping implementations need clarification
3. ⚠️ **Inconsistent Error Handling** - Mix of `anyhow::Result` without custom error types
4. ⚠️ **Async/Sync Mismatch** - Async functions doing synchronous file I/O
5. ⚠️ **Missing Documentation** - No module-level docs, minimal function docs
6. ⚠️ **Code Duplication** - File writing logic duplicated

## Improvement Plan

### Phase 1: Clean Up Architecture ✅ IN PROGRESS
- [x] Remove unused `service.rs` module
- [ ] Consolidate repository pattern - create clear separation of concerns
- [ ] Extract common file writing logic to shared module
- [ ] Remove code duplication in chunking logic

### Phase 2: Improve Error Handling ✅ STARTED
- [x] Create custom error types using `thiserror`
- [ ] Replace generic `anyhow::Result` with specific error types gradually
- [ ] Add proper error context throughout
- [ ] Ensure error messages are helpful and actionable

### Phase 3: Fix Async/Sync Patterns
- [ ] Make file I/O consistently async using `tokio::fs`
- [ ] OR make repository methods consistently synchronous (if preferred)
- [ ] Remove unnecessary async where not needed
- [ ] Properly handle blocking operations with `spawn_blocking`

### Phase 4: Add Documentation
- [ ] Add module-level documentation (`//!`)
- [ ] Document all public APIs
- [ ] Add examples where helpful
- [ ] Document architectural decisions

### Phase 5: Code Organization
- [ ] Extract common functionality (file writing, chunking)
- [ ] Use constants for magic strings/numbers
- [ ] Improve naming consistency
- [ ] Add proper module organization

## Implementation Strategy

**Current Focus:** Phase 1 & 2 (Clean up + Error handling)

**Next Steps:**
1. ✅ Created error module with custom error types
2. Start migrating to custom error types
3. Extract common file writing functionality
4. Clarify repository pattern responsibilities

## Principles

- **Idiomatic Rust**: Follow Rust best practices and conventions
- **Explicit over Implicit**: Clear error types, clear function signatures
- **DRY**: Don't Repeat Yourself - extract common functionality
- **Separation of Concerns**: Clear boundaries between modules
- **Documentation**: Public APIs should be well-documented
