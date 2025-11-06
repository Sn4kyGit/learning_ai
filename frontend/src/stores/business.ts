import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { businessService } from '@/services/business'
import type { Business } from '@/types'

export const useBusinessStore = defineStore('business', () => {
  const businesses = ref<Business[]>([])
  const currentBusiness = ref<Business | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  const hasBusinesses = computed(() => businesses.value.length > 0)
  const businessCount = computed(() => businesses.value.length)

  async function fetchBusinesses() {
    loading.value = true
    error.value = null
    
    try {
      businesses.value = await businessService.getBusinesses()
      
      // Set first business as current if none selected
      if (businesses.value.length > 0 && !currentBusiness.value) {
        currentBusiness.value = businesses.value[0]
      }
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createBusiness(businessData: any) {
    loading.value = true
    error.value = null
    
    try {
      const newBusiness = await businessService.createBusiness(businessData)
      businesses.value.push(newBusiness)
      
      // Set as current business if it's the first one
      if (businesses.value.length === 1) {
        currentBusiness.value = newBusiness
      }
      
      return newBusiness
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBusiness(businessId: string, updates: any) {
    loading.value = true
    error.value = null
    
    try {
      const updatedBusiness = await businessService.updateBusiness(businessId, updates)
      
      const index = businesses.value.findIndex(b => b.id === businessId)
      if (index !== -1) {
        businesses.value[index] = updatedBusiness
      }
      
      if (currentBusiness.value?.id === businessId) {
        currentBusiness.value = updatedBusiness
      }
      
      return updatedBusiness
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteBusiness(businessId: string) {
    loading.value = true
    error.value = null
    
    try {
      await businessService.deleteBusiness(businessId)
      
      businesses.value = businesses.value.filter(b => b.id !== businessId)
      
      if (currentBusiness.value?.id === businessId) {
        currentBusiness.value = businesses.value[0] || null
      }
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentBusiness(business: Business) {
    currentBusiness.value = business
  }

  async function importReviews(businessId: string, options: any = {}) {
    loading.value = true
    error.value = null
    
    try {
      const result = await businessService.importReviews(businessId, options)
      
      // Update the business with new review count if available
      const business = businesses.value.find(b => b.id === businessId)
      if (business && result.imported_count > 0) {
        business.total_reviews = (business.total_reviews || 0) + result.imported_count
      }
      
      return result
    } catch (err: any) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getImportStatus(businessId: string) {
    try {
      return await businessService.getImportStatus(businessId)
    } catch (err: any) {
      error.value = err.message
      throw err
    }
  }

  function clearError() {
    error.value = null
  }

  return {
    businesses,
    currentBusiness,
    loading,
    error,
    hasBusinesses,
    businessCount,
    fetchBusinesses,
    createBusiness,
    updateBusiness,
    deleteBusiness,
    importReviews,
    getImportStatus,
    setCurrentBusiness,
    clearError
  }
})