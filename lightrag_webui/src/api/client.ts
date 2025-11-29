import axios, { AxiosError } from 'axios'
import { backendBaseUrl } from '@/lib/constants'
import { useSettingsStore } from '@/stores/settings'
import { navigationService } from '@/services/navigation'

// Axios instance
export const axiosInstance = axios.create({
  baseURL: backendBaseUrl,
  headers: {
    'Content-Type': 'application/json'
  }
})

// WUI-003 FIX: Endpoints that require tenant context
// These endpoints will be blocked if no tenant/KB is selected
const TENANT_REQUIRED_ENDPOINTS = [
  '/documents',
  '/query',
  '/graph',
  '/knowledge-bases',  // KB operations require tenant
]

// Endpoints that are exempt from tenant context check
const TENANT_EXEMPT_ENDPOINTS = [
  '/tenants',  // Tenant listing doesn't require tenant context
  '/login',
  '/health',
  '/version',
]

function requiresTenantContext(url: string | undefined): boolean {
  if (!url) return false
  
  // Check if exempt
  for (const exempt of TENANT_EXEMPT_ENDPOINTS) {
    if (url.includes(exempt)) return false
  }
  
  // Check if requires tenant
  for (const required of TENANT_REQUIRED_ENDPOINTS) {
    if (url.includes(required)) return true
  }
  
  return false
}

// Interceptor: add api key, authentication, and tenant context
axiosInstance.interceptors.request.use((config) => {
  const apiKey = useSettingsStore.getState().apiKey
  const token = localStorage.getItem('LIGHTRAG-API-TOKEN');

  // Always include token if it exists, regardless of path
  if (token) {
    config.headers['Authorization'] = `Bearer ${token}`
  }
  if (apiKey) {
    config.headers['X-API-Key'] = apiKey
  }

  // Add tenant context headers from localStorage
  // We read directly from localStorage to avoid circular dependencies with stores
  const selectedTenantJson = localStorage.getItem('SELECTED_TENANT');
  const selectedKBJson = localStorage.getItem('SELECTED_KB');
  
  let hasTenantContext = false;
  let hasKBContext = false;
  
  if (selectedTenantJson) {
    try {
      const selectedTenant = JSON.parse(selectedTenantJson);
      if (selectedTenant?.tenant_id) {
        config.headers['X-Tenant-ID'] = selectedTenant.tenant_id;
        hasTenantContext = true;
        console.log('[Axios Interceptor] Added X-Tenant-ID header:', selectedTenant.tenant_id);
      } else {
        console.warn('[Axios Interceptor] Tenant in localStorage has no tenant_id:', selectedTenant);
      }
    } catch (e) {
      console.error('[Axios Interceptor] Failed to parse selected tenant from localStorage:', e);
    }
  } else {
    console.warn('[Axios Interceptor] No SELECTED_TENANT in localStorage');
  }

  if (selectedKBJson) {
    try {
      const selectedKB = JSON.parse(selectedKBJson);
      if (selectedKB?.kb_id) {
        config.headers['X-KB-ID'] = selectedKB.kb_id;
        hasKBContext = true;
        console.log('[Axios Interceptor] Added X-KB-ID header:', selectedKB.kb_id);
      } else {
        console.warn('[Axios Interceptor] KB in localStorage has no kb_id:', selectedKB);
      }
    } catch (e) {
      console.error('[Axios Interceptor] Failed to parse selected KB from localStorage:', e);
    }
  } else {
    console.log('[Axios Interceptor] No SELECTED_KB in localStorage (ok for some requests)');
  }

  // WUI-003 FIX: Block requests to tenant-required endpoints without proper context
  if (requiresTenantContext(config.url) && (!hasTenantContext || !hasKBContext)) {
    console.error('[Axios Interceptor] Tenant context required but missing for:', config.url);
    throw new axios.Cancel('Please select a tenant and knowledge base before performing this action.');
  }

  console.log('[Axios Interceptor] Request headers:', {
    url: config.url,
    method: config.method,
    'X-Tenant-ID': config.headers['X-Tenant-ID'],
    'X-KB-ID': config.headers['X-KB-ID'],
    'Authorization': config.headers['Authorization'] ? 'EXISTS' : 'MISSING'
  });

  return config
})

// Interceptor: handle error
axiosInstance.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response) {
      if (error.response?.status === 401) {
        // For login API, throw error directly
        if (error.config?.url?.includes('/login')) {
          throw error;
        }
        // For other APIs, navigate to login page
        navigationService.navigateToLogin();

        // return a reject Promise
        return Promise.reject(new Error('Authentication required'));
      }
      // Don't throw here, let the caller handle specific status codes if needed
      // or throw a standardized error
    }
    throw error
  }
)
