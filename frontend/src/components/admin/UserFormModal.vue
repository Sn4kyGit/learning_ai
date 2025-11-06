<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>

      <!-- Modal panel -->
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
              <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                {{ isEditing ? $t('admin.userManagement.editUser') : $t('admin.userManagement.createUser') }}
              </h3>

              <form @submit.prevent="saveUser" class="space-y-4">
                <!-- Name -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('admin.userManagement.name') }}
                  </label>
                  <input
                    v-model="form.name"
                    type="text"
                    required
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    :placeholder="$t('admin.userManagement.namePlaceholder')"
                  />
                </div>

                <!-- Email -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('auth.email') }}
                  </label>
                  <input
                    v-model="form.email"
                    type="email"
                    required
                    :disabled="isEditing"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 disabled:bg-gray-100"
                    :placeholder="$t('admin.userManagement.emailPlaceholder')"
                  />
                  <p v-if="isEditing" class="mt-1 text-xs text-gray-500">
                    {{ $t('admin.userManagement.emailCannotBeChanged') }}
                  </p>
                </div>

                <!-- Role -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('admin.userManagement.role') }}
                  </label>
                  <select
                    v-model="form.role"
                    required
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option value="">{{ $t('admin.userManagement.selectRole') }}</option>
                    <option value="admin">{{ $t('auth.roles.admin') }}</option>
                    <option value="viewer">{{ $t('auth.roles.viewer') }}</option>
                  </select>
                </div>

                <!-- Language Preference -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('admin.userManagement.languagePreference') }}
                  </label>
                  <select
                    v-model="form.language_preference"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option
                      v-for="lang in availableLanguages"
                      :key="lang.code"
                      :value="lang.code"
                    >
                      {{ lang.name }}
                    </option>
                  </select>
                </div>

                <!-- Organization ID (optional) -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('admin.userManagement.organizationId') }}
                  </label>
                  <input
                    v-model="form.organization_id"
                    type="text"
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    :placeholder="$t('admin.userManagement.organizationIdPlaceholder')"
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ $t('admin.userManagement.organizationIdHelp') }}
                  </p>
                </div>

                <!-- Password (only for new users) -->
                <div v-if="!isEditing">
                  <label class="block text-sm font-medium text-gray-700 mb-1">
                    {{ $t('auth.password') }}
                  </label>
                  <input
                    v-model="form.password"
                    type="password"
                    required
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    :placeholder="$t('admin.userManagement.passwordPlaceholder')"
                  />
                  <p class="mt-1 text-xs text-gray-500">
                    {{ $t('admin.userManagement.passwordHelp') }}
                  </p>
                </div>
              </form>
            </div>
          </div>
        </div>

        <!-- Modal actions -->
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            @click="saveUser"
            :disabled="loading || !isFormValid"
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ isEditing ? $t('common.updating') : $t('common.creating') }}
            </span>
            <span v-else>
              {{ isEditing ? $t('common.update') : $t('common.create') }}
            </span>
          </button>
          <button
            @click="$emit('close')"
            type="button"
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            {{ $t('common.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { userManagementService } from '@/services/userManagement'
import type { User } from '@/types'

interface Props {
  user?: User | null
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  saved: [user: User]
}>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

const loading = ref(false)

const isEditing = computed(() => !!props.user)

const availableLanguages = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'ar', name: 'العربية' }
]

const form = ref({
  name: '',
  email: '',
  role: '' as 'admin' | 'viewer' | '',
  language_preference: 'en',
  organization_id: '',
  password: ''
})

const isFormValid = computed(() => {
  const baseValid = form.value.name && form.value.email && form.value.role
  
  if (isEditing.value) {
    return baseValid
  } else {
    return baseValid && form.value.password && form.value.password.length >= 8
  }
})

const saveUser = async () => {
  if (!isFormValid.value) return

  try {
    loading.value = true
    
    let savedUser: User
    
    if (isEditing.value && props.user) {
      // Update existing user
      savedUser = await userManagementService.updateUser(props.user.id, {
        name: form.value.name,
        role: form.value.role as 'admin' | 'viewer',
        language_preference: form.value.language_preference,
        organization_id: form.value.organization_id || undefined
      })
      notificationsStore.showSuccess(t('admin.userManagement.updateSuccess', { name: form.value.name }))
    } else {
      // Create new user
      savedUser = await userManagementService.createUser({
        name: form.value.name,
        email: form.value.email,
        role: form.value.role as 'admin' | 'viewer',
        language_preference: form.value.language_preference,
        organization_id: form.value.organization_id || undefined
      })
      notificationsStore.showSuccess(t('admin.userManagement.createSuccess', { name: form.value.name }))
    }
    
    emit('saved', savedUser)
  } catch (error) {
    console.error('Failed to save user:', error)
    const errorKey = isEditing.value ? 'admin.userManagement.updateError' : 'admin.userManagement.createError'
    notificationsStore.showError(t(errorKey))
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  if (props.user) {
    form.value = {
      name: props.user.name,
      email: props.user.email,
      role: props.user.role as 'admin' | 'viewer',
      language_preference: props.user.language_preference,
      organization_id: props.user.organization_id || '',
      password: ''
    }
  }
})
</script>