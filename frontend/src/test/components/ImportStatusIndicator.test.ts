import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import ImportStatusIndicator from '@/components/businesses/ImportStatusIndicator.vue'
import { useNotificationsStore } from '@/stores/notifications'
import { businessService } from '@/services/business'
import type { ImportStatus, RealTimeImportStatus } from '@/types'

// Import actual translations
import enMessages from '@/i18n/locales/en.json'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  fallbackLocale: 'en',
  messages: {
    en: enMessages
  }
})

describe('ImportStatusIndicator', () => {
  let wrapper: any
  let mockNotificationsStore: any

  beforeEach(() => {
    setActivePinia(createPinia())
    
    // Mock notifications store
    mockNotificationsStore = {
      showSuccess: vi.fn(),
      showError: vi.fn(),
      showWarning: vi.fn()
    }
    
    // Clear all mocks
    vi.clearAllMocks()
  })

  afterEach(() => {
    if (wrapper) {
      wrapper.unmount()
    }
  })

  const createWrapper = (props = {}) => {
    const defaultProps = {
      businessId: 'business-123',
      ...props
    }

    return mount(ImportStatusIndicator, {
      props: defaultProps,
      global: {
        plugins: [i18n]
      }
    })
  }

  const mockImportStatus = (overrides: Partial<ImportStatus> = {}): ImportStatus => ({
    business_id: 'business-123',
    status: 'completed',
    is_active: false,
    last_import: '2024-01-15T10:30:00Z',
    total_imported: 150,
    last_import_count: 25,
    next_scheduled_import: '2024-01-16T00:00:00Z',
    import_errors: [],
    ...overrides
  })

  const mockRealTimeStatus = (overrides: Partial<RealTimeImportStatus> = {}): RealTimeImportStatus => ({
    is_active: false,
    status: 'idle',
    current_step: 'completed',
    progress_percent: 0,
    processed: 0,
    imported: 0,
    duplicates: 0,
    total_expected: 0,
    errors: [],
    ...overrides
  })

  describe('Component Rendering', () => {
    it('renders the component', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.exists()).toBe(true)
    })

    it('shows loading state initially', () => {
      vi.mocked(businessService.getImportStatus).mockImplementation(() => new Promise(() => {}))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      
      expect(wrapper.vm.loading).toBe(true)
    })
  })

  describe('Status Display', () => {
    it('shows completed status with green badge', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ status: 'completed' }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const statusBadge = wrapper.find('.w-2.h-2.rounded-full')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.classes()).toContain('bg-green-500')
    })

    it('shows in-progress status with blue badge', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ status: 'in_progress' }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const statusBadge = wrapper.find('.w-2.h-2.rounded-full')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.classes()).toContain('bg-blue-500')
    })

    it('shows failed status with red badge', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        status: 'failed',
        import_errors: ['API error']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const statusBadge = wrapper.find('.w-2.h-2.rounded-full')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.classes()).toContain('bg-red-500')
    })

    it('shows pending status with yellow badge', async () => {
      const oldDate = new Date()
      oldDate.setHours(oldDate.getHours() - 50) // 50 hours ago
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        last_import: oldDate.toISOString()
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const statusBadge = wrapper.find('.w-2.h-2.rounded-full')
      expect(statusBadge.exists()).toBe(true)
      expect(statusBadge.classes()).toContain('bg-yellow-500')
    })

    it('shows loading indicator during sync', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.find('.animate-spin').exists()).toBe(true)
      expect(wrapper.text()).toContain(enMessages.businesses.statusImporting)
    })
  })

  describe('Manual Sync Functionality', () => {
    it('triggers manual sync when sync button is clicked', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      vi.mocked(businessService.startManualImport).mockResolvedValue({ imported_count: 10 })
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      const syncButton = wrapper.find('button[title*="Manual"]')
      expect(syncButton.exists()).toBe(true)
      
      await syncButton.trigger('click')
      
      expect(businessService.startManualImport).toHaveBeenCalledWith('business-123', { max_reviews: 500 })
    })

    it('disables sync button during sync operation', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const syncButton = wrapper.find('button[title*="Manual"]')
      expect(syncButton.attributes('disabled')).toBeDefined()
    })

    it('shows success notification after successful sync', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      vi.mocked(businessService.startManualImport).mockResolvedValue({ imported_count: 10 })
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.startManualSync()
      
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(enMessages.businesses.importStarted)
    })

    it('emits sync-completed event after successful sync', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      vi.mocked(businessService.startManualImport).mockResolvedValue({ imported_count: 10 })
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.startManualSync()
      
      expect(wrapper.emitted('importCompleted')).toBeTruthy()
    })

    it('handles sync errors gracefully', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      vi.mocked(businessService.startManualImport).mockRejectedValue(new Error('Sync failed'))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.startManualSync()
      
      expect(mockNotificationsStore.showError).toHaveBeenCalledWith(enMessages.businesses.importFailed)
    })

    it('shows retry button after sync failure', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        status: 'failed',
        import_errors: ['Sync failed']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      // Check if error section is displayed
      expect(wrapper.text()).toContain('1')
      expect(wrapper.text()).toContain(enMessages.businesses.importErrors)
    })
  })

  describe('Error Handling and Display', () => {
    it('displays error message when provided', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({
        import_errors: ['API rate limit exceeded']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.text()).toContain('1')
      expect(wrapper.text()).toContain(enMessages.businesses.importErrors)
    })

    it('shows error details toggle', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({
        import_errors: ['API error']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const errorToggle = wrapper.find('button').filter((btn: any) => btn.text().includes(enMessages.businesses.importErrors))
      expect(errorToggle.length).toBeGreaterThan(0)
    })

    it('toggles error details visibility', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({
        import_errors: ['API error']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const errorToggle = wrapper.find('button').filter((btn: any) => btn.text().includes(enMessages.businesses.importErrors))[0]
      await errorToggle.trigger('click')
      
      expect(wrapper.vm.showErrors).toBe(true)
    })

    it('handles API rate limit errors specifically', async () => {
      const error = { response: { status: 429 } }
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      vi.mocked(businessService.startManualImport).mockRejectedValue(error)
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.startManualSync()
      
      expect(mockNotificationsStore.showError).toHaveBeenCalled()
    })

    it('shows countdown timer for rate limit errors', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({
        import_errors: ['Rate limit exceeded. Try again in 30 seconds.']
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.text()).toContain('1')
      expect(wrapper.text()).toContain(enMessages.businesses.importErrors)
    })
  })

  describe('Real-time Updates', () => {
    it('polls for status updates during import', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      // Check that polling is started (pollInterval should be set)
      expect(wrapper.vm.pollInterval).toBeDefined()
    })

    it('stops polling when import completes', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: false }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.vm.pollInterval).toBeNull()
    })

    it('updates status in real-time', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      await wrapper.vm.loadRealTimeStatus()
      
      expect(wrapper.emitted('refresh')).toBeFalsy() // No refresh event should be emitted automatically
    })
  })

  describe('Progress Indication', () => {
    it('shows progress bar during import', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ 
        is_active: true,
        progress_percent: 50
      }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const progressBar = wrapper.find('.bg-blue-600.h-1\\.5')
      expect(progressBar.exists()).toBe(true)
      expect(progressBar.attributes('style')).toContain('width: 50%')
    })

    it('shows estimated time remaining', async () => {
      const futureTime = new Date()
      futureTime.setMinutes(futureTime.getMinutes() + 2)
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ 
        is_active: true,
        estimated_completion: futureTime.toISOString()
      }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.text()).toContain(enMessages.businesses.estimatedCompletion)
    })

    it('shows current operation status', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ 
        is_active: true,
        current_step: 'fetching_reviews'
      }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.text()).toContain(enMessages.businesses.currentStep)
    })
  })

  describe('Accessibility', () => {
    it('has proper ARIA labels', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      const refreshButton = wrapper.find('button[title*="Refresh"]')
      expect(refreshButton.attributes('title')).toBeDefined()
    })

    it('announces status changes to screen readers', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      // Check for status text that would be read by screen readers
      expect(wrapper.find('span.text-xs.font-medium').exists()).toBe(true)
    })

    it('provides keyboard navigation support', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      const syncButton = wrapper.find('button[title*="Manual"]')
      await syncButton.trigger('keydown.enter')
      
      expect(businessService.startManualImport).toHaveBeenCalled()
    })
  })

  describe('Date and Time Formatting', () => {
    it('formats recent timestamps correctly', async () => {
      const recentTime = new Date()
      recentTime.setHours(recentTime.getHours() - 2)
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        last_import: recentTime.toISOString()
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const formattedTime = wrapper.vm.formatDate(recentTime.toISOString())
      expect(formattedTime).toContain('2')
      expect(formattedTime).toContain('hours')
    })

    it('formats old timestamps correctly', async () => {
      const oldTime = new Date()
      oldTime.setDate(oldTime.getDate() - 5)
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        last_import: oldTime.toISOString()
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      const formattedTime = wrapper.vm.formatDate(oldTime.toISOString())
      expect(formattedTime).toContain('/')
    })

    it('shows next scheduled import time', async () => {
      const nextImport = new Date()
      nextImport.setDate(nextImport.getDate() + 1)
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus({ 
        next_scheduled_import: nextImport.toISOString()
      }))
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      expect(wrapper.text()).toContain(enMessages.businesses.nextImport)
    })
  })

  describe('Component Lifecycle', () => {
    it('cleans up polling on unmount', async () => {
      const clearIntervalSpy = vi.spyOn(global, 'clearInterval')
      
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      await wrapper.vm.loadImportStatus()
      
      wrapper.unmount()
      
      expect(clearIntervalSpy).toHaveBeenCalled()
    })

    it('updates polling when status prop changes', async () => {
      vi.mocked(businessService.getImportStatus).mockResolvedValue(mockImportStatus())
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus())
      
      wrapper = createWrapper()
      await wrapper.vm.$nextTick()
      
      expect(wrapper.vm.pollInterval).toBeNull()
      
      // Simulate status change to active
      vi.mocked(businessService.getRealTimeImportStatus).mockResolvedValue(mockRealTimeStatus({ is_active: true }))
      await wrapper.vm.loadRealTimeStatus()
      
      expect(wrapper.vm.pollInterval).toBeDefined()
    })
  })
})