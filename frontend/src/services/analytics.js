import { apiClient } from './api'

export const analyticsService = {
  async getDashboardData(businessId) {
    const response = await apiClient.get(`/analytics/${businessId}/dashboard`)
    return response.data
  },

  async getTrends(businessId, days = 30) {
    const response = await apiClient.get(`/analytics/${businessId}/trends`, {
      params: { days }
    })
    return response.data
  },

  async getBusinessScore(businessId) {
    const response = await apiClient.get(`/analytics/${businessId}/score`)
    return response.data
  },

  async getSentimentAnalysis(businessId, period = '30d') {
    const response = await apiClient.get(`/analytics/${businessId}/sentiment`, {
      params: { period }
    })
    return response.data
  },

  async getTopicAnalysis(businessId, period = '30d') {
    const response = await apiClient.get(`/analytics/${businessId}/topics`, {
      params: { period }
    })
    return response.data
  },

  async getCompetitorAnalysis(businessId) {
    const response = await apiClient.get(`/analytics/${businessId}/competitors`)
    return response.data
  },

  async getPerformanceMetrics(businessId, startDate, endDate) {
    const response = await apiClient.get(`/analytics/${businessId}/performance`, {
      params: { start_date: startDate, end_date: endDate }
    })
    return response.data
  },

  async exportReport(businessId, reportType, format = 'pdf') {
    const response = await apiClient.get(`/analytics/${businessId}/export`, {
      params: { type: reportType, format },
      responseType: 'blob'
    })
    return response.data
  },

  async getCostSummary(businessId) {
    const response = await apiClient.get(`/analytics/${businessId}/costs`)
    return response.data
  }
}