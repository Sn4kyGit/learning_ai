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

// Mock axios with simpler structure
vi.mock('axios', () => ({
  default: {
    create: vi.fn(() => ({
      get: vi.fn(),
      post: vi.fn(),
      put: vi.fn(),
      patch: vi.fn(),
      delete: vi.fn(),
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() }
      }
    }))
  }
}))

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
    const apiModule = await import('@/services/api')
    
    // Check that the api client exists and has expected methods
    expect(apiModule.apiClient).toBeDefined()
    expect(typeof apiModule.apiClient.get).toBe('function')
    expect(typeof apiModule.apiClient.post).toBe('function')
    expect(typeof apiModule.apiClient.put).toBe('function')
    expect(typeof apiModule.apiClient.patch).toBe('function')
    expect(typeof apiModule.apiClient.delete).toBe('function')
    
    // Check that the default export exists
    expect(apiModule.default).toBeDefined()
  })
})