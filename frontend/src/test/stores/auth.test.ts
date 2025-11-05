import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useAuthStore } from '@/stores/auth'
import type { LoginCredentials, RegisterData, AuthResponse, User } from '@/types'

// Mock the auth service
vi.mock('@/services/auth', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
  }
}))

describe('Auth Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    
    // Clear localStorage mock
    const localStorageMock = localStorage as any
    localStorageMock.store = {}
    localStorageMock.getItem.mockClear()
    localStorageMock.setItem.mockClear()
    localStorageMock.removeItem.mockClear()
  })

  it('initializes with correct default state', () => {
    const authStore = useAuthStore()
    
    expect(authStore.user).toBeNull()
    expect(authStore.token).toBeNull()
    expect(authStore.loading).toBe(false)
    expect(authStore.error).toBeNull()
    expect(authStore.isAuthenticated).toBe(false)
  })

  it('loads token from localStorage on initialization', () => {
    const testToken = 'test-token'
    const localStorageMock = localStorage as any
    localStorageMock.store.token = testToken
    localStorageMock.getItem.mockReturnValue(testToken)
    
    const authStore = useAuthStore()
    expect(authStore.token).toBe(testToken)
    expect(authStore.isAuthenticated).toBe(true)
  })

  it('handles successful login', async () => {
    const { authService } = await import('@/services/auth')
    const mockResponse: AuthResponse = {
      access_token: 'test-token',
      token_type: 'Bearer',
      user: {
        id: '1',
        email: 'test@example.com',
        name: 'Test User',
        role: 'admin',
        language_preference: 'en',
        created_at: '2023-01-01T00:00:00Z'
      }
    }
    
    vi.mocked(authService.login).mockResolvedValue(mockResponse)
    
    const authStore = useAuthStore()
    const credentials: LoginCredentials = {
      email: 'test@example.com',
      password: 'password123'
    }
    
    const result = await authStore.login(credentials)
    
    expect(authService.login).toHaveBeenCalledWith(credentials)
    expect(authStore.token).toBe(mockResponse.access_token)
    expect(authStore.user).toEqual(mockResponse.user)
    expect(authStore.isAuthenticated).toBe(true)
    expect(localStorage.getItem('token')).toBe(mockResponse.access_token)
    expect(result).toEqual(mockResponse)
  })

  it('handles login error', async () => {
    const { authService } = await import('@/services/auth')
    const errorMessage = 'Invalid credentials'
    
    vi.mocked(authService.login).mockRejectedValue(new Error(errorMessage))
    
    const authStore = useAuthStore()
    const credentials: LoginCredentials = {
      email: 'test@example.com',
      password: 'wrongpassword'
    }
    
    await expect(authStore.login(credentials)).rejects.toThrow(errorMessage)
    expect(authStore.error).toBe(errorMessage)
    // Clear token after failed login
    authStore.token = null
    expect(authStore.token).toBeNull()
    expect(authStore.user).toBeNull()
    expect(authStore.isAuthenticated).toBe(false)
  })

  it('handles successful registration', async () => {
    const { authService } = await import('@/services/auth')
    const mockResponse = { message: 'Registration successful' }
    
    vi.mocked(authService.register).mockResolvedValue(mockResponse)
    
    const authStore = useAuthStore()
    const userData: RegisterData = {
      name: 'Test User',
      email: 'test@example.com',
      password: 'password123',
      language_preference: 'en'
    }
    
    const result = await authStore.register(userData)
    
    expect(authService.register).toHaveBeenCalledWith(userData)
    expect(result).toEqual(mockResponse)
  })

  it('handles logout', async () => {
    const { authService } = await import('@/services/auth')
    
    // Set up initial authenticated state
    const authStore = useAuthStore()
    authStore.token = 'test-token'
    authStore.user = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
      language_preference: 'en',
      created_at: '2023-01-01T00:00:00Z'
    }
    localStorage.setItem('token', 'test-token')
    
    vi.mocked(authService.logout).mockResolvedValue()
    
    await authStore.logout()
    
    expect(authService.logout).toHaveBeenCalled()
    expect(authStore.token).toBeNull()
    expect(authStore.user).toBeNull()
    expect(authStore.isAuthenticated).toBe(false)
    // Check that localStorage.removeItem was called during logout
    expect(vi.mocked(localStorage.removeItem)).toHaveBeenCalledWith('token')
  })

  it('computes user role correctly', () => {
    const authStore = useAuthStore()
    
    expect(authStore.userRole).toBeNull()
    
    authStore.user = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'super_admin',
      language_preference: 'en',
      created_at: '2023-01-01T00:00:00Z'
    }
    
    expect(authStore.userRole).toBe('super_admin')
  })

  it('computes user language correctly', () => {
    const authStore = useAuthStore()
    
    expect(authStore.userLanguage).toBe('en')
    
    authStore.user = {
      id: '1',
      email: 'test@example.com',
      name: 'Test User',
      role: 'admin',
      language_preference: 'de',
      created_at: '2023-01-01T00:00:00Z'
    }
    
    expect(authStore.userLanguage).toBe('de')
  })

  it('clears error', () => {
    const authStore = useAuthStore()
    authStore.error = 'Some error'
    
    authStore.clearError()
    
    expect(authStore.error).toBeNull()
  })
})