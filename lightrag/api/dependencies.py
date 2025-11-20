"""FastAPI dependencies for multi-tenant request handling.

This module provides dependency injection for tenant context extraction and validation.
"""

from fastapi import Depends, HTTPException, status, Header
from typing import Optional
import logging

from lightrag.models.tenant import TenantContext, Role
from lightrag.api.auth import auth_handler

logger = logging.getLogger(__name__)


async def get_tenant_context(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
    x_kb_id: Optional[str] = Header(None),
) -> TenantContext:
    """Extract and validate tenant context from request headers.
    
    Multi-tenant requests must include:
    - Authorization header with JWT token containing tenant_id
    - X-Tenant-ID header (optional, if not in token)
    - X-KB-ID header (optional, if not in token)
    
    Args:
        authorization: Authorization header with Bearer token
        x_tenant_id: Tenant ID from custom header
        x_kb_id: Knowledge base ID from custom header
    
    Returns:
        TenantContext: Validated tenant context for the request
        
    Raises:
        HTTPException: If tenant context cannot be extracted or validated
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    # Extract token from "Bearer <token>" format
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise ValueError("Invalid auth scheme")
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format. Use: Bearer <token>"
        )
    
    # Validate token
    token_data = auth_handler.validate_token(token)
    username = token_data.get("username")
    metadata = token_data.get("metadata", {})
    role_str = token_data.get("role", "viewer")
    
    # Convert role string to enum
    try:
        user_role = Role(role_str)
    except ValueError:
        user_role = Role.VIEWER
    
    # Extract tenant_id from token metadata or header
    tenant_id = metadata.get("tenant_id") or x_tenant_id
    if not tenant_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing tenant_id in token or X-Tenant-ID header"
        )
    
    # Extract kb_id from token metadata or header
    kb_id = metadata.get("kb_id") or x_kb_id
    if not kb_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing kb_id in token or X-KB-ID header"
        )
    
    # Create and return tenant context
    context = TenantContext(
        tenant_id=tenant_id,
        kb_id=kb_id,
        user_id=username,
        user_role=user_role
    )
    
    logger.debug(
        f"Extracted TenantContext: tenant={tenant_id}, kb={kb_id}, user={username}, role={role_str}"
    )
    
    return context


async def get_tenant_context_optional(
    authorization: Optional[str] = Header(None),
    x_tenant_id: Optional[str] = Header(None),
    x_kb_id: Optional[str] = Header(None),
) -> Optional[TenantContext]:
    """Extract tenant context from request headers (optional).
    
    Similar to get_tenant_context but doesn't raise if missing.
    Useful for backward compatibility with single-tenant endpoints.
    
    Returns:
        TenantContext or None: Validated tenant context, or None if not provided
    """
    try:
        return await get_tenant_context(authorization, x_tenant_id, x_kb_id)
    except HTTPException:
        return None


def check_permission(permission_required: str):
    """Factory function to create a dependency that checks for specific permission.
    
    Args:
        permission_required: The permission to check (e.g., "query:run")
    
    Returns:
        Async function that can be used as FastAPI dependency
    """
    async def verify_permission(
        context: TenantContext = Depends(get_tenant_context)
    ) -> TenantContext:
        """Verify that user has required permission."""
        from lightrag.models.tenant import Permission
        
        try:
            perm = Permission(permission_required)
        except ValueError:
            logger.error(f"Invalid permission: {permission_required}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Invalid permission check configuration"
            )
        
        if not context.has_permission(perm):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"User does not have permission: {permission_required}"
            )
        
        return context
    
    return verify_permission
