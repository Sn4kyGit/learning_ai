import { apiClient } from './api'
import type { 
  Business, 
  BusinessFormData, 
  GooglePlacesSearchResponse, 
  ImportStatus,
  RealTimeImportStatus 
} from '@/types'

export const businessService = {
  async getBusinesses(): Promise<Business[]> {
    const response = await apiClient.get('/businesses')
    return response.data
  },

  async getBusiness(businessId: string): Promise<Business> {
    const response = await apiClient.get(`/businesses/${businessId}`)
    return response.data
  },

  async createBusiness(businessData: BusinessFormData): Promise<Business> {
    const response = await apiClient.post('/businesses', businessData)
    return response.data
  },

  async updateBusiness(businessId: string, updates: Partial<BusinessFormData>): Promise<Business> {
    const response = await apiClient.put(`/businesses/${businessId}`, updates)
    return response.data
  },

  async deleteBusiness(businessId: string): Promise<void> {
    const response = await apiClient.delete(`/businesses/${businessId}`)
    return response.data
  },

  async importReviews(businessId: string, options: any = {}): Promise<any> {
    const response = await apiClient.post(`/businesses/${businessId}/import-reviews`, options)
    return response.data
  },

  async getBusinessStats(businessId: string): Promise<any> {
    const response = await apiClient.get(`/businesses/${businessId}/stats`)
    return response.data
  },

  async getConsolidatedStats(businessIds: string[] = []): Promise<any> {
    const params = businessIds.length > 0 ? { business_ids: businessIds.join(',') } : {}
    const response = await apiClient.get('/businesses/consolidated-stats', { params })
    return response.data
  },

  async searchGooglePlaces(
    query: string, 
    location: string | null = null, 
    radius: number = 5000
  ): Promise<GooglePlacesSearchResponse> {
    const params: any = { query, radius }
    if (location) {
      params.location = location
    }
    const response = await apiClient.get('/businesses/search/google-places', { params })
    return response.data
  },

  async getGooglePlaceDetails(placeId: string): Promise<any> {
    const response = await apiClient.get(`/businesses/google-places/${placeId}/details`)
    return response.data
  },

  async getImportStatus(businessId: string): Promise<ImportStatus> {
    const response = await apiClient.get(`/businesses/${businessId}/import-status`)
    return response.data
  },

  async getRealTimeImportStatus(businessId: string): Promise<RealTimeImportStatus> {
    const response = await apiClient.get(`/businesses/${businessId}/import-status/real-time`)
    return response.data
  },

  async getImportHistory(businessId: string, limit: number = 10): Promise<any> {
    const response = await apiClient.get(`/businesses/${businessId}/import-history`, {
      params: { limit }
    })
    return response.data
  },

  async startManualImport(businessId: string, options: any = {}): Promise<any> {
    const response = await apiClient.post(`/businesses/${businessId}/import-reviews/manual`, {
      max_reviews: options.max_reviews || 500,
      force_refresh: options.force_refresh || false
    })
    return response.data
  }
}