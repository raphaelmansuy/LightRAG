import { useEffect } from 'react'
import { useTenantState } from '@/stores/tenant'
import { fetchTenantsPaginated, fetchKnowledgeBasesPaginated } from '@/api/tenant'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/Select'
import Button from '@/components/ui/Button'
import { PlusIcon, Building2, ArrowRightLeft } from 'lucide-react'

interface TenantSelectorProps {
  onTenantChange?: () => void
  onKBChange?: () => void
  hideTenantSelect?: boolean
  hideKBSelect?: boolean
}

export function TenantSelector({ onTenantChange, onKBChange, hideTenantSelect = false, hideKBSelect = false }: TenantSelectorProps) {
  const selectedTenant = useTenantState.use.selectedTenant()
  const selectedKB = useTenantState.use.selectedKB()
  const tenants = useTenantState.use.tenants()
  const knowledgeBases = useTenantState.use.knowledgeBases()
  const loading = useTenantState.use.loading()
  const error = useTenantState.use.error()

  const setSelectedTenant = useTenantState.use.setSelectedTenant()
  const setSelectedKB = useTenantState.use.setSelectedKB()
  const setTenants = useTenantState.use.setTenants()
  const setKnowledgeBases = useTenantState.use.setKnowledgeBases()
  const setLoading = useTenantState.use.setLoading()
  const setError = useTenantState.use.setError()
  const initializeFromStorage = useTenantState.use.initializeFromStorage()
  const clearTenantSelection = useTenantState.use.clearTenantSelection()

  // Pagination settings
  const tenantPageSize = 5
  const kbPageSize = 5

  // Initialize from storage on mount
  useEffect(() => {
    initializeFromStorage()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load tenants on mount with pagination
  useEffect(() => {
    const loadTenants = async () => {
      setLoading(true)
      try {
        console.log('TenantSelector: Loading tenants...')
        const data = await fetchTenantsPaginated(1, tenantPageSize)
        console.log('TenantSelector: Loaded tenants:', data)
        setTenants(data.items)

        // If no tenant selected but we have tenants, auto-select first one
        if (!selectedTenant && data.items.length > 0) {
          console.log('TenantSelector: Auto-selecting first tenant:', data.items[0])
          setSelectedTenant(data.items[0])
        }
      } catch (err) {
        console.error('TenantSelector: Error loading tenants:', err)
        setError(err instanceof Error ? err.message : 'Failed to load tenants')
      } finally {
        setLoading(false)
      }
    }

    loadTenants()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // Load knowledge bases when tenant changes with pagination
  useEffect(() => {
    if (!selectedTenant) {
      setKnowledgeBases([])
      setSelectedKB(null)
      return
    }

    const loadKBs = async () => {
      setLoading(true)
      try {
        console.log('TenantSelector: Loading KBs for tenant:', selectedTenant.tenant_id)
        const data = await fetchKnowledgeBasesPaginated(selectedTenant.tenant_id, 1, kbPageSize)
        console.log('TenantSelector: Loaded KBs:', data)
        setKnowledgeBases(data.items)

        // If no KB selected but we have KBs, auto-select first one
        if (!selectedKB && data.items.length > 0) {
          console.log('TenantSelector: Auto-selecting first KB:', data.items[0])
          setSelectedKB(data.items[0])
        } else if (selectedKB && !data.items.find(kb => kb.kb_id === selectedKB.kb_id)) {
          // Clear KB if it no longer exists
          console.log('TenantSelector: KB no longer exists, clearing selection')
          setSelectedKB(null)
        }
      } catch (err) {
        console.error('TenantSelector: Error loading KBs:', err)
        setError(err instanceof Error ? err.message : 'Failed to load knowledge bases')
      } finally {
        setLoading(false)
      }
    }

    loadKBs()
    onTenantChange?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedTenant?.tenant_id])

  // Notify KB change
  useEffect(() => {
    onKBChange?.()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedKB?.kb_id])

  if (loading && tenants.length === 0) {
    return <div className="text-sm text-muted-foreground">Loading tenants...</div>
  }

  if (error && tenants.length === 0) {
    return <div className="text-sm text-destructive">{error}</div>
  }

  return (
    <div className="flex items-center gap-3 px-3 py-2 bg-muted/50 rounded-lg">
      {/* Tenant Selector */}
      {!hideTenantSelect ? (
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-muted-foreground">Tenant</label>
          <div className="flex gap-2 items-center">
            <Select
              value={selectedTenant?.tenant_id || ''}
              onValueChange={(value) => {
                const tenant = tenants.find(t => t.tenant_id === value)
                if (tenant) setSelectedTenant(tenant)
              }}
              disabled={loading || tenants.length === 0}
            >
              <SelectTrigger className="h-8 text-xs w-40">
                <SelectValue placeholder="Select tenant..." />
              </SelectTrigger>
              <SelectContent>
                {tenants.map(tenant => (
                  <SelectItem key={tenant.tenant_id} value={tenant.tenant_id}>
                    {tenant.name || tenant.tenant_name || tenant.tenant_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0 opacity-50 cursor-not-allowed"
              disabled
              title="Create new tenant (coming soon)"
            >
              <PlusIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      ) : (
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-muted-foreground">Tenant</label>
          <div className="flex gap-2 items-center h-8">
             <Building2 className="h-4 w-4 text-muted-foreground" />
             <span className="text-sm font-medium truncate max-w-[120px]" title={selectedTenant?.tenant_name}>
                {selectedTenant?.tenant_name || 'No Tenant'}
             </span>
             <Button 
                size="sm"
                variant="ghost" 
                className="h-6 w-6 ml-1 p-0" 
                onClick={() => clearTenantSelection()}
                title="Switch Tenant"
             >
                <ArrowRightLeft className="h-3 w-3" />
             </Button>
          </div>
        </div>
      )}

      {/* Divider - only show if KB selector is visible */}
      {!hideKBSelect && selectedTenant && (
        <div className="w-px h-12 bg-border/50" />
      )}

      {/* Knowledge Base Selector - hide if hideKBSelect is true */}
      {!hideKBSelect && selectedTenant && (
        <div className="flex flex-col gap-1">
          <label className="text-xs font-semibold text-muted-foreground">Knowledge Base</label>
          <div className="flex gap-2 items-center">
            <Select
              value={selectedKB?.kb_id || ''}
              onValueChange={(value) => {
                const kb = knowledgeBases.find(k => k.kb_id === value)
                if (kb) setSelectedKB(kb)
              }}
              disabled={loading || knowledgeBases.length === 0}
            >
              <SelectTrigger className="h-8 text-xs w-40">
                <SelectValue placeholder="Select KB..." />
              </SelectTrigger>
              <SelectContent>
                {knowledgeBases.map(kb => (
                  <SelectItem key={kb.kb_id} value={kb.kb_id}>
                    {kb.name || kb.kb_name || kb.kb_id}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              size="sm"
              variant="ghost"
              className="h-8 w-8 p-0 opacity-50 cursor-not-allowed"
              disabled
              title="Create new knowledge base (coming soon)"
            >
              <PlusIcon className="h-4 w-4" />
            </Button>
          </div>
        </div>
      )}

      {/* Selection Info - only show if KB selector is visible */}
      {!hideKBSelect && selectedTenant && selectedKB && (
        <div className="text-xs text-muted-foreground ml-2 px-2 py-1 bg-background rounded">
          {knowledgeBases.find(kb => kb.kb_id === selectedKB.kb_id)?.num_documents || 0} docs
        </div>
      )}
    </div>
  )
}

export default TenantSelector
