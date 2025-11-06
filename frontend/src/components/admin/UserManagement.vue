<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between">
        <div>
          <h2 class="text-xl font-semibold text-gray-900">
            {{ $t('admin.userManagement.title') }}
          </h2>
          <p class="mt-1 text-sm text-gray-500">
            {{ $t('admin.userManagement.description') }}
          </p>
        </div>
        <button
          @click="showCreateUserModal = true"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
          </svg>
          {{ $t('admin.userManagement.createUser') }}
        </button>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex flex-col sm:flex-row sm:items-center sm:justify-between space-y-4 sm:space-y-0">
        <div class="flex-1 max-w-lg">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
              <svg class="h-5 w-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </div>
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="$t('admin.userManagement.searchPlaceholder')"
              class="block w-full pl-10 pr-3 py-2 border border-gray-300 rounded-md leading-5 bg-white placeholder-gray-500 focus:outline-none focus:placeholder-gray-400 focus:ring-1 focus:ring-blue-500 focus:border-blue-500"
              @input="debouncedSearch"
            />
          </div>
        </div>
        <div class="flex items-center space-x-4">
          <select
            v-model="roleFilter"
            class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            @change="loadUsers"
          >
            <option value="">{{ $t('admin.userManagement.allRoles') }}</option>
            <option value="super_admin">{{ $t('auth.roles.super_admin') }}</option>
            <option value="admin">{{ $t('auth.roles.admin') }}</option>
            <option value="viewer">{{ $t('auth.roles.viewer') }}</option>
          </select>
          <button
            @click="loadUsers"
            :disabled="loading"
            class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
            {{ $t('common.refresh') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Users Table -->
    <div class="bg-white shadow rounded-lg overflow-hidden">
      <div v-if="loading" class="p-6 text-center">
        <div class="inline-flex items-center">
          <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
          </svg>
          {{ $t('common.loading') }}
        </div>
      </div>

      <div v-else-if="users.length === 0" class="p-6 text-center text-gray-500">
        {{ $t('admin.userManagement.noUsers') }}
      </div>

      <div v-else>
        <table class="min-w-full divide-y divide-gray-200">
          <thead class="bg-gray-50">
            <tr>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('admin.userManagement.user') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('admin.userManagement.role') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('admin.userManagement.organization') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('admin.userManagement.lastLogin') }}
              </th>
              <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider">
                {{ $t('admin.userManagement.businessAccess') }}
              </th>
              <th class="relative px-6 py-3">
                <span class="sr-only">{{ $t('common.actions') }}</span>
              </th>
            </tr>
          </thead>
          <tbody class="bg-white divide-y divide-gray-200">
            <tr v-for="user in users" :key="user.id" class="hover:bg-gray-50">
              <td class="px-6 py-4 whitespace-nowrap">
                <div class="flex items-center">
                  <div class="flex-shrink-0 h-10 w-10">
                    <div class="h-10 w-10 rounded-full bg-gray-300 flex items-center justify-center">
                      <span class="text-sm font-medium text-gray-700">
                        {{ user.name.charAt(0).toUpperCase() }}
                      </span>
                    </div>
                  </div>
                  <div class="ml-4">
                    <div class="text-sm font-medium text-gray-900">{{ user.name }}</div>
                    <div class="text-sm text-gray-500">{{ user.email }}</div>
                  </div>
                </div>
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <span
                  class="inline-flex px-2 py-1 text-xs font-semibold rounded-full"
                  :class="getRoleBadgeClass(user.role)"
                >
                  {{ $t(`auth.roles.${user.role}`) }}
                </span>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ user.organization_id || '-' }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                {{ user.last_login ? formatDate(user.last_login) : $t('admin.userManagement.neverLoggedIn') }}
              </td>
              <td class="px-6 py-4 whitespace-nowrap">
                <button
                  @click="showBusinessAccessModal(user)"
                  class="text-blue-600 hover:text-blue-900 text-sm font-medium"
                >
                  {{ $t('admin.userManagement.manageAccess') }}
                </button>
              </td>
              <td class="px-6 py-4 whitespace-nowrap text-right text-sm font-medium">
                <div class="flex items-center justify-end space-x-2">
                  <button
                    @click="editUser(user)"
                    class="text-blue-600 hover:text-blue-900"
                  >
                    {{ $t('common.edit') }}
                  </button>
                  <button
                    @click="confirmDeleteUser(user)"
                    class="text-red-600 hover:text-red-900"
                  >
                    {{ $t('common.delete') }}
                  </button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>

        <!-- Pagination -->
        <div v-if="totalUsers > users.length" class="bg-white px-4 py-3 border-t border-gray-200 sm:px-6">
          <div class="flex items-center justify-between">
            <div class="flex-1 flex justify-between sm:hidden">
              <button
                @click="loadPreviousPage"
                :disabled="currentPage === 0"
                class="relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                {{ $t('common.previous') }}
              </button>
              <button
                @click="loadNextPage"
                :disabled="(currentPage + 1) * pageSize >= totalUsers"
                class="ml-3 relative inline-flex items-center px-4 py-2 border border-gray-300 text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 disabled:opacity-50"
              >
                {{ $t('common.next') }}
              </button>
            </div>
            <div class="hidden sm:flex-1 sm:flex sm:items-center sm:justify-between">
              <div>
                <p class="text-sm text-gray-700">
                  {{ $t('admin.userManagement.showingResults', {
                    start: currentPage * pageSize + 1,
                    end: Math.min((currentPage + 1) * pageSize, totalUsers),
                    total: totalUsers
                  }) }}
                </p>
              </div>
              <div>
                <nav class="relative z-0 inline-flex rounded-md shadow-sm -space-x-px">
                  <button
                    @click="loadPreviousPage"
                    :disabled="currentPage === 0"
                    class="relative inline-flex items-center px-2 py-2 rounded-l-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span class="sr-only">{{ $t('common.previous') }}</span>
                    <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M12.707 5.293a1 1 0 010 1.414L9.414 10l3.293 3.293a1 1 0 01-1.414 1.414l-4-4a1 1 0 010-1.414l4-4a1 1 0 011.414 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <button
                    @click="loadNextPage"
                    :disabled="(currentPage + 1) * pageSize >= totalUsers"
                    class="relative inline-flex items-center px-2 py-2 rounded-r-md border border-gray-300 bg-white text-sm font-medium text-gray-500 hover:bg-gray-50 disabled:opacity-50"
                  >
                    <span class="sr-only">{{ $t('common.next') }}</span>
                    <svg class="h-5 w-5" fill="currentColor" viewBox="0 0 20 20">
                      <path fill-rule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clip-rule="evenodd" />
                    </svg>
                  </button>
                </nav>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Create/Edit User Modal -->
    <UserFormModal
      v-if="showCreateUserModal || editingUser"
      :user="editingUser"
      @close="closeUserModal"
      @saved="handleUserSaved"
    />

    <!-- Business Access Modal -->
    <BusinessAccessModal
      v-if="selectedUserForAccess"
      :user="selectedUserForAccess"
      @close="selectedUserForAccess = null"
      @updated="loadUsers"
    />

    <!-- Delete Confirmation Modal -->
    <ConfirmationModal
      v-if="userToDelete"
      :title="$t('admin.userManagement.deleteUserTitle')"
      :message="$t('admin.userManagement.deleteUserMessage', { name: userToDelete.name })"
      :confirmText="$t('common.delete')"
      :cancelText="$t('common.cancel')"
      :loading="deleting"
      @confirm="deleteUser"
      @cancel="userToDelete = null"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { userManagementService } from '@/services/userManagement'
import type { User } from '@/types'
import UserFormModal from './UserFormModal.vue'
import BusinessAccessModal from './BusinessAccessModal.vue'
import ConfirmationModal from '@/components/common/ConfirmationModal.vue'

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

const loading = ref(false)
const deleting = ref(false)
const users = ref<User[]>([])
const totalUsers = ref(0)
const currentPage = ref(0)
const pageSize = ref(50)
const searchQuery = ref('')
const roleFilter = ref('')

const showCreateUserModal = ref(false)
const editingUser = ref<User | null>(null)
const selectedUserForAccess = ref<User | null>(null)
const userToDelete = ref<User | null>(null)

let searchTimeout: NodeJS.Timeout

const debouncedSearch = () => {
  clearTimeout(searchTimeout)
  searchTimeout = setTimeout(() => {
    currentPage.value = 0
    loadUsers()
  }, 300)
}

const loadUsers = async () => {
  try {
    loading.value = true
    const result = await userManagementService.getAllUsers(
      currentPage.value * pageSize.value,
      pageSize.value,
      searchQuery.value || undefined
    )
    
    users.value = result.users
    totalUsers.value = result.total
  } catch (error) {
    console.error('Failed to load users:', error)
    notificationsStore.showError(t('admin.userManagement.loadError'))
  } finally {
    loading.value = false
  }
}

const loadNextPage = () => {
  if ((currentPage.value + 1) * pageSize.value < totalUsers.value) {
    currentPage.value++
    loadUsers()
  }
}

const loadPreviousPage = () => {
  if (currentPage.value > 0) {
    currentPage.value--
    loadUsers()
  }
}

const getRoleBadgeClass = (role: string) => {
  switch (role) {
    case 'super_admin':
      return 'bg-purple-100 text-purple-800'
    case 'admin':
      return 'bg-blue-100 text-blue-800'
    case 'viewer':
      return 'bg-gray-100 text-gray-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const editUser = (user: User) => {
  editingUser.value = user
}

const closeUserModal = () => {
  showCreateUserModal.value = false
  editingUser.value = null
}

const handleUserSaved = () => {
  closeUserModal()
  loadUsers()
}

const showBusinessAccessModal = (user: User) => {
  selectedUserForAccess.value = user
}

const confirmDeleteUser = (user: User) => {
  userToDelete.value = user
}

const deleteUser = async () => {
  if (!userToDelete.value) return

  try {
    deleting.value = true
    await userManagementService.deleteUser(userToDelete.value.id)
    notificationsStore.showSuccess(t('admin.userManagement.deleteSuccess', { name: userToDelete.value.name }))
    userToDelete.value = null
    loadUsers()
  } catch (error) {
    console.error('Failed to delete user:', error)
    notificationsStore.showError(t('admin.userManagement.deleteError'))
  } finally {
    deleting.value = false
  }
}

onMounted(() => {
  loadUsers()
})
</script>