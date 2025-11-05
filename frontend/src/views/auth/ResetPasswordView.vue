<template>
  <div class="min-h-screen flex items-center justify-center bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-md w-full space-y-8">
      <div>
        <h2 class="mt-6 text-center text-3xl font-extrabold text-gray-900">
          {{ $t('auth.resetPassword') }}
        </h2>
        <p class="mt-2 text-center text-sm text-gray-600">
          Enter your new password below.
        </p>
      </div>
      
      <form class="mt-8 space-y-6" @submit.prevent="handleSubmit">
        <div class="space-y-4">
          <div>
            <label for="password" class="block text-sm font-medium text-gray-700">
              {{ $t('auth.newPassword') }}
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
              :placeholder="$t('auth.newPassword')"
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
        </div>

        <!-- Error messages -->
        <div v-if="Object.keys(errors).length > 0" class="space-y-1">
          <p v-for="(error, field) in errors" :key="field" class="text-sm text-red-600">
            {{ error }}
          </p>
        </div>

        <!-- Success message -->
        <div v-if="success" class="p-4 bg-green-50 border border-green-200 rounded-md">
          <p class="text-sm text-green-600">
            {{ $t('auth.passwordResetSuccess') }}
          </p>
        </div>

        <div>
          <button
            type="submit"
            :disabled="loading || success"
            class="group relative w-full flex justify-center py-2 px-4 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="absolute left-0 inset-y-0 flex items-center pl-3">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white"></div>
            </span>
            {{ loading ? $t('common.loading') : $t('auth.resetPassword') }}
          </button>
        </div>

        <div class="text-center">
          <router-link
            to="/login"
            class="font-medium text-blue-600 hover:text-blue-500"
          >
            {{ $t('common.back') }} to {{ $t('auth.login') }}
          </router-link>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { authService } from '@/services/auth'

const { t } = useI18n()
const route = useRoute()
const router = useRouter()

const loading = ref(false)
const success = ref(false)
const form = reactive({
  password: '',
  confirmPassword: '',
  token: ''
})

const errors = reactive<Record<string, string>>({})

const validateForm = () => {
  const newErrors: Record<string, string> = {}

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
    await authService.resetPassword({
      token: form.token,
      password: form.password
    })
    success.value = true
    
    // Redirect to login after 2 seconds
    setTimeout(() => {
      router.push('/login')
    }, 2000)
  } catch (error: any) {
    console.error('Password reset error:', error)
    errors.general = error.message || t('errors.unknownError')
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  // Get token from query parameters
  const token = route.query.token as string
  if (token) {
    form.token = token
  } else {
    // Redirect to forgot password if no token
    router.push('/forgot-password')
  }
})
</script>