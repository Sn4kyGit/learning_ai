import { apiClient } from './api'

export const businessService = {
  async getBusinesses() {
    const response = await apiClient.get('/businesses')
    return response.data
  },

  async getBusiness(businessId) {
    const response = await apiClient.get(`/businesses/${businessId}`)
    return response.data
  },

  async createBusiness(businessData) {
    const response = await apiClient.post('/businesses', businessData)
    return response.data
  },

  async updateBusiness(businessId, updates) {
    const response = await apiClient.put(`/businesses/${businessId}`, updates)
    return response.data
  },

  async deleteBusiness(businessId) {
    const response = await apiClient.delete(`/businesses/${businessId}`)
    return response.data
  },

  async importReviews(businessId) {
    const response = await apiClient.post(`/businesses/${businessId}/import-reviews`)
    return response.data
  },

  async getBusinessStats(businessId) {
    const response = await apiClient.get(`/businesses/${businessId}/stats`)
    return response.data
  },

  async searchPlaces(query) {
    const response = await apiClient.get('/businesses/search-places', {
      params: { query }
    })
    return response.data
  }
}