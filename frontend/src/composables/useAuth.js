import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

export function useAuth() {
  const authStore = useAuthStore()
  const router = useRouter()

  const user = computed(() => authStore.user)
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const isLoading = computed(() => authStore.loading)
  const error = computed(() => authStore.error)
  const userRole = computed(() => authStore.userRole)
  const userLanguage = computed(() => authStore.userLanguage)

  // Permission checks
  const isSuperAdmin = computed(() => userRole.value === 'super_admin')
  const isAdmin = computed(() => ['super_admin', 'admin'].includes(userRole.value))
  const isViewer = computed(() => userRole.value === 'viewer')

  function hasPermission(permission) {
    if (isSuperAdmin.value) return true
    
    const permissions = {
      'manage_users': isSuperAdmin.value,
      'manage_businesses': isAdmin.value,
      'view_analytics': isAuthenticated.value,
      'manage_reviews': isAdmin.value,
      'view_reviews': isAuthenticated.value,
      'use_chat': isAuthenticated.value,
      'export_data': isAdmin.value
    }
    
    return permissions[permission] || false
  }

  function requireAuth() {
    if (!isAuthenticated.value) {
      router.push('/login')
      return false
    }
    return true
  }

  function requirePermission(permission) {
    if (!requireAuth()) return false
    
    if (!hasPermission(permission)) {
      router.push('/dashboard')
      return false
    }
    return true
  }

  async function login(credentials) {
    try {
      await authStore.login(credentials)
      return true
    } catch (error) {
      console.error('Login failed:', error)
      return false
    }
  }

  async function logout() {
    try {
      await authStore.logout()
      router.push('/login')
    } catch (error) {
      console.error('Logout failed:', error)
    }
  }

  function clearError() {
    authStore.clearError()
  }

  return {
    // State
    user,
    isAuthenticated,
    isLoading,
    error,
    userRole,
    userLanguage,
    
    // Computed permissions
    isSuperAdmin,
    isAdmin,
    isViewer,
    
    // Methods
    hasPermission,
    requireAuth,
    requirePermission,
    login,
    logout,
    clearError
  }
}