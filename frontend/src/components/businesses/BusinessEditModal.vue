<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-lg shadow-lg rounded-md bg-white">
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('businesses.editBusiness') }}
        </h3>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>

      <!-- Modal Body -->
      <form @submit.prevent="updateBusiness" class="mt-6 space-y-6">
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('businesses.businessName') }}
          </label>
          <input
            v-model="form.name"
            type="text"
            required
            class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('businesses.address') }}
          </label>
          <textarea
            v-model="form.address"
            rows="3"
            required
            class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          ></textarea>
        </div>

        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('businesses.category') }}
          </label>
          <input
            v-model="form.category"
            type="text"
            required
            class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          />
        </div>

        <!-- Google Place Info (Read-only) -->
        <div class="bg-gray-50 border border-gray-200 rounded-lg p-4">
          <h4 class="text-sm font-medium text-gray-900 mb-3">
            {{ $t('businesses.googlePlaceInfo') }}
          </h4>
          <div class="space-y-2 text-sm">
            <div class="flex justify-between">
              <span class="text-gray-600">{{ $t('businesses.placeId') }}:</span>
              <span class="font-mono text-xs text-gray-800">{{ business.google_place_id }}</span>
            </div>
            <div class="flex justify-between">
              <span class="text-gray-600">{{ $t('businesses.currentRating') }}:</span>
              <span class="text-gray-800">
                {{ business.avg_rating?.toFixed(1) || '0.0' }} ⭐
                <span class="text-gray-500">
                  ({{ business.total_reviews || 0 }} {{ $t('businesses.reviews') }})
                </span>
              </span>
            </div>
          </div>
        </div>

        <!-- Validation with Google Places -->
        <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
          <div class="flex items-start">
            <InformationCircleIcon class="h-5 w-5 text-blue-400 mt-0.5" />
            <div class="ml-3">
              <h4 class="text-sm font-medium text-blue-800">
                {{ $t('businesses.editNote') }}
              </h4>
              <div class="mt-1 text-sm text-blue-700">
                {{ $t('businesses.editNoteDescription') }}
              </div>
              <button
                type="button"
                @click="validateWithGooglePlaces"
                :disabled="validating"
                class="mt-2 text-sm font-medium text-blue-800 hover:text-blue-900 underline disabled:opacity-50"
              >
                <span v-if="validating" class="flex items-center">
                  <div class="animate-spin rounded-full h-3 w-3 border-b-2 border-blue-800 mr-1"></div>
                  {{ $t('businesses.validating') }}
                </span>
                <span v-else>
                  {{ $t('businesses.validateWithGoogle') }}
                </span>
              </button>
            </div>
          </div>
        </div>

        <!-- Validation Results -->
        <div v-if="validationResult" class="space-y-3">
          <div
            v-if="validationResult.status === 'success'"
            class="bg-green-50 border border-green-200 rounded-lg p-4"
          >
            <div class="flex">
              <CheckCircleIcon class="h-5 w-5 text-green-400" />
              <div class="ml-3">
                <h4 class="text-sm font-medium text-green-800">
                  {{ $t('businesses.validationSuccess') }}
                </h4>
                <div class="mt-1 text-sm text-green-700">
                  {{ $t('businesses.validationSuccessDescription') }}
                </div>
              </div>
            </div>
          </div>

          <div
            v-else-if="validationResult.status === 'warning'"
            class="bg-yellow-50 border border-yellow-200 rounded-lg p-4"
          >
            <div class="flex">
              <ExclamationTriangleIcon class="h-5 w-5 text-yellow-400" />
              <div class="ml-3">
                <h4 class="text-sm font-medium text-yellow-800">
                  {{ $t('businesses.validationWarning') }}
                </h4>
                <div class="mt-1 text-sm text-yellow-700">
                  {{ validationResult.message }}
                </div>
              </div>
            </div>
          </div>

          <div
            v-else-if="validationResult.status === 'error'"
            class="bg-red-50 border border-red-200 rounded-lg p-4"
          >
            <div class="flex">
              <XCircleIcon class="h-5 w-5 text-red-400" />
              <div class="ml-3">
                <h4 class="text-sm font-medium text-red-800">
                  {{ $t('businesses.validationError') }}
                </h4>
                <div class="mt-1 text-sm text-red-700">
                  {{ validationResult.message }}
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>

      <!-- Modal Footer -->
      <div class="mt-8 flex justify-end space-x-3 border-t border-gray-200 pt-4">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {{ $t('common.cancel') }}
        </button>
        <button
          @click="updateBusiness"
          :disabled="updating"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
        >
          <span v-if="updating" class="flex items-center">
            <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
            {{ $t('businesses.updating') }}
          </span>
          <span v-else>
            {{ $t('businesses.updateBusiness') }}
          </span>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBusinessStore } from '@/stores/business'
import { useNotificationsStore } from '@/stores/notifications'
import { businessService } from '@/services/business'
import type { Business } from '@/types'

// Icons
import {
  XMarkIcon,
  InformationCircleIcon,
  CheckCircleIcon,
  ExclamationTriangleIcon,
  XCircleIcon
} from '@heroicons/vue/24/outline'

interface Props {
  business: Business
}

const props = defineProps<Props>()

const emit = defineEmits<{
  close: []
  businessUpdated: [business: Business]
}>()

const { t } = useI18n()
const businessStore = useBusinessStore()
const notificationsStore = useNotificationsStore()

// Reactive state
const updating = ref(false)
const validating = ref(false)
const validationResult = ref<{
  status: 'success' | 'warning' | 'error'
  message?: string
} | null>(null)

const form = reactive({
  name: props.business.name,
  address: props.business.address,
  category: props.business.category,
})

// Methods
const validateWithGooglePlaces = async () => {
  validating.value = true
  validationResult.value = null

  try {
    const response = await businessService.getGooglePlaceDetails(props.business.google_place_id)
    const placeDetails = response.place_details

    // Compare current form data with Google Places data
    const differences = []
    
    if (form.name !== placeDetails.name) {
      differences.push(`Name: "${form.name}" vs Google: "${placeDetails.name}"`)
    }
    
    if (form.address !== placeDetails.formatted_address) {
      differences.push(`Address differs from Google Places`)
    }

    if (differences.length === 0) {
      validationResult.value = {
        status: 'success'
      }
    } else {
      validationResult.value = {
        status: 'warning',
        message: t('businesses.validationDifferences', { differences: differences.join(', ') })
      }
    }
  } catch (error) {
    console.error('Failed to validate with Google Places:', error)
    validationResult.value = {
      status: 'error',
      message: t('businesses.validationFailed')
    }
  } finally {
    validating.value = false
  }
}

const updateBusiness = async () => {
  updating.value = true

  try {
    const updatedBusiness = await businessStore.updateBusiness(props.business.id, form)
    emit('businessUpdated', updatedBusiness)
  } catch (error) {
    console.error('Failed to update business:', error)
    notificationsStore.showError(t('businesses.updateError'))
  } finally {
    updating.value = false
  }
}

// Lifecycle
onMounted(() => {
  // Auto-validate on mount
  validateWithGooglePlaces()
})
</script>