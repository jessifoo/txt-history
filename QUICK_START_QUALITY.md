# 🚀 Quick Start - Code Quality Tools

## TL;DR - Get Started in 2 Minutes

```bash
# 1. Format your code
cd txtHistoryRust
cargo fmt --all

# 2. Check for issues
cargo clippy --all-targets --all-features

# 3. Run tests
cargo test

# 4. Install pre-commit hook (optional but recommended)
cp scripts/pre-commit.sh ../.git/hooks/pre-commit
chmod +x ../.git/hooks/pre-commit

# 5. Make code executable and use helper script
chmod +x ../scripts/dev.sh
../scripts/dev.sh pre-commit  # Runs all checks
```

---

## 📋 Development Commands Cheat Sheet

```bash
# Using the dev script (RECOMMENDED)
./scripts/dev.sh <command>

# Essential Commands:
fmt           # Format code
lint          # Check for issues
fix           # Auto-fix issues
test          # Run tests
pre-commit    # Run all checks
ci            # Full CI locally

# Other useful commands:
doc           # Build & view docs
build-release # Production build
audit         # Security scan
clean         # Clean build files
```

---

## ✅ Pre-Commit Checklist

Before committing code:

```bash
./scripts/dev.sh pre-commit
```

This automatically runs:
- ✅ Code formatting
- ✅ Linting (clippy)
- ✅ All tests
- ✅ Build check
- ✅ Documentation check

**Takes ~30 seconds** and ensures your code meets all standards!

---

## 🎯 What's Enforced

### Zero Tolerance:
- ❌ No `unsafe` code
- ❌ No `unwrap()` or `expect()` in production
- ❌ No `panic!()` in production
- ❌ No `dbg!()` macro
- ❌ No clippy warnings

### Strict Limits:
- 📏 Max 100 characters per line
- 🧠 Max cognitive complexity: 12
- 📊 Max function arguments: 4
- 📄 Max lines per function: 80

### Required:
- ✅ Proper error handling
- ✅ Input validation
- ✅ Documentation for public APIs
- ✅ Tests for new features

---

## 🛠️ Fixing Common Issues

### "Unwrap on Result/Option"
```rust
// ❌ DON'T
let value = some_result.unwrap();

// ✅ DO
let value = some_result
    .context("Failed to get value")?;
```

### "Too Many Arguments"
```rust
// ❌ DON'T (5+ arguments)
fn process(a: i32, b: i32, c: String, d: bool, e: f64) {}

// ✅ DO (use a struct)
struct ProcessParams {
    a: i32,
    b: i32,
    c: String,
    d: bool,
    e: f64,
}
fn process(params: ProcessParams) {}
```

### "Cognitive Complexity Too High"
```rust
// ❌ DON'T (nested ifs, loops)
fn complex() {
    if x {
        if y {
            for i in z {
                if a {
                    // ...
                }
            }
        }
    }
}

// ✅ DO (extract functions)
fn complex() {
    if !x { return; }
    if !y { return; }
    process_z();
}

fn process_z() {
    for i in z {
        if a { process_item(i); }
    }
}
```

---

## 🔗 Quick Links

- 📖 [Full Standards](./CODE_QUALITY_STANDARDS.md)
- 🎯 [Implementation Summary](./QUALITY_IMPLEMENTATION_SUMMARY.md)
- 🏃 [Development Script](./scripts/dev.sh)
- 🪝 [Pre-Commit Hook](./txtHistoryRust/scripts/pre-commit.sh)

---

## 🆘 Help

### Script not working?
```bash
# Make sure it's executable
chmod +x scripts/dev.sh

# Run from project root
cd /workspace
./scripts/dev.sh help
```

### Clippy failing?
```bash
# Auto-fix many issues
cargo clippy --all-targets --all-features --fix

# Or use dev script
./scripts/dev.sh fix
```

### Need to skip pre-commit hook?
```bash
# Only if absolutely necessary!
git commit --no-verify -m "message"
```

---

## 🎓 Interview Tip

When discussing code quality in interviews, mention:

1. **"We enforce Google-level standards with automated tools"**
   - Zero clippy warnings
   - Strict complexity limits
   - Pre-commit hooks + CI/CD

2. **"Every PR goes through automated quality gates"**
   - Formatting checks
   - Linting
   - Tests
   - Security audits

3. **"We follow Rust best practices religiously"**
   - No unwrap in production
   - Comprehensive error handling
   - Performance-conscious design

This demonstrates professionalism and attention to detail!

---

**Ready to code with confidence!** 🚀

All checks are automated - just run `./scripts/dev.sh pre-commit` before committing!
