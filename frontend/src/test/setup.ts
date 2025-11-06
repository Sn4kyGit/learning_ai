import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia } from 'pinia'

// Import actual locale files for comprehensive testing
import enMessages from '@/i18n/locales/en.json'
import deMessages from '@/i18n/locales/de.json'
import trMessages from '@/i18n/locales/tr.json'
import arMessages from '@/i18n/locales/ar.json'

// Mock i18n with actual translations
const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: enMessages,
    de: deMessages,
    tr: trMessages,
    ar: arMessages
  }
})

// Create Pinia instance for state management
const pinia = createPinia()

// Global test configuration
config.global.plugins = [i18n, pinia]
config.global.stubs = {
  'router-link': {
    template: '<a><slot /></a>',
    props: ['to']
  },
  'router-view': {
    template: '<div><slot /></div>'
  }
}

// Mock localStorage with proper implementation
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageMock.store[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageMock.store[key]
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {}
  }),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

// Mock fetch
global.fetch = vi.fn()

// Mock router with proper exports
vi.mock('vue-router', async (importOriginal) => {
  const actual = await importOriginal() as any
  return {
    ...actual,
    useRouter: () => ({
      push: vi.fn(),
      replace: vi.fn(),
      go: vi.fn(),
      back: vi.fn(),
      forward: vi.fn(),
      currentRoute: { value: { path: '/', params: {}, query: {}, meta: {} } }
    }),
    useRoute: () => ({
      path: '/',
      params: {},
      query: {},
      meta: {},
    }),
    createRouter: actual.createRouter,
    createWebHistory: actual.createWebHistory,
  }
})

// Mock Google Places API
Object.defineProperty(window, 'google', {
  value: {
    maps: {
      places: {
        PlacesService: vi.fn(() => ({
          getDetails: vi.fn(),
          findPlaceFromQuery: vi.fn(),
          textSearch: vi.fn()
        })),
        PlacesServiceStatus: {
          OK: 'OK',
          ZERO_RESULTS: 'ZERO_RESULTS',
          OVER_QUERY_LIMIT: 'OVER_QUERY_LIMIT',
          REQUEST_DENIED: 'REQUEST_DENIED',
          INVALID_REQUEST: 'INVALID_REQUEST'
        }
      },
      Map: vi.fn(),
      LatLng: vi.fn(),
      Marker: vi.fn()
    }
  },
  writable: true
})

// Mock services
vi.mock('@/services/business', () => ({
  businessService: {
    getBusinesses: vi.fn(),
    getBusiness: vi.fn(),
    createBusiness: vi.fn(),
    updateBusiness: vi.fn(),
    deleteBusiness: vi.fn(),
    importReviews: vi.fn(),
    getBusinessStats: vi.fn(),
    getConsolidatedStats: vi.fn(),
    searchGooglePlaces: vi.fn(),
    getGooglePlaceDetails: vi.fn(),
    getImportStatus: vi.fn(),
    getRealTimeImportStatus: vi.fn(),
    getImportHistory: vi.fn(),
    startManualImport: vi.fn()
  }
}))

vi.mock('@/services/reports', () => ({
  reportsService: {
    getReportConfiguration: vi.fn(),
    updateReportConfiguration: vi.fn(),
    sendTestReport: vi.fn(),
    generateReport: vi.fn(),
    getReportHistory: vi.fn()
  }
}))

vi.mock('@/services/auth', () => ({
  authService: {
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    getCurrentUser: vi.fn(),
    refreshToken: vi.fn()
  }
}))

vi.mock('@/services/googlePlaces', () => ({
  googlePlacesService: {
    initialize: vi.fn(),
    searchPlaces: vi.fn(),
    getPlaceDetails: vi.fn(),
    getPhotoUrl: vi.fn(),
    getRateLimitStatus: vi.fn()
  },
  GooglePlacesError: class GooglePlacesError extends Error {
    constructor(message: string, public code?: string, public status?: number) {
      super(message)
      this.name = 'GooglePlacesError'
    }
  }
}))

// Mock stores
vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: vi.fn(() => ({
    showSuccess: vi.fn(),
    showError: vi.fn(),
    showWarning: vi.fn(),
    showInfo: vi.fn(),
    notifications: [],
    unreadCount: 0
  }))
}))

vi.mock('@/stores/auth', () => ({
  useAuthStore: vi.fn(() => ({
    user: null,
    token: null,
    loading: false,
    error: null,
    isAuthenticated: false,
    userRole: null,
    userLanguage: 'en',
    login: vi.fn(),
    register: vi.fn(),
    logout: vi.fn(),
    clearError: vi.fn()
  }))
}))

vi.mock('@/stores/business', () => ({
  useBusinessStore: vi.fn(() => ({
    businesses: [],
    currentBusiness: null,
    loading: false,
    error: null,
    fetchBusinesses: vi.fn(),
    createBusiness: vi.fn(),
    updateBusiness: vi.fn(),
    deleteBusiness: vi.fn(),
    setCurrentBusiness: vi.fn()
  }))
}))

// Mock composables
vi.mock('@/composables/useGooglePlaces', () => ({
  useGooglePlaces: () => ({
    isLoaded: vi.fn(() => true),
    load: vi.fn(),
    searchPlaces: vi.fn(),
    getPlaceDetails: vi.fn()
  })
}))