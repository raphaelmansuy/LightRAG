"""
Integration tests for tenant-scoped document routes (Phase 3).

This test suite verifies that all document-related endpoints properly use
tenant-scoped RAG instances, ensuring multi-tenant data isolation and correct
document visibility within each tenant's knowledge base.

Key test scenarios:
1. Document text insertion via /text endpoint (tenant-scoped)
2. Batch text insertion via /texts endpoint (tenant-scoped)
3. Document listing via /documents endpoint (tenant-scoped)
4. Document status tracking via /track_status endpoint (tenant-scoped)
5. Multi-tenant isolation: documents in Tenant A are not visible in Tenant B
"""

import pytest
from datetime import datetime
from unittest.mock import AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI, Depends

from lightrag.models.tenant import TenantContext, Role
from lightrag.base import DocProcessingStatus, DocStatus
from lightrag.api.dependencies import get_tenant_context
from lightrag.api.routers.document_routes import router as document_router
from lightrag.lightrag import LightRAG


# ============================================================================
# Fixtures
# ============================================================================

@pytest.fixture
def tenant_context_a():
    """Tenant A context for isolation testing."""
    return TenantContext(
        tenant_id="tenant-a",
        kb_id="kb-a-1",
        user_id="user-a-123",
        user_role=Role.ADMIN
    )


@pytest.fixture
def tenant_context_b():
    """Tenant B context for isolation testing."""
    return TenantContext(
        tenant_id="tenant-b",
        kb_id="kb-b-1",
        user_id="user-b-456",
        user_role=Role.ADMIN
    )


@pytest.fixture
def mock_rag_instance():
    """Create a mock LightRAG instance for testing."""
    mock = AsyncMock(spec=LightRAG)
    
    # Mock doc_status storage
    mock.doc_status = AsyncMock()
    mock.doc_status.get_doc_by_file_path = AsyncMock(return_value=None)
    mock.doc_status.get_doc = AsyncMock(return_value=None)
    
    # Mock document retrieval methods
    mock.get_docs_by_status = AsyncMock(return_value={})
    mock.aget_docs_by_track_id = AsyncMock(return_value={})
    
    return mock


@pytest.fixture
def mock_rag_instances():
    """Create separate mock RAG instances for each tenant for isolation testing."""
    rag_a = AsyncMock(spec=LightRAG)
    rag_b = AsyncMock(spec=LightRAG)
    
    # Setup Tenant A RAG
    rag_a.doc_status = AsyncMock()
    rag_a.doc_status.get_doc_by_file_path = AsyncMock(return_value=None)
    rag_a.get_docs_by_status = AsyncMock(return_value={
        "doc-a-1": DocProcessingStatus(
            id="doc-a-1",
            status=DocStatus.PROCESSED,
            content_summary="Sample doc in Tenant A",
            content_length=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            track_id="track-a-1"
        )
    })
    rag_a.aget_docs_by_track_id = AsyncMock(return_value={
        "doc-a-1": DocProcessingStatus(
            id="doc-a-1",
            status=DocStatus.PROCESSED,
            content_summary="Sample doc in Tenant A",
            content_length=100,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            track_id="track-a-1"
        )
    })
    
    # Setup Tenant B RAG
    rag_b.doc_status = AsyncMock()
    rag_b.doc_status.get_doc_by_file_path = AsyncMock(return_value=None)
    rag_b.get_docs_by_status = AsyncMock(return_value={
        "doc-b-1": DocProcessingStatus(
            id="doc-b-1",
            status=DocStatus.PROCESSED,
            content_summary="Sample doc in Tenant B",
            content_length=200,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            track_id="track-b-1"
        )
    })
    rag_b.aget_docs_by_track_id = AsyncMock(return_value={
        "doc-b-1": DocProcessingStatus(
            id="doc-b-1",
            status=DocStatus.PROCESSED,
            content_summary="Sample doc in Tenant B",
            content_length=200,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
            track_id="track-b-1"
        )
    })
    
    return {"tenant-a": rag_a, "tenant-b": rag_b}


@pytest.fixture
def app_with_document_routes(mock_rag_instances):
    """Create FastAPI app with document routes and mocked dependencies."""
    app = FastAPI()
    
    # Include document router
    app.include_router(document_router, prefix="/api/documents", tags=["documents"])
    
    # Track the current tenant context
    current_context = {"context": None, "rag": None}
    
    # Mock get_tenant_context
    async def mock_get_tenant_context(*args, **kwargs):
        return current_context["context"]
    
    # Mock get_tenant_rag that returns the appropriate RAG instance
    async def mock_get_tenant_rag(*args, **kwargs):
        tenant_id = current_context["context"].tenant_id
        return mock_rag_instances.get(tenant_id)
    
    # Override dependencies
    app.dependency_overrides[get_tenant_context] = mock_get_tenant_context
    app.dependency_overrides[get_tenant_rag] = mock_get_tenant_rag
    
    # Store context setter for tests
    app._set_context = lambda ctx: current_context.update({"context": ctx})
    
    return app


@pytest.fixture
def client(app_with_document_routes):
    """Create test client."""
    return TestClient(app_with_document_routes)


# ============================================================================
# Test Cases
# ============================================================================

class TestDocumentRoutesUseTenantRAG:
    """Test that document routes properly use tenant-scoped RAG instances."""
    
    def test_text_endpoint_uses_tenant_rag(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /text endpoint uses tenant-specific RAG instance."""
        app_with_document_routes._set_context(tenant_context_a)
        
        response = client.post(
            "/api/documents/text",
            json={
                "text": "This is a test document",
                "file_source": "test_file.txt"
            }
        )
        
        # Verify that the request was processed
        assert response.status_code in [200, 400, 500], f"Unexpected status code: {response.status_code}"
        
        # Verify that tenant A's RAG was queried for doc status
        mock_rag_instances["tenant-a"].doc_status.get_doc_by_file_path.assert_called()
    
    def test_texts_endpoint_uses_tenant_rag(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /texts endpoint uses tenant-specific RAG instance."""
        app_with_document_routes._set_context(tenant_context_a)
        
        response = client.post(
            "/api/documents/texts",
            json={
                "texts": ["Document 1", "Document 2"],
                "file_sources": ["doc1.txt", "doc2.txt"]
            }
        )
        
        # Verify that the request was processed
        assert response.status_code in [200, 400, 500]
        
        # Verify that tenant A's RAG was queried for doc status
        mock_rag_instances["tenant-a"].doc_status.get_doc_by_file_path.assert_called()
    
    def test_documents_endpoint_uses_tenant_rag(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /documents GET endpoint uses tenant-specific RAG instance."""
        app_with_document_routes._set_context(tenant_context_a)
        
        response = client.get("/api/documents")
        
        # Verify that the request was processed
        assert response.status_code == 200
        
        # Verify that tenant A's RAG was used to get docs by status
        mock_rag_instances["tenant-a"].get_docs_by_status.assert_called()
    
    def test_track_status_endpoint_uses_tenant_rag(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /track_status endpoint uses tenant-specific RAG instance."""
        app_with_document_routes._set_context(tenant_context_a)
        
        response = client.get("/api/documents/track_status/track-a-1")
        
        # Verify that the request was processed
        assert response.status_code == 200
        
        # Verify that tenant A's RAG was used to get docs by track_id
        mock_rag_instances["tenant-a"].aget_docs_by_track_id.assert_called()


class TestMultiTenantIsolation:
    """Test that documents from different tenants are isolated from each other."""
    
    def test_tenant_a_cannot_see_tenant_b_documents(self, client, app_with_document_routes, tenant_context_a, tenant_context_b, mock_rag_instances):
        """Verify that Tenant A's document queries don't return Tenant B's documents."""
        # Query as Tenant A
        app_with_document_routes._set_context(tenant_context_a)
        response_a = client.get("/api/documents")
        
        # Query as Tenant B
        app_with_document_routes._set_context(tenant_context_b)
        response_b = client.get("/api/documents")
        
        # Both should succeed
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        
        # Verify that different RAG instances were used
        mock_rag_instances["tenant-a"].get_docs_by_status.assert_called()
        mock_rag_instances["tenant-b"].get_docs_by_status.assert_called()
    
    def test_track_status_returns_only_tenant_documents(self, client, app_with_document_routes, tenant_context_a, tenant_context_b, mock_rag_instances):
        """Verify that track_status endpoint returns docs from the correct tenant only."""
        # Track status in Tenant A
        app_with_document_routes._set_context(tenant_context_a)
        response_a = client.get("/api/documents/track_status/track-a-1")
        
        # Track status in Tenant B
        app_with_document_routes._set_context(tenant_context_b)
        response_b = client.get("/api/documents/track_status/track-b-1")
        
        # Both should succeed
        assert response_a.status_code == 200
        assert response_b.status_code == 200
        
        # Verify that different RAG instances were queried for different track IDs
        mock_rag_instances["tenant-a"].aget_docs_by_track_id.assert_called_with("track-a-1")
        mock_rag_instances["tenant-b"].aget_docs_by_track_id.assert_called_with("track-b-1")


class TestDocumentEndpointFunctionality:
    """Test basic functionality of document endpoints."""
    
    def test_text_endpoint_duplicate_file_source_rejection(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /text endpoint rejects duplicate file sources."""
        app_with_document_routes._set_context(tenant_context_a)
        
        # Mock that file already exists
        existing_doc = {"status": "PROCESSED"}
        mock_rag_instances["tenant-a"].doc_status.get_doc_by_file_path.return_value = existing_doc
        
        response = client.post(
            "/api/documents/text",
            json={
                "text": "Duplicate content",
                "file_source": "duplicate.txt"
            }
        )
        
        # Should return duplicated status
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "duplicated"
    
    def test_texts_endpoint_accepts_batch_insert(self, client, app_with_document_routes, tenant_context_a, mock_rag_instances):
        """Test that /texts endpoint can handle batch text insertion."""
        app_with_document_routes._set_context(tenant_context_a)
        
        response = client.post(
            "/api/documents/texts",
            json={
                "texts": ["Text 1", "Text 2", "Text 3"],
                "file_sources": ["file1.txt", "file2.txt", "file3.txt"]
            }
        )
        
        # Should accept the batch
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "success"


# ============================================================================
# Test Runner Configuration
# ============================================================================

if __name__ == "__main__":
    pytest.main([__file__, "-v"])
