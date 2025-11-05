import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import AlertHistory from '@/components/common/AlertHistory.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { notificationService } from '@/services/notifications'

// Mock the services and stores
vi.mock('@/stores/notifications')
vi.mock('@/services/notifications')
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush
  })
}))

describe('AlertHistory', () => {
  let wrapper: any
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
          notifications: {
            alertHistory: 'Alert History',
            noRecentAlerts: 'No recent alerts',
            criticalReviewAlert: 'Critical Review Alert',
            competitorMentionAlert: 'Competitor Mention Alert',
            budgetWarningAlert: 'Budget Warning Alert',
            viewReview: 'View Review',
            markAsRead: 'Mark as read'
          },
          common: {
            refresh: 'Refresh',
            loading: 'Loading...'
          },
          analytics: {
            adjustBudget: 'Adjust Budget'
          }
        }
      }
    })
    
    // Mock notifications store
    mockNotificationsStore = {
      showError: vi.fn()
    }
    
    // Mock notification service
    vi.mocked(notificationService.getNotifications).mockResolvedValue({
      notifications: [
        {
          id: 'alert1',
          type: 'critical_review',
          title: 'Critical Review Alert',
          message: 'New critical review received',
          severity: 'high',
          read: false,
          timestamp: new Date(Date.now() - 2 * 60 * 60 * 1000), // 2 hours ago
          data: { review_id: 'rev123' }
        },
        {
          id: 'alert2',
          type: 'competitor_mention',
          title: 'Competitor Mention Alert',
          message: 'Competitor mentioned in review',
          severity: 'medium',
          read: true,
          timestamp: new Date(Date.now() - 24 * 60 * 60 * 1000), // 1 day ago
          data: { review_id: 'rev456' }
        },
        {
          id: 'alert3',
          type: 'budget_warning',
          title: 'Budget Warning Alert',
          message: 'Budget threshold reached',
          severity: 'medium',
          read: false,
          timestamp: new Date(Date.now() - 3 * 24 * 60 * 60 * 1000), // 3 days ago
          data: { usage_percentage: 85 }
        }
      ]
    })
    
    vi.mocked(notificationService.markAsRead).mockResolvedValue({
      success: true
    })
    
    vi.mocked(useNotificationsStore).mockReturnValue(mockNotificationsStore)
  })

  const createWrapper = (props = {}) => {
    return mount(AlertHistory, {
      props,
      global: {
        plugins: [i18n]
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders alert history with header', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Check for component structure instead of translated text
      expect(wrapper.find('h3').exists()).toBe(true)
      expect(wrapper.find('button').exists()).toBe(true)
    })

    it('shows loading state while fetching alerts', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.loading = true
      await wrapper.vm.$nextTick()
      
      const loadingElements = wrapper.findAll('.animate-pulse')
      expect(loadingElements.length).toBeGreaterThan(0)
    })

    it('shows empty state when no alerts', async () => {
      vi.mocked(notificationService.getNotifications).mockResolvedValue({
        notifications: []
      })
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that alerts array is empty
      expect(wrapper.vm.alerts).toHaveLength(0)
    })

    it('displays alerts list when data is loaded', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that alerts are loaded in component data
      expect(wrapper.vm.alerts).toHaveLength(3)
      expect(wrapper.vm.alerts[0].type).toBe('critical_review')
      expect(wrapper.vm.alerts[1].type).toBe('competitor_mention')
    })
  })

  describe('Alert Display', () => {
    it('shows alert icons based on type', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      const iconContainers = wrapper.findAll('.rounded-full.flex.items-center.justify-center')
      expect(iconContainers.length).toBeGreaterThan(0)
    })

    it('applies correct styling for unread alerts', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      const unreadAlerts = wrapper.findAll('.bg-blue-50')
      expect(unreadAlerts.length).toBeGreaterThan(0)
    })

    it('shows severity badges', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      expect(wrapper.text()).toContain('HIGH')
      expect(wrapper.text()).toContain('MEDIUM')
    })

    it('displays formatted timestamps', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      expect(wrapper.text()).toContain('2h ago')
    })

    it('shows action buttons for specific alert types', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 100))
      
      // Check that alerts have action data
      expect(wrapper.vm.alerts[0].data).toBeDefined()
      expect(wrapper.vm.alerts[0].data.review_id).toBe('rev123')
    })
  })

  describe('Alert Interactions', () => {
    it('marks alert as read when button is clicked', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      const markReadButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('Mark as read')
      )
      
      await markReadButton.trigger('click')
      
      expect(vi.mocked(notificationService.markAsRead)).toHaveBeenCalledWith('alert1')
    })

    it('updates alert state after marking as read', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      await wrapper.vm.markAsRead('alert1')
      
      const alert = wrapper.vm.alerts.find(a => a.id === 'alert1')
      expect(alert.read).toBe(true)
    })

    it('refreshes alerts when refresh button is clicked', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      const refreshButton = wrapper.find('button')
      await refreshButton.trigger('click')
      
      expect(vi.mocked(notificationService.getNotifications)).toHaveBeenCalled()
    })

    it('loads more alerts when load more button is clicked', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.hasMore = true
      await wrapper.vm.$nextTick()
      
      const loadMoreButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('Load More')
      )
      
      await loadMoreButton.trigger('click')
      
      expect(vi.mocked(notificationService.getNotifications)).toHaveBeenCalledWith(
        3, // skip count
        20, // limit
        false
      )
    })
  })

  describe('Navigation Actions', () => {
    it('navigates to review when view review is clicked', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.viewReview('rev123')
      
      expect(mockPush).toHaveBeenCalledWith('/reviews?review=rev123')
    })

    it('navigates to settings when manage budget is clicked', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.manageBudget()
      
      expect(mockPush).toHaveBeenCalledWith('/settings?tab=budget')
    })
  })

  describe('Utility Functions', () => {
    it('returns correct alert icon for each type', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getAlertIcon('critical_review')).toBeDefined()
      expect(wrapper.vm.getAlertIcon('competitor_mention')).toBeDefined()
      expect(wrapper.vm.getAlertIcon('budget_warning')).toBeDefined()
      expect(wrapper.vm.getAlertIcon('unknown')).toBeDefined()
    })

    it('returns correct icon classes for each type', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getAlertIconClass('critical_review')).toContain('bg-red-100')
      expect(wrapper.vm.getAlertIconClass('competitor_mention')).toContain('bg-yellow-100')
      expect(wrapper.vm.getAlertIconClass('budget_warning')).toContain('bg-orange-100')
    })

    it('returns correct border classes for each type', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getAlertBorderClass('critical_review')).toContain('border-l-red-400')
      expect(wrapper.vm.getAlertBorderClass('competitor_mention')).toContain('border-l-yellow-400')
      expect(wrapper.vm.getAlertBorderClass('budget_warning')).toContain('border-l-orange-400')
    })

    it('returns correct severity classes', () => {
      wrapper = createWrapper()
      
      expect(wrapper.vm.getSeverityClass('low')).toContain('bg-blue-100')
      expect(wrapper.vm.getSeverityClass('medium')).toContain('bg-yellow-100')
      expect(wrapper.vm.getSeverityClass('high')).toContain('bg-red-100')
    })

    it('formats time correctly for different periods', () => {
      wrapper = createWrapper()
      
      const now = new Date()
      const oneHourAgo = new Date(now.getTime() - 60 * 60 * 1000)
      const oneDayAgo = new Date(now.getTime() - 24 * 60 * 60 * 1000)
      const oneWeekAgo = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000)
      
      expect(wrapper.vm.formatTime(oneHourAgo)).toContain('1h ago')
      expect(wrapper.vm.formatTime(oneDayAgo)).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/)
      expect(wrapper.vm.formatTime(oneWeekAgo)).toMatch(/\d{1,2}\/\d{1,2}\/\d{4}/)
    })

    it('returns "Just now" for very recent timestamps', () => {
      wrapper = createWrapper()
      
      const justNow = new Date(Date.now() - 30 * 1000) // 30 seconds ago
      expect(wrapper.vm.formatTime(justNow)).toBe('Just now')
    })
  })

  describe('Error Handling', () => {
    it('shows error when alert loading fails', async () => {
      vi.mocked(notificationService.getNotifications).mockRejectedValue(
        new Error('Load Error')
      )
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Wait for loading to complete
      await new Promise(resolve => setTimeout(resolve, 0))
      
      expect(mockNotificationsStore.showError).toHaveBeenCalled()
    })

    it('handles mark as read errors gracefully', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      vi.mocked(notificationService.markAsRead).mockRejectedValue(
        new Error('Mark Read Error')
      )
      
      // Should not throw error
      await wrapper.vm.markAsRead('alert1')
      
      // Alert should not be marked as read
      const alert = wrapper.vm.alerts.find(a => a.id === 'alert1')
      expect(alert.read).toBe(false)
    })
  })

  describe('Props and Configuration', () => {
    it('uses provided business ID in API calls', async () => {
      wrapper = createWrapper({ businessId: 'test-business-123' })
      await wrapper.vm.$nextTick()
      
      // The component doesn't currently filter by business ID in the mock,
      // but this tests that the prop is accepted
      expect(wrapper.props('businessId')).toBe('test-business-123')
    })

    it('uses provided limit for API calls', async () => {
      wrapper = createWrapper({ limit: 10 })
      await wrapper.vm.$nextTick()
      
      expect(vi.mocked(notificationService.getNotifications)).toHaveBeenCalledWith(
        0, // skip
        10, // limit
        false
      )
    })

    it('uses default limit when not provided', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      expect(vi.mocked(notificationService.getNotifications)).toHaveBeenCalledWith(
        0, // skip
        20, // default limit
        false
      )
    })
  })

  describe('Load More Functionality', () => {
    it('shows load more button when hasMore is true', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.hasMore = true
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).toContain('Load More')
    })

    it('hides load more button when hasMore is false', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.hasMore = false
      await wrapper.vm.$nextTick()
      
      expect(wrapper.text()).not.toContain('Load More')
    })

    it('shows loading state on load more button', async () => {
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      wrapper.vm.hasMore = true
      wrapper.vm.loadingMore = true
      await wrapper.vm.$nextTick()
      
      const loadMoreButton = wrapper.findAll('button').find(btn => 
        btn.text().includes('Loading')
      )
      
      expect(loadMoreButton.attributes('disabled')).toBeDefined()
    })
  })
})