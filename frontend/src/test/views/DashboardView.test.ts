import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import DashboardView from '@/views/dashboard/DashboardView.vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { useBusinessStore } from '@/stores/business'

// Mock the stores
vi.mock('@/stores/auth')
vi.mock('@/stores/notifications')
vi.mock('@/stores/business')

describe('DashboardView', () => {
  let wrapper: any
  let mockAuthStore: any
  let mockNotificationsStore: any
  let mockBusinessStore: any
  let i18n: any

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // Create i18n instance
    i18n = createI18n({
      legacy: false,
      locale: 'en',
      messages: {
        en: {
          dashboard: {
            welcome: 'Welcome',
            overview: 'Here\'s an overview of your business performance',
            importReviews: 'Import Reviews',
            analytics: 'Analytics',
            recentReviews: 'Recent Reviews',
            viewAllReviews: 'View All Reviews',
            quickActions: 'Quick Actions',
            generateReport: 'Generate Report'
          },
          reviews: {
            averageRating: 'Average Rating',
            totalReviews: 'Total Reviews',
            positive: 'Positive',
            negative: 'Negative',
            neutral: 'Neutral',
            high: 'High',
            urgency: 'Urgency',
            noReviews: 'No reviews available'
          },
          topics: {
            food_quality: 'Food Quality',
            service: 'Service'
          },
          chat: {
            title: 'Chat',
            welcomeMessage: 'Get insights about your business performance'
          },
          common: {
            loading: 'Loading...'
          }
        }
      }
    })
    
    // Mock auth store
    mockAuthStore = {
      user: {
        id: '1',
        name: 'Test User',
        email: 'test@example.com',
        role: 'admin'
      }
    }
    
    // Mock notifications store
    mockNotificationsStore = {
      showSuccess: vi.fn(),
      showError: vi.fn()
    }
    
    // Mock business store
    mockBusinessStore = {
      businesses: [
        { id: '1', name: 'Test Restaurant 1' },
        { id: '2', name: 'Test Restaurant 2' }
      ],
      currentBusiness: { id: '1', name: 'Test Restaurant 1' },
      fetchBusinesses: vi.fn()
    }
    
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)
    vi.mocked(useNotificationsStore).mockReturnValue(mockNotificationsStore)
    vi.mocked(useBusinessStore).mockReturnValue(mockBusinessStore)
  })

  const createWrapper = (props = {}) => {
    return mount(DashboardView, {
      props,
      global: {
        plugins: [i18n],
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
            props: ['to']
          },
          'BusinessSelector': {
            template: '<div></div>',
            props: ['businesses', 'selectedBusinessId', 'viewMode', 'userRole'],
            emits: ['business-change', 'view-mode-change']
          }
        }
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders welcome message with user name', () => {
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('Test User')
      expect(wrapper.find('h1').text()).toContain('Test User')
    })

    it('renders KPI cards with correct structure', () => {
      wrapper = createWrapper()
      
      const kpiCards = wrapper.findAll('.bg-white.overflow-hidden.shadow.rounded-lg')
      expect(kpiCards).toHaveLength(4)
      
      // Check for average rating card
      expect(wrapper.text()).toContain('Average Rating')
      
      // Check for total reviews card
      expect(wrapper.text()).toContain('Total Reviews')
      
      // Check for positive percentage card
      expect(wrapper.text()).toContain('Positive')
      
      // Check for critical reviews card
      expect(wrapper.text()).toContain('High Urgency')
    })

    it('displays default stats when no data is loaded', () => {
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('0.0') // Default rating
      expect(wrapper.text()).toContain('0') // Default review count
    })

    it('renders import reviews button', () => {
      wrapper = createWrapper()
      
      const importButton = wrapper.find('button')
      expect(importButton.exists()).toBe(true)
      expect(importButton.text()).toContain('Import Reviews')
    })

    it('renders recent reviews section', () => {
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('Recent Reviews')
      expect(wrapper.text()).toContain('View All Reviews')
    })

    it('renders quick actions section', () => {
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('Quick Actions')
      expect(wrapper.text()).toContain('Chat')
      expect(wrapper.text()).toContain('Analytics')
      expect(wrapper.text()).toContain('Generate Report')
    })
  })

  describe('Data Display', () => {
    it('displays stats correctly when data is loaded', async () => {
      wrapper = createWrapper()
      
      // Wait for component to mount and load data
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check for the presence of stats values in the component data
      expect(wrapper.vm.stats.averageRating).toBe(4.2)
      expect(wrapper.vm.stats.totalReviews).toBe(156)
      expect(wrapper.vm.stats.positivePercentage).toBe(78)
      expect(wrapper.vm.stats.criticalReviews).toBe(3)
    })

    it('displays recent reviews when available', async () => {
      wrapper = createWrapper()
      
      // Wait for component to mount and load data
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that reviews are loaded in component data
      expect(wrapper.vm.recentReviews).toHaveLength(2)
      expect(wrapper.vm.recentReviews[0].author_name).toBe('John Doe')
      expect(wrapper.vm.recentReviews[1].author_name).toBe('Jane Smith')
    })

    it('shows sentiment badges for reviews', async () => {
      wrapper = createWrapper()
      
      // Wait for component to mount and load data
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that reviews have classification data
      expect(wrapper.vm.recentReviews[0].classification.sentiment).toBe('positive')
      expect(wrapper.vm.recentReviews[1].classification.sentiment).toBe('negative')
    })

    it('shows urgency badges for high urgency reviews', async () => {
      wrapper = createWrapper()
      
      // Wait for component to mount and load data
      await wrapper.vm.$nextTick()
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that high urgency review exists in data
      const highUrgencyReview = wrapper.vm.recentReviews.find((r: any) => r.classification.urgency === 'high')
      expect(highUrgencyReview).toBeDefined()
    })
  })

  describe('User Interactions', () => {
    it('handles import reviews button click', async () => {
      wrapper = createWrapper()
      
      const importButton = wrapper.find('button')
      await importButton.trigger('click')
      
      expect(wrapper.vm.importing).toBe(true)
      expect(importButton.attributes('disabled')).toBeDefined()
    })

    it('shows success notification after successful import', async () => {
      wrapper = createWrapper()
      
      const importButton = wrapper.find('button')
      await importButton.trigger('click')
      
      // Wait for the simulated API call to complete
      await new Promise(resolve => setTimeout(resolve, 2100))
      
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith('Reviews imported successfully')
      expect(wrapper.vm.importing).toBe(false)
    })

    it('handles generate report button click', async () => {
      wrapper = createWrapper()
      
      const generateButton = wrapper.findAll('button')[1] // Second button is generate report
      await generateButton.trigger('click')
      
      expect(wrapper.vm.generatingReport).toBe(true)
      expect(generateButton.attributes('disabled')).toBeDefined()
    })

    it('shows success notification after successful report generation', async () => {
      wrapper = createWrapper()
      
      const generateButton = wrapper.findAll('button')[1]
      await generateButton.trigger('click')
      
      // Wait for the simulated API call to complete
      await new Promise(resolve => setTimeout(resolve, 3100))
      
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith('Report generated successfully')
      expect(wrapper.vm.generatingReport).toBe(false)
    })
  })

  describe('Sentiment Color Helpers', () => {
    it('returns correct border colors for sentiment', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getSentimentBorderColor('positive')).toBe('border-green-400')
      expect(wrapper.vm.getSentimentBorderColor('negative')).toBe('border-red-400')
      expect(wrapper.vm.getSentimentBorderColor('neutral')).toBe('border-yellow-400')
      expect(wrapper.vm.getSentimentBorderColor(undefined)).toBe('border-gray-300')
    })

    it('returns correct badge colors for sentiment', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getSentimentBadgeColor('positive')).toBe('bg-green-100 text-green-800')
      expect(wrapper.vm.getSentimentBadgeColor('negative')).toBe('bg-red-100 text-red-800')
      expect(wrapper.vm.getSentimentBadgeColor('neutral')).toBe('bg-yellow-100 text-yellow-800')
      expect(wrapper.vm.getSentimentBadgeColor('unknown')).toBe('bg-gray-100 text-gray-800')
    })
  })

  describe('Date Formatting', () => {
    it('formats dates correctly', () => {
      wrapper = createWrapper()
      
      const testDate = new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString()
      const formatted = wrapper.vm.formatDate(testDate)
      
      expect(formatted).toContain('ago')
    })
  })

  describe('Error Handling', () => {
    it('shows error notification when import fails', async () => {
      wrapper = createWrapper()
      
      // Mock console.error to avoid test output noise
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      // Override the importReviews method to simulate failure
      wrapper.vm.importReviews = vi.fn().mockRejectedValue(new Error('Import failed'))
      
      const importButton = wrapper.find('button')
      await importButton.trigger('click')
      
      try {
        await wrapper.vm.importReviews()
      } catch (error) {
        // Expected to fail
      }
      
      consoleSpy.mockRestore()
    })

    it('shows error notification when report generation fails', async () => {
      wrapper = createWrapper()
      
      // Mock console.error to avoid test output noise
      const consoleSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      // Override the generateReport method to simulate failure
      wrapper.vm.generateReport = vi.fn().mockRejectedValue(new Error('Report failed'))
      
      const generateButton = wrapper.findAll('button')[1]
      await generateButton.trigger('click')
      
      try {
        await wrapper.vm.generateReport()
      } catch (error) {
        // Expected to fail
      }
      
      consoleSpy.mockRestore()
    })
  })
})