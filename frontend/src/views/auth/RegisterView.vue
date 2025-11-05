<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {{ $t('auth.registerTitle') }}
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          {{ $t('auth.registerSubtitle') }}
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <div>
            <label for="name" class="block text-sm font-medium text-gray-700">
              {{ $t('auth.firstName') }}
            </label>
            <input
              id="name"
              v-model="form.name"
              name="name"
              type="text"
              autocomplete="name"
              required
              :class="[
                'mt-1 appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                errors.name ? 'border-red-300' : 'border-gray-300'
              ]"
              :placeholder="$t('auth.firstName')"
            />
          </div>

          <div>
            <label for="email" class="block text-sm font-medium text-gray-700">
              {{ $t('auth.email') }}
            </label>
            <input
              id="email"
              v-model="form.email"
              name="email"
              type="email"
              autocomplete="email"
              required
              :class="[
                'mt-1 appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                errors.email ? 'border-red-300' : 'border-gray-300'
              ]"
              :placeholder="$t('auth.email')"
            />
          </div>

          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">
              {{ $t('auth.password') }}
            </label>
            <input
              id="password"
              v-model="form.password"
              name="password"
              type="password"
              autocomplete="new-password"
              required
              :class="[
                'mt-1 appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                errors.password ? 'border-red-300' : 'border-gray-300'
              ]"
              :placeholder="$t('auth.password')"
            />
          </div>

          <div>
            <label for="confirmPassword" class="block text-sm font-medium text-gray-700">
              {{ $t('auth.confirmPassword') }}
            </label>
            <input
              id="confirmPassword"
              v-model="form.confirmPassword"
              name="confirmPassword"
              type="password"
              autocomplete="new-password"
              required
              :class="[
                'mt-1 appearance-none relative block w-full px-3 py-2 border placeholder-gray-500 text-gray-900 rounded-md focus:outline-none focus:ring-blue-500 focus:border-blue-500 focus:z-10 sm:text-sm',
                errors.confirmPassword ? 'border-red-300' : 'border-gray-300'
              ]"
              :placeholder="$t('auth.confirmPassword')"
            />
          </div>

          <div>
            <label for="language" class="block text-sm font-medium text-gray-700">
              {{ $t('settings.language') }}
            </label>
            <select
              id="language"
              v-model="form.language_preference"
              name="language"
              :class="[
                'mt-1 block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 sm:text-sm',
                errors.language_preference ? 'border-red-300' : 'border-gray-300'
              ]"
            >
              <option value="en">English</option>
              <option value="de">Deutsch</option>
              <option value="tr">Türkçe</option>
              <option value="ar">العربية</option>
            </select>
          </div>
        </div>

        <!-- Error messages -->
        <div v-if="Object.keys(errors).length > 0" class="space-y-1">
          <p v-for="(error, field) in errors" :key="field" class="text-sm text-red-600">
            {{ error }}
          </p>
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            </span>
            {{ loading ? $t('common.loading') : $t('auth.signUp') }}
          </button>
        </div>

        <div class="text-center">
          <p class="text-sm text-gray-600">
            {{ $t('auth.alreadyHaveAccount') }}
            <router-link
              to="/login"
              class="font-medium text-blue-600 hover:text-blue-500"
            >
              {{ $t('auth.signIn') }}
            </router-link>
          </p>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import type { RegisterData } from '@/types'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()

const loading = ref(false)
const form = reactive<RegisterData & { confirmPassword: string }>({
  name: '',
  email: '',
  password: '',
  confirmPassword: '',
  language_preference: 'en'
})

const errors = reactive<Record<string, string>>({})

const validateForm = () => {
  const newErrors: Record<string, string> = {}

  if (!form.name.trim()) {
    newErrors.name = t('auth.nameRequired')
  }

  if (!form.email) {
    newErrors.email = t('auth.emailRequired')
  } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email)) {
    newErrors.email = t('auth.invalidEmail')
  }

  if (!form.password) {
    newErrors.password = t('auth.passwordRequired')
  } else if (form.password.length < 8) {
    newErrors.password = t('auth.passwordMinLength')
  }

  if (!form.confirmPassword) {
    newErrors.confirmPassword = t('auth.passwordRequired')
  } else if (form.password !== form.confirmPassword) {
    newErrors.confirmPassword = t('auth.passwordsDoNotMatch')
  }

  Object.assign(errors, newErrors)
  return Object.keys(newErrors).length === 0
}

const handleSubmit = async () => {
  // Clear previous errors
  Object.keys(errors).forEach(key => delete errors[key])

  if (!validateForm()) {
    return
  }

  loading.value = true

  try {
    const { confirmPassword, ...registerData } = form
    await authStore.register(registerData)
    notificationsStore.showSuccess(t('auth.registerSuccess'))
    router.push('/login')
  } catch (error: any) {
    console.error('Registration error:', error)
    
    if (error.response?.status === 400) {
      errors.general = t('auth.registerError')
    } else {
      errors.general = error.message || t('errors.unknownError')
    }
  } finally {
    loading.value = false
  }
}
</script>