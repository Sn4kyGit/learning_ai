<template>
  <div class="space-y-6">
    <!-- Welcome Section -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ $t('dashboard.welcome') }}, {{ user?.name }}!
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            {{ $t('dashboard.overview') }}
          </p>
        </div>
        <div class="flex space-x-3">
          <button
            @click="importReviews"
            :disabled="importing"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <ArrowDownTrayIcon class="h-4 w-4 mr-2" />
            {{ importing ? $t('common.loading') : $t('dashboard.importReviews') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <StarIcon class="h-6 w-6 text-yellow-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 truncate">
                  {{ $t('reviews.averageRating') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.averageRating?.toFixed(1) || '0.0' }}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <ChatBubbleLeftRightIcon class="h-6 w-6 text-blue-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 truncate">
                  {{ $t('reviews.totalReviews') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.totalReviews || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <FaceSmileIcon class="h-6 w-6 text-green-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 truncate">
                  {{ $t('reviews.positive') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.positivePercentage?.toFixed(0) || 0 }}%
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>

      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-5">
          <div class="flex items-center">
            <div class="flex-shrink-0">
              <ExclamationTriangleIcon class="h-6 w-6 text-red-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 truncate">
                  {{ $t('reviews.high') }} {{ $t('reviews.urgency') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ stats.criticalReviews || 0 }}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Recent Reviews and Quick Actions -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Recent Reviews -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
          <div class="flex items-center justify-between">
            <h3 class="text-lg font-medium text-gray-900">
              {{ $t('dashboard.recentReviews') }}
            </h3>
            <router-link
              to="/reviews"
              class="text-sm text-blue-600 hover:text-blue-800"
            >
              {{ $t('dashboard.viewAllReviews') }}
            </router-link>
          </div>
        </div>
        <div class="p-6">
          <div v-if="recentReviews.length === 0" class="text-center py-8">
            <ChatBubbleLeftRightIcon class="mx-auto h-12 w-12 text-gray-400" />
            <h3 class="mt-2 text-sm font-medium text-gray-900">{{ $t('reviews.noReviews') }}</h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ $t('dashboard.importReviews') }}
            </p>
          </div>
          <div v-else class="space-y-4">
            <div
              v-for="review in recentReviews.slice(0, 3)"
              :key="review.id"
              class="border-l-4 pl-4 py-2"
              :class="getSentimentBorderColor(review.classification?.sentiment)"
            >
              <div class="flex items-center justify-between">
                <div class="flex items-center space-x-2">
                  <div class="flex">
                    <StarIcon
                      v-for="i in 5"
                      :key="i"
                      :class="[
                        'h-4 w-4',
                        i <= review.rating ? 'text-yellow-400' : 'text-gray-300'
                      ]"
                    />
                  </div>
                  <span class="text-sm text-gray-500">{{ review.author_name }}</span>
                </div>
                <span class="text-xs text-gray-400">
                  {{ formatDate(review.published_at) }}
                </span>
              </div>
              <p class="mt-1 text-sm text-gray-700 line-clamp-2">
                {{ review.text }}
              </p>
              <div v-if="review.classification" class="mt-2 flex items-center space-x-2">
                <span
                  :class="[
                    'inline-flex items-center px-2 py-1 rounded-full text-xs font-medium',
                    getSentimentBadgeColor(review.classification.sentiment)
                  ]"
                >
                  {{ $t(`reviews.${review.classification.sentiment}`) }}
                </span>
                <span
                  v-if="review.classification.urgency === 'high'"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800"
                >
                  {{ $t('reviews.high') }} {{ $t('reviews.urgency') }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('dashboard.quickActions') }}
          </h3>
        </div>
        <div class="p-6">
          <div class="space-y-4">
            <router-link
              to="/chat"
              class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <ChatBubbleLeftRightIcon class="h-8 w-8 text-blue-500" />
              <div class="ml-4">
                <h4 class="text-sm font-medium text-gray-900">{{ $t('chat.title') }}</h4>
                <p class="text-sm text-gray-500">{{ $t('chat.welcomeMessage') }}</p>
              </div>
            </router-link>

            <router-link
              to="/analytics"
              class="flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors"
            >
              <ChartBarIcon class="h-8 w-8 text-green-500" />
              <div class="ml-4">
                <h4 class="text-sm font-medium text-gray-900">{{ $t('dashboard.analytics') }}</h4>
                <p class="text-sm text-gray-500">View detailed performance metrics</p>
              </div>
            </router-link>

            <button
              @click="generateReport"
              :disabled="generatingReport"
              class="w-full flex items-center p-4 border border-gray-200 rounded-lg hover:bg-gray-50 transition-colors disabled:opacity-50"
            >
              <DocumentTextIcon class="h-8 w-8 text-purple-500" />
              <div class="ml-4 text-left">
                <h4 class="text-sm font-medium text-gray-900">{{ $t('dashboard.generateReport') }}</h4>
                <p class="text-sm text-gray-500">
                  {{ generatingReport ? $t('common.loading') : 'Create weekly performance report' }}
                </p>
              </div>
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  StarIcon,
  ChatBubbleLeftRightIcon,
  FaceSmileIcon,
  ExclamationTriangleIcon,
  ArrowDownTrayIcon,
  ChartBarIcon,
  DocumentTextIcon
} from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { formatDistanceToNow } from 'date-fns'
import type { Review, DashboardMetrics } from '@/types'

const { t } = useI18n()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()

const user = computed(() => authStore.user)
const importing = ref(false)
const generatingReport = ref(false)
const recentReviews = ref<Review[]>([])
const stats = ref<Partial<DashboardMetrics>>({})

const getSentimentBorderColor = (sentiment?: string) => {
  switch (sentiment) {
    case 'positive':
      return 'border-green-400'
    case 'negative':
      return 'border-red-400'
    case 'neutral':
      return 'border-yellow-400'
    default:
      return 'border-gray-300'
  }
}

const getSentimentBadgeColor = (sentiment: string) => {
  switch (sentiment) {
    case 'positive':
      return 'bg-green-100 text-green-800'
    case 'negative':
      return 'bg-red-100 text-red-800'
    case 'neutral':
      return 'bg-yellow-100 text-yellow-800'
    default:
      return 'bg-gray-100 text-gray-800'
  }
}

const formatDate = (dateString: string) => {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true })
}

const importReviews = async () => {
  importing.value = true
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 2000))
    notificationsStore.showSuccess('Reviews imported successfully')
    loadDashboardData()
  } catch (error) {
    notificationsStore.showError('Failed to import reviews')
  } finally {
    importing.value = false
  }
}

const generateReport = async () => {
  generatingReport.value = true
  try {
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 3000))
    notificationsStore.showSuccess('Report generated successfully')
  } catch (error) {
    notificationsStore.showError('Failed to generate report')
  } finally {
    generatingReport.value = false
  }
}

const loadDashboardData = async () => {
  try {
    // Simulate loading dashboard data
    stats.value = {
      averageRating: 4.2,
      totalReviews: 156,
      positivePercentage: 78,
      criticalReviews: 3
    }

    // Simulate recent reviews
    recentReviews.value = [
      {
        id: '1',
        business_id: 'business-1',
        author_name: 'John Doe',
        rating: 5,
        text: 'Excellent food and service! The pasta was amazing and the staff was very friendly.',
        language: 'en',
        published_at: new Date(Date.now() - 2 * 24 * 60 * 60 * 1000).toISOString(),
        source: 'google',
        created_at: new Date().toISOString(),
        classification: {
          id: '1',
          review_id: '1',
          sentiment: 'positive',
          topics: ['food_quality', 'service'],
          urgency: 'low',
          competitor_mentioned: false,
          confidence_score: 0.95,
          ai_model: 'gpt-5-nano',
          processing_time_ms: 150,
          created_at: new Date().toISOString()
        }
      },
      {
        id: '2',
        business_id: 'business-1',
        author_name: 'Jane Smith',
        rating: 2,
        text: 'The service was very slow and the food was cold when it arrived. Very disappointed.',
        language: 'en',
        published_at: new Date(Date.now() - 1 * 24 * 60 * 60 * 1000).toISOString(),
        source: 'google',
        created_at: new Date().toISOString(),
        classification: {
          id: '2',
          review_id: '2',
          sentiment: 'negative',
          topics: ['service', 'food_quality'],
          urgency: 'high',
          competitor_mentioned: false,
          confidence_score: 0.92,
          ai_model: 'gpt-5-nano',
          processing_time_ms: 180,
          created_at: new Date().toISOString()
        }
      }
    ]
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

onMounted(() => {
  loadDashboardData()
})
</script>

<style scoped>
.line-clamp-2 {
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}
</style>