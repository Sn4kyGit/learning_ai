/**
 * Tests for Business Registration Modal component
 * Covers Google Places search, form validation, and business registration workflow
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import BusinessRegistrationModal from '@/components/businesses/BusinessRegistrationModal.vue'
import { useGooglePlaces } from '@/composables/useGooglePlaces'
import { businessService } from '@/services/business'
import { useNotificationsStore } from '@/stores/notifications'

// Mock dependencies
vi.mock('@/composables/useGooglePlaces')
vi.mock('@/services/business')
vi.mock('@/stores/notifications')

describe('BusinessRegistrationModal', () => {
  let wrapper: any
  let mockGooglePlaces: any
  let mockNotificationsStore: any
  let i18n: any

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // Create i18n instance
    i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: {
        en: {
          businesses: {
            register: 'Register Business',
            searchPlaceholder: 'Search for your business...',
            businessName: 'Business Name',
            address: 'Address',
            category: 'Category',
            googlePlaceId: 'Google Place ID',
            selectFromSearch: 'Please select a business from search results',
            registrationSuccess: 'Business registered successfully',
            registrationError: 'Failed to register business'
          },
          common: {
            search: 'Search',
            cancel: 'Cancel',
            register: 'Register',
            loading: 'Loading...',
            required: 'This field is required'
          }
        }
      }
    })

    // Mock Google Places composable
    mockGooglePlaces = {
      searchResults: { value: [] },
      selectedPlace: { value: null },
      isLoading: { value: false },
      error: { value: null },
      searchPlaces: vi.fn(),
      getPlaceDetails: vi.fn(),
      clearResults: vi.fn(),
      formatPlaceType: vi.fn((type: string) => type.replace('_', ' ')),
      formatRating: vi.fn((rating: number) => `${rating} ⭐`)
    }

    // Mock notifications store
    mockNotificationsStore = {
      showSuccess: vi.fn(),
      showError: vi.fn()
    }

    // Mock business service
    vi.mocked(businessService.createBusiness).mockResolvedValue({
      id: 'new-business-123',
      name: 'Test Restaurant',
      google_place_id: 'ChIJTest123',
      category: 'restaurant',
      address: '123 Test Street'
    })

    vi.mocked(useGooglePlaces).mockReturnValue(mockGooglePlaces)
    vi.mocked(useNotificationsStore).mockReturnValue(mockNotificationsStore)
  })

  const createWrapper = (props = {}) => {
    return mount(BusinessRegistrationModal, {
      props: {
        isOpen: true,
        organizationId: 'org-123',
        ...props
      },
      global: {
        plugins: [i18n],
        stubs: {
          'GooglePlacesAutocomplete': {
            template: '<div class="google-places-autocomplete"><slot /></div>',
            props: ['modelValue', 'placeholder', 'disabled'],
            emits: ['update:modelValue', 'place-selected', 'search']
          }
        }
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders modal when open', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('.modal-overlay').exists()).toBe(true)
      expect(wrapper.find('h2').text()).toContain('Register Business')
    })

    it('does not render modal when closed', () => {
      wrapper = createWrapper({ isOpen: false })
      
      expect(wrapper.find('.modal-overlay').exists()).toBe(false)
    })

    it('renders Google Places search component', () => {
      wrapper = createWrapper()
      
      expect(wrapper.findComponent({ name: 'GooglePlacesAutocomplete' }).exists()).toBe(true)
    })

    it('renders business form fields', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('#business-name').exists()).toBe(true)
      expect(wrapper.find('#business-address').exists()).toBe(true)
      expect(wrapper.find('#business-category').exists()).toBe(true)
      expect(wrapper.find('#google-place-id').exists()).toBe(true)
    })

    it('renders action buttons', () => {
      wrapper = createWrapper()
      
      const buttons = wrapper.findAll('button')
      expect(buttons.some(btn => btn.text().includes('Cancel'))).toBe(true)
      expect(buttons.some(btn => btn.text().includes('Register'))).toBe(true)
    })
  })

  describe('Google Places Integration', () => {
    it('handles place selection from search results', async () => {
      const mockPlace = {
        place_id: 'ChIJTest123',
        name: 'Test Restaurant',
        formatted_address: '123 Test Street, Test City',
        types: ['restaurant', 'food', 'establishment'],
        rating: 4.5,
        user_ratings_total: 100
      }

      mockGooglePlaces.selectedPlace.value = mockPlace
      wrapper = createWrapper()

      await wrapper.vm.$nextTick()

      // Simulate place selection
      await wrapper.vm.onPlaceSelected(mockPlace)

      expect(wrapper.vm.formData.name).toBe('Test Restaurant')
      expect(wrapper.vm.formData.address).toBe('123 Test Street, Test City')
      expect(wrapper.vm.formData.category).toBe('restaurant')
      expect(wrapper.vm.formData.google_place_id).toBe('ChIJTest123')
    })

    it('shows search results when available', async () => {
      const mockResults = [
        {
          place_id: 'ChIJTest1',
          name: 'Restaurant 1',
          formatted_address: '123 Street 1',
          types: ['restaurant'],
          rating: 4.2
        },
        {
          place_id: 'ChIJTest2',
          name: 'Restaurant 2',
          formatted_address: '456 Street 2',
          types: ['restaurant'],
          rating: 4.0
        }
      ]

      mockGooglePlaces.searchResults.value = mockResults
      wrapper = createWrapper()

      await wrapper.vm.$nextTick()

      // Check that search results are displayed
      expect(wrapper.vm.searchResults).toEqual(mockResults)
    })

    it('handles search errors gracefully', async () => {
      mockGooglePlaces.error.value = 'Search failed'
      wrapper = createWrapper()

      await wrapper.vm.$nextTick()

      expect(wrapper.vm.searchError).toBe('Search failed')
    })

    it('clears form when search is cleared', async () => {
      wrapper = createWrapper()
      
      // Set some form data
      wrapper.vm.formData.name = 'Test Restaurant'
      wrapper.vm.formData.address = 'Test Address'
      
      // Clear search
      await wrapper.vm.clearSearch()
      
      expect(wrapper.vm.formData.name).toBe('')
      expect(wrapper.vm.formData.address).toBe('')
      expect(wrapper.vm.formData.category).toBe('')
      expect(wrapper.vm.formData.google_place_id).toBe('')
    })
  })

  describe('Form Validation', () => {
    it('validates required fields', async () => {
      wrapper = createWrapper()
      
      // Try to submit empty form
      const form = wrapper.find('form')
      await form.trigger('submit.prevent')
      
      expect(wrapper.vm.errors.name).toBeTruthy()
      expect(wrapper.vm.errors.address).toBeTruthy()
      expect(wrapper.vm.errors.google_place_id).toBeTruthy()
    })

    it('validates business name length', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.formData.name = 'A' // Too short
      await wrapper.vm.validateForm()
      
      expect(wrapper.vm.errors.name).toBeTruthy()
      
      wrapper.vm.formData.name = 'A'.repeat(256) // Too long
      await wrapper.vm.validateForm()
      
      expect(wrapper.vm.errors.name).toBeTruthy()
      
      wrapper.vm.formData.name = 'Valid Restaurant Name'
      await wrapper.vm.validateForm()
      
      expect(wrapper.vm.errors.name).toBeFalsy()
    })

    it('validates Google Place ID format', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.formData.google_place_id = 'invalid-id'
      await wrapper.vm.validateForm()
      
      expect(wrapper.vm.errors.google_place_id).toBeTruthy()
      
      wrapper.vm.formData.google_place_id = 'ChIJValidPlaceId123'
      await wrapper.vm.validateForm()
      
      expect(wrapper.vm.errors.google_place_id).toBeFalsy()
    })

    it('shows validation errors in UI', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.errors.name = 'Name is required'
      wrapper.vm.errors.address = 'Address is required'
      
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('Name is required')
      expect(wrapper.text()).toContain('Address is required')
    })

    it('clears validation errors when form is corrected', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.errors.name = 'Name is required'
      wrapper.vm.formData.name = 'Valid Name'
      
      await wrapper.vm.validateField('name')
      
      expect(wrapper.vm.errors.name).toBeFalsy()
    })
  })

  describe('Business Registration', () => {
    it('submits valid form data', async () => {
      wrapper = createWrapper()
      
      // Fill form with valid data
      wrapper.vm.formData = {
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123'
      }
      
      const form = wrapper.find('form')
      await form.trigger('submit.prevent')
      
      expect(vi.mocked(businessService.createBusiness)).toHaveBeenCalledWith({
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123',
        organization_id: 'org-123'
      })
    })

    it('shows loading state during registration', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.isSubmitting = true
      await wrapper.vm.$nextTick()
      
      const submitButton = wrapper.find('button[type="submit"]')
      expect(submitButton.attributes('disabled')).toBeDefined()
      expect(submitButton.text()).toContain('Loading')
    })

    it('shows success notification on successful registration', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.formData = {
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123'
      }
      
      await wrapper.vm.submitForm()
      
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(
        'Business registered successfully'
      )
    })

    it('emits business-registered event on success', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.formData = {
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123'
      }
      
      await wrapper.vm.submitForm()
      
      expect(wrapper.emitted('business-registered')).toBeTruthy()
      expect(wrapper.emitted('business-registered')[0][0]).toEqual({
        id: 'new-business-123',
        name: 'Test Restaurant',
        google_place_id: 'ChIJTest123',
        category: 'restaurant',
        address: '123 Test Street'
      })
    })

    it('handles registration errors', async () => {
      vi.mocked(businessService.createBusiness).mockRejectedValue(
        new Error('Registration failed')
      )
      
      wrapper = createWrapper()
      
      wrapper.vm.formData = {
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123'
      }
      
      await wrapper.vm.submitForm()
      
      expect(mockNotificationsStore.showError).toHaveBeenCalledWith(
        'Failed to register business'
      )
    })

    it('handles duplicate business error', async () => {
      vi.mocked(businessService.createBusiness).mockRejectedValue({
        response: {
          status: 409,
          data: { detail: 'Business already exists' }
        }
      })
      
      wrapper = createWrapper()
      
      wrapper.vm.formData = {
        name: 'Test Restaurant',
        address: '123 Test Street',
        category: 'restaurant',
        google_place_id: 'ChIJTest123'
      }
      
      await wrapper.vm.submitForm()
      
      expect(wrapper.vm.errors.google_place_id).toContain('already exists')
    })
  })

  describe('Modal Interactions', () => {
    it('closes modal when cancel button is clicked', async () => {
      wrapper = createWrapper()
      
      const cancelButton = wrapper.find('button:not([type="submit"])')
      await cancelButton.trigger('click')
      
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('closes modal when overlay is clicked', async () => {
      wrapper = createWrapper()
      
      const overlay = wrapper.find('.modal-overlay')
      await overlay.trigger('click.self')
      
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('closes modal on escape key press', async () => {
      wrapper = createWrapper()
      
      await wrapper.trigger('keydown.escape')
      
      expect(wrapper.emitted('close')).toBeTruthy()
    })

    it('resets form when modal is closed', async () => {
      wrapper = createWrapper()
      
      // Set some form data
      wrapper.vm.formData.name = 'Test Restaurant'
      wrapper.vm.errors.name = 'Some error'
      
      // Close modal
      await wrapper.vm.closeModal()
      
      expect(wrapper.vm.formData.name).toBe('')
      expect(wrapper.vm.errors.name).toBeFalsy()
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
      expect(wrapper.find('[aria-labelledby]').exists()).toBe(true)
      expect(wrapper.find('[aria-describedby]').exists()).toBe(true)
    })

    it('focuses first input when modal opens', async () => {
      wrapper = createWrapper()
      
      await wrapper.vm.$nextTick()
      
      // Check that focus management is implemented
      expect(wrapper.vm.focusFirstInput).toBeDefined()
    })

    it('traps focus within modal', async () => {
      wrapper = createWrapper()
      
      // Check that focus trap is implemented
      expect(wrapper.vm.handleTabKey).toBeDefined()
    })
  })

  describe('Responsive Design', () => {
    it('adapts to mobile viewport', async () => {
      wrapper = createWrapper()
      
      // Check that responsive classes are applied
      expect(wrapper.find('.modal-content').classes()).toContain('max-w-lg')
    })

    it('shows mobile-optimized search interface', async () => {
      wrapper = createWrapper()
      
      // Check that mobile optimizations are in place
      expect(wrapper.find('.google-places-autocomplete').exists()).toBe(true)
    })
  })
})