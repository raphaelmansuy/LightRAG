import { useState, useEffect } from 'react'
import { fetchTenantsPaginated } from '@/api/tenant'
import { Tenant, useTenantState } from '@/stores/tenant'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/Card'
import Button from '@/components/ui/Button'
import Input from '@/components/ui/Input'
import { Loader2, Search, Building2 } from 'lucide-react'

interface TenantSelectionPageProps {
  onSelect: (tenant: Tenant) => void
}

export default function TenantSelectionPage({ onSelect }: TenantSelectionPageProps) {
  const [tenants, setTenants] = useState<Tenant[]>([])
  const [loading, setLoading] = useState(true)
  const [search, setSearch] = useState('')
  const [page, setPage] = useState(1)
  const [totalPages, setTotalPages] = useState(1)
  const [error, setError] = useState<string | null>(null)
  const setSelectedTenant = useTenantState.use.setSelectedTenant()

  const loadTenants = async () => {
    setLoading(true)
    setError(null)
    try {
      const response = await fetchTenantsPaginated(page, 12, search)
      setTenants(response.items)
      setTotalPages(response.total_pages)
    } catch (err) {
      console.error('Failed to load tenants', err)
      setError('Failed to load tenants. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    const timer = setTimeout(() => {
      loadTenants()
    }, 300)
    return () => clearTimeout(timer)
  }, [page, search])

  const handleSelect = (tenant: Tenant) => {
    // Set in store (which handles localStorage)
    setSelectedTenant(tenant)
    onSelect(tenant)
  }

  return (
    <div className="min-h-screen bg-background flex flex-col items-center justify-center p-4">
      <div className="w-full max-w-4xl space-y-8">
        <div className="text-center space-y-2">
          <h1 className="text-4xl font-bold tracking-tight">Welcome to LightRAG</h1>
          <p className="text-muted-foreground text-lg">Select a tenant to continue to the dashboard</p>
        </div>

        <div className="flex items-center space-x-2 max-w-md mx-auto">
          <div className="relative flex-1">
            <Search className="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
            <Input
              type="search"
              placeholder="Search tenants..."
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>
        </div>

        {error && (
          <div className="text-center text-destructive bg-destructive/10 p-4 rounded-md">
            {error}
            <Button variant="link" onClick={loadTenants} className="ml-2">Retry</Button>
          </div>
        )}

        {loading ? (
          <div className="flex justify-center py-12">
            <Loader2 className="h-8 w-8 animate-spin text-primary" />
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            {tenants.map((tenant) => (
              <Card 
                key={tenant.tenant_id} 
                className="cursor-pointer hover:border-primary transition-colors"
                onClick={() => handleSelect(tenant)}
              >
                <CardHeader className="pb-2">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-lg font-medium truncate" title={tenant.tenant_name}>
                      {tenant.tenant_name}
                    </CardTitle>
                    <Building2 className="h-4 w-4 text-muted-foreground" />
                  </div>
                  <CardDescription className="truncate" title={tenant.description}>
                    {tenant.description || 'No description'}
                  </CardDescription>
                </CardHeader>
                <CardContent>
                  <div className="text-xs text-muted-foreground space-y-1">
                    <div className="flex justify-between">
                      <span>Knowledge Bases:</span>
                      <span className="font-medium">{tenant.num_knowledge_bases || 0}</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Documents:</span>
                      <span className="font-medium">{tenant.num_documents || 0}</span>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
            
            {tenants.length === 0 && !loading && (
              <div className="col-span-full text-center py-12 text-muted-foreground">
                No tenants found matching your search.
              </div>
            )}
          </div>
        )}

        {totalPages > 1 && (
          <div className="flex justify-center space-x-2 mt-8">
            <Button 
              variant="outline" 
              disabled={page <= 1} 
              onClick={() => setPage(p => p - 1)}
            >
              Previous
            </Button>
            <div className="flex items-center px-4 text-sm">
              Page {page} of {totalPages}
            </div>
            <Button 
              variant="outline" 
              disabled={page >= totalPages} 
              onClick={() => setPage(p => p + 1)}
            >
              Next
            </Button>
          </div>
        )}
      </div>
    </div>
  )
}
