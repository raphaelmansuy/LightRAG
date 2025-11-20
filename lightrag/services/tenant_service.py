"""Service for managing tenants and knowledge bases."""

from typing import Optional, List, Dict, Any
import logging
from datetime import datetime

from lightrag.models.tenant import Tenant, KnowledgeBase, TenantConfig, KBConfig
from lightrag.base import BaseKVStorage

logger = logging.getLogger(__name__)


class TenantService:
    """Service for managing tenants and knowledge bases."""
    
    def __init__(self, kv_storage: BaseKVStorage):
        """Initialize tenant service with KV storage backend.
        
        Args:
            kv_storage: Backend storage for tenant/KB metadata
        """
        self.kv_storage = kv_storage
        self.tenant_namespace = "__tenants__"
        self.kb_namespace = "__knowledge_bases__"
    
    async def create_tenant(
        self,
        tenant_name: str,
        description: Optional[str] = None,
        config: Optional[TenantConfig] = None,
        created_by: Optional[str] = None,
    ) -> Tenant:
        """Create a new tenant.
        
        Args:
            tenant_name: Display name for the tenant
            description: Optional description
            config: Optional tenant configuration
            created_by: User ID that created the tenant
            
        Returns:
            Created Tenant object
        """
        tenant = Tenant(
            tenant_name=tenant_name,
            description=description,
            config=config or TenantConfig(),
            created_by=created_by,
        )
        
        # Store tenant metadata
        tenant_data = tenant.to_dict()
        await self.kv_storage.upsert({
            f"{self.tenant_namespace}:{tenant.tenant_id}": tenant_data
        })
        
        logger.info(f"Created tenant: {tenant.tenant_id} ({tenant_name})")
        return tenant
    
    async def get_tenant(self, tenant_id: str) -> Optional[Tenant]:
        """Retrieve a tenant by ID.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            Tenant object if found, None otherwise
        """
        data = await self.kv_storage.get_by_id(
            f"{self.tenant_namespace}:{tenant_id}"
        )
        if not data:
            return None
        return self._deserialize_tenant(data)
    
    async def update_tenant(
        self,
        tenant_id: str,
        **kwargs,
    ) -> Optional[Tenant]:
        """Update a tenant.
        
        Args:
            tenant_id: Tenant identifier
            **kwargs: Fields to update
            
        Returns:
            Updated Tenant object if found, None otherwise
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(tenant, key):
                setattr(tenant, key, value)
        
        tenant.updated_at = datetime.utcnow()
        
        # Store updated tenant
        tenant_data = tenant.to_dict()
        await self.kv_storage.upsert({
            f"{self.tenant_namespace}:{tenant_id}": tenant_data
        })
        
        logger.info(f"Updated tenant: {tenant_id}")
        return tenant
    
    async def list_tenants(self, skip: int = 0, limit: int = 100) -> List[Tenant]:
        """List all tenants.
        
        Args:
            skip: Number of tenants to skip
            limit: Maximum number of tenants to return
            
        Returns:
            List of Tenant objects
        """
        # This would need to be implemented based on storage backend
        # For now, return empty list as placeholder
        logger.info(f"Listing tenants (skip={skip}, limit={limit})")
        return []
    
    async def delete_tenant(self, tenant_id: str) -> bool:
        """Delete a tenant.
        
        Args:
            tenant_id: Tenant identifier
            
        Returns:
            True if deleted, False if not found
        """
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            return False
        
        # Delete all KBs associated with tenant
        kbs = await self.list_knowledge_bases(tenant_id)
        for kb in kbs:
            await self.delete_knowledge_base(tenant_id, kb.kb_id)
        
        # Delete tenant
        await self.kv_storage.delete(
            [f"{self.tenant_namespace}:{tenant_id}"]
        )
        
        logger.info(f"Deleted tenant: {tenant_id}")
        return True
    
    async def create_knowledge_base(
        self,
        tenant_id: str,
        kb_name: str,
        description: Optional[str] = None,
        config: Optional[KBConfig] = None,
        created_by: Optional[str] = None,
    ) -> KnowledgeBase:
        """Create a new knowledge base for a tenant.
        
        Args:
            tenant_id: Parent tenant ID
            kb_name: Display name for KB
            description: Optional description
            config: Optional KB configuration
            created_by: User ID that created the KB
            
        Returns:
            Created KnowledgeBase object
            
        Raises:
            ValueError: If tenant not found
        """
        # Verify tenant exists
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")
        
        kb = KnowledgeBase(
            tenant_id=tenant_id,
            kb_name=kb_name,
            description=description,
            config=config,
            created_by=created_by,
        )
        
        # Store KB metadata
        kb_data = kb.to_dict()
        await self.kv_storage.upsert({
            f"{self.kb_namespace}:{tenant_id}:{kb.kb_id}": kb_data
        })
        
        # Update tenant KB count
        tenant.kb_count += 1
        await self.update_tenant(tenant_id, kb_count=tenant.kb_count)
        
        logger.info(f"Created KB: {kb.kb_id} ({kb_name}) for tenant {tenant_id}")
        return kb
    
    async def get_knowledge_base(
        self,
        tenant_id: str,
        kb_id: str,
    ) -> Optional[KnowledgeBase]:
        """Retrieve a knowledge base.
        
        Args:
            tenant_id: Parent tenant ID
            kb_id: Knowledge base ID
            
        Returns:
            KnowledgeBase object if found, None otherwise
        """
        data = await self.kv_storage.get_by_id(
            f"{self.kb_namespace}:{tenant_id}:{kb_id}"
        )
        if not data:
            return None
        return self._deserialize_kb(data)
    
    async def update_knowledge_base(
        self,
        tenant_id: str,
        kb_id: str,
        **kwargs,
    ) -> Optional[KnowledgeBase]:
        """Update a knowledge base.
        
        Args:
            tenant_id: Parent tenant ID
            kb_id: Knowledge base ID
            **kwargs: Fields to update
            
        Returns:
            Updated KnowledgeBase object if found, None otherwise
        """
        kb = await self.get_knowledge_base(tenant_id, kb_id)
        if not kb:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(kb, key):
                setattr(kb, key, value)
        
        kb.updated_at = datetime.utcnow()
        
        # Store updated KB
        kb_data = kb.to_dict()
        await self.kv_storage.upsert({
            f"{self.kb_namespace}:{tenant_id}:{kb_id}": kb_data
        })
        
        logger.info(f"Updated KB: {kb_id} for tenant {tenant_id}")
        return kb
    
    async def list_knowledge_bases(
        self,
        tenant_id: str,
        skip: int = 0,
        limit: int = 100,
    ) -> List[KnowledgeBase]:
        """List all knowledge bases for a tenant.
        
        Args:
            tenant_id: Parent tenant ID
            skip: Number of KBs to skip
            limit: Maximum number of KBs to return
            
        Returns:
            List of KnowledgeBase objects
        """
        # This would need to be implemented based on storage backend
        # For now, return empty list as placeholder
        logger.info(f"Listing KBs for tenant {tenant_id} (skip={skip}, limit={limit})")
        return []
    
    async def delete_knowledge_base(
        self,
        tenant_id: str,
        kb_id: str,
    ) -> bool:
        """Delete a knowledge base.
        
        Args:
            tenant_id: Parent tenant ID
            kb_id: Knowledge base ID
            
        Returns:
            True if deleted, False if not found
        """
        kb = await self.get_knowledge_base(tenant_id, kb_id)
        if not kb:
            return False
        
        # Delete KB
        await self.kv_storage.delete(
            [f"{self.kb_namespace}:{tenant_id}:{kb_id}"]
        )
        
        # Update tenant KB count
        tenant = await self.get_tenant(tenant_id)
        if tenant:
            tenant.kb_count = max(0, tenant.kb_count - 1)
            await self.update_tenant(tenant_id, kb_count=tenant.kb_count)
        
        logger.info(f"Deleted KB: {kb_id} for tenant {tenant_id}")
        return True
    
    def _deserialize_tenant(self, data: Dict[str, Any]) -> Tenant:
        """Convert stored data to Tenant object."""
        config_data = data.get("config", {})
        quota_data = data.get("quota", {})
        
        config = TenantConfig(
            llm_model=config_data.get("llm_model", "gpt-4o-mini"),
            embedding_model=config_data.get("embedding_model", "bge-m3:latest"),
            rerank_model=config_data.get("rerank_model"),
            chunk_size=config_data.get("chunk_size", 1200),
            chunk_overlap=config_data.get("chunk_overlap", 100),
            top_k=config_data.get("top_k", 40),
            cosine_threshold=config_data.get("cosine_threshold", 0.2),
            enable_llm_cache=config_data.get("enable_llm_cache", True),
            custom_metadata=config_data.get("custom_metadata", {}),
        )
        
        # Create and return tenant
        tenant = Tenant(
            tenant_id=data.get("tenant_id", ""),
            tenant_name=data.get("tenant_name", ""),
            description=data.get("description"),
            config=config,
            is_active=data.get("is_active", True),
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.utcnow(),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
            metadata=data.get("metadata", {}),
            kb_count=data.get("kb_count", 0),
            total_documents=data.get("total_documents", 0),
            total_storage_mb=data.get("total_storage_mb", 0.0),
        )
        return tenant
    
    def _deserialize_kb(self, data: Dict[str, Any]) -> KnowledgeBase:
        """Convert stored data to KnowledgeBase object."""
        config_data = data.get("config")
        config = KBConfig(**config_data) if config_data else None
        
        kb = KnowledgeBase(
            kb_id=data.get("kb_id", ""),
            tenant_id=data.get("tenant_id", ""),
            kb_name=data.get("kb_name", ""),
            description=data.get("description"),
            is_active=data.get("is_active", True),
            status=data.get("status", "ready"),
            document_count=data.get("document_count", 0),
            entity_count=data.get("entity_count", 0),
            relationship_count=data.get("relationship_count", 0),
            chunk_count=data.get("chunk_count", 0),
            storage_used_mb=data.get("storage_used_mb", 0.0),
            last_indexed_at=datetime.fromisoformat(data.get("last_indexed_at")) if data.get("last_indexed_at") else None,
            index_version=data.get("index_version", 1),
            config=config,
            created_at=datetime.fromisoformat(data.get("created_at")) if data.get("created_at") else datetime.utcnow(),
            updated_at=datetime.fromisoformat(data.get("updated_at")) if data.get("updated_at") else datetime.utcnow(),
            created_by=data.get("created_by"),
            updated_by=data.get("updated_by"),
            metadata=data.get("metadata", {}),
        )
        return kb
