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
  
  if (selectedTenantJson) {
    try {
      const selectedTenant = JSON.parse(selectedTenantJson);
      if (selectedTenant?.tenant_id) {
        config.headers['X-Tenant-ID'] = selectedTenant.tenant_id;
      }
    } catch (e) {
      console.error('[Axios Interceptor] Failed to parse selected tenant from localStorage:', e);
    }
  }

  if (selectedKBJson) {
    try {
      const selectedKB = JSON.parse(selectedKBJson);
      if (selectedKB?.kb_id) {
        config.headers['X-KB-ID'] = selectedKB.kb_id;
      }
    } catch (e) {
      console.error('[Axios Interceptor] Failed to parse selected KB from localStorage:', e);
    }
  }

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
