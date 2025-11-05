import { describe, it, expect, vi, beforeEach } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'
import { useBusinessStore } from '@/stores/business'
import { businessService } from '@/services/business'

// Mock the business service
vi.mock('@/services/business', () => ({
  businessService: {
    getBusinesses: vi.fn(),
    createBusiness: vi.fn(),
    updateBusiness: vi.fn(),
    deleteBusiness: vi.fn()
  }
}))

describe('Business Store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
  })

  const mockBusinesses = [
    {
      id: 'business-1',
      name: 'Restaurant A',
      google_place_id: 'place-1',
      category: 'restaurant',
      address: '123 Main St',
      avg_rating: 4.2,
      total_reviews: 156,
      created_at: '2024-01-01T00:00:00Z',
      updated_at: '2024-01-01T00:00:00Z'
    },
    {
      id: 'business-2',
      name: 'Restaurant B',
      google_place_id: 'place-2',
      category: 'restaurant',
      address: '456 Oak Ave',
      avg_rating: 3.8,
      total_reviews: 89,
      created_at: '2024-01-02T00:00:00Z',
      updated_at: '2024-01-02T00:00:00Z'
    }
  ]

  describe('Initial State', () => {
    it('has correct initial state', () => {
      const store = useBusinessStore()
      
      expect(store.businesses).toEqual([])
      expect(store.currentBusiness).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasBusinesses).toBe(false)
      expect(store.businessCount).toBe(0)
    })
  })

  describe('fetchBusinesses', () => {
    it('fetches businesses successfully', async () => {
      vi.mocked(businessService.getBusinesses).mockResolvedValue(mockBusinesses)
      
      const store = useBusinessStore()
      await store.fetchBusinesses()
      
      expect(store.businesses).toEqual(mockBusinesses)
      expect(store.currentBusiness).toEqual(mockBusinesses[0])
      expect(store.loading).toBe(false)
      expect(store.error).toBeNull()
      expect(store.hasBusinesses).toBe(true)
      expect(store.businessCount).toBe(2)
    })

    it('handles fetch error', async () => {
      const errorMessage = 'Failed to fetch businesses'
      vi.mocked(businessService.getBusinesses).mockRejectedValue(new Error(errorMessage))
      
      const store = useBusinessStore()
      
      await expect(store.fetchBusinesses()).rejects.toThrow(errorMessage)
      expect(store.businesses).toEqual([])
      expect(store.currentBusiness).toBeNull()
      expect(store.loading).toBe(false)
      expect(store.error).toBe(errorMessage)
    })

    it('sets loading state correctly', async () => {
      let resolvePromise: (value: any) => void
      const promise = new Promise(resolve => {
        resolvePromise = resolve
      })
      vi.mocked(businessService.getBusinesses).mockReturnValue(promise)
      
      const store = useBusinessStore()
      const fetchPromise = store.fetchBusinesses()
      
      expect(store.loading).toBe(true)
      
      resolvePromise!(mockBusinesses)
      await fetchPromise
      
      expect(store.loading).toBe(false)
    })

    it('does not set current business if one already exists', async () => {
      vi.mocked(businessService.getBusinesses).mockResolvedValue(mockBusinesses)
      
      const store = useBusinessStore()
      store.currentBusiness = mockBusinesses[1]
      
      await store.fetchBusinesses()
      
      expect(store.currentBusiness).toEqual(mockBusinesses[1])
    })
  })

  describe('createBusiness', () => {
    it('creates business successfully', async () => {
      const newBusiness = {
        id: 'business-3',
        name: 'Restaurant C',
        google_place_id: 'place-3',
        category: 'restaurant',
        address: '789 Pine St',
        avg_rating: 0,
        total_reviews: 0,
        created_at: '2024-01-03T00:00:00Z',
        updated_at: '2024-01-03T00:00:00Z'
      }
      
      const businessData = {
        name: 'Restaurant C',
        google_place_id: 'place-3',
        category: 'restaurant',
        address: '789 Pine St'
      }
      
      vi.mocked(businessService.createBusiness).mockResolvedValue(newBusiness)
      
      const store = useBusinessStore()
      const result = await store.createBusiness(businessData)
      
      expect(businessService.createBusiness).toHaveBeenCalledWith(businessData)
      // Check that business was added to the store
      expect(store.businesses.find(b => b.id === newBusiness.id)).toEqual(newBusiness)
      expect(result).toEqual(newBusiness)
    })

    it('sets as current business if it is the first one', async () => {
      const newBusiness = mockBusinesses[0]
      vi.mocked(businessService.createBusiness).mockResolvedValue(newBusiness)
      
      const store = useBusinessStore()
      await store.createBusiness({})
      
      expect(store.currentBusiness).toEqual(newBusiness)
    })

    it('handles create error', async () => {
      const errorMessage = 'Failed to create business'
      vi.mocked(businessService.createBusiness).mockRejectedValue(new Error(errorMessage))
      
      const store = useBusinessStore()
      
      await expect(store.createBusiness({})).rejects.toThrow(errorMessage)
      expect(store.error).toBe(errorMessage)
    })
  })

  describe('updateBusiness', () => {
    it('updates business successfully', async () => {
      const updatedBusiness = { ...mockBusinesses[0], name: 'Updated Restaurant A' }
      vi.mocked(businessService.updateBusiness).mockResolvedValue(updatedBusiness)
      
      const store = useBusinessStore()
      store.businesses = [...mockBusinesses]
      store.currentBusiness = mockBusinesses[0]
      
      const updates = { name: 'Updated Restaurant A' }
      const result = await store.updateBusiness('business-1', updates)
      
      expect(businessService.updateBusiness).toHaveBeenCalledWith('business-1', updates)
      expect(store.businesses[0]).toEqual(updatedBusiness)
      expect(store.currentBusiness).toEqual(updatedBusiness)
      expect(result).toEqual(updatedBusiness)
    })

    it('updates current business if it matches', async () => {
      const updatedBusiness = { ...mockBusinesses[0], name: 'Updated Restaurant A' }
      vi.mocked(businessService.updateBusiness).mockResolvedValue(updatedBusiness)
      
      const store = useBusinessStore()
      store.businesses = [...mockBusinesses]
      store.currentBusiness = mockBusinesses[0]
      
      await store.updateBusiness('business-1', { name: 'Updated Restaurant A' })
      
      expect(store.currentBusiness).toEqual(updatedBusiness)
    })

    it('handles update error', async () => {
      const errorMessage = 'Failed to update business'
      vi.mocked(businessService.updateBusiness).mockRejectedValue(new Error(errorMessage))
      
      const store = useBusinessStore()
      
      await expect(store.updateBusiness('business-1', {})).rejects.toThrow(errorMessage)
      expect(store.error).toBe(errorMessage)
    })
  })

  describe('deleteBusiness', () => {
    it('deletes business successfully', async () => {
      vi.mocked(businessService.deleteBusiness).mockResolvedValue(undefined)
      
      const store = useBusinessStore()
      store.businesses = [...mockBusinesses]
      store.currentBusiness = mockBusinesses[0]
      
      await store.deleteBusiness('business-1')
      
      expect(businessService.deleteBusiness).toHaveBeenCalledWith('business-1')
      expect(store.businesses).toHaveLength(1)
      expect(store.businesses[0]).toEqual(mockBusinesses[1])
      expect(store.currentBusiness).toEqual(mockBusinesses[1])
    })

    it('sets current business to null if no businesses remain', async () => {
      vi.mocked(businessService.deleteBusiness).mockResolvedValue(undefined)
      
      const store = useBusinessStore()
      store.businesses = [mockBusinesses[0]]
      store.currentBusiness = mockBusinesses[0]
      
      await store.deleteBusiness('business-1')
      
      expect(store.businesses).toHaveLength(0)
      expect(store.currentBusiness).toBeNull()
    })

    it('handles delete error', async () => {
      const errorMessage = 'Failed to delete business'
      vi.mocked(businessService.deleteBusiness).mockRejectedValue(new Error(errorMessage))
      
      const store = useBusinessStore()
      
      await expect(store.deleteBusiness('business-1')).rejects.toThrow(errorMessage)
      expect(store.error).toBe(errorMessage)
    })
  })

  describe('setCurrentBusiness', () => {
    it('sets current business', () => {
      const store = useBusinessStore()
      store.setCurrentBusiness(mockBusinesses[1])
      
      expect(store.currentBusiness).toEqual(mockBusinesses[1])
    })
  })

  describe('clearError', () => {
    it('clears error state', () => {
      const store = useBusinessStore()
      store.error = 'Some error'
      
      store.clearError()
      
      expect(store.error).toBeNull()
    })
  })

  describe('Computed Properties', () => {
    it('hasBusinesses returns correct value', () => {
      const store = useBusinessStore()
      
      expect(store.hasBusinesses).toBe(false)
      
      store.businesses = mockBusinesses
      expect(store.hasBusinesses).toBe(true)
    })

    it('businessCount returns correct value', () => {
      const store = useBusinessStore()
      
      expect(store.businessCount).toBe(0)
      
      store.businesses = mockBusinesses
      expect(store.businessCount).toBe(2)
    })
  })
})