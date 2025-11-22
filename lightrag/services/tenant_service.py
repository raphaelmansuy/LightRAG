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
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Tenant:
        """Create a new tenant.
        
        Args:
            tenant_name: Display name for the tenant
            description: Optional description
            config: Optional tenant configuration
            created_by: User ID that created the tenant
            metadata: Optional metadata dictionary
            
        Returns:
            Created Tenant object
        """
        tenant = Tenant(
            tenant_name=tenant_name,
            description=description,
            config=config or TenantConfig(),
            created_by=created_by,
            metadata=metadata or {},
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
    
    async def verify_user_access(
        self,
        user_id: str,
        tenant_id: str
    ) -> bool:
        """Verify that a user has access to a specific tenant.
        
        This is a CRITICAL security function that prevents unauthorized
        cross-tenant data access. Currently implements a basic check that
        allows admin users and tenant creators to access tenants.
        
        TODO: Implement proper user-tenant membership table and roles.
        
        Args:
            user_id: User identifier from JWT token
            tenant_id: Requested tenant ID
            
        Returns:
            True if user has access, False otherwise
        """
        if not user_id or not tenant_id:
            logger.warning("verify_user_access called with empty user_id or tenant_id")
            return False
        
        # TEMPORARY: Allow admin users to access all tenants
        # This is for demo/development only - should be removed in production
        if user_id.lower() == "admin":
            logger.debug(f"Access granted: admin user {user_id} has access to all tenants")
            return True
        
        # Get tenant to check creator
        tenant = await self.get_tenant(tenant_id)
        if not tenant:
            logger.debug(f"Tenant {tenant_id} not found during access check")
            return False
            
        logger.info(f"Checking access for user={user_id} to tenant={tenant_id}. Metadata={tenant.metadata}")
        
        # Check if tenant is public
        if tenant.metadata.get("is_public", False):
            logger.debug(f"Access granted: tenant {tenant_id} is public")
            return True
        
        # Check if user is the creator
        if tenant.created_by == user_id:
            logger.debug(f"Access granted: user {user_id} is creator of tenant {tenant_id}")
            return True
        
        # TODO: Check user-tenant membership table
        # For now, only creator has access
        logger.warning(
            f"Access denied: user {user_id} is not creator of tenant {tenant_id}"
        )
        return False
    
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
    
    async def list_tenants(
        self,
        skip: int = 0,
        limit: int = 100,
        search: Optional[str] = None,
        tenant_id_filter: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all tenants with pagination.
        
        Args:
            skip: Number of tenants to skip (for pagination)
            limit: Maximum number of tenants to return
            search: Optional search string to filter by name or description
            tenant_id_filter: Optional tenant ID to filter by (for non-admin users)
            
        Returns:
            Dict with 'items' (list of tenants) and 'total' (count) keys
        """
        try:
            # Get all tenant keys from storage
            tenant_keys = []
            if hasattr(self.kv_storage, 'get_by_prefix'):
                # For storages that support prefix search
                tenant_keys = await self.kv_storage.get_by_prefix(self.tenant_namespace)
            elif hasattr(self.kv_storage, 'get_all'):
                # For storages like JsonKVStorage that have get_all
                all_data = await self.kv_storage.get_all()
                tenant_keys = [key for key in all_data.keys() if key.startswith(f"{self.tenant_namespace}:")]
            else:
                # Fallback: attempt to retrieve all tenants (backend dependent)
                logger.warning("Storage backend doesn't support prefix search, returning limited results")
                return {"items": [], "total": 0}
            
            # Filter and deserialize tenants
            all_tenants = []
            for key in tenant_keys:
                if not key.startswith(f"{self.tenant_namespace}:"):
                    continue
                try:
                    data = await self.kv_storage.get_by_id(key)
                    if data:
                        tenant = self._deserialize_tenant(data)
                        
                        # Skip invalid tenants
                        if not tenant.tenant_id:
                            logger.warning(f"Skipping tenant with empty ID from key {key}")
                            continue

                        # Apply filters
                        if tenant_id_filter and tenant.tenant_id != tenant_id_filter:
                            continue
                        if search:
                            search_lower = search.lower()
                            if not (search_lower in tenant.tenant_name.lower() or 
                                    search_lower in (tenant.description or "").lower()):
                                continue
                        
                        all_tenants.append(tenant)
                except Exception as e:
                    logger.error(f"Error deserializing tenant from key {key}: {e}")
                    continue
            
            # Sort by created_at descending
            all_tenants.sort(key=lambda t: t.created_at, reverse=True)
            
            # Apply pagination
            total = len(all_tenants)
            paginated_tenants = all_tenants[skip:skip + limit]
            
            logger.info(f"Listed {len(paginated_tenants)} tenants out of {total} (skip={skip}, limit={limit})")
            return {
                "items": paginated_tenants,
                "total": total
            }
        except Exception as e:
            logger.error(f"Error listing tenants: {e}")
            return {"items": [], "total": 0}
    
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
        kbs_result = await self.list_knowledge_bases(tenant_id)
        kbs_list = kbs_result.get("items", [])
        for kb in kbs_list:
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
        search: Optional[str] = None,
    ) -> Dict[str, Any]:
        """List all knowledge bases for a tenant with pagination.
        
        Args:
            tenant_id: Parent tenant ID
            skip: Number of KBs to skip (for pagination)
            limit: Maximum number of KBs to return
            search: Optional search string to filter by name or description
            
        Returns:
            Dict with 'items' (list of KBs) and 'total' (count) keys
        """
        try:
            # Get all KB keys for this tenant
            kb_keys = []
            if hasattr(self.kv_storage, 'get_by_prefix'):
                # For storages that support prefix search
                tenant_prefix = f"{self.kb_namespace}:{tenant_id}:"
                kb_keys = await self.kv_storage.get_by_prefix(tenant_prefix)
            elif hasattr(self.kv_storage, 'get_all'):
                # For storages like JsonKVStorage that have get_all
                all_data = await self.kv_storage.get_all()
                kb_keys = [key for key in all_data.keys() if key.startswith(f"{self.kb_namespace}:{tenant_id}:")]
            else:
                # Fallback: return empty list
                logger.warning("Storage backend doesn't support prefix search for KBs")
                return {"items": [], "total": 0}
            
            # Filter and deserialize KBs
            all_kbs = []
            for key in kb_keys:
                if not key.startswith(f"{self.kb_namespace}:{tenant_id}:"):
                    continue
                try:
                    data = await self.kv_storage.get_by_id(key)
                    if data:
                        kb = self._deserialize_kb(data)
                        
                        # Apply search filter
                        if search:
                            search_lower = search.lower()
                            if not (search_lower in kb.kb_name.lower() or 
                                    search_lower in (kb.description or "").lower()):
                                continue
                        
                        all_kbs.append(kb)
                except Exception as e:
                    logger.error(f"Error deserializing KB from key {key}: {e}")
                    continue
            
            # Sort by created_at descending
            all_kbs.sort(key=lambda k: k.created_at, reverse=True)
            
            # Apply pagination
            total = len(all_kbs)
            paginated_kbs = all_kbs[skip:skip + limit]
            
            logger.info(f"Listed {len(paginated_kbs)} KBs out of {total} for tenant {tenant_id} (skip={skip}, limit={limit})")
            return {
                "items": paginated_kbs,
                "total": total
            }
        except Exception as e:
            logger.error(f"Error listing KBs for tenant {tenant_id}: {e}")
            return {"items": [], "total": 0}
    
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
        import json
        
        # Handle PGKVStorage wrapping
        if "data" in data:
            inner_data = data["data"]
            if isinstance(inner_data, str):
                try:
                    inner_data = json.loads(inner_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from tenant data: {inner_data}")
            
            if isinstance(inner_data, dict) and "tenant_id" in inner_data:
                data = inner_data

        if not data.get("tenant_id"):
            logger.warning(f"Deserializing tenant with missing ID. Data keys: {list(data.keys())}")
            
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
        import json

        # Handle PGKVStorage wrapping
        if "data" in data:
            inner_data = data["data"]
            if isinstance(inner_data, str):
                try:
                    inner_data = json.loads(inner_data)
                except json.JSONDecodeError:
                    logger.warning(f"Failed to decode JSON from KB data: {inner_data}")
            
            if isinstance(inner_data, dict) and "kb_id" in inner_data:
                data = inner_data

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
