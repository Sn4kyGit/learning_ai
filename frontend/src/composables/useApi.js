import { ref, computed } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

export function useApi() {
  const loading = ref(false)
  const error = ref(null)
  const data = ref(null)
  const notificationsStore = useNotificationsStore()

  const isLoading = computed(() => loading.value)
  const hasError = computed(() => !!error.value)
  const hasData = computed(() => !!data.value)

  async function execute(apiCall, options = {}) {
    const {
      showSuccessMessage = false,
      successMessage = 'Operation completed successfully',
      showErrorMessage = true,
      loadingState = true
    } = options

    if (loadingState) {
      loading.value = true
    }
    error.value = null

    try {
      const result = await apiCall()
      data.value = result
      
      if (showSuccessMessage) {
        notificationsStore.showSuccess(successMessage)
      }
      
      return result
    } catch (err) {
      error.value = err
      
      if (showErrorMessage) {
        const errorMessage = err.response?.data?.detail || err.message || 'An error occurred'
        notificationsStore.showError(errorMessage)
      }
      
      throw err
    } finally {
      if (loadingState) {
        loading.value = false
      }
    }
  }

  function reset() {
    loading.value = false
    error.value = null
    data.value = null
  }

  function clearError() {
    error.value = null
  }

  return {
    loading: isLoading,
    error,
    data,
    hasError,
    hasData,
    execute,
    reset,
    clearError
  }
}

// Specialized composable for paginated data
export function usePaginatedApi() {
  const { loading, error, execute, reset, clearError } = useApi()
  const items = ref([])
  const pagination = ref({
    page: 1,
    limit: 20,
    total: 0,
    totalPages: 0
  })

  const hasNextPage = computed(() => pagination.value.page < pagination.value.totalPages)
  const hasPrevPage = computed(() => pagination.value.page > 1)

  async function fetchPage(apiCall, page = 1, limit = 20) {
    const result = await execute(() => apiCall({ page, limit }))
    
    if (result) {
      items.value = result.items || result.data || []
      pagination.value = {
        page: result.page || page,
        limit: result.limit || limit,
        total: result.total || 0,
        totalPages: result.totalPages || Math.ceil((result.total || 0) / limit)
      }
    }
    
    return result
  }

  async function nextPage(apiCall) {
    if (hasNextPage.value) {
      await fetchPage(apiCall, pagination.value.page + 1, pagination.value.limit)
    }
  }

  async function prevPage(apiCall) {
    if (hasPrevPage.value) {
      await fetchPage(apiCall, pagination.value.page - 1, pagination.value.limit)
    }
  }

  function resetPagination() {
    items.value = []
    pagination.value = {
      page: 1,
      limit: 20,
      total: 0,
      totalPages: 0
    }
    reset()
  }

  return {
    loading,
    error,
    items,
    pagination,
    hasNextPage,
    hasPrevPage,
    fetchPage,
    nextPage,
    prevPage,
    resetPagination,
    clearError
  }
}