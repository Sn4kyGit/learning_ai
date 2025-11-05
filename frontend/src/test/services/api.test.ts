import { describe, it, expect, beforeEach, vi } from 'vitest'

// Mock stores before importing the API service
vi.mock('@/stores/auth', () => ({
  useAuthStore: () => ({
    token: 'test-token',
    logout: vi.fn()
  })
}))

vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: () => ({
    showError: vi.fn()
  })
}))

// Mock axios
vi.mock('axios', () => {
  const mockAxiosInstance = {
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    patch: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: {
        use: vi.fn()
      },
      response: {
        use: vi.fn()
      }
    }
  }
  
  return {
    default: {
      create: vi.fn(() => mockAxiosInstance)
    }
  }
})

describe('API Client', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('provides API client methods', async () => {
    const { apiClient } = await import('@/services/api')
    
    expect(typeof apiClient.get).toBe('function')
    expect(typeof apiClient.post).toBe('function')
    expect(typeof apiClient.put).toBe('function')
    expect(typeof apiClient.patch).toBe('function')
    expect(typeof apiClient.delete).toBe('function')
  })

  it('creates axios instance with correct config', async () => {
    const axios = await import('axios')
    await import('@/services/api')
    
    expect(axios.default.create).toHaveBeenCalledWith({
      baseURL: 'http://localhost:8000/api',
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json'
      }
    })
  })
})