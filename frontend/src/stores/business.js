import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { businessService } from '@/services/business'

export const useBusinessStore = defineStore('business', () => {
  const businesses = ref([])
  const currentBusiness = ref(null)
  const loading = ref(false)
  const error = ref(null)

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
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createBusiness(businessData) {
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
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateBusiness(businessId, updates) {
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
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteBusiness(businessId) {
    loading.value = true
    error.value = null
    
    try {
      await businessService.deleteBusiness(businessId)
      
      businesses.value = businesses.value.filter(b => b.id !== businessId)
      
      if (currentBusiness.value?.id === businessId) {
        currentBusiness.value = businesses.value[0] || null
      }
    } catch (err) {
      error.value = err.message
      throw err
    } finally {
      loading.value = false
    }
  }

  function setCurrentBusiness(business) {
    currentBusiness.value = business
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
    setCurrentBusiness,
    clearError
  }
})