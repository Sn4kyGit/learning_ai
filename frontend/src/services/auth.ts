import { apiClient } from './api'
import type { LoginCredentials, RegisterData, AuthResponse, User } from '@/types'

export const authService = {
  async login(credentials: LoginCredentials): Promise<AuthResponse> {
    const response = await apiClient.post<AuthResponse>('/auth/login', credentials)
    return response.data
  },

  async register(userData: RegisterData) {
    const response = await apiClient.post('/auth/register', userData)
    return response.data
  },

  async logout(): Promise<void> {
    try {
      await apiClient.post('/auth/logout')
    } catch (error) {
      // Ignore logout errors - token will be cleared anyway
      console.warn('Logout request failed:', error)
    }
  },

  async getCurrentUser(): Promise<User> {
    const response = await apiClient.get<User>('/auth/me')
    return response.data
  },

  async refreshToken() {
    const response = await apiClient.post('/auth/refresh')
    return response.data
  },

  async changePassword(passwordData: { current_password: string; new_password: string }) {
    const response = await apiClient.post('/auth/change-password', passwordData)
    return response.data
  },

  async requestPasswordReset(email: string) {
    const response = await apiClient.post('/auth/forgot-password', { email })
    return response.data
  },

  async resetPassword(resetData: { token: string; password: string }) {
    const response = await apiClient.post('/auth/reset-password', resetData)
    return response.data
  },

  async updateProfile(profileData: Partial<User>) {
    const response = await apiClient.put<User>('/auth/profile', profileData)
    return response.data
  }
}