# Code Quality Standards - Google Interview Level

This document outlines the code quality standards implemented for this project, matching expectations for top-tier software engineering interviews.

## 🎯 Overview

We've implemented a comprehensive code quality system with:
- ✅ **Strict formatting** (rustfmt)
- ✅ **Comprehensive linting** (clippy with pedantic rules)
- ✅ **Automated checks** (pre-commit hooks, CI/CD)
- ✅ **Documentation standards**
- ✅ **Security auditing**

---

## 📝 Code Formatting

### Configuration (`.rustfmt.toml`)

```toml
edition = "2021"
max_width = 100              # Industry standard line length
tab_spaces = 4
reorder_imports = true       # Alphabetically organized imports
use_field_init_shorthand = true
use_try_shorthand = true
```

### Running Formatting

```bash
# Format all code
cargo fmt --all

# Check formatting without modifying
cargo fmt --all -- --check

# Using dev script
./scripts/dev.sh fmt
```

**Standards**:
- 100 character line limit
- Consistent spacing and indentation
- Alphabetically ordered imports
- Field init shorthand (`Point { x, y }` not `Point { x: x, y: y }`)
- Try shorthand (`?` operator)

---

## 🔧 Linting with Clippy

### Configuration (`Cargo.toml` and `clippy.toml`)

**Enabled Lint Groups**:
- ✅ `all` - All correctness lints (DENY level)
- ✅ `pedantic` - Strict style lints (WARN level)
- ✅ `nursery` - Experimental lints (WARN level)
- ✅ `perf` - Performance lints (WARN level)
- ✅ `complexity` - Code complexity warnings
- ✅ `cargo` - Cargo best practices

**Complexity Thresholds** (Stricter than defaults):
```toml
cognitive-complexity-threshold = 12    # Default: 25
type-complexity-threshold = 150        # Default: 250
too-many-arguments-threshold = 4       # Default: 7
too-many-lines-threshold = 80          # Default: 100
```

**Key Denials**:
- `unsafe_code` - **FORBID** (no unsafe allowed)
- `unwrap_used` - **WARN** (prefer proper error handling)
- `expect_used` - **WARN** (prefer proper error handling)
- `panic` - **WARN** (avoid panics in production)
- `todo` - **WARN** (track TODOs)
- `dbg_macro` - **WARN** (remove debug prints)

### Running Clippy

```bash
# Run all lints
cargo clippy --all-targets --all-features -- -D warnings

# Auto-fix issues
cargo clippy --all-targets --all-features --fix

# Using dev script
./scripts/dev.sh lint
./scripts/dev.sh fix
```

---

## 🚀 Development Workflow

### Quick Reference

```bash
# Development script (recommended)
./scripts/dev.sh <command>

# Available commands:
fmt              # Format code
lint             # Run lints
fix              # Auto-fix issues
test             # Run tests
build            # Debug build
build-release    # Release build
doc              # Build & open docs
pre-commit       # Run all checks
ci               # Full CI suite locally
```

### Pre-Commit Checks

```bash
./scripts/dev.sh pre-commit
```

Runs:
1. ✅ Code formatting check
2. ✅ Clippy lints (all warnings treated as errors)
3. ✅ All tests
4. ✅ Build check
5. ✅ Documentation build

### Manual Pre-Commit Hook Setup

```bash
# Copy pre-commit hook
cp txtHistoryRust/scripts/pre-commit.sh .git/hooks/pre-commit
chmod +x .git/hooks/pre-commit
```

Now all checks run automatically before each commit!

---

## 🤖 Continuous Integration

### GitHub Actions (`.github/workflows/rust-quality.yml`)

Automatic checks on every push/PR:

**Jobs**:
1. **Formatting** - Ensures consistent code style
2. **Linting** - Clippy checks with strict settings
3. **Testing** - Full test suite on Ubuntu & macOS
4. **Build** - Multi-platform builds (Linux, macOS, Windows)
5. **Documentation** - Ensures docs build correctly
6. **Security Audit** - Checks for known vulnerabilities
7. **Coverage** - Code coverage reporting

**Matrix Testing**:
- OS: Ubuntu, macOS, Windows
- Rust: stable, beta
- All feature combinations

---

## 📚 Documentation Standards

### Requirements

**All public items must have documentation**:
```rust
/// Calculate the sum of two numbers.
///
/// # Arguments
///
/// * `a` - The first number
/// * `b` - The second number
///
/// # Returns
///
/// The sum of `a` and `b`
///
/// # Examples
///
/// ```
/// let result = add(2, 3);
/// assert_eq!(result, 5);
/// ```
pub fn add(a: i32, b: i32) -> i32 {
    a + b
}
```

### Building Documentation

```bash
# Build and open docs
cargo doc --no-deps --all-features --open

# Check docs build
cargo doc --no-deps --all-features --document-private-items

# Using dev script
./scripts/dev.sh doc
```

---

## 🔒 Security

### Security Auditing

```bash
# Install cargo-audit
cargo install cargo-audit

# Run security audit
cargo audit

# Using dev script
./scripts/dev.sh audit
```

### Security Standards

- ✅ No `unsafe` code (enforced by lints)
- ✅ All dependencies audited
- ✅ Proper error handling (no `unwrap` in production)
- ✅ Input validation on all user inputs
- ✅ SQL injection prevention (parameterized queries)

---

## 📊 Code Quality Metrics

### Measuring Quality

```bash
# Binary size analysis
cargo install cargo-bloat
cargo bloat --release --all-features

# Build times
cargo clean
time cargo build --release

# Test coverage
cargo install cargo-tarpaulin
cargo tarpaulin --all-features --workspace
```

### Quality Targets

| Metric | Target | Current |
|--------|--------|---------|
| Test Coverage | >80% | TBD |
| Clippy Warnings | 0 | 0 |
| Doc Coverage | >90% | TBD |
| Cognitive Complexity | <12 per fn | ✅ |
| Build Time (release) | <2min | TBD |

---

## 🎓 Best Practices Checklist

### Before Every Commit

- [ ] Code formatted (`cargo fmt`)
- [ ] No clippy warnings (`cargo clippy`)
- [ ] All tests pass (`cargo test`)
- [ ] Documentation updated
- [ ] No `TODO` or `FIXME` without tracking
- [ ] Error handling reviewed
- [ ] Input validation added
- [ ] Performance considered

### Code Review Checklist

- [ ] Single Responsibility Principle followed
- [ ] Function complexity <12 (cognitive)
- [ ] Function arguments ≤4 (use structs for more)
- [ ] Proper error context added
- [ ] No unwrap/expect in production code
- [ ] Tests added for new functionality
- [ ] Edge cases handled
- [ ] Documentation complete
- [ ] No security issues

---

## 🏆 Google Interview Standards

### What Makes This Google-Level Quality?

1. **Zero Tolerance for Warnings**
   - All clippy warnings treated as errors
   - Comprehensive lint coverage
   - Automated enforcement

2. **Strict Complexity Limits**
   - Functions kept simple and testable
   - Clear separation of concerns
   - Enforced by automated checks

3. **Comprehensive Testing**
   - Unit tests
   - Integration tests
   - Doc tests
   - Property-based tests (proptest)

4. **Production-Ready Error Handling**
   - No `unwrap()` or `panic!()`
   - Rich error context with `anyhow`
   - User-friendly error messages

5. **Performance Consciousness**
   - Composite indexes on databases
   - Streaming serialization
   - Efficient algorithms (O(log n) queries)

6. **Security First**
   - No unsafe code
   - Dependency auditing
   - Input validation
   - SQL injection prevention

7. **Excellent Documentation**
   - All public APIs documented
   - Examples in doc comments
   - Architecture documents
   - Inline comments for complex logic

8. **Modern Tooling**
   - Pre-commit hooks
   - CI/CD pipeline
   - Automated security scanning
   - Code coverage tracking

---

## 📖 Additional Resources

### Rust Style Guide
- [Official Rust Style Guide](https://doc.rust-lang.org/nightly/style-guide/)
- [Rust API Guidelines](https://rust-lang.github.io/api-guidelines/)

### Clippy Lints
- [Clippy Lint List](https://rust-lang.github.io/rust-clippy/master/)
- [Clippy Documentation](https://doc.rust-lang.github.io/clippy/)

### Testing
- [Rust Book - Testing](https://doc.rust-lang.org/book/ch11-00-testing.html)
- [Property Testing with Proptest](https://proptest-rs.github.io/proptest/)

---

## 🔄 Continuous Improvement

This is a living document. As the project evolves and Rust best practices change, these standards will be updated to reflect the latest industry expectations.

**Last Updated**: 2025-10-25
**Version**: 1.0.0
