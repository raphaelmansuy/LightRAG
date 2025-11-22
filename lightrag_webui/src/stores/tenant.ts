import { create } from 'zustand'
import { createSelectors } from '@/lib/utils'

export interface Tenant {
  tenant_id: string
  tenant_name?: string // For backward compatibility
  name?: string // From API response
  description?: string
  created_at?: string
  updated_at?: string
  num_knowledge_bases?: number
  num_documents?: number
  storage_used_gb?: number
}

export interface KnowledgeBase {
  kb_id: string
  tenant_id: string
  kb_name?: string // For backward compatibility
  name?: string // From API response
  description?: string
  created_at?: string
  updated_at?: string
  num_documents?: number
  num_entities?: number
  num_relations?: number
}

interface TenantState {
  // Multi-tenant context
  selectedTenant: Tenant | null
  selectedKB: KnowledgeBase | null
  tenants: Tenant[]
  knowledgeBases: KnowledgeBase[]
  loading: boolean
  error: string | null

  // Actions
  setSelectedTenant: (tenant: Tenant | null) => void
  setSelectedKB: (kb: KnowledgeBase | null) => void
  setTenants: (tenants: Tenant[]) => void
  setKnowledgeBases: (kbs: KnowledgeBase[]) => void
  setLoading: (loading: boolean) => void
  setError: (error: string | null) => void
  clearTenantSelection: () => void
  clearKBSelection: () => void
  initializeFromStorage: () => void
  persistSelection: () => void
}

const useTenantStateStoreBase = create<TenantState>()((set, get) => ({
  selectedTenant: null,
  selectedKB: null,
  tenants: [],
  knowledgeBases: [],
  loading: false,
  error: null,

  setSelectedTenant: (tenant) => {
    set({ selectedTenant: tenant, selectedKB: null })
    if (tenant) {
      localStorage.setItem('SELECTED_TENANT', JSON.stringify(tenant))
    } else {
      localStorage.removeItem('SELECTED_TENANT')
    }
  },

  setSelectedKB: (kb) => {
    set({ selectedKB: kb })
    if (kb) {
      localStorage.setItem('SELECTED_KB', JSON.stringify(kb))
    } else {
      localStorage.removeItem('SELECTED_KB')
    }
  },

  setTenants: (tenants) => set({ tenants }),

  setKnowledgeBases: (kbs) => set({ knowledgeBases: kbs }),

  setLoading: (loading) => set({ loading }),

  setError: (error) => set({ error }),

  clearTenantSelection: () => {
    set({ selectedTenant: null, selectedKB: null, knowledgeBases: [] })
    localStorage.removeItem('SELECTED_TENANT')
    localStorage.removeItem('SELECTED_KB')
  },

  clearKBSelection: () => {
    set({ selectedKB: null })
    localStorage.removeItem('SELECTED_KB')
  },

  initializeFromStorage: () => {
    const storedTenant = localStorage.getItem('SELECTED_TENANT')
    const storedKB = localStorage.getItem('SELECTED_KB')

    if (storedTenant) {
      try {
        set({ selectedTenant: JSON.parse(storedTenant) })
      } catch (e) {
        console.error('Failed to parse stored tenant', e)
      }
    }

    if (storedKB) {
      try {
        set({ selectedKB: JSON.parse(storedKB) })
      } catch (e) {
        console.error('Failed to parse stored KB', e)
      }
    }
  },

  persistSelection: () => {
    const state = get()
    if (state.selectedTenant) {
      localStorage.setItem('SELECTED_TENANT', JSON.stringify(state.selectedTenant))
    }
    if (state.selectedKB) {
      localStorage.setItem('SELECTED_KB', JSON.stringify(state.selectedKB))
    }
  },
}))

export const useTenantState = createSelectors(useTenantStateStoreBase)
