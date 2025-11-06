<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-2xl shadow-lg rounded-md bg-white">
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('businesses.addBusiness') }}
        </h3>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="mt-6">
        <!-- Step Indicator -->
        <div class="mb-8">
          <nav aria-label="Progress">
            <ol class="flex items-center">
              <li class="relative">
                <div class="flex items-center">
                  <div
                    :class="[
                      'flex items-center justify-center w-8 h-8 rounded-full border-2',
                      currentStep >= 1
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'border-gray-300 text-gray-500'
                    ]"
                  >
                    <span class="text-sm font-medium">1</span>
                  </div>
                  <span class="ml-2 text-sm font-medium text-gray-900">
                    {{ $t('businesses.searchPlace') }}
                  </span>
                </div>
              </li>
              <li class="relative ml-8">
                <div class="flex items-center">
                  <div
                    :class="[
                      'flex items-center justify-center w-8 h-8 rounded-full border-2',
                      currentStep >= 2
                        ? 'bg-blue-600 border-blue-600 text-white'
                        : 'border-gray-300 text-gray-500'
                    ]"
                  >
                    <span class="text-sm font-medium">2</span>
                  </div>
                  <span class="ml-2 text-sm font-medium text-gray-900">
                    {{ $t('businesses.confirmDetails') }}
                  </span>
                </div>
              </li>
            </ol>
          </nav>
        </div>

        <!-- Step 1: Google Places Search -->
        <div v-if="currentStep === 1" class="space-y-6">
          <div>
            <label class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('businesses.searchForBusiness') }}
            </label>
            <GooglePlacesAutocomplete
              v-model="searchQuery"
              :placeholder="$t('businesses.searchPlaceholder')"
              @place-selected="handlePlaceSelected"
              @prediction-selected="handlePredictionSelected"
              @search-result-selected="handleSearchResultSelected"
            />
          </div>

          <!-- Rate Limit Info -->
          <div v-if="showRateLimitInfo" class="bg-amber-50 border border-amber-200 rounded-lg p-4">
            <div class="flex">
              <InformationCircleIcon class="h-5 w-5 text-amber-400" />
              <div class="ml-3">
                <h3 class="text-sm font-medium text-amber-800">
                  {{ $t('businesses.rateLimitInfo') }}
                </h3>
                <div class="mt-2 text-sm text-amber-700">
                  <p>{{ $t('businesses.rateLimitDescription') }}</p>
                  <div class="mt-2 text-xs">
                    {{ $t('businesses.requestsPerMinute') }}: {{ rateLimitStatus.requestsInLastMinute }}/{{ rateLimitStatus.maxRequestsPerMinute }}
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- Selected Place Preview -->
          <div v-if="selectedPlacePreview" class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex items-start space-x-3">
              <img
                v-if="selectedPlacePreview.photos && selectedPlacePreview.photos.length > 0"
                :src="getPhotoUrl(selectedPlacePreview.photos[0].photo_reference, { maxWidth: 80, maxHeight: 80 })"
                :alt="selectedPlacePreview.name"
                class="w-16 h-16 rounded-lg object-cover"
                @error="handleImageError"
              />
              <div v-else class="w-16 h-16 bg-gray-200 rounded-lg flex items-center justify-center">
                <BuildingStorefrontIcon class="h-8 w-8 text-gray-400" />
              </div>
              
              <div class="flex-1 min-w-0">
                <h4 class="font-medium text-blue-900">{{ selectedPlacePreview.name }}</h4>
                <p class="text-sm text-blue-700 mt-1">{{ selectedPlacePreview.formatted_address || selectedPlacePreview.address }}</p>
                <div class="flex items-center mt-2 space-x-4">
                  <div v-if="selectedPlacePreview.rating" class="flex items-center">
                    <StarIcon class="h-4 w-4 text-yellow-400 mr-1" />
                    <span class="text-sm text-blue-700">
                      {{ selectedPlacePreview.rating.toFixed(1) }}
                    </span>
                    <span v-if="selectedPlacePreview.user_ratings_total" class="text-sm text-blue-600 ml-1">
                      ({{ selectedPlacePreview.user_ratings_total }})
                    </span>
                  </div>
                </div>
                <div class="mt-2 flex space-x-2">
                  <button
                    @click="viewPlaceDetails"
                    class="text-xs text-blue-600 hover:text-blue-800 underline"
                  >
                    {{ $t('businesses.viewDetails') }}
                  </button>
                  <button
                    @click="proceedToStep2"
                    class="text-xs bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700"
                  >
                    {{ $t('businesses.useThisPlace') }}
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Step 2: Confirm Business Details -->
        <div v-if="currentStep === 2 && selectedPlace" class="space-y-6">
          <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
            <div class="flex">
              <InformationCircleIcon class="h-5 w-5 text-blue-400" />
              <div class="ml-3">
                <h3 class="text-sm font-medium text-blue-800">
                  {{ $t('businesses.confirmDetailsTitle') }}
                </h3>
                <div class="mt-2 text-sm text-blue-700">
                  {{ $t('businesses.confirmDetailsDescription') }}
                </div>
              </div>
            </div>
          </div>

          <form @submit.prevent="createBusiness" class="space-y-6">
            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                {{ $t('businesses.businessName') }}
              </label>
              <input
                v-model="businessForm.name"
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
                v-model="businessForm.address"
                rows="2"
                required
                class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
              ></textarea>
            </div>

            <div>
              <label class="block text-sm font-medium text-gray-700 mb-2">
                {{ $t('businesses.category') }}
              </label>
              <input
                v-model="businessForm.category"
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
                  <span class="font-mono text-xs text-gray-800">{{ selectedPlace.place_id }}</span>
                </div>
                <div v-if="selectedPlace.rating" class="flex justify-between">
                  <span class="text-gray-600">{{ $t('businesses.rating') }}:</span>
                  <span class="text-gray-800">
                    {{ selectedPlace.rating.toFixed(1) }} ⭐
                    <span v-if="selectedPlace.user_ratings_total" class="text-gray-500">
                      ({{ selectedPlace.user_ratings_total }} {{ $t('businesses.reviews') }})
                    </span>
                  </span>
                </div>
              </div>
            </div>
          </form>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="mt-8 flex justify-between border-t border-gray-200 pt-4">
        <button
          v-if="currentStep === 2"
          @click="currentStep = 1"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          {{ $t('common.back') }}
        </button>
        <div v-else></div>

        <div class="flex space-x-3">
          <button
            @click="$emit('close')"
            class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            {{ $t('common.cancel') }}
          </button>
          <button
            v-if="currentStep === 2"
            @click="createBusiness"
            :disabled="creating"
            class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <span v-if="creating" class="flex items-center">
              <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"></div>
              {{ $t('businesses.creating') }}
            </span>
            <span v-else>
              {{ $t('businesses.createBusiness') }}
            </span>
          </button>
        </div>
      </div>
    </div>

    <!-- Place Details Modal -->
    <PlaceDetailsModal
      v-if="showPlaceDetailsModal"
      :place="selectedPlacePreview"
      :loading="placeDetailsLoading"
      :error="placeDetailsError"
      @close="showPlaceDetailsModal = false"
      @select="handlePlaceDetailsSelect"
      @retry="viewPlaceDetails"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBusinessStore } from '@/stores/business'
import { useNotificationsStore } from '@/stores/notifications'
import { useGooglePlaces } from '@/composables/useGooglePlaces'
import { businessService } from '@/services/business'
import GooglePlacesAutocomplete from './GooglePlacesAutocomplete.vue'
import PlaceDetailsModal from './PlaceDetailsModal.vue'
import type { GooglePlaceSearchResult, GooglePlaceDetails, BusinessFormData } from '@/types'

// Icons
import {
  XMarkIcon,
  StarIcon,
  InformationCircleIcon,
  BuildingStorefrontIcon
} from '@heroicons/vue/24/outline'

const emit = defineEmits<{
  close: []
  businessCreated: [business: any]
}>()

const { t } = useI18n()
const businessStore = useBusinessStore()
const notificationsStore = useNotificationsStore()

// Google Places composable
const { 
  getPhotoUrl, 
  formatPlaceType, 
  rateLimitStatus, 
  updateRateLimitStatus 
} = useGooglePlaces()

// Reactive state
const currentStep = ref(1)
const searchQuery = ref('')
const selectedPlace = ref<GooglePlaceDetails | null>(null)
const selectedPlacePreview = ref<GooglePlaceDetails | null>(null)
const creating = ref(false)
const showPlaceDetailsModal = ref(false)
const placeDetailsLoading = ref(false)
const placeDetailsError = ref<string | null>(null)

const businessForm = reactive<BusinessFormData>({
  name: '',
  google_place_id: '',
  category: '',
  address: '',
})

// Computed
const showRateLimitInfo = computed(() => {
  updateRateLimitStatus()
  return rateLimitStatus.value.requestsInLastMinute > rateLimitStatus.value.maxRequestsPerMinute * 0.8
})

// Methods
const handlePlaceSelected = (place: GooglePlaceDetails) => {
  selectedPlace.value = place
  selectedPlacePreview.value = place
  
  // Auto-populate form fields
  businessForm.name = place.name
  businessForm.address = place.formatted_address || place.address
  businessForm.google_place_id = place.place_id
  businessForm.category = formatPlaceType(place.types[0] || 'business')
}

const handlePredictionSelected = (prediction: google.maps.places.AutocompletePrediction) => {
  // This will trigger place-selected when details are fetched
  console.log('Prediction selected:', prediction.structured_formatting.main_text)
}

const handleSearchResultSelected = (result: GooglePlaceSearchResult) => {
  // This will trigger place-selected when details are fetched
  console.log('Search result selected:', result.name)
}

const viewPlaceDetails = () => {
  if (selectedPlacePreview.value) {
    showPlaceDetailsModal.value = true
  }
}

const proceedToStep2 = () => {
  if (selectedPlacePreview.value) {
    currentStep.value = 2
  }
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const createBusiness = async () => {
  if (!selectedPlace.value) return

  creating.value = true

  try {
    const newBusiness = await businessStore.createBusiness(businessForm)
    emit('businessCreated', newBusiness)
  } catch (error) {
    console.error('Failed to create business:', error)
    notificationsStore.showError(t('businesses.createError'))
  } finally {
    creating.value = false
  }
}

const handlePlaceDetailsSelect = (place: GooglePlaceDetails) => {
  selectedPlace.value = place
  selectedPlacePreview.value = place
  showPlaceDetailsModal.value = false
  
  // Auto-populate form fields
  businessForm.name = place.name
  businessForm.address = place.formatted_address || place.address
  businessForm.google_place_id = place.place_id
  businessForm.category = formatPlaceType(place.types[0] || 'business')
  
  currentStep.value = 2
}
</script>