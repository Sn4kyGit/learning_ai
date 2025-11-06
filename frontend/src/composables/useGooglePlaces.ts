/**
 * Vue composable for Google Places API integration
 * Provides reactive state and methods for place search and autocomplete
 */

import { ref, computed, onMounted, onUnmounted } from 'vue'
import { googlePlacesService, GooglePlacesError } from '@/services/googlePlaces'
import type { 
  GooglePlaceSearchResult, 
  GooglePlaceDetails,
  GooglePlacesSearchResponse 
} from '@/types'

export interface UseGooglePlacesOptions {
  autoInitialize?: boolean
  defaultLocation?: { lat: number; lng: number }
  defaultRadius?: number
  debounceMs?: number
}

export function useGooglePlaces(options: UseGooglePlacesOptions = {}) {
  const {
    autoInitialize = true,
    defaultLocation,
    defaultRadius = 5000,
    debounceMs = 300
  } = options

  // Reactive state
  const isInitialized = ref(false)
  const isLoading = ref(false)
  const error = ref<string | null>(null)
  const searchResults = ref<GooglePlaceSearchResult[]>([])
  const autocompletePredictions = ref<google.maps.places.AutocompletePrediction[]>([])
  const selectedPlace = ref<GooglePlaceDetails | null>(null)
  const rateLimitStatus = ref({
    requestsInLastSecond: 0,
    requestsInLastMinute: 0,
    maxRequestsPerSecond: 10,
    maxRequestsPerMinute: 100
  })

  // Computed properties
  const isRateLimited = computed(() => {
    return rateLimitStatus.value.requestsInLastSecond >= rateLimitStatus.value.maxRequestsPerSecond ||
           rateLimitStatus.value.requestsInLastMinute >= rateLimitStatus.value.maxRequestsPerMinute
  })

  const hasResults = computed(() => searchResults.value.length > 0)
  const hasPredictions = computed(() => autocompletePredictions.value.length > 0)

  // Debounce utility
  let debounceTimer: NodeJS.Timeout | null = null

  const debounce = (func: Function, delay: number) => {
    return (...args: any[]) => {
      if (debounceTimer) clearTimeout(debounceTimer)
      debounceTimer = setTimeout(() => func(...args), delay)
    }
  }

  // Error handling
  const handleError = (err: unknown, operation: string) => {
    console.error(`Google Places ${operation} error:`, err)
    
    if (err instanceof GooglePlacesError) {
      switch (err.code) {
        case 'MISSING_API_KEY':
          error.value = 'Google Places API key not configured'
          break
        case 'INITIALIZATION_ERROR':
          error.value = 'Failed to initialize Google Places API'
          break
        case 'SERVICE_NOT_INITIALIZED':
          error.value = 'Google Places service not ready'
          break
        case 'SEARCH_ERROR':
        case 'AUTOCOMPLETE_ERROR':
        case 'DETAILS_ERROR':
          error.value = `Search failed: ${err.message}`
          break
        default:
          error.value = err.message
      }
    } else {
      error.value = `${operation} failed: ${err instanceof Error ? err.message : 'Unknown error'}`
    }
  }

  // Clear error state
  const clearError = () => {
    error.value = null
  }

  // Update rate limit status
  const updateRateLimitStatus = () => {
    rateLimitStatus.value = googlePlacesService.getRateLimitStatus()
  }

  // Initialize Google Places API
  const initialize = async () => {
    if (isInitialized.value) return

    isLoading.value = true
    clearError()

    try {
      // The service initializes itself, we just need to wait for it
      await new Promise(resolve => setTimeout(resolve, 100))
      isInitialized.value = true
    } catch (err) {
      handleError(err, 'initialization')
    } finally {
      isLoading.value = false
    }
  }

  // Search for places using text search
  const searchPlaces = async (
    query: string,
    options: {
      location?: { lat: number; lng: number }
      radius?: number
      type?: string
      minPriceLevel?: number
      maxPriceLevel?: number
      openNow?: boolean
    } = {}
  ): Promise<GooglePlacesSearchResponse | null> => {
    if (!query.trim()) {
      searchResults.value = []
      return null
    }

    isLoading.value = true
    clearError()
    updateRateLimitStatus()

    try {
      const searchOptions = {
        location: options.location || defaultLocation,
        radius: options.radius || defaultRadius,
        ...options
      }

      const response = await googlePlacesService.searchPlaces(query, searchOptions)
      searchResults.value = response.results
      updateRateLimitStatus()
      return response
    } catch (err) {
      handleError(err, 'search')
      searchResults.value = []
      return null
    } finally {
      isLoading.value = false
    }
  }

  // Get autocomplete predictions
  const getAutocompletePredictions = async (
    input: string,
    options: {
      types?: string[]
      componentRestrictions?: { country: string | string[] }
      location?: { lat: number; lng: number }
      radius?: number
    } = {}
  ): Promise<google.maps.places.AutocompletePrediction[]> => {
    if (!input.trim()) {
      autocompletePredictions.value = []
      return []
    }

    isLoading.value = true
    clearError()
    updateRateLimitStatus()

    try {
      const searchOptions = {
        types: ['establishment'],
        location: defaultLocation,
        radius: defaultRadius,
        ...options
      }

      const predictions = await googlePlacesService.getAutocompletePredictions(input, searchOptions)
      autocompletePredictions.value = predictions
      updateRateLimitStatus()
      return predictions
    } catch (err) {
      handleError(err, 'autocomplete')
      autocompletePredictions.value = []
      return []
    } finally {
      isLoading.value = false
    }
  }

  // Debounced autocomplete
  const debouncedAutocomplete = debounce(getAutocompletePredictions, debounceMs)

  // Get place details
  const getPlaceDetails = async (
    placeId: string,
    fields?: string[]
  ): Promise<GooglePlaceDetails | null> => {
    isLoading.value = true
    clearError()
    updateRateLimitStatus()

    try {
      const details = await googlePlacesService.getPlaceDetails(placeId, fields)
      selectedPlace.value = details
      updateRateLimitStatus()
      return details
    } catch (err) {
      handleError(err, 'place details')
      return null
    } finally {
      isLoading.value = false
    }
  }

  // Get place details from prediction
  const getPlaceDetailsFromPrediction = async (
    prediction: google.maps.places.AutocompletePrediction
  ): Promise<GooglePlaceDetails | null> => {
    return getPlaceDetails(prediction.place_id)
  }

  // Validate place ID
  const validatePlaceId = async (placeId: string): Promise<boolean> => {
    clearError()
    updateRateLimitStatus()

    try {
      const isValid = await googlePlacesService.validatePlaceId(placeId)
      updateRateLimitStatus()
      return isValid
    } catch (err) {
      handleError(err, 'validation')
      return false
    }
  }

  // Get photo URL
  const getPhotoUrl = (
    photoReference: string,
    options: { maxWidth?: number; maxHeight?: number } = {}
  ): string => {
    return googlePlacesService.getPhotoUrl(photoReference, options)
  }

  // Clear all results
  const clearResults = () => {
    searchResults.value = []
    autocompletePredictions.value = []
    selectedPlace.value = null
    clearError()
  }

  // Format place types for display
  const formatPlaceType = (type: string): string => {
    const typeMap: Record<string, string> = {
      restaurant: 'Restaurant',
      food: 'Food',
      establishment: 'Business',
      point_of_interest: 'Point of Interest',
      meal_takeaway: 'Takeaway',
      meal_delivery: 'Delivery',
      cafe: 'Café',
      bar: 'Bar',
      bakery: 'Bakery',
      store: 'Store',
      shopping_mall: 'Shopping Mall',
      gas_station: 'Gas Station',
      lodging: 'Hotel',
      tourist_attraction: 'Tourist Attraction'
    }
    
    return typeMap[type] || type.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase())
  }

  // Format rating display
  const formatRating = (rating: number, totalRatings?: number): string => {
    const stars = '⭐'.repeat(Math.floor(rating))
    const ratingText = rating.toFixed(1)
    const totalText = totalRatings ? ` (${totalRatings})` : ''
    return `${ratingText} ${stars}${totalText}`
  }

  // Lifecycle hooks
  onMounted(() => {
    if (autoInitialize) {
      initialize()
    }
  })

  onUnmounted(() => {
    if (debounceTimer) {
      clearTimeout(debounceTimer)
    }
  })

  return {
    // State
    isInitialized,
    isLoading,
    error,
    searchResults,
    autocompletePredictions,
    selectedPlace,
    rateLimitStatus,

    // Computed
    isRateLimited,
    hasResults,
    hasPredictions,

    // Methods
    initialize,
    searchPlaces,
    getAutocompletePredictions,
    debouncedAutocomplete,
    getPlaceDetails,
    getPlaceDetailsFromPrediction,
    validatePlaceId,
    getPhotoUrl,
    clearResults,
    clearError,
    formatPlaceType,
    formatRating,
    updateRateLimitStatus
  }
}