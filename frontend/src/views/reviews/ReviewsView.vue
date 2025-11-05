<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between mb-4">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ $t('reviews.title') }}
          </h1>
          <p class="text-gray-600">
            {{ selectedBusiness?.name || $t('reviews.title') }}
          </p>
        </div>
        
        <div class="flex items-center space-x-3">
          <BusinessSelector 
            v-model="selectedBusinessId" 
            @update:modelValue="onBusinessChange"
          />
          
          <button
            @click="processReviews"
            :disabled="loading.processing"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <CogIcon class="h-4 w-4 mr-2" :class="{ 'animate-spin': loading.processing }" />
            {{ loading.processing ? $t('reviews.processing') : $t('reviews.processReviews') }}
          </button>
        </div>
      </div>

      <!-- Statistics -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div class="bg-gray-50 p-4 rounded-lg">
          <p class="text-sm font-medium text-gray-600">{{ $t('reviews.totalReviews') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ statistics.total_reviews || 0 }}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <p class="text-sm font-medium text-gray-600">{{ $t('reviews.averageRating') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ statistics.avg_rating?.toFixed(1) || '0.0' }}</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <p class="text-sm font-medium text-gray-600">{{ $t('reviews.responseRate') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ statistics.response_rate?.toFixed(0) || 0 }}%</p>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <p class="text-sm font-medium text-gray-600">{{ $t('reviews.avgResponseTime') }}</p>
          <p class="text-2xl font-bold text-gray-900">{{ statistics.avg_response_time?.toFixed(1) || 0 }} {{ $t('reviews.hours') }}</p>
        </div>
      </div>
    </div>

    <!-- Filters and Search -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- Search -->
        <div class="md:col-span-2">
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('common.search') }}
          </label>
          <div class="relative">
            <MagnifyingGlassIcon class="absolute left-3 top-1/2 transform -translate-y-1/2 h-4 w-4 text-gray-400" />
            <input
              v-model="searchQuery"
              type="text"
              :placeholder="$t('reviews.searchPlaceholder')"
              class="pl-10 block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
              @input="debouncedSearch"
            />
          </div>
        </div>

        <!-- Filter by type -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('reviews.filterBy') }}
          </label>
          <select
            v-model="filters.type"
            @change="applyFilters"
            class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          >
            <option value="">{{ $t('reviews.allReviews') }}</option>
            <option value="unclassified">{{ $t('reviews.unclassified') }}</option>
            <option value="critical">{{ $t('reviews.critical') }}</option>
            <option value="competitor_mentions">{{ $t('reviews.competitorMentions') }}</option>
          </select>
        </div>

        <!-- Sort by -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('reviews.sortBy') }}
          </label>
          <select
            v-model="filters.sort"
            @change="applyFilters"
            class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
          >
            <option value="newest">{{ $t('reviews.newest') }}</option>
            <option value="oldest">{{ $t('reviews.oldest') }}</option>
            <option value="highest_rating">{{ $t('reviews.highestRating') }}</option>
            <option value="lowest_rating">{{ $t('reviews.lowestRating') }}</option>
          </select>
        </div>
      </div>

      <!-- Additional filters -->
      <div class="mt-4 flex flex-wrap gap-2">
        <button
          v-for="sentiment in ['positive', 'neutral', 'negative']"
          :key="sentiment"
          @click="toggleSentimentFilter(sentiment)"
          class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
          :class="[
            filters.sentiment.includes(sentiment)
              ? getSentimentActiveClass(sentiment)
              : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
          ]"
        >
          {{ $t(`reviews.${sentiment}`) }}
        </button>
        
        <button
          v-for="urgency in ['low', 'medium', 'high']"
          :key="urgency"
          @click="toggleUrgencyFilter(urgency)"
          class="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium"
          :class="[
            filters.urgency.includes(urgency)
              ? getUrgencyActiveClass(urgency)
              : 'bg-gray-100 text-gray-800 hover:bg-gray-200'
          ]"
        >
          {{ $t(`reviews.${urgency}`) }}
        </button>
      </div>
    </div>

    <!-- Reviews List -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-6 py-4 border-b border-gray-200">
        <h2 class="text-lg font-medium text-gray-900">
          {{ $t('reviews.title') }} ({{ reviews.length }})
        </h2>
      </div>

      <div v-if="loading.reviews" class="p-6">
        <div class="space-y-4">
          <div v-for="i in 5" :key="i" class="animate-pulse">
            <div class="flex space-x-4">
              <div class="h-12 w-12 bg-gray-300 rounded-full"></div>
              <div class="flex-1 space-y-2">
                <div class="h-4 bg-gray-300 rounded w-3/4"></div>
                <div class="h-4 bg-gray-300 rounded w-1/2"></div>
                <div class="h-16 bg-gray-300 rounded"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <div v-else-if="reviews.length === 0" class="p-12 text-center">
        <DocumentTextIcon class="mx-auto h-16 w-16 text-gray-400" />
        <p class="mt-4 text-lg text-gray-500">{{ $t('reviews.noReviews') }}</p>
      </div>

      <div v-else class="divide-y divide-gray-200">
        <div
          v-for="review in reviews"
          :key="review.id"
          class="p-6 hover:bg-gray-50 transition-colors"
        >
          <div class="flex items-start space-x-4">
            <!-- Rating -->
            <div class="flex-shrink-0">
              <div class="flex items-center justify-center w-12 h-12 rounded-full"
                   :class="getRatingBgClass(review.rating)">
                <span class="text-white font-bold">{{ review.rating }}</span>
              </div>
            </div>

            <!-- Review content -->
            <div class="flex-1 min-w-0">
              <div class="flex items-center justify-between mb-2">
                <div class="flex items-center space-x-2">
                  <h3 class="text-sm font-medium text-gray-900">{{ review.author_name }}</h3>
                  <span class="text-xs text-gray-500">{{ formatDate(review.published_at) }}</span>
                  <span v-if="review.language !== 'en'" class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-gray-100 text-gray-800">
                    {{ review.language.toUpperCase() }}
                  </span>
                </div>
                
                <div class="flex items-center space-x-2">
                  <!-- Classification badges -->
                  <div v-if="review.classification" class="flex items-center space-x-1">
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                          :class="getSentimentClass(review.classification.sentiment)">
                      {{ $t(`reviews.${review.classification.sentiment}`) }}
                    </span>
                    <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                          :class="getUrgencyClass(review.classification.urgency)">
                      {{ $t(`reviews.${review.classification.urgency}`) }}
                    </span>
                    <span v-if="review.classification.competitor_mentioned" 
                          class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-red-100 text-red-800">
                      Competitor
                    </span>
                  </div>
                  
                  <!-- Actions -->
                  <div class="flex items-center space-x-1">
                    <button
                      @click="toggleReviewDetails(review.id)"
                      class="p-1 text-gray-400 hover:text-gray-600"
                      :title="showDetails[review.id] ? $t('reviews.hideDetails') : $t('reviews.viewDetails')"
                    >
                      <ChevronDownIcon class="h-4 w-4 transform transition-transform"
                                       :class="{ 'rotate-180': showDetails[review.id] }" />
                    </button>
                    <button
                      @click="openResponseModal(review)"
                      class="p-1 text-gray-400 hover:text-blue-600"
                      :title="$t('reviews.respond')"
                    >
                      <ChatBubbleLeftIcon class="h-4 w-4" />
                    </button>
                  </div>
                </div>
              </div>

              <!-- Review text -->
              <p class="text-sm text-gray-700 mb-3">{{ review.text }}</p>

              <!-- Topics -->
              <div v-if="review.classification?.topics" class="flex flex-wrap gap-1 mb-3">
                <span
                  v-for="topic in review.classification.topics"
                  :key="topic"
                  class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-blue-100 text-blue-800"
                >
                  {{ $t(`topics.${topic}`) }}
                </span>
              </div>

              <!-- Expanded details -->
              <div v-if="showDetails[review.id]" class="mt-4 p-4 bg-gray-50 rounded-lg">
                <div class="grid grid-cols-2 gap-4 text-sm">
                  <div>
                    <span class="font-medium text-gray-700">{{ $t('reviews.confidence') }}:</span>
                    <span class="ml-2">{{ (review.classification?.confidence_score * 100)?.toFixed(1) }}%</span>
                  </div>
                  <div>
                    <span class="font-medium text-gray-700">{{ $t('reviews.aiModel') }}:</span>
                    <span class="ml-2">{{ review.classification?.ai_model }}</span>
                  </div>
                  <div>
                    <span class="font-medium text-gray-700">{{ $t('reviews.processingTime') }}:</span>
                    <span class="ml-2">{{ review.classification?.processing_time_ms }} {{ $t('reviews.ms') }}</span>
                  </div>
                  <div>
                    <span class="font-medium text-gray-700">{{ $t('reviews.date') }}:</span>
                    <span class="ml-2">{{ formatDateTime(review.created_at) }}</span>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Response Modal -->
    <div v-if="responseModal.show" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="closeResponseModal"></div>
        
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
              {{ $t('reviews.respond') }}
            </h3>
            
            <!-- Original review -->
            <div class="mb-4 p-3 bg-gray-50 rounded-lg">
              <div class="flex items-center space-x-2 mb-2">
                <span class="font-medium">{{ responseModal.review?.author_name }}</span>
                <span class="text-sm text-gray-500">{{ responseModal.review?.rating }}/5</span>
              </div>
              <p class="text-sm text-gray-700">{{ responseModal.review?.text }}</p>
            </div>

            <!-- Response options -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                {{ $t('reviews.responseOptions') }}
              </label>
              <div class="flex space-x-2">
                <button
                  v-for="tone in ['professional', 'friendly', 'apologetic', 'thankful']"
                  :key="tone"
                  @click="generateResponseSuggestion(tone)"
                  :disabled="loading.suggestions"
                  class="px-3 py-1 text-xs font-medium rounded-md border border-gray-300 hover:bg-gray-50 disabled:opacity-50"
                >
                  {{ $t(`reviews.${tone}`) }}
                </button>
              </div>
            </div>

            <!-- Suggested response -->
            <div v-if="responseModal.suggestion" class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                {{ $t('reviews.suggestedResponse') }}
              </label>
              <div class="p-3 bg-blue-50 rounded-lg">
                <p class="text-sm text-gray-700">{{ responseModal.suggestion }}</p>
                <button
                  @click="responseModal.text = responseModal.suggestion"
                  class="mt-2 text-xs text-blue-600 hover:text-blue-800"
                >
                  Use this response
                </button>
              </div>
            </div>

            <!-- Response text -->
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                {{ $t('reviews.customResponse') }}
              </label>
              <textarea
                v-model="responseModal.text"
                rows="4"
                class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
                :placeholder="$t('reviews.customResponse')"
              ></textarea>
            </div>

            <!-- Tone analysis -->
            <div v-if="responseModal.toneAnalysis" class="mb-4 p-3 bg-yellow-50 rounded-lg">
              <p class="text-sm font-medium text-yellow-800">{{ $t('reviews.toneAnalysis') }}</p>
              <p class="text-sm text-yellow-700">{{ responseModal.toneAnalysis }}</p>
            </div>
          </div>
          
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              @click="sendResponse"
              :disabled="!responseModal.text.trim() || loading.sendingResponse"
              class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50"
            >
              {{ loading.sendingResponse ? $t('common.loading') : $t('reviews.sendResponse') }}
            </button>
            <button
              @click="closeResponseModal"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              {{ $t('common.cancel') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBusinessStore } from '@/stores/business'
import { useNotificationsStore } from '@/stores/notifications'
import { reviewService } from '@/services/review'
import BusinessSelector from '@/components/dashboard/BusinessSelector.vue'
import {
  CogIcon,
  MagnifyingGlassIcon,
  DocumentTextIcon,
  ChevronDownIcon,
  ChatBubbleLeftIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()
const businessStore = useBusinessStore()
const notificationsStore = useNotificationsStore()

// Reactive state
const selectedBusinessId = ref<string>('')
const reviews = ref([])
const statistics = ref({})
const searchQuery = ref('')
const showDetails = ref({})

const filters = reactive({
  type: '',
  sort: 'newest',
  sentiment: [],
  urgency: []
})

const loading = reactive({
  reviews: false,
  processing: false,
  suggestions: false,
  sendingResponse: false
})

const responseModal = reactive({
  show: false,
  review: null,
  text: '',
  suggestion: '',
  toneAnalysis: ''
})

// Computed properties
const selectedBusiness = computed(() => 
  businessStore.businesses.find(b => b.id === selectedBusinessId.value)
)

// Methods
const onBusinessChange = async (businessId: string) => {
  selectedBusinessId.value = businessId
  await Promise.all([
    loadReviews(),
    loadStatistics()
  ])
}

const loadReviews = async () => {
  if (!selectedBusinessId.value) return
  
  loading.reviews = true
  try {
    const params = {
      include_classifications: true,
      ...buildFilterParams()
    }
    
    const response = await reviewService.getReviews(selectedBusinessId.value, params)
    reviews.value = response.reviews
  } catch (error) {
    console.error('Failed to load reviews:', error)
    notificationsStore.showError(t('errors.serverError'))
  } finally {
    loading.reviews = false
  }
}

const loadStatistics = async () => {
  if (!selectedBusinessId.value) return
  
  try {
    const response = await reviewService.getReviewStatistics(selectedBusinessId.value)
    statistics.value = response.review_statistics
  } catch (error) {
    console.error('Failed to load statistics:', error)
  }
}

const buildFilterParams = () => {
  const params = {}
  
  if (searchQuery.value) {
    params.query = searchQuery.value
  }
  
  if (filters.type) {
    params.type = filters.type
  }
  
  if (filters.sentiment.length > 0) {
    params.sentiment = filters.sentiment.join(',')
  }
  
  if (filters.urgency.length > 0) {
    params.urgency = filters.urgency.join(',')
  }
  
  params.sort = filters.sort
  
  return params
}

const applyFilters = () => {
  loadReviews()
}

const debouncedSearch = debounce(() => {
  loadReviews()
}, 500)

const toggleSentimentFilter = (sentiment: string) => {
  const index = filters.sentiment.indexOf(sentiment)
  if (index > -1) {
    filters.sentiment.splice(index, 1)
  } else {
    filters.sentiment.push(sentiment)
  }
  applyFilters()
}

const toggleUrgencyFilter = (urgency: string) => {
  const index = filters.urgency.indexOf(urgency)
  if (index > -1) {
    filters.urgency.splice(index, 1)
  } else {
    filters.urgency.push(urgency)
  }
  applyFilters()
}

const processReviews = async () => {
  if (!selectedBusinessId.value) return
  
  loading.processing = true
  try {
    const response = await reviewService.processReviews(selectedBusinessId.value)
    notificationsStore.showSuccess(
      `Processed ${response.success_count} reviews successfully`
    )
    await loadReviews()
  } catch (error) {
    console.error('Failed to process reviews:', error)
    notificationsStore.showError(t('errors.serverError'))
  } finally {
    loading.processing = false
  }
}

const toggleReviewDetails = (reviewId: string) => {
  showDetails.value[reviewId] = !showDetails.value[reviewId]
}

const openResponseModal = (review: any) => {
  responseModal.show = true
  responseModal.review = review
  responseModal.text = ''
  responseModal.suggestion = ''
  responseModal.toneAnalysis = ''
}

const closeResponseModal = () => {
  responseModal.show = false
  responseModal.review = null
  responseModal.text = ''
  responseModal.suggestion = ''
  responseModal.toneAnalysis = ''
}

const generateResponseSuggestion = async (tone: string) => {
  if (!responseModal.review) return
  
  loading.suggestions = true
  try {
    const response = await reviewService.getResponseSuggestions(responseModal.review.id)
    responseModal.suggestion = response.suggestion
    responseModal.toneAnalysis = response.tone_analysis
  } catch (error) {
    console.error('Failed to generate suggestion:', error)
    notificationsStore.showError(t('errors.serverError'))
  } finally {
    loading.suggestions = false
  }
}

const sendResponse = async () => {
  if (!responseModal.review || !responseModal.text.trim()) return
  
  loading.sendingResponse = true
  try {
    await reviewService.addReviewResponse(responseModal.review.id, responseModal.text)
    notificationsStore.showSuccess('Response sent successfully')
    closeResponseModal()
    await loadReviews()
  } catch (error) {
    console.error('Failed to send response:', error)
    notificationsStore.showError(t('errors.serverError'))
  } finally {
    loading.sendingResponse = false
  }
}

// Utility functions
const getRatingBgClass = (rating: number) => {
  if (rating >= 4) return 'bg-green-500'
  if (rating >= 3) return 'bg-yellow-500'
  return 'bg-red-500'
}

const getSentimentClass = (sentiment: string) => {
  const classes = {
    positive: 'bg-green-100 text-green-800',
    neutral: 'bg-yellow-100 text-yellow-800',
    negative: 'bg-red-100 text-red-800'
  }
  return classes[sentiment] || 'bg-gray-100 text-gray-800'
}

const getSentimentActiveClass = (sentiment: string) => {
  const classes = {
    positive: 'bg-green-200 text-green-900',
    neutral: 'bg-yellow-200 text-yellow-900',
    negative: 'bg-red-200 text-red-900'
  }
  return classes[sentiment] || 'bg-gray-200 text-gray-900'
}

const getUrgencyClass = (urgency: string) => {
  const classes = {
    low: 'bg-blue-100 text-blue-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800'
  }
  return classes[urgency] || 'bg-gray-100 text-gray-800'
}

const getUrgencyActiveClass = (urgency: string) => {
  const classes = {
    low: 'bg-blue-200 text-blue-900',
    medium: 'bg-yellow-200 text-yellow-900',
    high: 'bg-red-200 text-red-900'
  }
  return classes[urgency] || 'bg-gray-200 text-gray-900'
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const formatDateTime = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

// Debounce utility
function debounce(func: Function, wait: number) {
  let timeout: NodeJS.Timeout
  return function executedFunction(...args: any[]) {
    const later = () => {
      clearTimeout(timeout)
      func(...args)
    }
    clearTimeout(timeout)
    timeout = setTimeout(later, wait)
  }
}

// Lifecycle
onMounted(async () => {
  await businessStore.loadBusinesses()
  if (businessStore.businesses.length > 0) {
    selectedBusinessId.value = businessStore.currentBusiness?.id || businessStore.businesses[0].id
    await Promise.all([
      loadReviews(),
      loadStatistics()
    ])
  }
})
</script>