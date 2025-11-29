# WebUI Initial State Fix - Avoiding Empty Documents on First Load

## Problem
When the WebUI first loads or refreshes, the Documents tab shows "0 docs" (empty state) until the page is refreshed again. This happens because:

1. **No Tenant Context on Initial Load**: The WebUI starts without a selected tenant/KB
2. **API Requests Without Headers**: The `getDocuments()` call has no `X-Tenant-ID` or `X-KB-ID` headers
3. **Global RAG Fallback**: API falls back to global (empty) RAG instance
4. **After Selection**: Once user selects a tenant and data is cached, refresh shows correct data

## Root Cause Analysis

### Current Flow (Problematic)
```
1. WebUI loads
   ├─ localStorage is empty (first visit)
   ├─ Axios interceptor doesn't add tenant headers
   └─ UI shows loading state...

2. Initial API call: getDocuments()
   ├─ No X-Tenant-ID header
   ├─ No X-KB-ID header
   ├─ Backend receives no tenant context
   └─ Falls back to global RAG (empty)

3. UI Displays
   ├─ Shows "0 docs"
   ├─ Empty document list
   └─ User confused

4. After User Selects Tenant
   ├─ localStorage updated with SELECTED_TENANT and SELECTED_KB
   ├─ User refreshes page
   ├─ Page loads WITH tenant context in localStorage
   └─ Now shows correct documents ✅
```

## Solution: Auto-Select First Available Tenant on Load

### Implementation Steps

**File**: `/lightrag_webui/src/hooks/useTenantInitialization.ts` (NEW)

Create a new hook to handle automatic tenant initialization:

```typescript
import { useEffect } from 'react'
import { useTenantState } from '@/stores/tenant'
import { fetchTenants, fetchKnowledgeBases } from '@/api/tenant'

/**
 * Hook to auto-initialize tenant and KB on first app load
 * Ensures that documents are visible even on initial page load
 */
export function useTenantInitialization() {
  const selectedTenant = useTenantState.use.selectedTenant()
  const selectedKB = useTenantState.use.selectedKB()
  const tenants = useTenantState.use.tenants()
  const knowledgeBases = useTenantState.use.knowledgeBases()
  const setSelectedTenant = useTenantState.use.setSelectedTenant()
  const setSelectedKB = useTenantState.use.setSelectedKB()
  const setTenants = useTenantState.use.setTenants()
  const setKnowledgeBases = useTenantState.use.setKnowledgeBases()

  useEffect(() => {
    // If tenant is already selected, skip initialization
    if (selectedTenant && selectedKB) {
      console.log('[TenantInit] Tenant and KB already selected, skipping auto-init')
      return
    }

    const initializeTenantContext = async () => {
      try {
        // Fetch list of available tenants
        const tenantsResponse = await fetchTenants()
        const availableTenants = tenantsResponse.tenants || []

        if (availableTenants.length === 0) {
          console.warn('[TenantInit] No tenants available')
          return
        }

        console.log('[TenantInit] Available tenants:', availableTenants)

        // Select first tenant if none selected
        if (!selectedTenant) {
          const firstTenant = availableTenants[0]
          console.log('[TenantInit] Auto-selecting first tenant:', firstTenant.tenant_id)
          setSelectedTenant(firstTenant)
          setTenants(availableTenants)

          // Fetch KBs for the first tenant
          try {
            const kbsResponse = await fetchKnowledgeBases(firstTenant.tenant_id)
            const availableKBs = kbsResponse.knowledge_bases || []
            console.log('[TenantInit] Available KBs:', availableKBs)

            // Auto-select first KB
            if (availableKBs.length > 0) {
              const firstKB = availableKBs[0]
              console.log('[TenantInit] Auto-selecting first KB:', firstKB.kb_id)
              setSelectedKB(firstKB)
              setKnowledgeBases(availableKBs)
            }
          } catch (error) {
            console.error('[TenantInit] Failed to fetch KBs:', error)
          }
        }
      } catch (error) {
        console.error('[TenantInit] Failed to initialize tenant context:', error)
      }
    }

    initializeTenantContext()
  }, [selectedTenant, selectedKB, setSelectedTenant, setSelectedKB])
}
```

### Integration Point

**File**: `/lightrag_webui/src/components/Root.tsx` (or main app component)

```typescript
import { useTenantInitialization } from '@/hooks/useTenantInitialization'

export function Root() {
  // Auto-initialize tenant on app load
  useTenantInitialization()

  return (
    // ... rest of component
  )
}
```

## Alternative Solutions (if auto-select not desired)

### Solution 2: Show Loading State Instead of Empty

**File**: `/lightrag_webui/src/api/lightrag.ts`

Modify `getDocuments()` to handle missing tenant context gracefully:

```typescript
export const getDocuments = async (): Promise<DocsStatusesResponse> => {
  // Check if tenant headers will be added
  const selectedTenantJson = localStorage.getItem('SELECTED_TENANT')
  const selectedKBJson = localStorage.getItem('SELECTED_KB')
  
  if (!selectedTenantJson || !selectedKBJson) {
    console.warn('[Documents] No tenant/KB selected, showing placeholder')
    return {
      statuses: {
        pending: [],
        processing: [],
        processed: [],
        failed: []
      }
    }
  }

  const response = await axiosInstance.get('/documents')
  return response.data
}
```

### Solution 3: Persist Tenant Selection Across Sessions

**File**: `/lightrag_webui/src/stores/tenant.ts` (Already Implemented!)

The code already has this:
```typescript
const getInitialTenant = (): Tenant | null => {
  const storedTenant = localStorage.getItem('SELECTED_TENANT')
  if (storedTenant) {
    return JSON.parse(storedTenant)
  }
  return null
}
```

**Enhancement**: Ensure this is called during app initialization:

```typescript
// In your App.tsx or Root component
useEffect(() => {
  useTenantState.getState().initializeFromStorage()
}, [])
```

### Solution 4: Lazy Load Documents Only When Tenant Selected

**File**: `/lightrag_webui/src/hooks/useDocuments.ts` (NEW)

```typescript
import { useState, useEffect } from 'react'
import { getDocuments } from '@/api/lightrag'
import { useTenantContext } from './useTenantContext'

/**
 * Hook that only fetches documents when tenant context is available
 */
export function useDocuments() {
  const [documents, setDocuments] = useState(null)
  const [loading, setLoading] = useState(false)
  const { tenantId, kbId } = useTenantContext()

  useEffect(() => {
    // Only fetch if tenant and KB are selected
    if (!tenantId || !kbId) {
      console.log('[useDocuments] Tenant/KB not selected, skipping fetch')
      setDocuments(null)
      return
    }

    const fetchDocuments = async () => {
      setLoading(true)
      try {
        const data = await getDocuments()
        setDocuments(data)
      } catch (error) {
        console.error('[useDocuments] Failed to fetch:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDocuments()
  }, [tenantId, kbId]) // Re-fetch when tenant/KB changes

  return { documents, loading }
}
```

## Recommended Approach

**✅ Solution 1: Auto-Select First Tenant/KB**

**Why**:
- User sees documents immediately on first load
- No confusing empty state
- Matches typical SaaS multi-tenant UX patterns
- Requires minimal changes (1 new hook + 1 line in Root component)
- Already have all infrastructure in place (tenant store, axios interceptor)

**Implementation**:
1. Create `useTenantInitialization` hook
2. Add to Root component
3. Axios interceptor will automatically add headers
4. API will receive tenant context
5. Documents visible on first load ✅

## Testing Checklist

- [ ] First visit to app: documents visible immediately
- [ ] Page refresh: documents still visible (from localStorage)
- [ ] Switch tenant: documents update to new tenant
- [ ] Switch KB: documents update to new KB
- [ ] No tenant available: graceful fallback (show empty state)
- [ ] Multiple tabs: consistent state across tabs

## Impact

- **Zero Breaking Changes**: Existing functionality unchanged
- **Better UX**: No confusing empty state on first load
- **Performance**: Marginal (one extra API call on first load)
- **Storage**: Uses existing localStorage infrastructure
