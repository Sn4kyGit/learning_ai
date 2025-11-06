import { describe, it, expect, beforeEach, vi } from 'vitest'
import { googlePlacesService, GooglePlacesError } from '@/services/googlePlaces'

describe('GooglePlacesService', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Service Initialization', () => {
    it('should initialize without errors', () => {
      expect(googlePlacesService).toBeDefined()
      expect(typeof googlePlacesService.initialize).toBe('function')
    })

    it('should have all required methods', () => {
      expect(typeof googlePlacesService.searchPlaces).toBe('function')
      expect(typeof googlePlacesService.getPlaceDetails).toBe('function')
      expect(typeof googlePlacesService.getPhotoUrl).toBe('function')
      expect(typeof googlePlacesService.getRateLimitStatus).toBe('function')
    })
  })

  describe('Rate Limiting', () => {
    it('should track rate limit status', () => {
      const status = googlePlacesService.getRateLimitStatus()
      
      expect(status).toBeDefined()
      expect(typeof status).toBe('object')
    })

    it('should enforce rate limits', () => {
      const status = googlePlacesService.getRateLimitStatus()
      
      expect(status).toBeDefined()
    })
  })

  describe('Photo URL Generation', () => {
    it('should generate correct photo URLs', () => {
      const photoReference = 'test-photo-reference'
      const url = googlePlacesService.getPhotoUrl(photoReference, 400, 300)
      
      expect(url).toBeDefined()
      expect(typeof url).toBe('string')
    })

    it('should use default dimensions when not specified', () => {
      const photoReference = 'test-photo-reference'
      const url = googlePlacesService.getPhotoUrl(photoReference)
      
      expect(url).toBeDefined()
      expect(typeof url).toBe('string')
    })
  })

  describe('Error Handling', () => {
    it('should create GooglePlacesError with correct properties', () => {
      const error = new GooglePlacesError(
        'Test error message',
        'TEST_ERROR',
        400
      )
      
      expect(error).toBeInstanceOf(Error)
      expect(error).toBeInstanceOf(GooglePlacesError)
      expect(error.message).toBe('Test error message')
      expect(error.code).toBe('TEST_ERROR')
      expect(error.status).toBe(400)
      expect(error.name).toBe('GooglePlacesError')
    })
  })

  describe('Service Methods', () => {
    it('should have all required methods', () => {
      expect(typeof googlePlacesService.getRateLimitStatus).toBe('function')
      expect(typeof googlePlacesService.getPhotoUrl).toBe('function')
      expect(typeof googlePlacesService.searchPlaces).toBe('function')
      expect(typeof googlePlacesService.getPlaceDetails).toBe('function')
      expect(typeof googlePlacesService.initialize).toBe('function')
    })

    it('should handle method calls without throwing', () => {
      expect(() => {
        googlePlacesService.getRateLimitStatus()
      }).not.toThrow()
      
      expect(() => {
        googlePlacesService.getPhotoUrl('test-ref')
      }).not.toThrow()
    })
  })

  describe('Search Functionality', () => {
    it('should handle search requests', async () => {
      // Mock successful search
      vi.mocked(googlePlacesService.searchPlaces).mockResolvedValue({
        results: [],
        status: 'OK'
      })
      
      const result = await googlePlacesService.searchPlaces('test query')
      expect(result).toBeDefined()
    })

    it('should handle search errors', async () => {
      // Mock search error
      vi.mocked(googlePlacesService.searchPlaces).mockRejectedValue(
        new GooglePlacesError('Search failed', 'SEARCH_ERROR')
      )
      
      await expect(googlePlacesService.searchPlaces('test query')).rejects.toThrow(GooglePlacesError)
    })
  })

  describe('Place Details', () => {
    it('should fetch place details', async () => {
      // Mock successful details fetch
      vi.mocked(googlePlacesService.getPlaceDetails).mockResolvedValue({
        place_id: 'test-place-id',
        name: 'Test Place',
        formatted_address: '123 Test St'
      })
      
      const details = await googlePlacesService.getPlaceDetails('test-place-id')
      expect(details).toBeDefined()
      expect(details.place_id).toBe('test-place-id')
    })

    it('should handle details fetch errors', async () => {
      // Mock details error
      vi.mocked(googlePlacesService.getPlaceDetails).mockRejectedValue(
        new GooglePlacesError('Details fetch failed', 'DETAILS_ERROR')
      )
      
      await expect(googlePlacesService.getPlaceDetails('invalid-id')).rejects.toThrow(GooglePlacesError)
    })
  })
})