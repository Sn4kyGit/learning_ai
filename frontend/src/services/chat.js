import { apiClient } from './api'

export const chatService = {
  async sendMessage(businessId, message, conversationId = null, language = 'en') {
    const response = await apiClient.post(`/chat/${businessId}`, {
      message,
      language
    }, {
      params: conversationId ? { conversation_id: conversationId } : {}
    })
    return response.data
  },

  async getConversations(businessId, skip = 0, limit = 50) {
    const response = await apiClient.get(`/chat/${businessId}/conversations`, {
      params: { skip, limit }
    })
    return response.data
  },

  async getConversationMessages(businessId, conversationId, skip = 0, limit = 100) {
    const response = await apiClient.get(`/chat/${businessId}/conversations/${conversationId}`, {
      params: { skip, limit }
    })
    return response.data
  },

  async deleteConversation(businessId, conversationId) {
    const response = await apiClient.delete(`/chat/${businessId}/conversations/${conversationId}`)
    return response.data
  },

  async clearConversationContext(businessId, conversationId) {
    const response = await apiClient.post(`/chat/${businessId}/conversations/${conversationId}/clear`)
    return response.data
  },

  async getBusinessContextSummary(businessId) {
    const response = await apiClient.get(`/chat/${businessId}/context-summary`)
    return response.data
  },

  async getChatUsageStats(businessId, days = 30) {
    const response = await apiClient.get(`/chat/usage-stats/${businessId}`, {
      params: { days }
    })
    return response.data
  }
}