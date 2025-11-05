import { apiClient } from './api'

export const notificationService = {
  async getNotifications(skip = 0, limit = 50, unreadOnly = false) {
    const response = await apiClient.get('/notifications', {
      params: { skip, limit, unread_only: unreadOnly }
    })
    return response.data
  },

  async markAsRead(notificationId) {
    const response = await apiClient.patch(`/notifications/${notificationId}/read`)
    return response.data
  },

  async markAllAsRead() {
    const response = await apiClient.patch('/notifications/mark-all-read')
    return response.data
  },

  async deleteNotification(notificationId) {
    const response = await apiClient.delete(`/notifications/${notificationId}`)
    return response.data
  },

  async getNotificationPreferences(businessId) {
    const response = await apiClient.get(`/notifications/preferences/${businessId}`)
    return response.data
  },

  async updateNotificationPreferences(businessId, preferences) {
    const response = await apiClient.put(`/notifications/preferences/${businessId}`, preferences)
    return response.data
  },

  async getAlertSettings(businessId) {
    const response = await apiClient.get(`/notifications/alerts/${businessId}`)
    return response.data
  },

  async updateAlertSettings(businessId, settings) {
    const response = await apiClient.put(`/notifications/alerts/${businessId}`, settings)
    return response.data
  },

  async testNotification(businessId, type, channel) {
    const response = await apiClient.post(`/notifications/test/${businessId}`, {
      type,
      channel
    })
    return response.data
  }
}