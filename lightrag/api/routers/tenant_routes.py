"""Tenant management routes for multi-tenant LightRAG API.

Provides CRUD endpoints for managing tenants and knowledge bases.
"""

import logging
from typing import List, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from lightrag.models.tenant import Tenant, KnowledgeBase, TenantContext, Permission
from lightrag.services.tenant_service import TenantService
from lightrag.api.dependencies import get_tenant_context, check_permission

logger = logging.getLogger(__name__)

# Request/Response Models
class TenantCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    metadata: Optional[dict] = None

class TenantUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class TenantResponse(BaseModel):
    tenant_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    num_knowledge_bases: int
    num_documents: int
    storage_used_gb: float

class KBCreateRequest(BaseModel):
    name: str
    description: Optional[str] = ""
    metadata: Optional[dict] = None

class KBUpdateRequest(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    metadata: Optional[dict] = None

class KBResponse(BaseModel):
    kb_id: str
    tenant_id: str
    name: str
    description: str
    created_at: str
    updated_at: str
    num_documents: int
    num_entities: int
    num_relations: int


def create_tenant_routes(tenant_service: TenantService) -> APIRouter:
    """Create tenant management routes.
    
    Args:
        tenant_service: Service instance for tenant operations
        
    Returns:
        APIRouter with tenant routes
    """
    router = APIRouter(prefix="/api/v1", tags=["tenants"])
    
    # Tenant management endpoints
    
    @router.post("/tenants", response_model=TenantResponse, status_code=status.HTTP_201_CREATED)
    async def create_tenant(
        request: TenantCreateRequest,
        context: TenantContext = Depends(check_permission(Permission.KB_CREATE.value))
    ):
        """Create a new tenant.
        
        Requires admin or tenant creation permission.
        """
        try:
            tenant = await tenant_service.create_tenant(
                name=request.name,
                description=request.description or "",
                metadata=request.metadata or {}
            )
            return TenantResponse(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                description=tenant.description,
                created_at=tenant.created_at.isoformat(),
                updated_at=tenant.updated_at.isoformat(),
                num_knowledge_bases=tenant.num_knowledge_bases,
                num_documents=tenant.num_documents,
                storage_used_gb=tenant.storage_used_gb,
            )
        except Exception as e:
            logger.error(f"Error creating tenant: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create tenant"
            )
    
    @router.get("/tenants/{tenant_id}", response_model=TenantResponse)
    async def get_tenant(
        tenant_id: str,
        context: TenantContext = Depends(get_tenant_context)
    ):
        """Get tenant details.
        
        Users can only view their own tenant.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other tenants"
            )
        
        try:
            tenant = await tenant_service.get_tenant(tenant_id)
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            return TenantResponse(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                description=tenant.description,
                created_at=tenant.created_at.isoformat(),
                updated_at=tenant.updated_at.isoformat(),
                num_knowledge_bases=tenant.num_knowledge_bases,
                num_documents=tenant.num_documents,
                storage_used_gb=tenant.storage_used_gb,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get tenant"
            )
    
    @router.put("/tenants/{tenant_id}", response_model=TenantResponse)
    async def update_tenant(
        tenant_id: str,
        request: TenantUpdateRequest,
        context: TenantContext = Depends(
            check_permission(Permission.CONFIG_UPDATE.value)
        )
    ):
        """Update tenant settings.
        
        Users can only update their own tenant.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update other tenants"
            )
        
        try:
            tenant = await tenant_service.update_tenant(
                tenant_id=tenant_id,
                name=request.name,
                description=request.description,
                metadata=request.metadata
            )
            
            if not tenant:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
            
            return TenantResponse(
                tenant_id=tenant.tenant_id,
                name=tenant.name,
                description=tenant.description,
                created_at=tenant.created_at.isoformat(),
                updated_at=tenant.updated_at.isoformat(),
                num_knowledge_bases=tenant.num_knowledge_bases,
                num_documents=tenant.num_documents,
                storage_used_gb=tenant.storage_used_gb,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update tenant"
            )
    
    @router.delete("/tenants/{tenant_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_tenant(
        tenant_id: str,
        context: TenantContext = Depends(check_permission(Permission.KB_DELETE.value))
    ):
        """Delete a tenant and all associated data.
        
        Users can only delete their own tenant. This operation is irreversible.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete other tenants"
            )
        
        try:
            success = await tenant_service.delete_tenant(tenant_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Tenant not found"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete tenant"
            )
    
    # Knowledge base management endpoints
    
    @router.post("/tenants/{tenant_id}/knowledge-bases", response_model=KBResponse, status_code=status.HTTP_201_CREATED)
    async def create_knowledge_base(
        tenant_id: str,
        request: KBCreateRequest,
        context: TenantContext = Depends(
            check_permission(Permission.KB_CREATE.value)
        )
    ):
        """Create a new knowledge base within a tenant.
        
        Users can only create KBs in their own tenant.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot create KBs in other tenants"
            )
        
        try:
            kb = await tenant_service.create_knowledge_base(
                tenant_id=tenant_id,
                name=request.name,
                description=request.description or "",
                metadata=request.metadata or {}
            )
            
            return KBResponse(
                kb_id=kb.kb_id,
                tenant_id=kb.tenant_id,
                name=kb.name,
                description=kb.description,
                created_at=kb.created_at.isoformat(),
                updated_at=kb.updated_at.isoformat(),
                num_documents=kb.num_documents,
                num_entities=kb.num_entities,
                num_relations=kb.num_relations,
            )
        except Exception as e:
            logger.error(f"Error creating KB for tenant {tenant_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to create knowledge base"
            )
    
    @router.get("/tenants/{tenant_id}/knowledge-bases/{kb_id}", response_model=KBResponse)
    async def get_knowledge_base(
        tenant_id: str,
        kb_id: str,
        context: TenantContext = Depends(get_tenant_context)
    ):
        """Get knowledge base details.
        
        Users can only view KBs in their own tenant.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access KBs in other tenants"
            )
        
        if context.kb_id != kb_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot access other knowledge bases"
            )
        
        try:
            kb = await tenant_service.get_knowledge_base(kb_id)
            if not kb or kb.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Knowledge base not found"
                )
            
            return KBResponse(
                kb_id=kb.kb_id,
                tenant_id=kb.tenant_id,
                name=kb.name,
                description=kb.description,
                created_at=kb.created_at.isoformat(),
                updated_at=kb.updated_at.isoformat(),
                num_documents=kb.num_documents,
                num_entities=kb.num_entities,
                num_relations=kb.num_relations,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error getting KB {kb_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to get knowledge base"
            )
    
    @router.put("/tenants/{tenant_id}/knowledge-bases/{kb_id}", response_model=KBResponse)
    async def update_knowledge_base(
        tenant_id: str,
        kb_id: str,
        request: KBUpdateRequest,
        context: TenantContext = Depends(
            check_permission(Permission.KB_UPDATE.value)
        )
    ):
        """Update knowledge base settings.
        
        Users can only update KBs in their own tenant.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update KBs in other tenants"
            )
        
        if context.kb_id != kb_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot update other knowledge bases"
            )
        
        try:
            kb = await tenant_service.update_knowledge_base(
                kb_id=kb_id,
                name=request.name,
                description=request.description,
                metadata=request.metadata
            )
            
            if not kb or kb.tenant_id != tenant_id:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Knowledge base not found"
                )
            
            return KBResponse(
                kb_id=kb.kb_id,
                tenant_id=kb.tenant_id,
                name=kb.name,
                description=kb.description,
                created_at=kb.created_at.isoformat(),
                updated_at=kb.updated_at.isoformat(),
                num_documents=kb.num_documents,
                num_entities=kb.num_entities,
                num_relations=kb.num_relations,
            )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error updating KB {kb_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update knowledge base"
            )
    
    @router.delete("/tenants/{tenant_id}/knowledge-bases/{kb_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def delete_knowledge_base(
        tenant_id: str,
        kb_id: str,
        context: TenantContext = Depends(
            check_permission(Permission.KB_DELETE.value)
        )
    ):
        """Delete a knowledge base.
        
        Users can only delete KBs in their own tenant. This operation is irreversible.
        """
        if context.tenant_id != tenant_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete KBs in other tenants"
            )
        
        if context.kb_id != kb_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Cannot delete other knowledge bases"
            )
        
        try:
            success = await tenant_service.delete_knowledge_base(kb_id)
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="Knowledge base not found"
                )
        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Error deleting KB {kb_id}: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to delete knowledge base"
            )
    
    return router
