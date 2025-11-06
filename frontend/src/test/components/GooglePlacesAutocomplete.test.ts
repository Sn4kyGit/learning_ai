/**
 * Tests for Google Places Autocomplete component
 * Covers API calls, autocomplete functionality, and validation
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import GooglePlacesAutocomplete from '@/components/businesses/GooglePlacesAutocomplete.vue'
import { useGooglePlaces } from '@/composables/useGooglePlaces'

// Mock dependencies
vi.mock('@/composables/useGooglePlaces')

describe('GooglePlacesAutocomplete', () => {
  let wrapper: any
  let mockGooglePlaces: any
  let i18n: any

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // Create i18n instance
    i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: {
        en: {
          places: {
            searchPlaceholder: 'Search for your business...',
            noResults: 'No results found',
            selectPlace: 'Select a place',
            loading: 'Searching...',
            error: 'Search failed',
            tryAgain: 'Try again',
            clearSearch: 'Clear search',
            poweredByGoogle: 'Powered by Google'
          },
          common: {
            loading: 'Loading...',
            error: 'Error'
          }
        }
      }
    })

    // Mock Google Places composable
    mockGooglePlaces = {
      autocompletePredictions: { value: [] },
      selectedPlace: { value: null },
      isLoading: { value: false },
      error: { value: null },
      isRateLimited: { value: false },
      getAutocompletePredictions: vi.fn(),
      getPlaceDetails: vi.fn(),
      clearResults: vi.fn(),
      clearError: vi.fn(),
      formatPlaceType: vi.fn((type: string) => type.replace('_', ' ')),
      formatRating: vi.fn((rating: number, total?: number) => 
        `${rating} ⭐${total ? ` (${total})` : ''}`
      )
    }

    vi.mocked(useGooglePlaces).mockReturnValue(mockGooglePlaces)
  })

  const createWrapper = (props = {}) => {
    return mount(GooglePlacesAutocomplete, {
      props: {
        modelValue: '',
        placeholder: 'Search for your business...',
        ...props
      },
      global: {
        plugins: [i18n]
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders search input', () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input[type="text"]')
      expect(input.exists()).toBe(true)
      expect(input.attributes('placeholder')).toBe('Search for your business...')
    })

    it('renders with custom placeholder', () => {
      wrapper = createWrapper({ placeholder: 'Custom placeholder' })
      
      const input = wrapper.find('input')
      expect(input.attributes('placeholder')).toBe('Custom placeholder')
    })

    it('renders clear button when input has value', async () => {
      wrapper = createWrapper({ modelValue: 'test search' })
      
      const clearButton = wrapper.find('[data-testid="clear-button"]')
      expect(clearButton.exists()).toBe(true)
    })

    it('does not render clear button when input is empty', () => {
      wrapper = createWrapper()
      
      const clearButton = wrapper.find('[data-testid="clear-button"]')
      expect(clearButton.exists()).toBe(false)
    })

    it('renders loading indicator when searching', async () => {
      mockGooglePlaces.isLoading.value = true
      wrapper = createWrapper()
      
      expect(wrapper.find('.loading-spinner').exists()).toBe(true)
    })

    it('renders Google attribution', () => {
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('Powered by Google')
    })
  })

  describe('Autocomplete Functionality', () => {
    it('triggers search on input change', async () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input')
      await input.setValue('restaurant')
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 300))
      
      expect(mockGooglePlaces.getAutocompletePredictions).toHaveBeenCalledWith('restaurant')
    })

    it('debounces search input', async () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input')
      
      // Rapid typing
      await input.setValue('r')
      await input.setValue('re')
      await input.setValue('res')
      await input.setValue('rest')
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // Should only call once with final value
      expect(mockGooglePlaces.getAutocompletePredictions).toHaveBeenCalledTimes(1)
      expect(mockGooglePlaces.getAutocompletePredictions).toHaveBeenCalledWith('rest')
    })

    it('shows autocomplete predictions', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St, City'
          },
          types: ['restaurant']
        },
        {
          place_id: 'ChIJTest2',
          structured_formatting: {
            main_text: 'Restaurant Two',
            secondary_text: '456 Oak Ave, City'
          },
          types: ['restaurant']
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const predictions = wrapper.findAll('.prediction-item')
      expect(predictions).toHaveLength(2)
      expect(predictions[0].text()).toContain('Restaurant One')
      expect(predictions[1].text()).toContain('Restaurant Two')
    })

    it('handles prediction selection', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St, City'
          },
          types: ['restaurant']
        }
      ]
      
      const mockPlaceDetails = {
        place_id: 'ChIJTest1',
        name: 'Restaurant One',
        formatted_address: '123 Main St, City',
        types: ['restaurant'],
        rating: 4.5,
        user_ratings_total: 100
      }
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      mockGooglePlaces.getPlaceDetails.mockResolvedValue(mockPlaceDetails)
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      const prediction = wrapper.find('.prediction-item')
      await prediction.trigger('click')
      
      expect(mockGooglePlaces.getPlaceDetails).toHaveBeenCalledWith('ChIJTest1')
      expect(wrapper.emitted('place-selected')).toBeTruthy()
      expect(wrapper.emitted('place-selected')[0][0]).toEqual(mockPlaceDetails)
    })

    it('clears predictions when input is cleared', async () => {
      wrapper = createWrapper({ modelValue: 'test' })
      
      const clearButton = wrapper.find('[data-testid="clear-button"]')
      await clearButton.trigger('click')
      
      expect(mockGooglePlaces.clearResults).toHaveBeenCalled()
      expect(wrapper.emitted('update:modelValue')).toBeTruthy()
      expect(wrapper.emitted('update:modelValue')[0][0]).toBe('')
    })

    it('shows no results message when no predictions found', async () => {
      mockGooglePlaces.autocompletePredictions.value = []
      wrapper = createWrapper({ modelValue: 'nonexistent' })
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('No results found')
    })
  })

  describe('Keyboard Navigation', () => {
    beforeEach(async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          }
        },
        {
          place_id: 'ChIJTest2',
          structured_formatting: {
            main_text: 'Restaurant Two',
            secondary_text: '456 Oak Ave'
          }
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
    })

    it('navigates predictions with arrow keys', async () => {
      const input = wrapper.find('input')
      
      await input.trigger('keydown.down')
      expect(wrapper.vm.selectedIndex).toBe(0)
      
      await input.trigger('keydown.down')
      expect(wrapper.vm.selectedIndex).toBe(1)
      
      await input.trigger('keydown.up')
      expect(wrapper.vm.selectedIndex).toBe(0)
    })

    it('selects prediction with enter key', async () => {
      const input = wrapper.find('input')
      
      await input.trigger('keydown.down') // Select first item
      await input.trigger('keydown.enter')
      
      expect(mockGooglePlaces.getPlaceDetails).toHaveBeenCalledWith('ChIJTest1')
    })

    it('closes predictions with escape key', async () => {
      const input = wrapper.find('input')
      
      await input.trigger('keydown.escape')
      
      expect(wrapper.vm.showPredictions).toBe(false)
    })

    it('highlights selected prediction', async () => {
      const input = wrapper.find('input')
      
      await input.trigger('keydown.down')
      await wrapper.vm.$nextTick()
      
      const predictions = wrapper.findAll('.prediction-item')
      expect(predictions[0].classes()).toContain('selected')
    })
  })

  describe('Error Handling', () => {
    it('displays error message when search fails', async () => {
      mockGooglePlaces.error.value = 'Search failed'
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('Search failed')
    })

    it('shows retry button on error', async () => {
      mockGooglePlaces.error.value = 'Search failed'
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const retryButton = wrapper.find('[data-testid="retry-button"]')
      expect(retryButton.exists()).toBe(true)
    })

    it('retries search when retry button is clicked', async () => {
      mockGooglePlaces.error.value = 'Search failed'
      wrapper = createWrapper({ modelValue: 'restaurant' })
      
      await wrapper.vm.$nextTick()
      
      const retryButton = wrapper.find('[data-testid="retry-button"]')
      await retryButton.trigger('click')
      
      expect(mockGooglePlaces.clearError).toHaveBeenCalled()
      expect(mockGooglePlaces.getAutocompletePredictions).toHaveBeenCalledWith('restaurant')
    })

    it('handles rate limiting gracefully', async () => {
      mockGooglePlaces.isRateLimited.value = true
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('rate limit')
    })

    it('disables input when rate limited', async () => {
      mockGooglePlaces.isRateLimited.value = true
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const input = wrapper.find('input')
      expect(input.attributes('disabled')).toBeDefined()
    })
  })

  describe('Place Details Display', () => {
    it('shows place rating when available', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          },
          rating: 4.5,
          user_ratings_total: 100
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('4.5 ⭐ (100)')
    })

    it('shows place types', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          },
          types: ['restaurant', 'food', 'establishment']
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('restaurant')
    })

    it('shows place photos when available', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          },
          photos: [{ photo_reference: 'photo123' }]
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const photo = wrapper.find('.place-photo')
      expect(photo.exists()).toBe(true)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA attributes', () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input')
      expect(input.attributes('role')).toBe('combobox')
      expect(input.attributes('aria-expanded')).toBeDefined()
      expect(input.attributes('aria-autocomplete')).toBe('list')
    })

    it('has proper ARIA labels for predictions', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          }
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const predictionsList = wrapper.find('[role="listbox"]')
      expect(predictionsList.exists()).toBe(true)
      
      const prediction = wrapper.find('[role="option"]')
      expect(prediction.exists()).toBe(true)
    })

    it('announces selection changes to screen readers', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          }
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      const input = wrapper.find('input')
      await input.trigger('keydown.down')
      
      expect(input.attributes('aria-activedescendant')).toBeDefined()
    })
  })

  describe('Performance Optimization', () => {
    it('implements debouncing for search requests', async () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input')
      
      // Rapid input changes
      for (let i = 0; i < 10; i++) {
        await input.setValue(`search${i}`)
      }
      
      // Wait for debounce
      await new Promise(resolve => setTimeout(resolve, 300))
      
      // Should only make one API call
      expect(mockGooglePlaces.getAutocompletePredictions).toHaveBeenCalledTimes(1)
    })

    it('cancels previous requests when new search is initiated', async () => {
      wrapper = createWrapper()
      
      const input = wrapper.find('input')
      
      await input.setValue('first search')
      await input.setValue('second search')
      
      // Check that request cancellation is implemented
      expect(wrapper.vm.cancelPreviousRequest).toBeDefined()
    })

    it('implements virtual scrolling for large result sets', async () => {
      // Create large prediction list
      const largePredictionList = Array.from({ length: 100 }, (_, i) => ({
        place_id: `ChIJTest${i}`,
        structured_formatting: {
          main_text: `Restaurant ${i}`,
          secondary_text: `Address ${i}`
        }
      }))
      
      mockGooglePlaces.autocompletePredictions.value = largePredictionList
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      // Check that virtual scrolling is implemented
      expect(wrapper.vm.virtualScrolling).toBeDefined()
    })
  })

  describe('Mobile Responsiveness', () => {
    it('adapts to mobile viewport', async () => {
      wrapper = createWrapper()
      
      // Simulate mobile viewport
      Object.defineProperty(window, 'innerWidth', {
        writable: true,
        configurable: true,
        value: 375
      })
      
      window.dispatchEvent(new Event('resize'))
      await wrapper.vm.$nextTick()
      
      expect(wrapper.find('.mobile-optimized').exists()).toBe(true)
    })

    it('shows mobile-friendly prediction layout', async () => {
      const mockPredictions = [
        {
          place_id: 'ChIJTest1',
          structured_formatting: {
            main_text: 'Restaurant One',
            secondary_text: '123 Main St'
          }
        }
      ]
      
      mockGooglePlaces.autocompletePredictions.value = mockPredictions
      wrapper = createWrapper()
      
      // Simulate mobile
      wrapper.vm.isMobile = true
      await wrapper.vm.$nextTick()
      
      const prediction = wrapper.find('.prediction-item')
      expect(prediction.classes()).toContain('mobile-layout')
    })
  })
})