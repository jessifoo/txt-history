#!/usr/bin/env bash
# Makefile-style script for common development tasks
# Google interview-level quality checks

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

PROJECT_DIR="txtHistoryRust"

# Change to project directory
cd "$(dirname "$0")/../$PROJECT_DIR" || exit 1

show_help() {
    echo -e "${BLUE}Txt History Rust - Development Commands${NC}"
    echo ""
    echo "Usage: ./scripts/dev.sh <command>"
    echo ""
    echo "Commands:"
    echo "  fmt           - Format code with rustfmt"
    echo "  lint          - Run clippy lints"
    echo "  fix           - Auto-fix clippy issues"
    echo "  test          - Run all tests"
    echo "  test-unit     - Run unit tests only"
    echo "  test-integration - Run integration tests only"
    echo "  bench         - Run benchmarks"
    echo "  doc           - Build and open documentation"
    echo "  doc-check     - Check documentation builds"
    echo "  build         - Build in debug mode"
    echo "  build-release - Build in release mode"
    echo "  check         - Fast compilation check"
    echo "  clean         - Clean build artifacts"
    echo "  audit         - Security audit"
    echo "  bloat         - Analyze binary size"
    echo "  pre-commit    - Run all pre-commit checks"
    echo "  ci            - Run full CI suite locally"
    echo ""
}

fmt() {
    echo -e "${BLUE}📝 Formatting code...${NC}"
    cargo fmt --all
    echo -e "${GREEN}✅ Done!${NC}"
}

lint() {
    echo -e "${BLUE}🔧 Running Clippy...${NC}"
    cargo clippy --all-targets --all-features -- -D warnings
    echo -e "${GREEN}✅ Done!${NC}"
}

fix() {
    echo -e "${BLUE}🔧 Auto-fixing Clippy issues...${NC}"
    cargo clippy --all-targets --all-features --fix --allow-dirty
    echo -e "${GREEN}✅ Done!${NC}"
}

test() {
    echo -e "${BLUE}🧪 Running all tests...${NC}"
    cargo test --all-features --verbose
    echo -e "${GREEN}✅ Done!${NC}"
}

test_unit() {
    echo -e "${BLUE}🧪 Running unit tests...${NC}"
    cargo test --lib --all-features
    echo -e "${GREEN}✅ Done!${NC}"
}

test_integration() {
    echo -e "${BLUE}🧪 Running integration tests...${NC}"
    cargo test --test '*' --all-features
    echo -e "${GREEN}✅ Done!${NC}"
}

bench() {
    echo -e "${BLUE}⚡ Running benchmarks...${NC}"
    cargo bench --all-features
    echo -e "${GREEN}✅ Done!${NC}"
}

doc() {
    echo -e "${BLUE}📚 Building and opening documentation...${NC}"
    cargo doc --no-deps --all-features --open
}

doc_check() {
    echo -e "${BLUE}📚 Checking documentation...${NC}"
    cargo doc --no-deps --all-features --document-private-items
    echo -e "${GREEN}✅ Done!${NC}"
}

build() {
    echo -e "${BLUE}🏗️  Building (debug)...${NC}"
    cargo build --all-features
    echo -e "${GREEN}✅ Done!${NC}"
}

build_release() {
    echo -e "${BLUE}🏗️  Building (release)...${NC}"
    cargo build --all-features --release
    echo -e "${GREEN}✅ Done!${NC}"
}

check() {
    echo -e "${BLUE}⚡ Fast compilation check...${NC}"
    cargo check --all-targets --all-features
    echo -e "${GREEN}✅ Done!${NC}"
}

clean() {
    echo -e "${BLUE}🧹 Cleaning build artifacts...${NC}"
    cargo clean
    echo -e "${GREEN}✅ Done!${NC}"
}

audit() {
    echo -e "${BLUE}🔒 Running security audit...${NC}"
    if ! command -v cargo-audit &> /dev/null; then
        echo -e "${YELLOW}Installing cargo-audit...${NC}"
        cargo install cargo-audit
    fi
    cargo audit
    echo -e "${GREEN}✅ Done!${NC}"
}

bloat() {
    echo -e "${BLUE}📊 Analyzing binary size...${NC}"
    if ! command -v cargo-bloat &> /dev/null; then
        echo -e "${YELLOW}Installing cargo-bloat...${NC}"
        cargo install cargo-bloat
    fi
    cargo bloat --release --all-features
}

pre_commit() {
    echo -e "${BLUE}🚀 Running pre-commit checks...${NC}"
    
    echo -e "\n${YELLOW}[1/5] Formatting...${NC}"
    fmt
    
    echo -e "\n${YELLOW}[2/5] Linting...${NC}"
    lint
    
    echo -e "\n${YELLOW}[3/5] Testing...${NC}"
    test
    
    echo -e "\n${YELLOW}[4/5] Building...${NC}"
    build
    
    echo -e "\n${YELLOW}[5/5] Documentation...${NC}"
    doc_check
    
    echo -e "\n${GREEN}✨ All pre-commit checks passed!${NC}"
}

ci() {
    echo -e "${BLUE}🤖 Running full CI suite locally...${NC}"
    
    pre_commit
    
    echo -e "\n${YELLOW}Running security audit...${NC}"
    audit
    
    echo -e "\n${YELLOW}Building release...${NC}"
    build_release
    
    echo -e "\n${GREEN}✅ Full CI suite completed successfully!${NC}"
}

# Main command dispatcher
case "${1:-help}" in
    fmt) fmt ;;
    lint) lint ;;
    fix) fix ;;
    test) test ;;
    test-unit) test_unit ;;
    test-integration) test_integration ;;
    bench) bench ;;
    doc) doc ;;
    doc-check) doc_check ;;
    build) build ;;
    build-release) build_release ;;
    check) check ;;
    clean) clean ;;
    audit) audit ;;
    bloat) bloat ;;
    pre-commit) pre_commit ;;
    ci) ci ;;
    help|--help|-h) show_help ;;
    *)
        echo -e "${RED}❌ Unknown command: $1${NC}"
        echo ""
        show_help
        exit 1
        ;;
esac
