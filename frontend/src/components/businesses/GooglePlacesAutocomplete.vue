<template>
  <div class="relative">
    <!-- Input Field -->
    <div class="relative">
      <input
        ref="inputRef"
        v-model="inputValue"
        @input="handleInput"
        @focus="handleFocus"
        @blur="handleBlur"
        @keydown="handleKeydown"
        type="text"
        :class="[
          'block w-full px-3 py-2 border rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-blue-500',
          error ? 'border-red-300 focus:border-red-500' : 'border-gray-300 focus:border-blue-500',
          disabled ? 'bg-gray-100 cursor-not-allowed' : 'bg-white'
        ]"
        :placeholder="placeholder"
        :disabled="disabled || isLoading"
        autocomplete="off"
      />
      
      <!-- Loading Spinner -->
      <div
        v-if="isLoading"
        class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none"
      >
        <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
      </div>
      
      <!-- Clear Button -->
      <button
        v-else-if="inputValue && !disabled"
        @click="clearInput"
        type="button"
        class="absolute inset-y-0 right-0 pr-3 flex items-center text-gray-400 hover:text-gray-600"
      >
        <XMarkIcon class="h-4 w-4" />
      </button>
    </div>

    <!-- Error Message -->
    <p v-if="error" class="mt-1 text-sm text-red-600">
      {{ error }}
    </p>

    <!-- Rate Limit Warning -->
    <div
      v-if="isRateLimited"
      class="mt-1 flex items-center text-sm text-amber-600"
    >
      <ExclamationTriangleIcon class="h-4 w-4 mr-1" />
      Rate limit reached. Please wait before searching again.
    </div>

    <!-- Dropdown -->
    <div
      v-if="showDropdown && (hasPredictions || hasSearchResults)"
      class="absolute z-50 mt-1 w-full bg-white border border-gray-300 rounded-md shadow-lg max-h-96 overflow-y-auto"
    >
      <!-- Autocomplete Predictions -->
      <div v-if="hasPredictions" class="py-1">
        <div class="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b">
          {{ $t('businesses.suggestions') }}
        </div>
        <button
          v-for="(prediction, index) in autocompletePredictions"
          :key="prediction.place_id"
          @click="selectPrediction(prediction)"
          :class="[
            'w-full text-left px-3 py-2 hover:bg-blue-50 focus:bg-blue-50 focus:outline-none',
            selectedIndex === index ? 'bg-blue-50' : ''
          ]"
          type="button"
        >
          <div class="flex items-start">
            <MapPinIcon class="h-4 w-4 text-gray-400 mt-0.5 mr-2 flex-shrink-0" />
            <div class="flex-1 min-w-0">
              <div class="font-medium text-gray-900 truncate">
                {{ prediction.structured_formatting.main_text }}
              </div>
              <div class="text-sm text-gray-500 truncate">
                {{ prediction.structured_formatting.secondary_text }}
              </div>
              <div v-if="prediction.types && prediction.types.length > 0" class="flex flex-wrap gap-1 mt-1">
                <span
                  v-for="type in prediction.types.slice(0, 2)"
                  :key="type"
                  class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                >
                  {{ formatPlaceType(type) }}
                </span>
              </div>
            </div>
          </div>
        </button>
      </div>

      <!-- Search Results -->
      <div v-if="hasSearchResults" class="py-1">
        <div v-if="hasPredictions" class="px-3 py-2 text-xs font-medium text-gray-500 bg-gray-50 border-b border-t">
          {{ $t('businesses.searchResults') }}
        </div>
        <button
          v-for="(result, index) in searchResults"
          :key="result.place_id"
          @click="selectSearchResult(result)"
          :class="[
            'w-full text-left px-3 py-2 hover:bg-blue-50 focus:bg-blue-50 focus:outline-none',
            selectedIndex === (autocompletePredictions.length + index) ? 'bg-blue-50' : ''
          ]"
          type="button"
        >
          <div class="flex items-start">
            <div class="flex-shrink-0 mr-3">
              <img
                v-if="result.photos && result.photos.length > 0"
                :src="getPhotoUrl(result.photos[0].photo_reference, { maxWidth: 60, maxHeight: 60 })"
                :alt="result.name"
                class="w-12 h-12 rounded-lg object-cover"
                @error="handleImageError"
              />
              <div v-else class="w-12 h-12 bg-gray-200 rounded-lg flex items-center justify-center">
                <BuildingStorefrontIcon class="h-6 w-6 text-gray-400" />
              </div>
            </div>
            <div class="flex-1 min-w-0">
              <div class="font-medium text-gray-900 truncate">
                {{ result.name }}
              </div>
              <div class="text-sm text-gray-500 truncate">
                {{ result.address }}
              </div>
              <div class="flex items-center mt-1 space-x-4">
                <div v-if="result.rating" class="flex items-center">
                  <StarIcon class="h-4 w-4 text-yellow-400 mr-1" />
                  <span class="text-sm text-gray-600">
                    {{ result.rating.toFixed(1) }}
                  </span>
                  <span v-if="result.user_ratings_total" class="text-sm text-gray-500 ml-1">
                    ({{ result.user_ratings_total }})
                  </span>
                </div>
                <div v-if="result.types && result.types.length > 0" class="flex flex-wrap gap-1">
                  <span
                    v-for="type in result.types.slice(0, 2)"
                    :key="type"
                    class="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-700"
                  >
                    {{ formatPlaceType(type) }}
                  </span>
                </div>
              </div>
            </div>
            <ChevronRightIcon class="h-4 w-4 text-gray-400 ml-2" />
          </div>
        </button>
      </div>

      <!-- No Results -->
      <div v-if="showDropdown && !hasPredictions && !hasSearchResults && inputValue.length > 2" class="py-8 text-center">
        <MagnifyingGlassIcon class="mx-auto h-8 w-8 text-gray-400" />
        <p class="mt-2 text-sm text-gray-500">
          {{ $t('businesses.noResults') }}
        </p>
        <p class="text-xs text-gray-400 mt-1">
          {{ $t('businesses.tryDifferentSearch') }}
        </p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useGooglePlaces } from '@/composables/useGooglePlaces'
import type { GooglePlaceSearchResult, GooglePlaceDetails } from '@/types'

// Icons
import {
  XMarkIcon,
  MapPinIcon,
  StarIcon,
  ChevronRightIcon,
  MagnifyingGlassIcon,
  BuildingStorefrontIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

interface Props {
  modelValue?: string
  placeholder?: string
  disabled?: boolean
  searchOnFocus?: boolean
  minSearchLength?: number
  showPhotos?: boolean
  types?: string[]
  componentRestrictions?: { country: string | string[] }
  location?: { lat: number; lng: number }
  radius?: number
}

interface Emits {
  (e: 'update:modelValue', value: string): void
  (e: 'place-selected', place: GooglePlaceDetails): void
  (e: 'prediction-selected', prediction: google.maps.places.AutocompletePrediction): void
  (e: 'search-result-selected', result: GooglePlaceSearchResult): void
  (e: 'input', value: string): void
  (e: 'focus'): void
  (e: 'blur'): void
}

const props = withDefaults(defineProps<Props>(), {
  placeholder: 'Search for a business...',
  disabled: false,
  searchOnFocus: true,
  minSearchLength: 2,
  showPhotos: true,
  types: () => ['establishment']
})

const emit = defineEmits<Emits>()

const { t } = useI18n()

// Google Places composable
const {
  isLoading,
  error,
  searchResults,
  autocompletePredictions,
  isRateLimited,
  hasResults: hasSearchResults,
  hasPredictions,
  debouncedAutocomplete,
  searchPlaces,
  getPlaceDetailsFromPrediction,
  getPlaceDetails,
  getPhotoUrl,
  formatPlaceType,
  clearResults
} = useGooglePlaces({
  defaultLocation: props.location,
  defaultRadius: props.radius
})

// Local state
const inputRef = ref<HTMLInputElement>()
const inputValue = ref(props.modelValue || '')
const showDropdown = ref(false)
const selectedIndex = ref(-1)
const isFocused = ref(false)

// Computed
const totalOptions = computed(() => autocompletePredictions.value.length + searchResults.value.length)

// Watch for external model value changes
watch(() => props.modelValue, (newValue) => {
  if (newValue !== inputValue.value) {
    inputValue.value = newValue || ''
  }
})

// Watch input value changes
watch(inputValue, (newValue) => {
  emit('update:modelValue', newValue)
  emit('input', newValue)
  
  if (newValue.length >= props.minSearchLength) {
    performSearch(newValue)
  } else {
    clearResults()
    showDropdown.value = false
  }
})

// Methods
const performSearch = async (query: string) => {
  if (!query.trim() || query.length < props.minSearchLength) return

  // Get autocomplete predictions
  await debouncedAutocomplete(query, {
    types: props.types,
    componentRestrictions: props.componentRestrictions,
    location: props.location,
    radius: props.radius
  })

  // Also perform text search for more comprehensive results
  await searchPlaces(query, {
    location: props.location,
    radius: props.radius
  })

  showDropdown.value = true
  selectedIndex.value = -1
}

const handleInput = () => {
  // Input handling is done through the watcher
}

const handleFocus = () => {
  isFocused.value = true
  emit('focus')
  
  if (props.searchOnFocus && inputValue.value.length >= props.minSearchLength) {
    showDropdown.value = true
  }
}

const handleBlur = () => {
  isFocused.value = false
  emit('blur')
  
  // Delay hiding dropdown to allow for clicks
  setTimeout(() => {
    if (!isFocused.value) {
      showDropdown.value = false
      selectedIndex.value = -1
    }
  }, 200)
}

const handleKeydown = (event: KeyboardEvent) => {
  if (!showDropdown.value) return

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      selectedIndex.value = Math.min(selectedIndex.value + 1, totalOptions.value - 1)
      break
    case 'ArrowUp':
      event.preventDefault()
      selectedIndex.value = Math.max(selectedIndex.value - 1, -1)
      break
    case 'Enter':
      event.preventDefault()
      if (selectedIndex.value >= 0) {
        selectByIndex(selectedIndex.value)
      }
      break
    case 'Escape':
      showDropdown.value = false
      selectedIndex.value = -1
      inputRef.value?.blur()
      break
  }
}

const selectByIndex = (index: number) => {
  if (index < autocompletePredictions.value.length) {
    selectPrediction(autocompletePredictions.value[index])
  } else {
    const resultIndex = index - autocompletePredictions.value.length
    selectSearchResult(searchResults.value[resultIndex])
  }
}

const selectPrediction = async (prediction: google.maps.places.AutocompletePrediction) => {
  inputValue.value = prediction.structured_formatting.main_text
  showDropdown.value = false
  selectedIndex.value = -1
  
  emit('prediction-selected', prediction)
  
  // Get detailed place information
  try {
    const details = await getPlaceDetailsFromPrediction(prediction)
    if (details) {
      emit('place-selected', details)
    }
  } catch (err) {
    console.error('Failed to get place details:', err)
  }
}

const selectSearchResult = async (result: GooglePlaceSearchResult) => {
  inputValue.value = result.name
  showDropdown.value = false
  selectedIndex.value = -1
  
  emit('search-result-selected', result)
  
  // Get detailed place information
  try {
    const details = await getPlaceDetails(result.place_id)
    if (details) {
      emit('place-selected', details)
    }
  } catch (err) {
    console.error('Failed to get place details:', err)
  }
}

const clearInput = () => {
  inputValue.value = ''
  clearResults()
  showDropdown.value = false
  selectedIndex.value = -1
  inputRef.value?.focus()
}

const handleImageError = (event: Event) => {
  const img = event.target as HTMLImageElement
  img.style.display = 'none'
}

// Focus method for external use
const focus = () => {
  inputRef.value?.focus()
}

// Expose methods
defineExpose({
  focus,
  clearInput
})

// Cleanup
onUnmounted(() => {
  clearResults()
})
</script>