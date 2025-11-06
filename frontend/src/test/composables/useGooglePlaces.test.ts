/**
 * Tests for useGooglePlaces composable
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useGooglePlaces } from '@/composables/useGooglePlaces'

// Mock the Google Places service
const mockGooglePlacesService = {
  searchPlaces: vi.fn(),
  getAutocompletePredictions: vi.fn(),
  getPlaceDetails: vi.fn(),
  getPlaceDetailsFromPrediction: vi.fn(),
  validatePlaceId: vi.fn(),
  getPhotoUrl: vi.fn(),
  getRateLimitStatus: vi.fn(() => ({
    requestsInLastSecond: 0,
    requestsInLastMinute: 0,
    maxRequestsPerSecond: 10,
    maxRequestsPerMinute: 100
  }))
}

const mockGooglePlacesError = class GooglePlacesError extends Error {
  constructor(message: string, public code: string, public status?: any) {
    super(message)
    this.name = 'GooglePlacesError'
  }
}

vi.mock('@/services/googlePlaces', () => ({
  googlePlacesService: mockGooglePlacesService,
  GooglePlacesError: mockGooglePlacesError
}))

describe('useGooglePlaces', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('Initialization', () => {
    it('should initialize with default options', () => {
      const {
        isInitialized,
        isLoading,
        error,
        searchResults,
        autocompletePredictions,
        rateLimitStatus
      } = useGooglePlaces()

      expect(isInitialized.value).toBe(false)
      expect(isLoading.value).toBe(false)
      expect(error.value).toBe(null)
      expect(searchResults.value).toEqual([])
      expect(autocompletePredictions.value).toEqual([])
      expect(rateLimitStatus.value).toHaveProperty('requestsInLastSecond')
    })

    it('should initialize with custom options', () => {
      const options = {
        autoInitialize: false,
        defaultLocation: { lat: 40.7128, lng: -74.0060 },
        defaultRadius: 10000,
        debounceMs: 500
      }

      const composable = useGooglePlaces(options)
      expect(composable).toBeDefined()
    })
  })

  describe('Computed Properties', () => {
    it('should compute rate limit status correctly', () => {
      const { isRateLimited, updateRateLimitStatus } = useGooglePlaces()
      
      updateRateLimitStatus()
      expect(typeof isRateLimited.value).toBe('boolean')
    })

    it('should compute results status correctly', () => {
      const { hasResults, hasPredictions, searchResults, autocompletePredictions } = useGooglePlaces()

      expect(hasResults.value).toBe(false)
      expect(hasPredictions.value).toBe(false)

      // Simulate adding results
      searchResults.value = [{ place_id: 'test', name: 'Test Place' } as any]
      autocompletePredictions.value = [{ place_id: 'test', structured_formatting: { main_text: 'Test' } } as any]

      expect(hasResults.value).toBe(true)
      expect(hasPredictions.value).toBe(true)
    })
  })

  describe('Search Methods', () => {
    it('should clear results when query is empty', async () => {
      const { searchPlaces, searchResults, clearResults } = useGooglePlaces()

      // Add some mock results first
      searchResults.value = [{ place_id: 'test', name: 'Test Place' } as any]
      
      const result = await searchPlaces('')
      expect(result).toBe(null)
      expect(searchResults.value).toEqual([])
    })

    it('should handle search errors gracefully', async () => {
      const { searchPlaces, error } = useGooglePlaces()
      const mockError = new Error('Search failed')
      
      mockGooglePlacesService.searchPlaces.mockRejectedValueOnce(mockError)

      await searchPlaces('test query')
      expect(error.value).toContain('Search failed')
    })
  })

  describe('Autocomplete Methods', () => {
    it('should clear predictions when input is empty', async () => {
      const { getAutocompletePredictions, autocompletePredictions } = useGooglePlaces()

      const result = await getAutocompletePredictions('')
      expect(result).toEqual([])
      expect(autocompletePredictions.value).toEqual([])
    })

    it('should handle autocomplete errors gracefully', async () => {
      const { getAutocompletePredictions, error } = useGooglePlaces()
      const mockError = new Error('Autocomplete failed')
      
      mockGooglePlacesService.getAutocompletePredictions.mockRejectedValueOnce(mockError)

      await getAutocompletePredictions('test input')
      expect(error.value).toContain('Autocomplete failed')
    })
  })

  describe('Place Details Methods', () => {
    it('should get place details successfully', async () => {
      const { getPlaceDetails, selectedPlace } = useGooglePlaces()
      const mockDetails = { place_id: 'test', name: 'Test Place' }
      
      mockGooglePlacesService.getPlaceDetails.mockResolvedValueOnce(mockDetails)

      const result = await getPlaceDetails('test-place-id')
      expect(result).toEqual(mockDetails)
      expect(selectedPlace.value).toEqual(mockDetails)
    })

    it('should handle place details errors gracefully', async () => {
      const { getPlaceDetails, error } = useGooglePlaces()
      const mockError = new Error('Details failed')
      
      mockGooglePlacesService.getPlaceDetails.mockRejectedValueOnce(mockError)

      const result = await getPlaceDetails('test-place-id')
      expect(result).toBe(null)
      expect(error.value).toContain('Details failed')
    })
  })

  describe('Validation Methods', () => {
    it('should validate place IDs', async () => {
      const { validatePlaceId } = useGooglePlaces()
      
      mockGooglePlacesService.validatePlaceId.mockResolvedValueOnce(true)

      const result = await validatePlaceId('valid-place-id')
      expect(result).toBe(true)
    })

    it('should handle validation errors', async () => {
      const { validatePlaceId, error } = useGooglePlaces()
      const mockError = new Error('Validation failed')
      
      mockGooglePlacesService.validatePlaceId.mockRejectedValueOnce(mockError)

      const result = await validatePlaceId('invalid-place-id')
      expect(result).toBe(false)
      expect(error.value).toContain('Validation failed')
    })
  })

  describe('Utility Methods', () => {
    it('should format place types correctly', () => {
      const { formatPlaceType } = useGooglePlaces()

      expect(formatPlaceType('restaurant')).toBe('Restaurant')
      expect(formatPlaceType('meal_takeaway')).toBe('Takeaway')
      expect(formatPlaceType('unknown_type')).toBe('Unknown Type')
    })

    it('should format ratings correctly', () => {
      const { formatRating } = useGooglePlaces()

      expect(formatRating(4.5)).toContain('4.5')
      expect(formatRating(4.5)).toContain('⭐')
      expect(formatRating(4.5, 100)).toContain('(100)')
    })

    it('should clear all results', () => {
      const { clearResults, searchResults, autocompletePredictions, selectedPlace, error } = useGooglePlaces()

      // Set some mock data
      searchResults.value = [{ place_id: 'test' } as any]
      autocompletePredictions.value = [{ place_id: 'test' } as any]
      selectedPlace.value = { place_id: 'test' } as any
      error.value = 'Test error'

      clearResults()

      expect(searchResults.value).toEqual([])
      expect(autocompletePredictions.value).toEqual([])
      expect(selectedPlace.value).toBe(null)
      expect(error.value).toBe(null)
    })

    it('should clear errors', () => {
      const { clearError, error } = useGooglePlaces()

      error.value = 'Test error'
      clearError()
      expect(error.value).toBe(null)
    })
  })

  describe('Error Handling', () => {
    it('should handle GooglePlacesError correctly', async () => {
      const { searchPlaces, error } = useGooglePlaces()
      const mockError = new mockGooglePlacesError('API key missing', 'MISSING_API_KEY')
      
      mockGooglePlacesService.searchPlaces.mockRejectedValueOnce(mockError)

      await searchPlaces('test query')
      expect(error.value).toBe('Google Places API key not configured')
    })

    it('should handle generic errors', async () => {
      const { searchPlaces, error } = useGooglePlaces()
      const mockError = new Error('Generic error')
      
      mockGooglePlacesService.searchPlaces.mockRejectedValueOnce(mockError)

      await searchPlaces('test query')
      expect(error.value).toContain('Generic error')
    })
  })
})