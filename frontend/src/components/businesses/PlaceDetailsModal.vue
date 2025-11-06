<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-10 mx-auto p-5 border w-full max-w-4xl shadow-lg rounded-md bg-white">
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('businesses.placeDetails') }}
        </h3>
        <button
          @click="$emit('close')"
          class="text-gray-400 hover:text-gray-600"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="py-12 text-center">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600 mx-auto"></div>
        <p class="mt-4 text-gray-600">{{ $t('businesses.loadingPlaceDetails') }}</p>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="py-12 text-center">
        <ExclamationCircleIcon class="mx-auto h-12 w-12 text-red-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900">{{ $t('common.error') }}</h3>
        <p class="mt-1 text-sm text-gray-500">{{ error }}</p>
        <button
          @click="$emit('retry')"
          class="mt-4 px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
        >
          {{ $t('common.retry') }}
        </button>
      </div>

      <!-- Place Details Content -->
      <div v-else-if="place" class="mt-6">
        <!-- Place Header -->
        <div class="flex items-start space-x-4 mb-6">
          <!-- Place Photo -->
          <div class="flex-shrink-0">
            <img
              v-if="place.photos && place.photos.length > 0"
              :src="getPhotoUrl(place.photos[0].photo_reference, { maxWidth: 200, maxHeight: 200 })"
              :alt="place.name"
              class="w-24 h-24 rounded-lg object-cover"
              @error="handleImageError"
            />
            <div v-else class="w-24 h-24 bg-gray-200 rounded-lg flex items-center justify-center">
              <BuildingStorefrontIcon class="h-12 w-12 text-gray-400" />
            </div>
          </div>

          <!-- Place Info -->
          <div class="flex-1 min-w-0">
            <h2 class="text-xl font-semibold text-gray-900 truncate">
              {{ place.name }}
            </h2>
            <p class="text-gray-600 mt-1">
              {{ place.formatted_address }}
            </p>
            
            <!-- Rating and Reviews -->
            <div v-if="place.rating" class="flex items-center mt-2">
              <div class="flex items-center">
                <StarIcon class="h-5 w-5 text-yellow-400 mr-1" />
                <span class="text-lg font-medium text-gray-900">
                  {{ place.rating.toFixed(1) }}
                </span>
              </div>
              <span v-if="place.user_ratings_total" class="text-gray-500 ml-2">
                ({{ place.user_ratings_total }} {{ $t('businesses.reviews') }})
              </span>
            </div>

            <!-- Place Types -->
            <div v-if="place.types && place.types.length > 0" class="flex flex-wrap gap-2 mt-3">
              <span
                v-for="type in place.types.slice(0, 4)"
                :key="type"
                class="inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium bg-blue-100 text-blue-800"
              >
                {{ formatPlaceType(type) }}
              </span>
            </div>
          </div>
        </div>

        <!-- Place Details Grid -->
        <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
          <!-- Contact Information -->
          <div class="space-y-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ $t('businesses.contactInformation') }}
            </h3>
            
            <div class="space-y-3">
              <!-- Phone -->
              <div v-if="place.formatted_phone_number" class="flex items-center">
                <PhoneIcon class="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <p class="text-sm font-medium text-gray-900">
                    {{ place.formatted_phone_number }}
                  </p>
                  <p v-if="place.international_phone_number" class="text-xs text-gray-500">
                    {{ place.international_phone_number }}
                  </p>
                </div>
              </div>

              <!-- Website -->
              <div v-if="place.website" class="flex items-center">
                <GlobeAltIcon class="h-5 w-5 text-gray-400 mr-3" />
                <a
                  :href="place.website"
                  target="_blank"
                  rel="noopener noreferrer"
                  class="text-sm text-blue-600 hover:text-blue-800 underline"
                >
                  {{ formatWebsiteUrl(place.website) }}
                </a>
              </div>

              <!-- Address -->
              <div class="flex items-start">
                <MapPinIcon class="h-5 w-5 text-gray-400 mr-3 mt-0.5" />
                <div>
                  <p class="text-sm text-gray-900">
                    {{ place.formatted_address }}
                  </p>
                  <p class="text-xs text-gray-500 mt-1">
                    {{ $t('businesses.coordinates') }}: 
                    {{ place.geometry.location.lat.toFixed(6) }}, 
                    {{ place.geometry.location.lng.toFixed(6) }}
                  </p>
                </div>
              </div>

              <!-- Price Level -->
              <div v-if="place.price_level !== undefined" class="flex items-center">
                <CurrencyDollarIcon class="h-5 w-5 text-gray-400 mr-3" />
                <div>
                  <p class="text-sm font-medium text-gray-900">
                    {{ formatPriceLevel(place.price_level) }}
                  </p>
                  <p class="text-xs text-gray-500">
                    {{ $t('businesses.priceLevel') }}
                  </p>
                </div>
              </div>
            </div>
          </div>

          <!-- Opening Hours -->
          <div v-if="place.opening_hours" class="space-y-4">
            <h3 class="text-lg font-medium text-gray-900">
              {{ $t('businesses.openingHours') }}
            </h3>
            
            <div class="space-y-2">
              <div
                v-if="place.opening_hours.open_now !== undefined"
                :class="[
                  'inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium',
                  place.opening_hours.open_now
                    ? 'bg-green-100 text-green-800'
                    : 'bg-red-100 text-red-800'
                ]"
              >
                {{ place.opening_hours.open_now ? $t('businesses.openNow') : $t('businesses.closedNow') }}
              </div>
              
              <div v-if="place.opening_hours.weekday_text" class="space-y-1">
                <p
                  v-for="(day, index) in place.opening_hours.weekday_text"
                  :key="index"
                  class="text-sm text-gray-700"
                >
                  {{ day }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Photo Gallery -->
        <div v-if="place.photos && place.photos.length > 1" class="mt-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('businesses.photos') }}
          </h3>
          <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
            <img
              v-for="(photo, index) in place.photos.slice(0, 8)"
              :key="index"
              :src="getPhotoUrl(photo.photo_reference, { maxWidth: 300, maxHeight: 300 })"
              :alt="`${place.name} photo ${index + 1}`"
              class="w-full h-24 object-cover rounded-lg cursor-pointer hover:opacity-75 transition-opacity"
              @click="openPhotoModal(photo, index)"
              @error="handleImageError"
            />
          </div>
        </div>

        <!-- Recent Reviews -->
        <div v-if="place.reviews && place.reviews.length > 0" class="mt-6">
          <h3 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('businesses.recentReviews') }}
          </h3>
          <div class="space-y-4">
            <div
              v-for="review in place.reviews.slice(0, 3)"
              :key="review.time"
              class="border border-gray-200 rounded-lg p-4"
            >
              <div class="flex items-start space-x-3">
                <img
                  :src="review.profile_photo_url"
                  :alt="review.author_name"
                  class="w-10 h-10 rounded-full"
                  @error="handleImageError"
                />
                <div class="flex-1 min-w-0">
                  <div class="flex items-center justify-between">
                    <p class="text-sm font-medium text-gray-900">
                      {{ review.author_name }}
                    </p>
                    <div class="flex items-center">
                      <StarIcon class="h-4 w-4 text-yellow-400 mr-1" />
                      <span class="text-sm text-gray-600">{{ review.rating }}</span>
                    </div>
                  </div>
                  <p class="text-xs text-gray-500 mt-1">
                    {{ review.relative_time_description }}
                  </p>
                  <p class="text-sm text-gray-700 mt-2 line-clamp-3">
                    {{ review.text }}
                  </p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Business Status -->
        <div v-if="place.business_status" class="mt-6 p-4 bg-gray-50 rounded-lg">
          <div class="flex items-center">
            <InformationCircleIcon class="h-5 w-5 text-gray-400 mr-2" />
            <span class="text-sm text-gray-700">
              {{ $t('businesses.businessStatus') }}: 
              <span class="font-medium">{{ formatBusinessStatus(place.business_status) }}</span>
            </span>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="mt-8 flex justify-end space-x-3 border-t border-gray-200 pt-4">
        <button
          @click="$emit('close')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50"
        >
          {{ $t('common.close') }}
        </button>
        <button
          v-if="place"
          @click="$emit('select', place)"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700"
        >
          {{ $t('businesses.selectThisPlace') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGooglePlaces } from '@/composables/useGooglePlaces'
import type { GooglePlaceDetails } from '@/types'

// Icons
import {
  XMarkIcon,
  StarIcon,
  PhoneIcon,
  GlobeAltIcon,
  MapPinIcon,
  CurrencyDollarIcon,
  BuildingStorefrontIcon,
  InformationCircleIcon,
  ExclamationCircleIcon
} from '@heroicons/vue/24/outline'

interface Props {
  place: GooglePlaceDetails | null
  loading?: boolean
  error?: string | null
}

interface Emits {
  (e: 'close'): void
  (e: 'select', place: GooglePlaceDetails): void
  (e: 'retry'): void
  (e: 'photo-click', photo: any, index: number): void
}

const props = withDefaults(defineProps<Props>(), {
  loading: false,
  error: null
})

const emit = defineEmits<Emits>()

const { t } = useI18n()
const { getPhotoUrl, formatPlaceType } = useGooglePlaces()

// Methods
const formatWebsiteUrl = (url: string): string => {
  try {
    const urlObj = new URL(url)
    return urlObj.hostname
  } catch {
    return url
  }
}

const formatPriceLevel = (level: number): string => {
  const levels = ['Free', '$', '$$', '$$$', '$$$$']
  return levels[level] || 'Unknown'
}

const formatBusinessStatus = (status: string): string => {
  const statusMap: Record<string, string> = {
    OPERATIONAL: t('businesses.operational'),
    CLOSED_TEMPORARILY: t('businesses.closedTemporarily'),
    CLOSED_PERMANENTLY: t('businesses.closedPermanently')
  }
  return statusMap[status] || status
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

const openPhotoModal = (photo: any, index: number) => {
  emit('photo-click', photo, index)
}
</script>

<style scoped>
.line-clamp-3 {
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>