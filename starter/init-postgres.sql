-- ============================================================================
-- LightRAG Multi-Tenant PostgreSQL Schema Initialization
-- 
-- This script initializes the PostgreSQL database with multi-tenant support
-- It is automatically executed when PostgreSQL container starts
-- 
-- Features:
--   • Multi-tenant isolation with composite keys
--   • pgvector support for embeddings
--   • Automatic indexes for performance
--   • Sample data for testing
-- ============================================================================

-- ============================================================================
-- Extensions
-- ============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "vector";
CREATE EXTENSION IF NOT EXISTS "age";

-- ============================================================================
-- Tenants Table
-- 
-- Stores tenant information for multi-tenant system
-- Each tenant represents an organization, customer, or project
-- ============================================================================

CREATE TABLE IF NOT EXISTS tenants (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW()
);

CREATE INDEX idx_tenants_id ON tenants(tenant_id);

-- ============================================================================
-- Knowledge Bases Table
-- 
-- Stores knowledge base metadata for each tenant
-- Each tenant can have multiple KBs (prod, dev, staging, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS knowledge_bases (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_kb_tenant_kb UNIQUE(tenant_id, kb_id)
);

CREATE INDEX idx_kbs_tenant_kb ON knowledge_bases(tenant_id, kb_id);
CREATE INDEX idx_kbs_tenant ON knowledge_bases(tenant_id);

-- ============================================================================
-- Documents Table
-- 
-- Stores document metadata with multi-tenant isolation
-- Composite key: (tenant_id, kb_id, id)
-- This ensures data isolation at database level
-- ============================================================================

CREATE TABLE IF NOT EXISTS documents (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    content TEXT NOT NULL,
    file_name VARCHAR(512),
    file_path VARCHAR(512),
    file_type VARCHAR(50),
    file_size BIGINT,
    metadata JSONB,
    status VARCHAR(50) DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_doc_tenant_kb_id UNIQUE(tenant_id, kb_id, id)
);

CREATE INDEX idx_documents_tenant_kb ON documents(tenant_id, kb_id);
CREATE INDEX idx_documents_tenant_kb_created ON documents(tenant_id, kb_id, created_at DESC);
CREATE INDEX idx_documents_status ON documents(tenant_id, kb_id, status);
CREATE INDEX idx_documents_file_type ON documents(tenant_id, kb_id, file_type);

-- ============================================================================
-- Entities Table
-- 
-- Stores knowledge graph entities with multi-tenant isolation
-- Examples: Person, Organization, Location, Concept
-- ============================================================================

CREATE TABLE IF NOT EXISTS entities (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    entity_id VARCHAR(512) NOT NULL,
    name VARCHAR(512) NOT NULL,
    type VARCHAR(100),
    description TEXT,
    embedding VECTOR(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_entity_tenant_kb_id UNIQUE(tenant_id, kb_id, entity_id)
);

CREATE INDEX idx_entities_tenant_kb ON entities(tenant_id, kb_id);
CREATE INDEX idx_entities_tenant_kb_type ON entities(tenant_id, kb_id, type);
CREATE INDEX idx_entities_embedding ON entities USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- Relations Table
-- 
-- Stores knowledge graph relationships with multi-tenant isolation
-- Represents connections between entities (is_parent_of, works_for, etc.)
-- ============================================================================

CREATE TABLE IF NOT EXISTS relations (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    source_entity_id VARCHAR(512) NOT NULL,
    target_entity_id VARCHAR(512) NOT NULL,
    relation_type VARCHAR(255) NOT NULL,
    description TEXT,
    weight FLOAT DEFAULT 1.0,
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_relation_tenant_kb UNIQUE(tenant_id, kb_id, source_entity_id, target_entity_id, relation_type)
);

CREATE INDEX idx_relations_tenant_kb ON relations(tenant_id, kb_id);
CREATE INDEX idx_relations_source_target ON relations(tenant_id, kb_id, source_entity_id, target_entity_id);
CREATE INDEX idx_relations_type ON relations(tenant_id, kb_id, relation_type);

-- ============================================================================
-- Vector Embeddings Table
-- 
-- Stores vector embeddings for semantic search
-- Composite key ensures tenant/KB isolation
-- ============================================================================

CREATE TABLE IF NOT EXISTS embeddings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    document_id UUID NOT NULL,
    chunk_id VARCHAR(512) NOT NULL,
    content TEXT NOT NULL,
    embedding VECTOR(1024),
    metadata JSONB,
    created_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT uk_embedding_tenant_kb_chunk UNIQUE(tenant_id, kb_id, chunk_id)
);

CREATE INDEX idx_embeddings_tenant_kb ON embeddings(tenant_id, kb_id);
CREATE INDEX idx_embeddings_doc_id ON embeddings(tenant_id, kb_id, document_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops);

-- ============================================================================
-- Document Status Table
-- 
-- Tracks document processing status
-- Used to manage async document ingestion pipeline
-- ============================================================================

CREATE TABLE IF NOT EXISTS document_status (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    document_id UUID NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'pending',
    progress INT DEFAULT 0,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
    CONSTRAINT uk_doc_status_tenant_kb_doc UNIQUE(tenant_id, kb_id, document_id)
);

CREATE INDEX idx_doc_status_tenant_kb ON document_status(tenant_id, kb_id);
CREATE INDEX idx_doc_status_status ON document_status(tenant_id, kb_id, status);

-- ============================================================================
-- KV Storage Table
-- 
-- General key-value storage for multi-tenant data
-- Used for caching and temporary storage
-- ============================================================================

CREATE TABLE IF NOT EXISTS kv_storage (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    tenant_id VARCHAR(255) NOT NULL,
    kb_id VARCHAR(255) NOT NULL,
    key VARCHAR(512) NOT NULL,
    value TEXT NOT NULL,
    expiry_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    FOREIGN KEY (tenant_id) REFERENCES tenants(tenant_id) ON DELETE CASCADE,
    CONSTRAINT uk_kv_tenant_kb_key UNIQUE(tenant_id, kb_id, key)
);

CREATE INDEX idx_kv_tenant_kb ON kv_storage(tenant_id, kb_id);
CREATE INDEX idx_kv_expiry ON kv_storage(expiry_at);

-- ============================================================================
-- Sample Data for Testing Multi-Tenant Features
-- ============================================================================

-- Insert sample tenants
INSERT INTO tenants (tenant_id, name, description) VALUES
    ('acme-corp', 'Acme Corporation', 'Enterprise customer - production deployment'),
    ('techstart', 'TechStart Inc', 'Startup customer - evaluation environment')
ON CONFLICT (tenant_id) DO NOTHING;

-- Insert sample knowledge bases for Acme Corp
INSERT INTO knowledge_bases (tenant_id, kb_id, name, description) VALUES
    ('acme-corp', 'kb-prod', 'Production KB', 'Production knowledge base for Acme Corp'),
    ('acme-corp', 'kb-dev', 'Development KB', 'Development knowledge base for Acme Corp')
ON CONFLICT (tenant_id, kb_id) DO NOTHING;

-- Insert sample knowledge bases for TechStart
INSERT INTO knowledge_bases (tenant_id, kb_id, name, description) VALUES
    ('techstart', 'kb-main', 'Main KB', 'Main knowledge base for TechStart'),
    ('techstart', 'kb-backup', 'Backup KB', 'Backup knowledge base for TechStart')
ON CONFLICT (tenant_id, kb_id) DO NOTHING;

-- ============================================================================
-- Grant Permissions
-- ============================================================================

-- Grant all permissions to lightrag user
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO lightrag;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO lightrag;
GRANT ALL PRIVILEGES ON ALL FUNCTIONS IN SCHEMA public TO lightrag;
GRANT CREATE ON SCHEMA public TO lightrag;

-- ============================================================================
-- Cleanup and Vacuuming
-- ============================================================================

-- Analyze table statistics for query optimization
ANALYZE tenants;
ANALYZE knowledge_bases;
ANALYZE documents;
ANALYZE entities;
ANALYZE relations;
ANALYZE embeddings;
ANALYZE document_status;
ANALYZE kv_storage;

-- ============================================================================
-- Initialization Complete
-- ============================================================================

-- Enable showing all messages
-- SELECT 'PostgreSQL multi-tenant schema initialized successfully' AS status;
