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

// Endpoints that require Tenant ID but NOT KB ID
const TENANT_ONLY_ENDPOINTS = [
  '/knowledge-bases',
]

// Endpoints that require BOTH Tenant ID and KB ID
const KB_REQUIRED_ENDPOINTS = [
  '/documents',
  '/query',
  '/graph',
]

// Endpoints that are exempt from any context check
const EXEMPT_ENDPOINTS = [
  '/tenants',
  '/login',
  '/health',
  '/version',
  '/auth-status',
]

type ContextRequirement = 'none' | 'tenant' | 'kb'

function getContextRequirement(url: string | undefined): ContextRequirement {
  if (!url) return 'none'
  
  // Check if exempt
  for (const exempt of EXEMPT_ENDPOINTS) {
    if (url.includes(exempt)) return 'none'
  }
  
  // Check if requires KB (which implies Tenant)
  for (const required of KB_REQUIRED_ENDPOINTS) {
    if (url.includes(required)) return 'kb'
  }

  // Check if requires Tenant only
  for (const required of TENANT_ONLY_ENDPOINTS) {
    if (url.includes(required)) return 'tenant'
  }
  
  return 'none'
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
  const requirement = getContextRequirement(config.url);
  
  if (requirement === 'kb') {
    if (!hasTenantContext || !hasKBContext) {
      console.error('[Axios Interceptor] KB context required but missing for:', config.url);
      throw new axios.Cancel('Please select a tenant and knowledge base before performing this action.');
    }
  } else if (requirement === 'tenant') {
    if (!hasTenantContext) {
      console.error('[Axios Interceptor] Tenant context required but missing for:', config.url);
      throw new axios.Cancel('Please select a tenant before performing this action.');
    }
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

        // Clear stored auth + tenant context to force re-login
        try {
          localStorage.removeItem('LIGHTRAG-API-TOKEN');
          localStorage.removeItem('SELECTED_TENANT');
          localStorage.removeItem('SELECTED_KB');
        } catch (e) {
          console.warn('[axios interceptor] Failed to clear localStorage on 401', e)
        }

        // Update auth state (if store available) and navigate to login
        try {
          // Importing the store lazily to avoid circular deps in build
          // eslint-disable-next-line @typescript-eslint/no-var-requires
          const authStore = require('@/stores/state').useAuthStore
          if (authStore && authStore.getState) {
            authStore.getState().logout()
          }
        } catch (e) {
          console.debug('[axios interceptor] Could not access auth store to logout', e)
        }

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
