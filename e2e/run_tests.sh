#!/bin/bash
# ==============================================================================
# LightRAG E2E Test Runner - Enhanced Version
# ==============================================================================
# An interactive test runner for LightRAG end-to-end tests with support for
# multiple backends, test selection, and improved user experience.
#
# Features:
#   - Interactive mode with menu-driven selection
#   - Multiple backend support (file, postgres, all)
#   - Individual test case selection
#   - Verbose and quiet modes
#   - Colored output with emojis
#   - Comprehensive help system
#
# Author: LightRAG Team
# ==============================================================================

set -e

# ==============================================================================
# Constants & Colors
# ==============================================================================
readonly VERSION="2.1.0"
readonly SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
readonly PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
readonly DEFAULT_PORT=9621
readonly SERVER_TIMEOUT=30
readonly LOG_FILE="${PROJECT_ROOT}/server.log"

# OpenAI Defaults (used with --openai flag)
readonly OPENAI_LLM_MODEL="gpt-4o-mini"
readonly OPENAI_EMBEDDING_MODEL="text-embedding-3-small"
readonly OPENAI_EMBEDDING_DIM="1536"

# Colors
readonly RED='\033[0;31m'
readonly GREEN='\033[0;32m'
readonly YELLOW='\033[0;33m'
readonly BLUE='\033[0;34m'
readonly MAGENTA='\033[0;35m'
readonly CYAN='\033[0;36m'
readonly WHITE='\033[1;37m'
readonly BOLD='\033[1m'
readonly DIM='\033[2m'
readonly NC='\033[0m' # No Color

# ==============================================================================
# Available Tests (bash 3.2 compatible - using parallel arrays)
# ==============================================================================
TEST_KEYS=("isolation" "deletion" "mixed")
TEST_FILES=("test_multitenant_isolation.py" "test_deletion.py" "test_mixed_operations.py")
TEST_NAMES=("Multi-Tenant Isolation" "Document Deletion" "Mixed Operations")
TEST_DESCS=("Tests data isolation between tenants" "Tests document deletion and cleanup" "Tests interleaved tenant operations")

# Available Backends
BACKEND_KEYS=("file" "postgres")
BACKEND_NAMES=("File-based Storage" "PostgreSQL Storage")
BACKEND_DESCS=("Uses JSON, NetworkX, and NanoVectorDB for local storage" "Uses PostgreSQL with pgvector for production storage")

# ==============================================================================
# Default Configuration
# ==============================================================================
BACKEND="file"
LLM_MODEL="gpt-oss:20b"
LLM_BINDING="ollama"
EMBEDDING_MODEL="bge-m3:latest"
EMBEDDING_BINDING="ollama"
EMBEDDING_DIM="1024"
SERVER_PORT="$DEFAULT_PORT"
VERBOSE=false
QUIET=false
INTERACTIVE=false
DRY_RUN=false
SKIP_SERVER=false
KEEP_SERVER=false
SELECTED_TESTS=""
USE_OPENAI=false
RESET_DB=false

# ==============================================================================
# Helper Functions
# ==============================================================================

print_banner() {
    echo -e "${CYAN}"
    echo "╔══════════════════════════════════════════════════════════════════════╗"
    echo "║                                                                      ║"
    echo "║     ██╗     ██╗ ██████╗ ██╗  ██╗████████╗██████╗  █████╗  ██████╗    ║"
    echo "║     ██║     ██║██╔════╝ ██║  ██║╚══██╔══╝██╔══██╗██╔══██╗██╔════╝    ║"
    echo "║     ██║     ██║██║  ███╗███████║   ██║   ██████╔╝███████║██║  ███╗   ║"
    echo "║     ██║     ██║██║   ██║██╔══██║   ██║   ██╔══██╗██╔══██║██║   ██║   ║"
    echo "║     ███████╗██║╚██████╔╝██║  ██║   ██║   ██║  ██║██║  ██║╚██████╔╝   ║"
    echo "║     ╚══════╝╚═╝ ╚═════╝ ╚═╝  ╚═╝   ╚═╝   ╚═╝  ╚═╝╚═╝  ╚═╝ ╚═════╝    ║"
    echo "║                                                                      ║"
    echo "║                    E2E Test Runner v${VERSION}                          ║"
    echo "║                                                                      ║"
    echo "╚══════════════════════════════════════════════════════════════════════╝"
    echo -e "${NC}"
}

log_info() {
    if [[ "$QUIET" != "true" ]]; then
        echo -e "${BLUE}ℹ️  ${NC}$1"
    fi
}

log_success() {
    echo -e "${GREEN}✅ ${NC}$1"
}

log_warning() {
    echo -e "${YELLOW}⚠️  ${NC}$1"
}

log_error() {
    echo -e "${RED}❌ ${NC}$1"
}

log_step() {
    echo -e "\n${BOLD}${MAGENTA}▶ $1${NC}"
}

log_debug() {
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${DIM}[DEBUG] $1${NC}"
    fi
}

print_separator() {
    echo -e "${DIM}────────────────────────────────────────────────────────────────────────${NC}"
}

# Get test info by key
get_test_index() {
    local key=$1
    for i in "${!TEST_KEYS[@]}"; do
        if [[ "${TEST_KEYS[$i]}" == "$key" ]]; then
            echo "$i"
            return 0
        fi
    done
    echo "-1"
    return 1
}

# Check if test exists
test_exists() {
    local key=$1
    for k in "${TEST_KEYS[@]}"; do
        if [[ "$k" == "$key" ]]; then
            return 0
        fi
    done
    return 1
}

# ==============================================================================
# Help & Usage
# ==============================================================================

show_help() {
    print_banner
    
    echo -e "${BOLD}USAGE${NC}"
    echo "    $0 [OPTIONS] [TESTS...]"
    echo ""
    
    echo -e "${BOLD}DESCRIPTION${NC}"
    echo "    Run end-to-end tests for LightRAG multi-tenant functionality."
    echo "    Supports multiple storage backends and individual test selection."
    echo ""
    
    echo -e "${BOLD}OPTIONS${NC}"
    echo -e "    ${GREEN}-b, --backend${NC} <type>"
    echo "        Storage backend to test. Options: file, postgres, all"
    echo "        Default: file"
    echo ""
    echo -e "    ${GREEN}-t, --tests${NC} <tests>"
    echo "        Comma-separated list of tests to run."
    echo "        Options: isolation, deletion, mixed, all"
    echo "        Default: all"
    echo ""
    echo -e "    ${GREEN}-m, --llm-model${NC} <model>"
    echo "        LLM model to use (for Ollama). Default: gpt-oss:20b"
    echo ""
    echo -e "    ${GREEN}--llm-binding${NC} <binding>"
    echo "        LLM binding type. Default: ollama"
    echo ""
    echo -e "    ${GREEN}-e, --embedding-model${NC} <model>"
    echo "        Embedding model to use. Default: bge-m3:latest"
    echo ""
    echo -e "    ${GREEN}--embedding-binding${NC} <binding>"
    echo "        Embedding binding type. Default: ollama"
    echo ""
    echo -e "    ${GREEN}-d, --dim${NC} <number>"
    echo "        Embedding dimension. Default: 1024"
    echo ""
    echo -e "    ${GREEN}-p, --port${NC} <number>"
    echo "        Server port. Default: 9621"
    echo ""
    echo -e "    ${GREEN}-i, --interactive${NC}"
    echo "        Run in interactive mode with menu selection"
    echo ""
    echo -e "    ${GREEN}-v, --verbose${NC}"
    echo "        Enable verbose output with debug information"
    echo ""
    echo -e "    ${GREEN}-q, --quiet${NC}"
    echo "        Suppress non-essential output"
    echo ""
    echo -e "    ${GREEN}--dry-run${NC}"
    echo "        Show what would be run without executing"
    echo ""
    echo -e "    ${GREEN}--skip-server${NC}"
    echo "        Skip server management (use existing server)"
    echo ""
    echo -e "    ${GREEN}--keep-server${NC}"
    echo "        Keep server running after tests complete"
    echo ""
    echo -e "    ${GREEN}--openai${NC}"
    echo "        Use OpenAI models (gpt-4o-mini + text-embedding-3-small)"
    echo "        Requires OPENAI_API_KEY environment variable"
    echo ""
    echo -e "    ${GREEN}--reset-db${NC}"
    echo "        Reset/reinitialize database and KB before each run"
    echo "        Clears all existing data for clean test state"
    echo ""
    echo -e "    ${GREEN}-l, --list${NC}"
    echo "        List available tests and backends"
    echo ""
    echo -e "    ${GREEN}-h, --help${NC}"
    echo "        Show this help message"
    echo ""
    echo -e "    ${GREEN}--version${NC}"
    echo "        Show version information"
    echo ""
    
    echo -e "${BOLD}EXAMPLES${NC}"
    echo -e "    ${DIM}# Run all tests with file backend (default)${NC}"
    echo "    $0"
    echo ""
    echo -e "    ${DIM}# Run all tests with PostgreSQL backend${NC}"
    echo "    $0 -b postgres"
    echo ""
    echo -e "    ${DIM}# Run only isolation test${NC}"
    echo "    $0 -t isolation"
    echo ""
    echo -e "    ${DIM}# Run isolation and deletion tests with postgres${NC}"
    echo "    $0 -b postgres -t isolation,deletion"
    echo ""
    echo -e "    ${DIM}# Run tests on all backends${NC}"
    echo "    $0 -b all"
    echo ""
    echo -e "    ${DIM}# Interactive mode${NC}"
    echo "    $0 -i"
    echo ""
    echo -e "    ${DIM}# Use custom LLM model${NC}"
    echo "    $0 -m llama3.1:8b"
    echo ""
    echo -e "    ${DIM}# Dry run to see configuration${NC}"
    echo "    $0 --dry-run -b postgres -t isolation"
    echo ""
    echo -e "    ${DIM}# Run with OpenAI (requires OPENAI_API_KEY)${NC}"
    echo "    $0 --openai"
    echo ""
    echo -e "    ${DIM}# Run with OpenAI and reset database${NC}"
    echo "    $0 --openai --reset-db -b postgres"
    echo ""
    echo -e "    ${DIM}# Reset database before each test run${NC}"
    echo "    $0 --reset-db"
    echo ""
    
    echo -e "${BOLD}ENVIRONMENT VARIABLES${NC}"
    echo "    OPENAI_API_KEY       OpenAI API key (required for --openai)"
    echo "    LIGHTRAG_API_URL     API URL (default: http://localhost:9621)"
    echo "    AUTH_USER            Admin username (default: admin)"
    echo "    AUTH_PASS            Admin password (default: admin123)"
    echo "    POSTGRES_HOST        PostgreSQL host (default: localhost)"
    echo "    POSTGRES_PORT        PostgreSQL port (default: 5432)"
    echo "    POSTGRES_USER        PostgreSQL user (default: lightrag)"
    echo "    POSTGRES_PASSWORD    PostgreSQL password"
    echo "    POSTGRES_DATABASE    PostgreSQL database (default: lightrag_multitenant)"
    echo ""
    
    echo -e "${BOLD}EXIT CODES${NC}"
    echo "    0    All tests passed"
    echo "    1    One or more tests failed"
    echo "    2    Configuration or setup error"
    echo ""
}

show_version() {
    echo "LightRAG E2E Test Runner v${VERSION}"
}

list_available() {
    print_banner
    
    echo -e "${BOLD}📋 AVAILABLE TESTS${NC}"
    print_separator
    for i in "${!TEST_KEYS[@]}"; do
        echo -e "  ${GREEN}${TEST_KEYS[$i]}${NC}"
        echo -e "    Name: ${TEST_NAMES[$i]}"
        echo -e "    File: ${TEST_FILES[$i]}"
        echo -e "    ${DIM}${TEST_DESCS[$i]}${NC}"
        echo ""
    done
    
    echo -e "${BOLD}💾 AVAILABLE BACKENDS${NC}"
    print_separator
    for i in "${!BACKEND_KEYS[@]}"; do
        echo -e "  ${GREEN}${BACKEND_KEYS[$i]}${NC}"
        echo -e "    Name: ${BACKEND_NAMES[$i]}"
        echo -e "    ${DIM}${BACKEND_DESCS[$i]}${NC}"
        echo ""
    done
}

# ==============================================================================
# Interactive Mode
# ==============================================================================

interactive_menu() {
    print_banner
    
    echo -e "${BOLD}🎮 INTERACTIVE MODE${NC}"
    print_separator
    
    # Select Backend
    echo -e "\n${BOLD}Select Storage Backend:${NC}"
    echo "  1) file     - File-based storage (JSON, NetworkX, NanoVectorDB)"
    echo "  2) postgres - PostgreSQL with pgvector"
    echo "  3) all      - Test both backends"
    echo ""
    read -p "Enter choice [1-3] (default: 1): " backend_choice
    
    case "$backend_choice" in
        2) BACKEND="postgres" ;;
        3) BACKEND="all" ;;
        *) BACKEND="file" ;;
    esac
    
    # Select Tests
    echo -e "\n${BOLD}Select Tests to Run:${NC}"
    echo "  1) all       - Run all tests"
    echo "  2) isolation - Multi-tenant isolation test"
    echo "  3) deletion  - Document deletion test"
    echo "  4) mixed     - Mixed operations test"
    echo "  5) custom    - Select multiple tests"
    echo ""
    read -p "Enter choice [1-5] (default: 1): " test_choice
    
    case "$test_choice" in
        2) SELECTED_TESTS="isolation" ;;
        3) SELECTED_TESTS="deletion" ;;
        4) SELECTED_TESTS="mixed" ;;
        5) 
            echo ""
            echo "Select tests (space-separated, e.g., '1 3'):"
            echo "  1) isolation"
            echo "  2) deletion"
            echo "  3) mixed"
            read -p "Enter choices: " custom_tests
            SELECTED_TESTS=""
            for choice in $custom_tests; do
                case "$choice" in
                    1) SELECTED_TESTS="$SELECTED_TESTS isolation" ;;
                    2) SELECTED_TESTS="$SELECTED_TESTS deletion" ;;
                    3) SELECTED_TESTS="$SELECTED_TESTS mixed" ;;
                esac
            done
            SELECTED_TESTS=$(echo "$SELECTED_TESTS" | xargs)  # Trim whitespace
            ;;
        *) SELECTED_TESTS="" ;;  # Empty means all
    esac
    
    # Advanced Options
    echo -e "\n${BOLD}Advanced Options:${NC}"
    
    read -p "Use OpenAI models? [y/N]: " openai_choice
    if [[ "$openai_choice" =~ ^[Yy] ]]; then
        USE_OPENAI="true"
        LLM_BINDING="openai"
        LLM_MODEL="$OPENAI_LLM_MODEL"
        EMBEDDING_BINDING="openai"
        EMBEDDING_MODEL="$OPENAI_EMBEDDING_MODEL"
        EMBEDDING_DIM="$OPENAI_EMBEDDING_DIM"
        if [[ -z "$OPENAI_API_KEY" ]]; then
            log_warning "OPENAI_API_KEY not set. Please set it before running tests."
        fi
    fi
    
    read -p "Reset database before tests? [y/N]: " reset_choice
    [[ "$reset_choice" =~ ^[Yy] ]] && RESET_DB="true"
    
    read -p "Enable verbose output? [y/N]: " verbose_choice
    [[ "$verbose_choice" =~ ^[Yy] ]] && VERBOSE="true"
    
    read -p "Keep server running after tests? [y/N]: " keep_choice
    [[ "$keep_choice" =~ ^[Yy] ]] && KEEP_SERVER="true"
    
    # Custom LLM Model (only if not using OpenAI)
    if [[ "$USE_OPENAI" != "true" ]]; then
        echo ""
        read -p "LLM Model (default: $LLM_MODEL): " custom_llm
        [[ -n "$custom_llm" ]] && LLM_MODEL="$custom_llm"
    fi
    
    # Confirmation
    echo ""
    print_separator
    echo -e "${BOLD}Configuration Summary:${NC}"
    echo "  Backend:     $BACKEND"
    if [[ -z "$SELECTED_TESTS" ]]; then
        echo "  Tests:       all"
    else
        echo "  Tests:       $SELECTED_TESTS"
    fi
    echo "  LLM Binding: $LLM_BINDING"
    echo "  LLM Model:   $LLM_MODEL"
    echo "  Embedding:   $EMBEDDING_MODEL (dim: $EMBEDDING_DIM)"
    echo "  Reset DB:    $RESET_DB"
    echo "  Verbose:     $VERBOSE"
    echo "  Keep Server: $KEEP_SERVER"
    print_separator
    echo ""
    
    read -p "Proceed with these settings? [Y/n]: " confirm
    if [[ "$confirm" =~ ^[Nn] ]]; then
        echo "Aborted."
        exit 0
    fi
}

# ==============================================================================
# Server Management
# ==============================================================================

cleanup_server() {
    if [[ "$SKIP_SERVER" == "true" ]]; then
        log_debug "Skipping server cleanup (--skip-server)"
        return 0
    fi
    
    if lsof -i :$SERVER_PORT > /dev/null 2>&1; then
        log_info "Stopping existing server on port $SERVER_PORT..."
        lsof -i :$SERVER_PORT | grep -i python | awk '{print $2}' | xargs kill -9 2>/dev/null || true
        sleep 2
        log_success "Server stopped"
    fi
}

start_server() {
    if [[ "$SKIP_SERVER" == "true" ]]; then
        log_debug "Skipping server start (--skip-server)"
        return 0
    fi
    
    log_step "Starting LightRAG Server"
    
    cd "$PROJECT_ROOT"
    
    if [[ "$VERBOSE" == "true" ]]; then
        python -m lightrag.api.lightrag_server --port "$SERVER_PORT" 2>&1 | tee "$LOG_FILE" &
    else
        nohup python -m lightrag.api.lightrag_server --port "$SERVER_PORT" > "$LOG_FILE" 2>&1 &
    fi
    
    SERVER_PID=$!
    echo "$SERVER_PID" > /tmp/lightrag_test_server.pid
    log_debug "Server PID: $SERVER_PID"
    
    # Wait for server to be ready
    log_info "Waiting for server to be ready..."
    local count=0
    while [[ $count -lt $SERVER_TIMEOUT ]]; do
        if curl -s "http://localhost:$SERVER_PORT/health" > /dev/null 2>&1; then
            log_success "Server is ready!"
            return 0
        fi
        if curl -s "http://localhost:$SERVER_PORT/docs" > /dev/null 2>&1; then
            log_success "Server is ready!"
            return 0
        fi
        sleep 1
        count=$((count + 1))
        log_debug "Waiting... ($count/$SERVER_TIMEOUT)"
    done
    
    log_error "Server failed to start within $SERVER_TIMEOUT seconds"
    log_error "Check $LOG_FILE for details"
    if [[ -f "$LOG_FILE" ]]; then
        echo -e "${DIM}Last 20 lines of server log:${NC}"
        tail -20 "$LOG_FILE"
    fi
    return 1
}

stop_server() {
    if [[ "$SKIP_SERVER" == "true" ]]; then
        log_debug "Skipping server stop (--skip-server)"
        return 0
    fi
    
    if [[ "$KEEP_SERVER" == "true" ]]; then
        log_info "Keeping server running (--keep-server)"
        return 0
    fi
    
    if [[ -f /tmp/lightrag_test_server.pid ]]; then
        local pid=$(cat /tmp/lightrag_test_server.pid)
        if kill -0 "$pid" 2>/dev/null; then
            log_info "Stopping server (PID: $pid)..."
            kill "$pid" 2>/dev/null || true
            wait "$pid" 2>/dev/null || true
            log_success "Server stopped"
        fi
        rm -f /tmp/lightrag_test_server.pid
    fi
}

# ==============================================================================
# Environment Configuration
# ==============================================================================

configure_environment() {
    local backend_type=$1
    
    log_step "Configuring Environment for $backend_type"
    
    # Common settings
    export LLM_BINDING="$LLM_BINDING"
    export LLM_MODEL="$LLM_MODEL"
    export EMBEDDING_BINDING="$EMBEDDING_BINDING"
    export EMBEDDING_MODEL="$EMBEDDING_MODEL"
    export EMBEDDING_DIM="$EMBEDDING_DIM"
    export LIGHTRAG_API_KEY="${LIGHTRAG_API_KEY:-admin123}"
    export AUTH_ACCOUNTS="${AUTH_ACCOUNTS:-admin:admin123}"
    
    case "$backend_type" in
        file)
            export LIGHTRAG_KV_STORAGE="JsonKVStorage"
            export LIGHTRAG_DOC_STATUS_STORAGE="JsonDocStatusStorage"
            export LIGHTRAG_GRAPH_STORAGE="NetworkXStorage"
            export LIGHTRAG_VECTOR_STORAGE="NanoVectorDBStorage"
            
            log_info "Cleaning up local storage..."
            rm -rf "$PROJECT_ROOT/rag_storage"
            ;;
            
        postgres)
            export LIGHTRAG_KV_STORAGE="PGKVStorage"
            export LIGHTRAG_DOC_STATUS_STORAGE="PGDocStatusStorage"
            export LIGHTRAG_GRAPH_STORAGE="PGGraphStorage"
            export LIGHTRAG_VECTOR_STORAGE="PGVectorStorage"
            
            export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
            export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
            export POSTGRES_USER="${POSTGRES_USER:-lightrag}"
            export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-lightrag_secure_password}"
            export POSTGRES_DATABASE="${POSTGRES_DATABASE:-lightrag_multitenant}"
            
            log_warning "Ensure PostgreSQL is running at $POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DATABASE"
            
            # Reset PostgreSQL database if requested
            if [[ "$RESET_DB" == "true" ]]; then
                log_info "Resetting PostgreSQL database..."
                reset_postgres_database
            fi
            ;;
            
        *)
            log_error "Unknown backend: $backend_type"
            return 1
            ;;
    esac
    
    if [[ "$VERBOSE" == "true" ]]; then
        echo -e "${DIM}Environment Variables:${NC}"
        echo "  LIGHTRAG_KV_STORAGE=$LIGHTRAG_KV_STORAGE"
        echo "  LIGHTRAG_GRAPH_STORAGE=$LIGHTRAG_GRAPH_STORAGE"
        echo "  LIGHTRAG_VECTOR_STORAGE=$LIGHTRAG_VECTOR_STORAGE"
        echo "  LLM_BINDING=$LLM_BINDING"
        echo "  LLM_MODEL=$LLM_MODEL"
        echo "  EMBEDDING_BINDING=$EMBEDDING_BINDING"
        echo "  EMBEDDING_MODEL=$EMBEDDING_MODEL"
    fi
    
    log_success "Environment configured for $backend_type"
}

# ==============================================================================
# Database Reset Functions
# ==============================================================================

reset_postgres_database() {
    log_step "Resetting PostgreSQL Database"
    
    local pg_host="${POSTGRES_HOST:-localhost}"
    local pg_port="${POSTGRES_PORT:-5432}"
    local pg_user="${POSTGRES_USER:-lightrag}"
    local pg_pass="${POSTGRES_PASSWORD:-lightrag_secure_password}"
    local pg_db="${POSTGRES_DATABASE:-lightrag_multitenant}"
    
    # Check if psql is available
    if ! command -v psql &> /dev/null; then
        log_warning "psql not found. Skipping database reset."
        log_info "Install PostgreSQL client or reset manually."
        return 0
    fi
    
    export PGPASSWORD="$pg_pass"
    
    # Drop and recreate tables for multi-tenant data
    log_info "Clearing tenant data from PostgreSQL..."
    
    # Try to truncate/delete data from known tables
    psql -h "$pg_host" -p "$pg_port" -U "$pg_user" -d "$pg_db" -q << EOF 2>/dev/null || true
-- Truncate all tenant-related tables if they exist
DO \$\$
DECLARE
    t TEXT;
BEGIN
    FOR t IN 
        SELECT tablename FROM pg_tables 
        WHERE schemaname = 'public' 
        AND (tablename LIKE '%tenant%' OR tablename LIKE '%kb%' OR tablename LIKE '%chunk%' 
             OR tablename LIKE '%entity%' OR tablename LIKE '%relation%' OR tablename LIKE '%document%')
    LOOP
        EXECUTE 'TRUNCATE TABLE ' || quote_ident(t) || ' CASCADE';
        RAISE NOTICE 'Truncated table: %', t;
    END LOOP;
END \$\$;
EOF
    
    unset PGPASSWORD
    
    log_success "PostgreSQL database reset complete"
}

reset_file_storage() {
    log_step "Resetting File Storage"
    
    if [[ -d "$PROJECT_ROOT/rag_storage" ]]; then
        log_info "Removing rag_storage directory..."
        rm -rf "$PROJECT_ROOT/rag_storage"
        log_success "File storage reset complete"
    else
        log_info "No existing file storage found"
    fi
}

# ==============================================================================
# Test Execution
# ==============================================================================

get_tests_to_run() {
    if [[ -z "$SELECTED_TESTS" ]]; then
        # Run all tests
        echo "${TEST_KEYS[*]}"
    else
        # Convert comma-separated to space-separated
        echo "$SELECTED_TESTS" | tr ',' ' '
    fi
}

run_single_test() {
    local test_key=$1
    local backend=$2
    
    # Find test index
    local idx=-1
    for i in "${!TEST_KEYS[@]}"; do
        if [[ "${TEST_KEYS[$i]}" == "$test_key" ]]; then
            idx=$i
            break
        fi
    done
    
    if [[ $idx -eq -1 ]]; then
        log_error "Unknown test: $test_key"
        return 1
    fi
    
    local file="${TEST_FILES[$idx]}"
    local name="${TEST_NAMES[$idx]}"
    local test_file="$SCRIPT_DIR/$file"
    
    if [[ ! -f "$test_file" ]]; then
        log_error "Test file not found: $test_file"
        return 1
    fi
    
    echo ""
    print_separator
    echo -e "${BOLD}🧪 Running: ${name}${NC}"
    echo -e "${DIM}   File: $file | Backend: $backend${NC}"
    print_separator
    
    cd "$PROJECT_ROOT"
    
    if python "$test_file"; then
        log_success "$name PASSED"
        return 0
    else
        log_error "$name FAILED"
        return 1
    fi
}

run_test_suite() {
    local backend=$1
    local passed=0
    local failed=0
    local test_results=""
    
    log_step "Running Test Suite for Backend: $backend"
    
    cleanup_server
    configure_environment "$backend"
    
    if ! start_server; then
        log_error "Failed to start server"
        return 1
    fi
    
    local tests_to_run=$(get_tests_to_run)
    local total=0
    local current=0
    
    # Count total tests
    for test_key in $tests_to_run; do
        total=$((total + 1))
    done
    
    for test_key in $tests_to_run; do
        current=$((current + 1))
        echo -e "\n${CYAN}[$current/$total]${NC}"
        
        if run_single_test "$test_key" "$backend"; then
            passed=$((passed + 1))
            test_results="$test_results\n  ${GREEN}✅ $test_key${NC}"
        else
            failed=$((failed + 1))
            test_results="$test_results\n  ${RED}❌ $test_key${NC}"
        fi
    done
    
    stop_server
    
    # Print summary
    echo ""
    print_separator
    echo -e "${BOLD}📊 Test Results for $backend${NC}"
    print_separator
    echo -e "$test_results"
    print_separator
    echo -e "  Total: $total | ${GREEN}Passed: $passed${NC} | ${RED}Failed: $failed${NC}"
    print_separator
    
    if [[ $failed -eq 0 ]]; then
        echo -e "\n${GREEN}🎉 All tests passed for $backend!${NC}"
        return 0
    else
        echo -e "\n${RED}💥 $failed test(s) failed for $backend${NC}"
        return 1
    fi
}

# ==============================================================================
# Dry Run
# ==============================================================================

show_dry_run() {
    print_banner
    
    echo -e "${BOLD}🔍 DRY RUN - Configuration Preview${NC}"
    print_separator
    
    echo -e "\n${BOLD}Selected Backend(s):${NC}"
    if [[ "$BACKEND" == "all" ]]; then
        echo "  - file"
        echo "  - postgres"
    else
        echo "  - $BACKEND"
    fi
    
    echo -e "\n${BOLD}Selected Tests:${NC}"
    local tests_to_run=$(get_tests_to_run)
    for test_key in $tests_to_run; do
        local idx=-1
        for i in "${!TEST_KEYS[@]}"; do
            if [[ "${TEST_KEYS[$i]}" == "$test_key" ]]; then
                idx=$i
                break
            fi
        done
        if [[ $idx -ne -1 ]]; then
            echo "  - $test_key (${TEST_FILES[$idx]})"
        fi
    done
    
    echo -e "\n${BOLD}Model Configuration:${NC}"
    echo "  LLM Binding:       $LLM_BINDING"
    echo "  LLM Model:         $LLM_MODEL"
    echo "  Embedding Binding: $EMBEDDING_BINDING"
    echo "  Embedding Model:   $EMBEDDING_MODEL"
    echo "  Embedding Dim:     $EMBEDDING_DIM"
    
    echo -e "\n${BOLD}Server Configuration:${NC}"
    echo "  Port:        $SERVER_PORT"
    echo "  Skip Server: $SKIP_SERVER"
    echo "  Keep Server: $KEEP_SERVER"
    echo "  Reset DB:    $RESET_DB"
    
    echo -e "\n${BOLD}Output Options:${NC}"
    echo "  Verbose: $VERBOSE"
    echo "  Quiet:   $QUIET"
    
    if [[ "$USE_OPENAI" == "true" ]]; then
        echo ""
        if [[ -n "$OPENAI_API_KEY" ]]; then
            echo -e "  ${GREEN}OpenAI API Key: Set ✓${NC}"
        else
            echo -e "  ${RED}OpenAI API Key: NOT SET ✗${NC}"
        fi
    fi
    
    print_separator
    echo -e "\n${DIM}To run these tests, remove the --dry-run flag${NC}"
}

# ==============================================================================
# Argument Parsing
# ==============================================================================

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            -b|--backend)
                BACKEND="$2"
                shift 2
                ;;
            -t|--tests)
                SELECTED_TESTS="$2"
                shift 2
                ;;
            -m|--llm-model)
                LLM_MODEL="$2"
                shift 2
                ;;
            --llm-binding)
                LLM_BINDING="$2"
                shift 2
                ;;
            -e|--embedding-model)
                EMBEDDING_MODEL="$2"
                shift 2
                ;;
            --embedding-binding)
                EMBEDDING_BINDING="$2"
                shift 2
                ;;
            -d|--dim)
                EMBEDDING_DIM="$2"
                shift 2
                ;;
            -p|--port)
                SERVER_PORT="$2"
                shift 2
                ;;
            -i|--interactive)
                INTERACTIVE="true"
                shift
                ;;
            -v|--verbose)
                VERBOSE="true"
                shift
                ;;
            -q|--quiet)
                QUIET="true"
                shift
                ;;
            --dry-run)
                DRY_RUN="true"
                shift
                ;;
            --skip-server)
                SKIP_SERVER="true"
                shift
                ;;
            --keep-server)
                KEEP_SERVER="true"
                shift
                ;;
            --openai)
                USE_OPENAI="true"
                LLM_BINDING="openai"
                LLM_MODEL="$OPENAI_LLM_MODEL"
                EMBEDDING_BINDING="openai"
                EMBEDDING_MODEL="$OPENAI_EMBEDDING_MODEL"
                EMBEDDING_DIM="$OPENAI_EMBEDDING_DIM"
                shift
                ;;
            --reset-db)
                RESET_DB="true"
                shift
                ;;
            -l|--list)
                list_available
                exit 0
                ;;
            -h|--help)
                show_help
                exit 0
                ;;
            --version)
                show_version
                exit 0
                ;;
            -*)
                log_error "Unknown option: $1"
                echo "Use --help for usage information"
                exit 2
                ;;
            *)
                # Treat as test name
                if [[ -z "$SELECTED_TESTS" ]]; then
                    SELECTED_TESTS="$1"
                else
                    SELECTED_TESTS="$SELECTED_TESTS $1"
                fi
                shift
                ;;
        esac
    done
    
    # Validate OpenAI API key if using OpenAI
    if [[ "$USE_OPENAI" == "true" && -z "$OPENAI_API_KEY" ]]; then
        log_warning "OPENAI_API_KEY environment variable is not set"
        log_info "Please set it before running: export OPENAI_API_KEY=your-key"
    fi
    
    # Validate backend
    if [[ "$BACKEND" != "file" && "$BACKEND" != "postgres" && "$BACKEND" != "all" ]]; then
        log_error "Invalid backend: $BACKEND"
        echo "Valid backends: file, postgres, all"
        exit 2
    fi
    
    # Validate selected tests
    if [[ -n "$SELECTED_TESTS" ]]; then
        for test in $(echo "$SELECTED_TESTS" | tr ',' ' '); do
            if [[ "$test" != "all" ]]; then
                local found=false
                for k in "${TEST_KEYS[@]}"; do
                    if [[ "$k" == "$test" ]]; then
                        found=true
                        break
                    fi
                done
                if [[ "$found" != "true" ]]; then
                    log_error "Unknown test: $test"
                    echo "Use --list to see available tests"
                    exit 2
                fi
            fi
        done
    fi
    
    # Handle "all" in tests
    if [[ "$SELECTED_TESTS" == "all" ]]; then
        SELECTED_TESTS=""
    fi
}

# ==============================================================================
# Main Entry Point
# ==============================================================================

main() {
    parse_args "$@"
    
    # Interactive mode
    if [[ "$INTERACTIVE" == "true" ]]; then
        interactive_menu
    fi
    
    # Dry run mode
    if [[ "$DRY_RUN" == "true" ]]; then
        show_dry_run
        exit 0
    fi
    
    # Print banner unless quiet
    if [[ "$QUIET" != "true" ]]; then
        print_banner
    fi
    
    # Track overall results
    local overall_result=0
    local backend_results=""
    
    # Set up trap for cleanup
    trap 'stop_server; exit' INT TERM
    
    # Run tests for selected backend(s)
    if [[ "$BACKEND" == "all" ]]; then
        log_step "Running tests on ALL backends"
        
        for backend in file postgres; do
            echo ""
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            echo -e "${CYAN}                    BACKEND: ${BOLD}$backend${NC}"
            echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
            
            if run_test_suite "$backend"; then
                backend_results="$backend_results\n  ${GREEN}✅ $backend${NC}"
            else
                backend_results="$backend_results\n  ${RED}❌ $backend${NC}"
                overall_result=1
            fi
        done
        
        # Print overall summary
        echo ""
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "${BOLD}                    OVERALL RESULTS${NC}"
        echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
        echo -e "$backend_results"
        
        if [[ $overall_result -eq 0 ]]; then
            echo -e "\n${GREEN}🏆 ALL BACKENDS PASSED!${NC}"
        else
            echo -e "\n${RED}💥 SOME BACKENDS FAILED${NC}"
        fi
    else
        if ! run_test_suite "$BACKEND"; then
            overall_result=1
        fi
    fi
    
    exit $overall_result
}

# Run main
main "$@"
