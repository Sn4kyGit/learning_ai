import { apiClient } from './api'
import type {
  NotificationPreferences,
  NotificationPreferencesRequest,
  AlertThresholds,
  AlertThresholdsRequest,
  NotificationHistory
} from '@/types'

export class NotificationConfigService {
  /**
   * Set notification preferences for current user
   */
  async setNotificationPreferences(
    preferences: NotificationPreferencesRequest,
    businessId?: string
  ): Promise<NotificationPreferences> {
    const response = await apiClient.post<NotificationPreferences>(
      '/notifications/preferences',
      preferences,
      {
        params: businessId ? { business_id: businessId } : {}
      }
    )
    return response.data
  }

  /**
   * Get notification preferences for current user
   */
  async getNotificationPreferences(businessId?: string): Promise<NotificationPreferences | null> {
    try {
      const response = await apiClient.get<NotificationPreferences>(
        '/notifications/preferences',
        {
          params: businessId ? { business_id: businessId } : {}
        }
      )
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  /**
   * Update notification preferences for current user
   */
  async updateNotificationPreferences(
    preferences: NotificationPreferencesRequest,
    businessId?: string
  ): Promise<NotificationPreferences> {
    const response = await apiClient.put<NotificationPreferences>(
      '/notifications/preferences',
      preferences,
      {
        params: businessId ? { business_id: businessId } : {}
      }
    )
    return response.data
  }

  /**
   * Set alert thresholds for a business (Admin+ only)
   */
  async setAlertThresholds(
    businessId: string,
    thresholds: AlertThresholdsRequest
  ): Promise<AlertThresholds> {
    const response = await apiClient.post<AlertThresholds>(
      `/notifications/alert-thresholds/${businessId}`,
      thresholds
    )
    return response.data
  }

  /**
   * Get alert thresholds for a business
   */
  async getAlertThresholds(businessId: string): Promise<AlertThresholds | null> {
    try {
      const response = await apiClient.get<AlertThresholds>(
        `/notifications/alert-thresholds/${businessId}`
      )
      return response.data
    } catch (error: any) {
      if (error.response?.status === 404) {
        return null
      }
      throw error
    }
  }

  /**
   * Update alert thresholds for a business (Admin+ only)
   */
  async updateAlertThresholds(
    businessId: string,
    thresholds: AlertThresholdsRequest
  ): Promise<AlertThresholds> {
    const response = await apiClient.put<AlertThresholds>(
      `/notifications/alert-thresholds/${businessId}`,
      thresholds
    )
    return response.data
  }

  /**
   * Get notification history for current user
   */
  async getNotificationHistory(
    businessId?: string,
    skip: number = 0,
    limit: number = 50,
    alertType?: string
  ): Promise<NotificationHistory[]> {
    const response = await apiClient.get<NotificationHistory[]>(
      '/notifications/history',
      {
        params: {
          business_id: businessId,
          skip,
          limit,
          alert_type: alertType
        }
      }
    )
    return response.data
  }

  /**
   * Send test notification
   */
  async sendTestNotification(
    businessId: string,
    channel: 'email' | 'sms' | 'push' | 'in_app'
  ): Promise<{
    message: string
    channel: string
    recipient?: string
    status?: string
    sent_at?: string
  }> {
    const response = await apiClient.post(
      `/notifications/test/${businessId}`,
      {},
      {
        params: { channel }
      }
    )
    return response.data
  }

  /**
   * Get available notification channels
   */
  async getAvailableChannels(): Promise<{
    available_channels: string[]
    user_preferences: {
      email: string
      language: string
    }
  }> {
    const response = await apiClient.get('/notifications/channels')
    return response.data
  }
}

export const notificationConfigService = new NotificationConfigService()