<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>

      <!-- Modal panel -->
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-4xl sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
              <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                {{ $t('admin.businessAccess.title', { name: user.name }) }}
              </h3>

              <!-- Current Access -->
              <div class="mb-6">
                <h4 class="text-md font-medium text-gray-900 mb-3">
                  {{ $t('admin.businessAccess.currentAccess') }}
                </h4>
                
                <div v-if="loading" class="text-center py-4">
                  <div class="inline-flex items-center">
                    <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    {{ $t('common.loading') }}
                  </div>
                </div>

                <div v-else-if="userBusinesses.length === 0" class="text-sm text-gray-500 italic">
                  {{ $t('admin.businessAccess.noAccess') }}
                </div>

                <div v-else class="space-y-2">
                  <div
                    v-for="access in userBusinesses"
                    :key="access.business.id"
                    class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
                  >
                    <div>
                      <h5 class="text-sm font-medium text-gray-900">{{ access.business.name }}</h5>
                      <p class="text-xs text-gray-500">{{ access.business.address }}</p>
                    </div>
                    <div class="flex items-center space-x-2">
                      <select
                        :value="access.permission_level"
                        @change="updatePermission(access.business.id, ($event.target as HTMLSelectElement).value)"
                        class="text-xs border border-gray-300 rounded px-2 py-1"
                      >
                        <option value="read_only">{{ $t('admin.businessAccess.readOnly') }}</option>
                        <option value="full_access">{{ $t('admin.businessAccess.fullAccess') }}</option>
                      </select>
                      <button
                        @click="revokeAccess(access.business.id)"
                        class="text-red-600 hover:text-red-800 text-xs"
                      >
                        {{ $t('common.revoke') }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>

              <!-- Grant New Access -->
              <div>
                <h4 class="text-md font-medium text-gray-900 mb-3">
                  {{ $t('admin.businessAccess.grantAccess') }}
                </h4>
                
                <div class="flex items-end space-x-3">
                  <div class="flex-1">
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ $t('admin.businessAccess.selectBusiness') }}
                    </label>
                    <select
                      v-model="newAccess.businessId"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="">{{ $t('admin.businessAccess.selectBusinessPlaceholder') }}</option>
                      <option
                        v-for="business in availableBusinesses"
                        :key="business.id"
                        :value="business.id"
                      >
                        {{ business.name }} - {{ business.address }}
                      </option>
                    </select>
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ $t('admin.businessAccess.permissionLevel') }}
                    </label>
                    <select
                      v-model="newAccess.permissionLevel"
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    >
                      <option value="read_only">{{ $t('admin.businessAccess.readOnly') }}</option>
                      <option value="full_access">{{ $t('admin.businessAccess.fullAccess') }}</option>
                    </select>
                  </div>
                  <button
                    @click="grantAccess"
                    :disabled="!newAccess.businessId || granting"
                    class="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
                  >
                    {{ granting ? $t('admin.businessAccess.granting') : $t('admin.businessAccess.grant') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal actions -->
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            @click="$emit('close')"
            type="button"
            class="w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:w-auto sm:text-sm"
          >
            {{ $t('common.close') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { userManagementService } from '@/services/userManagement'
import { useBusinessStore } from '@/stores/business'
import type { User, UserBusinessAccess, Business } from '@/types'

interface Props {
  user: User
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  updated: []
}>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()
const businessStore = useBusinessStore()

const loading = ref(false)
const granting = ref(false)
const userBusinesses = ref<UserBusinessAccess[]>([])

const newAccess = ref({
  businessId: '',
  permissionLevel: 'read_only' as 'read_only' | 'full_access'
})

const availableBusinesses = computed(() => {
  const userBusinessIds = new Set(userBusinesses.value.map(access => access.business.id))
  return businessStore.businesses.filter(business => !userBusinessIds.has(business.id))
})

const loadUserBusinesses = async () => {
  try {
    loading.value = true
    userBusinesses.value = await userManagementService.getUserBusinesses(props.user.id)
  } catch (error) {
    console.error('Failed to load user businesses:', error)
    notificationsStore.showError(t('admin.businessAccess.loadError'))
  } finally {
    loading.value = false
  }
}

const grantAccess = async () => {
  if (!newAccess.value.businessId) return

  try {
    granting.value = true
    await userManagementService.grantBusinessAccess(
      props.user.id,
      newAccess.value.businessId,
      newAccess.value.permissionLevel
    )
    
    notificationsStore.showSuccess(t('admin.businessAccess.grantSuccess'))
    
    // Reset form and reload
    newAccess.value.businessId = ''
    newAccess.value.permissionLevel = 'read_only'
    await loadUserBusinesses()
    emit('updated')
  } catch (error) {
    console.error('Failed to grant access:', error)
    notificationsStore.showError(t('admin.businessAccess.grantError'))
  } finally {
    granting.value = false
  }
}

const updatePermission = async (businessId: string, permissionLevel: string) => {
  try {
    await userManagementService.updateBusinessAccess(
      props.user.id,
      businessId,
      permissionLevel as 'read_only' | 'full_access'
    )
    
    notificationsStore.showSuccess(t('admin.businessAccess.updateSuccess'))
    await loadUserBusinesses()
    emit('updated')
  } catch (error) {
    console.error('Failed to update permission:', error)
    notificationsStore.showError(t('admin.businessAccess.updateError'))
  }
}

const revokeAccess = async (businessId: string) => {
  try {
    await userManagementService.revokeBusinessAccess(props.user.id, businessId)
    notificationsStore.showSuccess(t('admin.businessAccess.revokeSuccess'))
    await loadUserBusinesses()
    emit('updated')
  } catch (error) {
    console.error('Failed to revoke access:', error)
    notificationsStore.showError(t('admin.businessAccess.revokeError'))
  }
}

onMounted(async () => {
  await loadUserBusinesses()
  
  // Load businesses if not already loaded
  if (businessStore.businesses.length === 0) {
    await businessStore.loadBusinesses()
  }
})
</script>