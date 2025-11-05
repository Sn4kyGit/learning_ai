import axios, { AxiosInstance, AxiosRequestConfig, AxiosResponse } from 'axios'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

// Create axios instance
const api: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api',
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    const authStore = useAuthStore()
    if (authStore.token) {
      config.headers.Authorization = `Bearer ${authStore.token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor for error handling
api.interceptors.response.use(
  (response) => {
    return response
  },
  (error) => {
    const authStore = useAuthStore()
    const notificationsStore = useNotificationsStore()
    
    if (error.response?.status === 401) {
      // Unauthorized - clear auth and redirect to login
      authStore.logout()
      window.location.href = '/login'
    } else if (error.response?.status === 403) {
      // Forbidden
      notificationsStore.showError('You do not have permission to perform this action')
    } else if (error.response?.status >= 500) {
      // Server error
      notificationsStore.showError('Server error. Please try again later.')
    } else if (error.code === 'ECONNABORTED') {
      // Timeout
      notificationsStore.showError('Request timeout. Please check your connection.')
    }
    
    return Promise.reject(error)
  }
)

// API helper methods
export const apiClient = {
  get: <T = any>(url: string, config: AxiosRequestConfig = {}): Promise<AxiosResponse<T>> => 
    api.get(url, config),
  post: <T = any>(url: string, data: any = {}, config: AxiosRequestConfig = {}): Promise<AxiosResponse<T>> => 
    api.post(url, data, config),
  put: <T = any>(url: string, data: any = {}, config: AxiosRequestConfig = {}): Promise<AxiosResponse<T>> => 
    api.put(url, data, config),
  patch: <T = any>(url: string, data: any = {}, config: AxiosRequestConfig = {}): Promise<AxiosResponse<T>> => 
    api.patch(url, data, config),
  delete: <T = any>(url: string, config: AxiosRequestConfig = {}): Promise<AxiosResponse<T>> => 
    api.delete(url, config)
}

export default api