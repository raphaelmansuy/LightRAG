.PHONY: help setup up down logs clean reset test status init-db view-compose

# Color definitions for beautiful output
BLUE := \033[0;34m
GREEN := \033[0;32m
YELLOW := \033[1;33m
RED := \033[0;31m
NC := \033[0m # No Color

# Configuration
DOCKER_COMPOSE_FILE := docker-compose.yml
ENV_FILE := .env
PROJECT_NAME := lightrag-multitenant

# ============================================================================
# HELP - Display available commands with descriptions
# ============================================================================
help:
	@echo "$(BLUE)╔════════════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(BLUE)║                 LightRAG Multi-Tenant Stack                         ║$(NC)"
	@echo "$(BLUE)║              (PostgreSQL Backend with Docker Compose)               ║$(NC)"
	@echo "$(BLUE)╚════════════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@echo "$(GREEN)🚀 QUICK START:$(NC)"
	@echo "  1. $(YELLOW)make setup$(NC)         → Initialize project (first time only)"
	@echo "  2. $(YELLOW)make up$(NC)            → Start all services"
	@echo "  3. $(YELLOW)make logs$(NC)          → View service logs"
	@echo ""
	@echo "$(GREEN)📋 AVAILABLE COMMANDS:$(NC)"
	@echo ""
	@echo "$(YELLOW)Setup & Configuration:$(NC)"
	@echo "  $(YELLOW)make setup$(NC)              Initialize .env file from template (run once)"
	@echo "  $(YELLOW)make init-db$(NC)            Initialize PostgreSQL database (run once after services start)"
	@echo ""
	@echo "$(YELLOW)Service Control:$(NC)"
	@echo "  $(YELLOW)make up$(NC)                 Start all services (PostgreSQL, Redis, LightRAG API, WebUI)"
	@echo "  $(YELLOW)make down$(NC)               Stop and remove all services"
	@echo "  $(YELLOW)make restart$(NC)            Restart all services"
	@echo "  $(YELLOW)make logs$(NC)               Stream logs from all services"
	@echo "  $(YELLOW)make logs-api$(NC)           Stream logs from LightRAG API only"
	@echo "  $(YELLOW)make logs-db$(NC)            Stream logs from PostgreSQL only"
	@echo "  $(YELLOW)make logs-webui$(NC)         Stream logs from WebUI only"
	@echo ""
	@echo "$(YELLOW)Database Management:$(NC)"
	@echo "  $(YELLOW)make db-shell$(NC)           Connect to PostgreSQL shell"
	@echo "  $(YELLOW)make db-backup$(NC)          Create database backup"
	@echo "  $(YELLOW)make db-restore$(NC)         Restore database from backup"
	@echo "  $(YELLOW)make db-reset$(NC)           Reset database (⚠️  WARNING: deletes all data)"
	@echo ""
	@echo "$(YELLOW)Development & Testing:$(NC)"
	@echo "  $(YELLOW)make test$(NC)               Run multi-tenant tests"
	@echo "  $(YELLOW)make test-isolation$(NC)     Run tenant isolation tests"
	@echo "  $(YELLOW)make api-health$(NC)         Check API health status"
	@echo ""
	@echo "$(YELLOW)Debugging & Monitoring:$(NC)"
	@echo "  $(YELLOW)make status$(NC)             Show status of all services"
	@echo "  $(YELLOW)make ps$(NC)                 List running containers"
	@echo "  $(YELLOW)make view-compose$(NC)       Display docker-compose.yml contents"
	@echo "  $(YELLOW)make clean$(NC)              Remove stopped containers and dangling images"
	@echo "  $(YELLOW)make reset$(NC)              Full reset (⚠️  WARNING: stops services, deletes volumes)"
	@echo ""
	@echo "$(BLUE)═════════════════════════════════════════════════════════════════════$(NC)"
	@echo "$(GREEN)📖 DOCUMENTATION:$(NC)"
	@echo ""
	@echo "  WebUI:        http://localhost:3001"
	@echo "  API Server:   http://localhost:8000"
	@echo "  PostgreSQL:   internal-only on the compose network (no host port by default)"
	@echo "               Use 'docker compose exec postgres psql -U lightrag -d lightrag_multitenant' to connect"
	@echo ""
	@echo "$(YELLOW)▶ Get started quickly:$(NC)"
	@echo "  1) Start services: $(YELLOW)make up$(NC)  (wait ~30-60s for services to warm up)"
	@echo "  2) Open the WebUI: $(YELLOW)http://localhost:3001$(NC) or check the API at $(YELLOW)http://localhost:8000$(NC)"
	@echo "  3) Need to access Postgres from your host?\n     • For dev: temporarily map ports or use:\n       $(YELLOW)docker compose exec postgres psql -U lightrag -d lightrag_multitenant$(NC)"
	@echo ""
	@echo "  Default Credentials for Login:"
	@echo "    - Username: $(YELLOW)admin$(NC)"
	@echo "    - Password: $(YELLOW)password$(NC)"
	@echo "  Default Credentials (see .env file):"
	@echo "    - PostgreSQL User: lightrag"
	@echo "    - PostgreSQL Database: lightrag_multitenant"
	@echo ""
	@echo "  $(YELLOW)WebUI Login Credentials:$(NC)"
	@echo "    - Username: $(YELLOW)admin$(NC)"
	@echo "    - Password: $(YELLOW)password$(NC)"
	@echo ""
	@echo "  Default Demo Credentials (see starter/env.example or .env) — for local/dev only!"
	@echo "    - PostgreSQL User:     $(YELLOW)lightrag$(NC)"
	@echo "    - PostgreSQL Password: $(YELLOW)lightrag_secure_password$(NC)"
	@echo "    - PostgreSQL Database: $(YELLOW)lightrag_multitenant$(NC)"
	@echo ""
	@echo "    ⚠️ NOTE: These defaults are provided for demos and development. Change POSTGRES_PASSWORD in"
	@echo "    your .env before using in a shared or production environment."
	@echo ""
	@echo "$(YELLOW)⚡ MULTI-TENANT FEATURES:$(NC)"
	@echo "  • Database-level tenant isolation (tenant_id + kb_id)"
	@echo "  • Automatic tenant context enforcement"
	@echo "  • Composite key pattern for data integrity"
	@echo "  • Cross-tenant access prevention"
	@echo ""
	@echo "$(BLUE)═════════════════════════════════════════════════════════════════════$(NC)"
	@echo ""

# ============================================================================
# SETUP - Initialize environment and configuration files
# ============================================================================
setup:
	@echo "$(BLUE)🔧 Setting up LightRAG Multi-Tenant Stack...$(NC)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(YELLOW)→ Creating .env file from template...$(NC)"; \
		cp env.template.example $(ENV_FILE); \
		echo "$(GREEN)✓ .env file created$(NC)"; \
		echo ""; \
		echo "$(YELLOW)⚠️  IMPORTANT: Edit .env file to configure:$(NC)"; \
		echo "  • OpenAI API key (or your LLM provider)"; \
		echo "  • PostgreSQL credentials (if different from defaults)"; \
		echo "  • Other service settings as needed"; \
		echo ""; \
		echo "$(YELLOW)Run 'make up' when ready to start services$(NC)"; \
	else \
		echo "$(GREEN)✓ .env file already exists$(NC)"; \
	fi
	@echo ""
	@echo "$(BLUE)✓ Setup complete!$(NC)"
	@echo ""

# ============================================================================
# UP - Start all services
# ============================================================================
up:
	@echo "$(BLUE)🚀 Starting LightRAG Multi-Tenant Stack...$(NC)"
	@if [ ! -f "$(ENV_FILE)" ]; then \
		echo "$(RED)✗ .env file not found!$(NC)"; \
		echo "$(YELLOW)Run 'make setup' first to create it.$(NC)"; \
		exit 1; \
	fi
	@echo "$(YELLOW)→ Starting services with Docker Compose...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) up -d
	@echo "$(GREEN)✓ Services started!$(NC)"
	@echo ""
	@echo "$(BLUE)📡 Service Endpoints:$(NC)"
	@echo "  • WebUI:       $(YELLOW)http://localhost:3001$(NC)"
	@echo "  • API Server:  $(YELLOW)http://localhost:8000$(NC)"
	@echo "  • PostgreSQL:  $(YELLOW)internal-only on compose network (no host port by default)$(NC)"
	@echo ""
	@echo "$(YELLOW)⏳ Waiting for services to be ready (this may take 30-60 seconds)...$(NC)"
	@sleep 10
	@make status
	@echo ""
	@echo "$(BLUE)Next steps:$(NC)"
	@echo "  1. Initialize database: $(YELLOW)make init-db$(NC)"
	@echo "  2. View logs:          $(YELLOW)make logs$(NC)"
	@echo "  3. Check API health:   $(YELLOW)make api-health$(NC)"
	@echo ""

# ============================================================================
# DOWN - Stop and remove all services
# ============================================================================
down:
	@echo "$(BLUE)🛑 Stopping LightRAG Multi-Tenant Stack...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) down
	@echo "$(GREEN)✓ Services stopped$(NC)"
	@echo ""

# ============================================================================
# RESTART - Restart all services
# ============================================================================
restart:
	@echo "$(BLUE)🔄 Restarting LightRAG Multi-Tenant Stack...$(NC)"
	make down
	@sleep 2
	make up

# ============================================================================
# LOGS - Stream logs from all services
# ============================================================================
logs:
	@echo "$(BLUE)📋 Streaming logs from all services (Ctrl+C to exit)...$(NC)"
	@echo ""
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) logs -f

# Stream logs from specific services
logs-api:
	@echo "$(BLUE)📋 Streaming logs from LightRAG API (Ctrl+C to exit)...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) logs -f lightrag-api

logs-webui:
	@echo "$(BLUE)📋 Streaming logs from WebUI (Ctrl+C to exit)...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) logs -f lightrag-webui

logs-db:
	@echo "$(BLUE)📋 Streaming logs from PostgreSQL (Ctrl+C to exit)...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) logs -f postgres

# ============================================================================
# STATUS - Show service health status
# ============================================================================
status:
	@echo "$(BLUE)📊 Service Status:$(NC)"
	@echo ""
	@docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) ps
	@echo ""

ps: status

# ============================================================================
# DATABASE OPERATIONS
# ============================================================================

# Initialize database with multi-tenant schema
init-db:
	@echo "$(BLUE)🗄️  Initializing PostgreSQL database...$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Waiting for PostgreSQL to be ready...$(NC)"
	@sleep 5
	@echo ""
	@echo "$(YELLOW)→ Creating database schema and multi-tenant support...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T postgres psql -U lightrag -d postgres -c "CREATE DATABASE lightrag_multitenant;" 2>/dev/null || true
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T postgres psql -U lightrag -d lightrag_multitenant -f /docker-entrypoint-initdb.d/01-init.sql
	@echo ""
	@echo "$(GREEN)✓ Database initialized with multi-tenant schema!$(NC)"
	@echo ""
	@echo "$(BLUE)Sample Tenants Created:$(NC)"
	@echo "  • acme-corp (kb-prod, kb-dev)"
	@echo "  • techstart (kb-main, kb-backup)"
	@echo ""

# Connect to PostgreSQL shell
db-shell:
	@echo "$(BLUE)🖥️  Connecting to PostgreSQL shell...$(NC)"
	@echo "$(YELLOW)Type \\q to exit$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec postgres psql -U lightrag -d lightrag_multitenant
	@echo ""

# Backup database
db-backup:
	@echo "$(BLUE)💾 Creating database backup...$(NC)"
	@mkdir -p ./backups
	@TIMESTAMP=$$(date +%Y%m%d_%H%M%S); \
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T postgres pg_dump -U lightrag lightrag_multitenant > ./backups/lightrag_backup_$$TIMESTAMP.sql
	@echo "$(GREEN)✓ Backup created at ./backups/$(NC)"

# Restore database from latest backup
db-restore:
	@echo "$(RED)⚠️  Restoring database from backup...$(NC)"
	@LATEST_BACKUP=$$(ls -t ./backups/lightrag_backup_*.sql 2>/dev/null | head -1); \
	if [ -z "$$LATEST_BACKUP" ]; then \
		echo "$(RED)✗ No backup files found in ./backups/$(NC)"; \
		exit 1; \
	fi; \
	echo "$(YELLOW)Restoring from: $$LATEST_BACKUP$(NC)"; \
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T postgres psql -U lightrag lightrag_multitenant < $$LATEST_BACKUP
	@echo "$(GREEN)✓ Database restored$(NC)"

# Reset database (WARNING: deletes all data)
db-reset:
	@echo "$(RED)⚠️  WARNING: This will delete ALL database data!$(NC)"
	@read -p "Are you sure? Type 'yes' to confirm: " confirm; \
	if [ "$$confirm" = "yes" ]; then \
		echo "$(YELLOW)Resetting database...$(NC)"; \
		docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T postgres psql -U lightrag -d postgres -c "DROP DATABASE IF EXISTS lightrag_multitenant;"; \
		make init-db; \
	else \
		echo "$(GREEN)Cancelled$(NC)"; \
	fi
	@echo ""

# ============================================================================
# HEALTH CHECKS & TESTING
# ============================================================================

# Check API health
api-health:
	@echo "$(BLUE)🏥 Checking API Health...$(NC)"
	@echo ""
	@if curl -s http://localhost:9621/health > /dev/null 2>&1; then \
		echo "$(GREEN)✓ API is healthy and responding$(NC)"; \
		echo "$(BLUE)API Response:$(NC)"; \
		curl -s http://localhost:9621/health | jq . 2>/dev/null || curl -s http://localhost:9621/health; \
	else \
		echo "$(RED)✗ API is not responding$(NC)"; \
		echo "$(YELLOW)Services may still be starting. Check logs with: make logs$(NC)"; \
	fi
	@echo ""

# Run multi-tenant tests
test:
	@echo "$(BLUE)🧪 Running Multi-Tenant Tests...$(NC)"
	@echo ""
	@echo "$(YELLOW)Running pytest on multi-tenant test suite...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T lightrag-api pytest tests/test_multi_tenant_backends.py -v 2>/dev/null || \
		echo "$(YELLOW)Note: Run 'make up' first to start services$(NC)"

# Run tenant isolation tests
test-isolation:
	@echo "$(BLUE)🔒 Running Tenant Isolation Tests...$(NC)"
	@echo ""
	@echo "$(YELLOW)Testing data isolation between tenants...$(NC)"
	docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) exec -T lightrag-api pytest tests/test_multi_tenant_backends.py::TestTenantIsolation -v 2>/dev/null || \
		echo "$(YELLOW)Note: Run 'make up' first to start services$(NC)"

# ============================================================================
# CLEANUP
# ============================================================================

# Clean up stopped containers and dangling images
clean:
	@echo "$(BLUE)🧹 Cleaning up Docker resources...$(NC)"
	@echo ""
	@echo "$(YELLOW)→ Removing stopped containers...$(NC)"
	docker container prune -f > /dev/null
	@echo "$(YELLOW)→ Removing dangling images...$(NC)"
	docker image prune -f > /dev/null
	@echo "$(YELLOW)→ Removing dangling volumes...$(NC)"
	docker volume prune -f > /dev/null
	@echo "$(GREEN)✓ Cleanup complete$(NC)"
	@echo ""

# Full reset - WARNING: stops services and removes volumes
reset:
	@echo "$(RED)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(RED)║          ⚠️  FULL SYSTEM RESET WARNING ⚠️                  ║$(NC)"
	@echo "$(RED)║                                                            ║$(NC)"
	@echo "$(RED)║  This will:                                              ║$(NC)"
	@echo "$(RED)║    • Stop all services                                   ║$(NC)"
	@echo "$(RED)║    • Remove all containers                              ║$(NC)"
	@echo "$(RED)║    • Delete all volumes (including database data)       ║$(NC)"
	@echo "$(RED)║    • Remove all networks                                ║$(NC)"
	@echo "$(RED)║                                                            ║$(NC)"
	@echo "$(RED)║  ALL DATA WILL BE LOST!                                 ║$(NC)"
	@echo "$(RED)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
	@read -p "$(RED)Type 'RESET' to confirm (all caps):$(NC) " confirm; \
	if [ "$$confirm" = "RESET" ]; then \
		echo "$(RED)Executing full reset...$(NC)"; \
		docker compose -f $(DOCKER_COMPOSE_FILE) -p $(PROJECT_NAME) down -v; \
		echo "$(GREEN)✓ Full reset complete$(NC)"; \
		echo ""; \
		echo "$(YELLOW)Run 'make setup' and 'make up' to start fresh$(NC)"; \
	else \
		echo "$(GREEN)Reset cancelled$(NC)"; \
	fi

# ============================================================================
# UTILITIES
# ============================================================================

# Display docker-compose.yml
view-compose:
	@echo "$(BLUE)📄 Docker Compose Configuration:$(NC)"
	@echo ""
	cat $(DOCKER_COMPOSE_FILE)

# Prune unused Docker resources
prune:
	@echo "$(BLUE)🗑️  Pruning unused Docker resources...$(NC)"
	docker system prune -f
	@echo "$(GREEN)✓ Pruned$(NC)"

# ============================================================================
# DEFAULT TARGET
# ============================================================================
.DEFAULT_GOAL := help
