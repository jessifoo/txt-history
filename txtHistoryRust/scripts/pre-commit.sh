#!/usr/bin/env bash
# Pre-commit hook for maintaining Google interview-level code quality
# Place in .git/hooks/pre-commit and make executable: chmod +x .git/hooks/pre-commit

set -e

echo "🔍 Running pre-commit checks..."

# Change to project root
cd "$(git rev-parse --show-toplevel)/txtHistoryRust"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track if any check fails
CHECKS_FAILED=0

# === 1. Format Check ===
echo -e "\n📝 Checking code formatting..."
if ! cargo fmt --all -- --check; then
    echo -e "${RED}❌ Code formatting issues found!${NC}"
    echo -e "${YELLOW}Run: cargo fmt --all${NC}"
    CHECKS_FAILED=1
else
    echo -e "${GREEN}✅ Code formatting looks good!${NC}"
fi

# === 2. Clippy Linting ===
echo -e "\n🔧 Running Clippy lints..."
if ! cargo clippy --all-targets --all-features -- -D warnings; then
    echo -e "${RED}❌ Clippy found issues!${NC}"
    echo -e "${YELLOW}Run: cargo clippy --all-targets --all-features --fix${NC}"
    CHECKS_FAILED=1
else
    echo -e "${GREEN}✅ Clippy checks passed!${NC}"
fi

# === 3. Tests ===
echo -e "\n🧪 Running tests..."
if ! cargo test --all-features; then
    echo -e "${RED}❌ Tests failed!${NC}"
    CHECKS_FAILED=1
else
    echo -e "${GREEN}✅ All tests passed!${NC}"
fi

# === 4. Build Check ===
echo -e "\n🏗️  Checking build..."
if ! cargo build --all-features; then
    echo -e "${RED}❌ Build failed!${NC}"
    CHECKS_FAILED=1
else
    echo -e "${GREEN}✅ Build successful!${NC}"
fi

# === 5. Documentation Check ===
echo -e "\n📚 Checking documentation..."
if ! cargo doc --no-deps --all-features --document-private-items; then
    echo -e "${RED}❌ Documentation build failed!${NC}"
    CHECKS_FAILED=1
else
    echo -e "${GREEN}✅ Documentation builds correctly!${NC}"
fi

# === Summary ===
echo -e "\n" "=" "50"
if [ $CHECKS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✨ All pre-commit checks passed!${NC}"
    exit 0
else
    echo -e "${RED}💥 Some checks failed. Please fix the issues above.${NC}"
    exit 1
fi
