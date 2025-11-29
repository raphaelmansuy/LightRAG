import { useEffect, useRef, useCallback } from 'react'
import { useTenantState } from '@/stores/tenant'
import { fetchTenants, fetchKnowledgeBases } from '@/api/tenant'
import type { Tenant, KnowledgeBase } from '@/stores/tenant'

/**
 * Hook to auto-initialize tenant and KB on first app load
 * Ensures that documents are visible even on initial page load
 * This solves the "empty state on refresh" issue by automatically
 * selecting the first available tenant and KB if none are currently selected
 */
export function useTenantInitialization() {
  const selectedTenant = useTenantState.use.selectedTenant()
  const selectedKB = useTenantState.use.selectedKB()
  const setSelectedTenant = useTenantState.use.setSelectedTenant()
  const setSelectedKB = useTenantState.use.setSelectedKB()
  const setTenants = useTenantState.use.setTenants()
  const setKnowledgeBases = useTenantState.use.setKnowledgeBases()
  const setLoading = useTenantState.use.setLoading()
  const setError = useTenantState.use.setError()

  const initializationAttempted = useRef(false)

  const initializeTenantContext = useCallback(async () => {
    try {
      setLoading(true)
      setError(null)

      // Fetch list of available tenants
      console.log('[TenantInit] Fetching available tenants...')
      const availableTenants: Tenant[] = await fetchTenants()

      if (availableTenants.length === 0) {
        console.warn('[TenantInit] No tenants available')
        setError('No tenants available')
        setLoading(false)
        return
      }

      console.log(
        '[TenantInit] Available tenants:',
        availableTenants.map((t) => t.tenant_id)
      )
      setTenants(availableTenants)

      // Select first tenant if none selected
      if (!selectedTenant) {
        const firstTenant = availableTenants[0]
        console.log('[TenantInit] Auto-selecting first tenant:', firstTenant.tenant_id)
        setSelectedTenant(firstTenant)

        // Fetch KBs for the first tenant
        try {
          console.log(
            '[TenantInit] Fetching knowledge bases for tenant:',
            firstTenant.tenant_id
          )
          const availableKBs: KnowledgeBase[] = await fetchKnowledgeBases(
            firstTenant.tenant_id
          )
          console.log('[TenantInit] Available KBs:', availableKBs.map((kb) => kb.kb_id))
          setKnowledgeBases(availableKBs)

          // Auto-select first KB
          if (availableKBs.length > 0) {
            const firstKB = availableKBs[0]
            console.log('[TenantInit] Auto-selecting first KB:', firstKB.kb_id)
            setSelectedKB(firstKB)
            console.log('[TenantInit] Initialization complete! Tenant and KB selected.')
          } else {
            console.warn('[TenantInit] No knowledge bases available for tenant')
            setError('No knowledge bases available')
          }
        } catch (error) {
          console.error('[TenantInit] Failed to fetch KBs:', error)
          setError('Failed to fetch knowledge bases')
        }
      }

      setLoading(false)
    } catch (error) {
      console.error('[TenantInit] Failed to initialize tenant context:', error)
      setError(error instanceof Error ? error.message : 'Failed to initialize tenant context')
      setLoading(false)
    }
  }, [selectedTenant, setError, setKnowledgeBases, setLoading, setSelectedKB, setSelectedTenant, setTenants])

  useEffect(() => {
    // Prevent double initialization in strict mode
    if (initializationAttempted.current) {
      return
    }

    // If tenant and KB are already selected, skip initialization
    if (selectedTenant && selectedKB) {
      console.log('[TenantInit] Tenant and KB already selected, skipping auto-init', {
        tenant: selectedTenant.tenant_id,
        kb: selectedKB.kb_id,
      })
      return
    }

    initializationAttempted.current = true
    initializeTenantContext()
  }, [initializeTenantContext, selectedTenant, selectedKB])
}
