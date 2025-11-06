/**
 * Tests for Business Management Dashboard component
 * Covers business listing, management operations, and dashboard functionality
 */

import { describe, it, expect, vi, beforeEach } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { createI18n } from 'vue-i18n'
import BusinessManagementView from '@/views/businesses/BusinessManagementView.vue'
import { useBusinessStore } from '@/stores/business'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { businessService } from '@/services/business'

// Mock dependencies
vi.mock('@/stores/business')
vi.mock('@/stores/auth')
vi.mock('@/stores/notifications')
vi.mock('@/services/business')

describe('BusinessManagementView', () => {
  let wrapper: any
  let mockBusinessStore: any
  let mockAuthStore: any
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
            management: 'Business Management',
            addBusiness: 'Add Business',
            noBusinesses: 'No businesses found',
            businessName: 'Business Name',
            address: 'Address',
            category: 'Category',
            rating: 'Rating',
            reviews: 'Reviews',
            lastImport: 'Last Import',
            actions: 'Actions',
            edit: 'Edit',
            delete: 'Delete',
            view: 'View',
            importReviews: 'Import Reviews',
            deleteConfirm: 'Are you sure you want to delete this business?',
            deleteSuccess: 'Business deleted successfully',
            deleteError: 'Failed to delete business'
          },
          common: {
            loading: 'Loading...',
            search: 'Search',
            filter: 'Filter',
            cancel: 'Cancel',
            confirm: 'Confirm'
          }
        }
      }
    })

    // Mock business store
    mockBusinessStore = {
      businesses: [
        {
          id: '1',
          name: 'Restaurant One',
          address: '123 Main St',
          category: 'restaurant',
          avg_rating: 4.5,
          total_reviews: 150,
          last_import: '2024-01-15T10:30:00Z',
          import_status: 'completed'
        },
        {
          id: '2',
          name: 'Cafe Two',
          address: '456 Oak Ave',
          category: 'cafe',
          avg_rating: 4.2,
          total_reviews: 89,
          last_import: '2024-01-14T08:15:00Z',
          import_status: 'in_progress'
        }
      ],
      loading: false,
      fetchBusinesses: vi.fn(),
      deleteBusiness: vi.fn(),
      updateBusiness: vi.fn()
    }

    // Mock auth store
    mockAuthStore = {
      user: {
        id: '1',
        role: 'admin',
        organization_id: 'org-123'
      },
      hasPermission: vi.fn(() => true)
    }

    // Mock notifications store
    mockNotificationsStore = {
      showSuccess: vi.fn(),
      showError: vi.fn(),
      showConfirm: vi.fn(() => Promise.resolve(true))
    }

    // Mock business service
    vi.mocked(businessService.deleteBusiness).mockResolvedValue({ success: true })
    vi.mocked(businessService.importReviews).mockResolvedValue({
      imported_count: 25,
      skipped_count: 5,
      total_processed: 30
    })

    vi.mocked(useBusinessStore).mockReturnValue(mockBusinessStore)
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)
    vi.mocked(useNotificationsStore).mockReturnValue(mockNotificationsStore)
  })

  const createWrapper = (props = {}) => {
    return mount(BusinessManagementView, {
      props,
      global: {
        plugins: [i18n],
        stubs: {
          'router-link': {
            template: '<a><slot /></a>',
            props: ['to']
          },
          'BusinessRegistrationModal': {
            template: '<div class="registration-modal"></div>',
            props: ['isOpen', 'organizationId'],
            emits: ['close', 'business-registered']
          },
          'BusinessEditModal': {
            template: '<div class="edit-modal"></div>',
            props: ['isOpen', 'business'],
            emits: ['close', 'business-updated']
          },
          'ImportStatusIndicator': {
            template: '<div class="import-status">{{ status }}</div>',
            props: ['status', 'lastImport', 'errorMessage']
          }
        }
      }
    })
  }

  describe('Component Rendering', () => {
    it('renders business management header', () => {
      wrapper = createWrapper()
      
      expect(wrapper.find('h1').text()).toContain('Business Management')
    })

    it('renders add business button', () => {
      wrapper = createWrapper()
      
      const addButton = wrapper.find('[data-testid="add-business-btn"]')
      expect(addButton.exists()).toBe(true)
      expect(addButton.text()).toContain('Add Business')
    })

    it('renders business table with headers', () => {
      wrapper = createWrapper()
      
      const table = wrapper.find('table')
      expect(table.exists()).toBe(true)
      
      const headers = wrapper.findAll('th')
      expect(headers.some(h => h.text().includes('Business Name'))).toBe(true)
      expect(headers.some(h => h.text().includes('Address'))).toBe(true)
      expect(headers.some(h => h.text().includes('Category'))).toBe(true)
      expect(headers.some(h => h.text().includes('Rating'))).toBe(true)
      expect(headers.some(h => h.text().includes('Reviews'))).toBe(true)
      expect(headers.some(h => h.text().includes('Last Import'))).toBe(true)
      expect(headers.some(h => h.text().includes('Actions'))).toBe(true)
    })

    it('renders business rows with data', () => {
      wrapper = createWrapper()
      
      const rows = wrapper.findAll('tbody tr')
      expect(rows).toHaveLength(2)
      
      // Check first business row
      expect(rows[0].text()).toContain('Restaurant One')
      expect(rows[0].text()).toContain('123 Main St')
      expect(rows[0].text()).toContain('restaurant')
      expect(rows[0].text()).toContain('4.5')
      expect(rows[0].text()).toContain('150')
      
      // Check second business row
      expect(rows[1].text()).toContain('Cafe Two')
      expect(rows[1].text()).toContain('456 Oak Ave')
      expect(rows[1].text()).toContain('cafe')
      expect(rows[1].text()).toContain('4.2')
      expect(rows[1].text()).toContain('89')
    })

    it('shows loading state when businesses are loading', async () => {
      mockBusinessStore.loading = true
      wrapper = createWrapper()
      
      expect(wrapper.find('.loading-spinner').exists()).toBe(true)
      expect(wrapper.text()).toContain('Loading')
    })

    it('shows empty state when no businesses exist', async () => {
      mockBusinessStore.businesses = []
      wrapper = createWrapper()
      
      expect(wrapper.text()).toContain('No businesses found')
    })
  })

  describe('Search and Filtering', () => {
    it('renders search input', () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      expect(searchInput.exists()).toBe(true)
      expect(searchInput.attributes('placeholder')).toContain('Search')
    })

    it('filters businesses by name', async () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      await searchInput.setValue('Restaurant')
      
      expect(wrapper.vm.filteredBusinesses).toHaveLength(1)
      expect(wrapper.vm.filteredBusinesses[0].name).toBe('Restaurant One')
    })

    it('filters businesses by address', async () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      await searchInput.setValue('Oak Ave')
      
      expect(wrapper.vm.filteredBusinesses).toHaveLength(1)
      expect(wrapper.vm.filteredBusinesses[0].name).toBe('Cafe Two')
    })

    it('filters businesses by category', async () => {
      wrapper = createWrapper()
      
      const categoryFilter = wrapper.find('[data-testid="category-filter"]')
      await categoryFilter.setValue('cafe')
      
      expect(wrapper.vm.filteredBusinesses).toHaveLength(1)
      expect(wrapper.vm.filteredBusinesses[0].category).toBe('cafe')
    })

    it('combines search and filter criteria', async () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      const categoryFilter = wrapper.find('[data-testid="category-filter"]')
      
      await searchInput.setValue('Restaurant')
      await categoryFilter.setValue('restaurant')
      
      expect(wrapper.vm.filteredBusinesses).toHaveLength(1)
      expect(wrapper.vm.filteredBusinesses[0].name).toBe('Restaurant One')
    })

    it('shows no results message when search yields no matches', async () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      await searchInput.setValue('NonexistentBusiness')
      
      expect(wrapper.text()).toContain('No businesses found')
    })
  })

  describe('Business Actions', () => {
    it('renders action buttons for each business', () => {
      wrapper = createWrapper()
      
      const actionButtons = wrapper.findAll('[data-testid^="action-"]')
      expect(actionButtons.length).toBeGreaterThan(0)
      
      // Check for view, edit, delete, and import buttons
      expect(wrapper.find('[data-testid="action-view-1"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="action-edit-1"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="action-delete-1"]').exists()).toBe(true)
      expect(wrapper.find('[data-testid="action-import-1"]').exists()).toBe(true)
    })

    it('opens edit modal when edit button is clicked', async () => {
      wrapper = createWrapper()
      
      const editButton = wrapper.find('[data-testid="action-edit-1"]')
      await editButton.trigger('click')
      
      expect(wrapper.vm.showEditModal).toBe(true)
      expect(wrapper.vm.selectedBusiness).toEqual(mockBusinessStore.businesses[0])
    })

    it('shows delete confirmation when delete button is clicked', async () => {
      wrapper = createWrapper()
      
      const deleteButton = wrapper.find('[data-testid="action-delete-1"]')
      await deleteButton.trigger('click')
      
      expect(mockNotificationsStore.showConfirm).toHaveBeenCalledWith(
        'Are you sure you want to delete this business?'
      )
    })

    it('deletes business after confirmation', async () => {
      wrapper = createWrapper()
      
      await wrapper.vm.deleteBusiness('1')
      
      expect(vi.mocked(businessService.deleteBusiness)).toHaveBeenCalledWith('1')
      expect(mockBusinessStore.fetchBusinesses).toHaveBeenCalled()
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(
        'Business deleted successfully'
      )
    })

    it('handles delete errors', async () => {
      vi.mocked(businessService.deleteBusiness).mockRejectedValue(
        new Error('Delete failed')
      )
      
      wrapper = createWrapper()
      
      await wrapper.vm.deleteBusiness('1')
      
      expect(mockNotificationsStore.showError).toHaveBeenCalledWith(
        'Failed to delete business'
      )
    })

    it('triggers review import when import button is clicked', async () => {
      wrapper = createWrapper()
      
      const importButton = wrapper.find('[data-testid="action-import-1"]')
      await importButton.trigger('click')
      
      expect(wrapper.vm.importingReviews['1']).toBe(true)
    })

    it('shows import progress during review import', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.importingReviews['1'] = true
      await wrapper.vm.$nextTick()
      
      const importButton = wrapper.find('[data-testid="action-import-1"]')
      expect(importButton.attributes('disabled')).toBeDefined()
      expect(importButton.text()).toContain('Importing')
    })

    it('shows import success notification', async () => {
      wrapper = createWrapper()
      
      await wrapper.vm.importReviews('1')
      
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(
        'Reviews imported successfully: 25 new, 5 skipped'
      )
    })
  })

  describe('Import Status Display', () => {
    it('shows import status indicators', () => {
      wrapper = createWrapper()
      
      const statusIndicators = wrapper.findAllComponents({ name: 'ImportStatusIndicator' })
      expect(statusIndicators).toHaveLength(2)
    })

    it('displays completed import status', () => {
      wrapper = createWrapper()
      
      const completedStatus = wrapper.find('[data-testid="import-status-1"]')
      expect(completedStatus.text()).toContain('completed')
    })

    it('displays in-progress import status', () => {
      wrapper = createWrapper()
      
      const progressStatus = wrapper.find('[data-testid="import-status-2"]')
      expect(progressStatus.text()).toContain('in_progress')
    })

    it('formats last import timestamp', () => {
      wrapper = createWrapper()
      
      const timestamp = wrapper.vm.formatLastImport('2024-01-15T10:30:00Z')
      expect(timestamp).toContain('ago')
    })

    it('handles missing import timestamp', () => {
      wrapper = createWrapper()
      
      const timestamp = wrapper.vm.formatLastImport(null)
      expect(timestamp).toBe('Never')
    })
  })

  describe('Modal Management', () => {
    it('opens registration modal when add button is clicked', async () => {
      wrapper = createWrapper()
      
      const addButton = wrapper.find('[data-testid="add-business-btn"]')
      await addButton.trigger('click')
      
      expect(wrapper.vm.showRegistrationModal).toBe(true)
    })

    it('closes registration modal', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.showRegistrationModal = true
      await wrapper.vm.closeRegistrationModal()
      
      expect(wrapper.vm.showRegistrationModal).toBe(false)
    })

    it('refreshes business list after registration', async () => {
      wrapper = createWrapper()
      
      const newBusiness = {
        id: '3',
        name: 'New Restaurant',
        address: '789 New St',
        category: 'restaurant'
      }
      
      await wrapper.vm.onBusinessRegistered(newBusiness)
      
      expect(mockBusinessStore.fetchBusinesses).toHaveBeenCalled()
      expect(wrapper.vm.showRegistrationModal).toBe(false)
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(
        'Business registered successfully'
      )
    })

    it('refreshes business list after update', async () => {
      wrapper = createWrapper()
      
      const updatedBusiness = {
        id: '1',
        name: 'Updated Restaurant',
        address: '123 Updated St',
        category: 'restaurant'
      }
      
      await wrapper.vm.onBusinessUpdated(updatedBusiness)
      
      expect(mockBusinessStore.fetchBusinesses).toHaveBeenCalled()
      expect(wrapper.vm.showEditModal).toBe(false)
      expect(mockNotificationsStore.showSuccess).toHaveBeenCalledWith(
        'Business updated successfully'
      )
    })
  })

  describe('Permissions and Access Control', () => {
    it('shows add button only for users with create permission', () => {
      mockAuthStore.hasPermission.mockReturnValue(false)
      wrapper = createWrapper()
      
      const addButton = wrapper.find('[data-testid="add-business-btn"]')
      expect(addButton.exists()).toBe(false)
    })

    it('shows edit button only for users with update permission', () => {
      mockAuthStore.hasPermission.mockImplementation((permission) => 
        permission !== 'business:update'
      )
      wrapper = createWrapper()
      
      const editButton = wrapper.find('[data-testid="action-edit-1"]')
      expect(editButton.exists()).toBe(false)
    })

    it('shows delete button only for users with delete permission', () => {
      mockAuthStore.hasPermission.mockImplementation((permission) => 
        permission !== 'business:delete'
      )
      wrapper = createWrapper()
      
      const deleteButton = wrapper.find('[data-testid="action-delete-1"]')
      expect(deleteButton.exists()).toBe(false)
    })

    it('filters businesses based on user access', () => {
      // Mock user with limited access
      mockAuthStore.user.role = 'viewer'
      mockBusinessStore.businesses = mockBusinessStore.businesses.filter(b => b.id === '1')
      
      wrapper = createWrapper()
      
      expect(wrapper.vm.filteredBusinesses).toHaveLength(1)
      expect(wrapper.vm.filteredBusinesses[0].id).toBe('1')
    })
  })

  describe('Responsive Design', () => {
    it('adapts table for mobile view', async () => {
      wrapper = createWrapper()
      
      // Simulate mobile viewport
      wrapper.vm.isMobile = true
      await wrapper.vm.$nextTick()
      
      expect(wrapper.find('.mobile-card-view').exists()).toBe(true)
    })

    it('shows mobile-optimized action menu', async () => {
      wrapper = createWrapper()
      
      wrapper.vm.isMobile = true
      await wrapper.vm.$nextTick()
      
      const mobileActions = wrapper.find('.mobile-actions')
      expect(mobileActions.exists()).toBe(true)
    })
  })

  describe('Performance Optimization', () => {
    it('implements virtual scrolling for large lists', () => {
      // Create large business list
      const largeBuinessList = Array.from({ length: 1000 }, (_, i) => ({
        id: `${i}`,
        name: `Business ${i}`,
        address: `Address ${i}`,
        category: 'restaurant'
      }))
      
      mockBusinessStore.businesses = largeBuinessList
      wrapper = createWrapper()
      
      // Check that virtual scrolling is implemented
      expect(wrapper.vm.virtualScrolling).toBeDefined()
    })

    it('debounces search input', async () => {
      wrapper = createWrapper()
      
      const searchInput = wrapper.find('[data-testid="search-input"]')
      
      // Rapid typing simulation
      await searchInput.setValue('R')
      await searchInput.setValue('Re')
      await searchInput.setValue('Res')
      await searchInput.setValue('Rest')
      
      // Check that debouncing is implemented
      expect(wrapper.vm.debouncedSearch).toBeDefined()
    })
  })
})