import { apiClient } from './api'
import type {
  User,
  UserBusinessAccess,
  OrganizationUser,
  BulkAccessRequest
} from '@/types'

export class UserManagementService {
  /**
   * Grant user access to a business
   */
  async grantBusinessAccess(
    userId: string,
    businessId: string,
    permissionLevel: 'read_only' | 'full_access'
  ): Promise<void> {
    await apiClient.post(`/users/${userId}/business-access`, {
      business_id: businessId,
      permission_level: permissionLevel
    })
  }

  /**
   * Revoke user access to a business
   */
  async revokeBusinessAccess(userId: string, businessId: string): Promise<void> {
    await apiClient.delete(`/users/${userId}/business-access/${businessId}`)
  }

  /**
   * Update user's permission level for a business
   */
  async updateBusinessAccess(
    userId: string,
    businessId: string,
    permissionLevel: 'read_only' | 'full_access'
  ): Promise<void> {
    await apiClient.put(`/users/${userId}/business-access/${businessId}`, {
      permission_level: permissionLevel
    })
  }

  /**
   * Get all users with access to a business
   */
  async getBusinessUsers(businessId: string): Promise<UserBusinessAccess[]> {
    const response = await apiClient.get<UserBusinessAccess[]>(
      `/businesses/${businessId}/users`
    )
    return response.data
  }

  /**
   * Get all businesses accessible to a user
   */
  async getUserBusinesses(userId: string): Promise<UserBusinessAccess[]> {
    const response = await apiClient.get<UserBusinessAccess[]>(
      `/users/${userId}/businesses`
    )
    return response.data
  }

  /**
   * Get all users in an organization
   */
  async getOrganizationUsers(organizationId: string): Promise<OrganizationUser[]> {
    const response = await apiClient.get<OrganizationUser[]>(
      `/organizations/${organizationId}/users`
    )
    return response.data
  }

  /**
   * Bulk grant organization access to a business
   */
  async bulkGrantOrganizationAccess(
    organizationId: string,
    businessId: string,
    permissionLevel: 'read_only' | 'full_access'
  ): Promise<{ granted_count: number }> {
    const response = await apiClient.post(
      `/organizations/${organizationId}/bulk-access`,
      {
        business_id: businessId,
        permission_level: permissionLevel
      }
    )
    return response.data
  }

  /**
   * Bulk grant access to multiple users
   */
  async bulkGrantAccess(request: BulkAccessRequest): Promise<{ granted_count: number }> {
    const response = await apiClient.post('/users/bulk-access', request)
    return response.data
  }

  /**
   * Get all users (Super-Admin only)
   */
  async getAllUsers(
    skip: number = 0,
    limit: number = 50,
    search?: string
  ): Promise<{ users: User[]; total: number }> {
    const response = await apiClient.get('/users', {
      params: { skip, limit, search }
    })
    return response.data
  }

  /**
   * Create new user (Super-Admin only)
   */
  async createUser(userData: {
    email: string
    name: string
    role: 'admin' | 'viewer'
    language_preference?: string
    organization_id?: string
  }): Promise<User> {
    const response = await apiClient.post<User>('/users', userData)
    return response.data
  }

  /**
   * Update user (Super-Admin only)
   */
  async updateUser(
    userId: string,
    userData: Partial<{
      name: string
      role: 'admin' | 'viewer'
      language_preference: string
      organization_id: string
    }>
  ): Promise<User> {
    const response = await apiClient.put<User>(`/users/${userId}`, userData)
    return response.data
  }

  /**
   * Delete user (Super-Admin only)
   */
  async deleteUser(userId: string): Promise<void> {
    await apiClient.delete(`/users/${userId}`)
  }

  /**
   * Get user details
   */
  async getUser(userId: string): Promise<User> {
    const response = await apiClient.get<User>(`/users/${userId}`)
    return response.data
  }

  /**
   * Update user profile (own profile)
   */
  async updateProfile(userData: {
    name?: string
    language_preference?: string
  }): Promise<User> {
    const response = await apiClient.put<User>('/users/profile', userData)
    return response.data
  }

  /**
   * Change password
   */
  async changePassword(currentPassword: string, newPassword: string): Promise<void> {
    await apiClient.post('/users/change-password', {
      current_password: currentPassword,
      new_password: newPassword
    })
  }
}

export const userManagementService = new UserManagementService()