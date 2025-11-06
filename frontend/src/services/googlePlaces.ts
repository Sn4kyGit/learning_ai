/**
 * Enhanced Google Places API service with JavaScript SDK integration
 * Provides autocomplete, place details, photos, and rate limiting
 */

import type { 
  GooglePlaceSearchResult, 
  GooglePlaceDetails,
  GooglePlacesSearchResponse 
} from '@/types'

// Helper to get environment variables with proper typing
const getEnvVar = (key: string): string => {
  return (import.meta as any).env[key]
}

// Rate limiting configuration
const RATE_LIMIT_CONFIG = {
  maxRequestsPerSecond: 10,
  maxRequestsPerMinute: 100,
  requestQueue: [] as Array<() => Promise<any>>,
  requestTimes: [] as number[],
  isProcessingQueue: false
}

// Google Places API types
interface GooglePlacesAPIService {
  textSearch(request: google.maps.places.TextSearchRequest, callback: (results: google.maps.places.PlaceResult[] | null, status: google.maps.places.PlacesServiceStatus) => void): void
  getDetails(request: google.maps.places.PlaceDetailsRequest, callback: (result: google.maps.places.PlaceResult | null, status: google.maps.places.PlacesServiceStatus) => void): void
}

interface GoogleAutocompleteService {
  getPlacePredictions(request: google.maps.places.AutocompletionRequest, callback: (predictions: google.maps.places.AutocompletePrediction[] | null, status: google.maps.places.PlacesServiceStatus) => void): void
}

declare global {
  interface Window {
    google: typeof google
    googlePlacesLoaded: boolean
    initGooglePlaces: () => void
  }
}

class GooglePlacesError extends Error {
  constructor(
    message: string,
    public code: string,
    public status?: google.maps.places.PlacesServiceStatus
  ) {
    super(message)
    this.name = 'GooglePlacesError'
  }
}

class GooglePlacesService {
  private placesService: GooglePlacesAPIService | null = null
  private autocompleteService: GoogleAutocompleteService | null = null
  private isInitialized = false
  private initializationPromise: Promise<void> | null = null

  constructor() {
    this.initializationPromise = this.initialize()
  }

  /**
   * Initialize Google Places API
   */
  private async initialize(): Promise<void> {
    if (this.isInitialized) return

    try {
      await this.loadGooglePlacesAPI()
      await this.waitForGooglePlaces()
      
      // Create a dummy map element for PlacesService (required by Google)
      const mapDiv = document.createElement('div')
      mapDiv.style.display = 'none'
      document.body.appendChild(mapDiv)
      
      const map = new google.maps.Map(mapDiv, {
        center: { lat: 0, lng: 0 },
        zoom: 1
      })

      this.placesService = new google.maps.places.PlacesService(map)
      this.autocompleteService = new google.maps.places.AutocompleteService()
      
      this.isInitialized = true
      console.log('Google Places API initialized successfully')
    } catch (error) {
      console.error('Failed to initialize Google Places API:', error)
      throw new GooglePlacesError(
        'Failed to initialize Google Places API',
        'INITIALIZATION_ERROR'
      )
    }
  }

  /**
   * Load Google Places API script dynamically
   */
  private async loadGooglePlacesAPI(): Promise<void> {
    if (window.google && window.google.maps && window.google.maps.places) {
      return
    }

    const apiKey = getEnvVar('VITE_GOOGLE_PLACES_API_KEY')
    if (!apiKey || apiKey === 'your-google-places-api-key-here') {
      throw new GooglePlacesError(
        'Google Places API key not configured',
        'MISSING_API_KEY'
      )
    }

    return new Promise((resolve, reject) => {
      const script = document.createElement('script')
      script.src = `https://maps.googleapis.com/maps/api/js?key=${apiKey}&libraries=places&callback=initGooglePlaces`
      script.async = true
      script.defer = true
      
      script.onload = () => resolve()
      script.onerror = () => reject(new Error('Failed to load Google Places API script'))
      
      document.head.appendChild(script)
    })
  }

  /**
   * Wait for Google Places API to be ready
   */
  private async waitForGooglePlaces(): Promise<void> {
    return new Promise((resolve) => {
      if (window.googlePlacesLoaded) {
        resolve()
        return
      }

      window.addEventListener('google-places-loaded', () => resolve(), { once: true })
    })
  }

  /**
   * Rate limiting implementation
   */
  private async rateLimit<T>(operation: () => Promise<T>): Promise<T> {
    const now = Date.now()
    
    // Clean old request times (older than 1 minute)
    RATE_LIMIT_CONFIG.requestTimes = RATE_LIMIT_CONFIG.requestTimes.filter(
      time => now - time < 60000
    )

    // Check rate limits
    const recentRequests = RATE_LIMIT_CONFIG.requestTimes.filter(
      time => now - time < 1000
    )

    if (recentRequests.length >= RATE_LIMIT_CONFIG.maxRequestsPerSecond) {
      // Wait until we can make the request
      const waitTime = 1000 - (now - recentRequests[0])
      await new Promise(resolve => setTimeout(resolve, waitTime))
    }

    if (RATE_LIMIT_CONFIG.requestTimes.length >= RATE_LIMIT_CONFIG.maxRequestsPerMinute) {
      // Wait until the oldest request is more than 1 minute old
      const waitTime = 60000 - (now - RATE_LIMIT_CONFIG.requestTimes[0])
      await new Promise(resolve => setTimeout(resolve, waitTime))
    }

    // Record this request
    RATE_LIMIT_CONFIG.requestTimes.push(now)

    return operation()
  }

  /**
   * Convert Google Places result to our format
   */
  private convertPlaceResult(place: google.maps.places.PlaceResult): GooglePlaceSearchResult {
    return {
      place_id: place.place_id!,
      name: place.name!,
      address: place.formatted_address || place.vicinity || '',
      rating: place.rating,
      user_ratings_total: place.user_ratings_total,
      types: place.types || [],
      geometry: {
        location: {
          lat: place.geometry?.location?.lat() || 0,
          lng: place.geometry?.location?.lng() || 0
        }
      },
      photos: place.photos?.map(photo => ({
        photo_reference: photo.getUrl({ maxWidth: 400, maxHeight: 400 }),
        height: photo.height,
        width: photo.width
      })),
      price_level: place.price_level,
      business_status: place.business_status
    }
  }

  /**
   * Convert Google Places detailed result to our format
   */
  private convertPlaceDetails(place: google.maps.places.PlaceResult): GooglePlaceDetails {
    const baseResult = this.convertPlaceResult(place)
    
    return {
      ...baseResult,
      formatted_address: place.formatted_address || '',
      formatted_phone_number: place.formatted_phone_number,
      international_phone_number: place.international_phone_number,
      website: place.website,
      opening_hours: place.opening_hours ? {
        open_now: place.opening_hours.open_now || false,
        periods: place.opening_hours.periods?.map(period => ({
          close: {
            day: period.close?.day || 0,
            time: period.close?.time || ''
          },
          open: {
            day: period.open?.day || 0,
            time: period.open?.time || ''
          }
        })) || [],
        weekday_text: place.opening_hours.weekday_text || []
      } : undefined,
      reviews: place.reviews?.map(review => ({
        author_name: review.author_name,
        author_url: review.author_url || '',
        language: review.language,
        profile_photo_url: review.profile_photo_url,
        rating: review.rating || 0,
        relative_time_description: review.relative_time_description,
        text: review.text,
        time: review.time
      }))
    }
  }

  /**
   * Search for places with autocomplete predictions
   */
  async getAutocompletePredictions(
    input: string,
    options: {
      types?: string[]
      componentRestrictions?: { country: string | string[] }
      location?: { lat: number; lng: number }
      radius?: number
    } = {}
  ): Promise<google.maps.places.AutocompletePrediction[]> {
    await this.initializationPromise
    
    if (!this.autocompleteService) {
      throw new GooglePlacesError(
        'Autocomplete service not initialized',
        'SERVICE_NOT_INITIALIZED'
      )
    }

    return this.rateLimit(() => {
      return new Promise((resolve, reject) => {
        const request: google.maps.places.AutocompletionRequest = {
          input,
          types: options.types || ['establishment'],
          componentRestrictions: options.componentRestrictions,
          location: options.location ? new google.maps.LatLng(options.location.lat, options.location.lng) : undefined,
          radius: options.radius
        }

        this.autocompleteService!.getPlacePredictions(request, (predictions, status) => {
          if (status === google.maps.places.PlacesServiceStatus.OK && predictions) {
            resolve(predictions)
          } else if (status === google.maps.places.PlacesServiceStatus.ZERO_RESULTS) {
            resolve([])
          } else {
            reject(new GooglePlacesError(
              `Autocomplete request failed: ${status}`,
              'AUTOCOMPLETE_ERROR',
              status
            ))
          }
        })
      })
    })
  }

  /**
   * Search for places using text search
   */
  async searchPlaces(
    query: string,
    options: {
      location?: { lat: number; lng: number }
      radius?: number
      type?: string
      minPriceLevel?: number
      maxPriceLevel?: number
      openNow?: boolean
    } = {}
  ): Promise<GooglePlacesSearchResponse> {
    await this.initializationPromise
    
    if (!this.placesService) {
      throw new GooglePlacesError(
        'Places service not initialized',
        'SERVICE_NOT_INITIALIZED'
      )
    }

    return this.rateLimit(() => {
      return new Promise((resolve, reject) => {
        const request: google.maps.places.TextSearchRequest = {
          query,
          location: options.location ? new google.maps.LatLng(options.location.lat, options.location.lng) : undefined,
          radius: options.radius || 5000,
          type: options.type as any
        }

        this.placesService!.textSearch(request, (results, status) => {
          if (status === google.maps.places.PlacesServiceStatus.OK && results) {
            const convertedResults = results.map(place => this.convertPlaceResult(place))
            resolve({
              results: convertedResults,
              query,
              location: options.location ? `${options.location.lat},${options.location.lng}` : undefined,
              radius: options.radius || 5000
            })
          } else if (status === google.maps.places.PlacesServiceStatus.ZERO_RESULTS) {
            resolve({
              results: [],
              query,
              location: options.location ? `${options.location.lat},${options.location.lng}` : undefined,
              radius: options.radius || 5000
            })
          } else {
            reject(new GooglePlacesError(
              `Places search failed: ${status}`,
              'SEARCH_ERROR',
              status
            ))
          }
        })
      })
    })
  }

  /**
   * Get detailed information about a place
   */
  async getPlaceDetails(
    placeId: string,
    fields: string[] = [
      'place_id', 'name', 'formatted_address', 'geometry', 'rating',
      'user_ratings_total', 'types', 'photos', 'price_level', 'business_status',
      'formatted_phone_number', 'international_phone_number', 'website',
      'opening_hours', 'reviews'
    ]
  ): Promise<GooglePlaceDetails> {
    await this.initializationPromise
    
    if (!this.placesService) {
      throw new GooglePlacesError(
        'Places service not initialized',
        'SERVICE_NOT_INITIALIZED'
      )
    }

    return this.rateLimit(() => {
      return new Promise((resolve, reject) => {
        const request: google.maps.places.PlaceDetailsRequest = {
          placeId,
          fields
        }

        this.placesService!.getDetails(request, (place, status) => {
          if (status === google.maps.places.PlacesServiceStatus.OK && place) {
            resolve(this.convertPlaceDetails(place))
          } else {
            reject(new GooglePlacesError(
              `Place details request failed: ${status}`,
              'DETAILS_ERROR',
              status
            ))
          }
        })
      })
    })
  }

  /**
   * Get place photo URL
   */
  getPhotoUrl(
    photoReference: string,
    options: {
      maxWidth?: number
      maxHeight?: number
    } = {}
  ): string {
    const apiKey = getEnvVar('VITE_GOOGLE_PLACES_API_KEY')
    const { maxWidth = 400, maxHeight = 400 } = options
    
    return `https://maps.googleapis.com/maps/api/place/photo?maxwidth=${maxWidth}&maxheight=${maxHeight}&photoreference=${photoReference}&key=${apiKey}`
  }

  /**
   * Validate a place ID
   */
  async validatePlaceId(placeId: string): Promise<boolean> {
    try {
      await this.getPlaceDetails(placeId, ['place_id', 'name'])
      return true
    } catch (error) {
      if (error instanceof GooglePlacesError && error.status === google.maps.places.PlacesServiceStatus.NOT_FOUND) {
        return false
      }
      throw error
    }
  }

  /**
   * Get current rate limit status
   */
  getRateLimitStatus(): {
    requestsInLastSecond: number
    requestsInLastMinute: number
    maxRequestsPerSecond: number
    maxRequestsPerMinute: number
  } {
    const now = Date.now()
    const requestsInLastSecond = RATE_LIMIT_CONFIG.requestTimes.filter(
      time => now - time < 1000
    ).length
    const requestsInLastMinute = RATE_LIMIT_CONFIG.requestTimes.filter(
      time => now - time < 60000
    ).length

    return {
      requestsInLastSecond,
      requestsInLastMinute,
      maxRequestsPerSecond: RATE_LIMIT_CONFIG.maxRequestsPerSecond,
      maxRequestsPerMinute: RATE_LIMIT_CONFIG.maxRequestsPerMinute
    }
  }
}

// Export singleton instance
export const googlePlacesService = new GooglePlacesService()
export { GooglePlacesError }