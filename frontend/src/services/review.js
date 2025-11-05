import { apiClient } from './api'

export const reviewService = {
  async getReviews(businessId, params = {}) {
    const response = await apiClient.get(`/reviews/${businessId}`, { params })
    return response.data
  },

  async getReview(reviewId) {
    const response = await apiClient.get(`/reviews/detail/${reviewId}`)
    return response.data
  },

  async classifyReviews(businessId, reviews) {
    const response = await apiClient.post('/reviews/classify', {
      business_id: businessId,
      reviews
    })
    return response.data
  },

  async getClassifications(businessId, filters = {}) {
    const response = await apiClient.get(`/reviews/${businessId}/classifications`, {
      params: filters
    })
    return response.data
  },

  async getCriticalReviews(businessId, hoursBack = 24) {
    const response = await apiClient.get(`/reviews/${businessId}/critical`, {
      params: { hours_back: hoursBack }
    })
    return response.data
  },

  async getSentimentDistribution(businessId) {
    const response = await apiClient.get(`/reviews/${businessId}/sentiment`)
    return response.data
  },

  async getTopicAnalysis(businessId) {
    const response = await apiClient.get(`/reviews/${businessId}/topics`)
    return response.data
  },

  async markReviewAsHandled(reviewId) {
    const response = await apiClient.patch(`/reviews/${reviewId}/handled`)
    return response.data
  },

  async addReviewResponse(reviewId, responseText) {
    const response = await apiClient.post(`/reviews/${reviewId}/response`, {
      response: responseText
    })
    return response.data
  }
}