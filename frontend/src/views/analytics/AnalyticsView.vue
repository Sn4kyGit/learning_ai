<template>
  <div class="space-y-6">
    <!-- Header with Business Selector for Super-Admins -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ $t('analytics.title') }}
          </h1>
          <p class="mt-1 text-sm text-gray-600">
            {{ $t('analytics.subtitle') }}
          </p>
        </div>
        
        <!-- Multi-Restaurant Selector for Super-Admins -->
        <div v-if="user?.role === 'super_admin' && businesses.length > 1" class="flex items-center space-x-4">
          <label class="text-sm font-medium text-gray-700">{{ $t('analytics.selectBusiness') }}:</label>
          <select
            v-model="selectedBusinessId"
            @change="onBusinessChange"
            class="block w-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          >
            <option value="all">{{ $t('analytics.allBusinesses') }}</option>
            <option v-for="business in businesses" :key="business.id" :value="business.id">
              {{ business.name }}
            </option>
          </select>
        </div>
      </div>
    </div>

    <!-- KPI Cards -->
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
                  {{ $t('analytics.averageRating') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ dashboardData.avg_rating?.toFixed(1) || '0.0' }}
                </dd>
                <dd class="text-sm text-gray-500">
                  <span :class="getRatingTrendColor(dashboardData.rating_trend)">
                    {{ formatTrend(dashboardData.rating_trend) }}
                  </span>
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
                  {{ $t('analytics.totalReviews') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ dashboardData.review_count || 0 }}
                </dd>
                <dd class="text-sm text-gray-500">
                  <span :class="getReviewTrendColor(dashboardData.review_trend)">
                    {{ formatTrend(dashboardData.review_trend) }}
                  </span>
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
                  {{ $t('analytics.positiveReviews') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  {{ dashboardData.sentiment_positive?.toFixed(0) || 0 }}%
                </dd>
                <dd class="text-sm text-gray-500">
                  <span :class="getSentimentTrendColor(dashboardData.sentiment_trend)">
                    {{ formatTrend(dashboardData.sentiment_trend) }}
                  </span>
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
              <CurrencyDollarIcon class="h-6 w-6 text-purple-400" />
            </div>
            <div class="ml-5 w-0 flex-1">
              <dl>
                <dt class="text-sm font-medium text-gray-500 truncate">
                  {{ $t('analytics.aiCosts') }}
                </dt>
                <dd class="text-lg font-medium text-gray-900">
                  ${{ costData.current_month?.toFixed(2) || '0.00' }}
                </dd>
                <dd class="text-sm" :class="getCostWarningColor(costData.usage_percentage)">
                  {{ costData.usage_percentage?.toFixed(0) || 0 }}% {{ $t('analytics.ofBudget') }}
                </dd>
              </dl>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Cost Warning Alert -->
    <div v-if="costData.usage_percentage >= 80" class="bg-yellow-50 border-l-4 border-yellow-400 p-4">
      <div class="flex">
        <div class="flex-shrink-0">
          <ExclamationTriangleIcon class="h-5 w-5 text-yellow-400" />
        </div>
        <div class="ml-3">
          <p class="text-sm text-yellow-700">
            <strong>{{ $t('analytics.budgetWarning') }}</strong>
            {{ $t('analytics.budgetWarningMessage', { percentage: costData.usage_percentage?.toFixed(0) }) }}
          </p>
        </div>
      </div>
    </div>

    <!-- Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Sentiment Trend Chart -->
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('analytics.sentimentTrends') }}
          </h3>
          <select
            v-model="sentimentPeriod"
            @change="loadSentimentTrends"
            class="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="7d">{{ $t('analytics.last7Days') }}</option>
            <option value="30d">{{ $t('analytics.last30Days') }}</option>
            <option value="90d">{{ $t('analytics.last90Days') }}</option>
          </select>
        </div>
        <div class="h-64">
          <Line
            v-if="sentimentChartData.datasets.length > 0"
            :data="sentimentChartData"
            :options="sentimentChartOptions"
          />
          <div v-else class="flex items-center justify-center h-full text-gray-500">
            {{ $t('analytics.noData') }}
          </div>
        </div>
      </div>

      <!-- Topic Analysis Chart -->
      <div class="bg-white shadow rounded-lg p-6">
        <div class="flex items-center justify-between mb-4">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('analytics.topicAnalysis') }}
          </h3>
          <select
            v-model="topicPeriod"
            @change="loadTopicAnalysis"
            class="text-sm border border-gray-300 rounded-md px-2 py-1"
          >
            <option value="7d">{{ $t('analytics.last7Days') }}</option>
            <option value="30d">{{ $t('analytics.last30Days') }}</option>
            <option value="90d">{{ $t('analytics.last90Days') }}</option>
          </select>
        </div>
        <div class="h-64">
          <Doughnut
            v-if="topicChartData.datasets.length > 0"
            :data="topicChartData"
            :options="topicChartOptions"
          />
          <div v-else class="flex items-center justify-center h-full text-gray-500">
            {{ $t('analytics.noData') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Detailed Analytics Tables -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <!-- Recent Critical Reviews -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('analytics.criticalReviews') }}
          </h3>
        </div>
        <div class="p-6">
          <div v-if="criticalReviews.length === 0" class="text-center py-8">
            <ExclamationTriangleIcon class="mx-auto h-12 w-12 text-gray-400" />
            <h3 class="mt-2 text-sm font-medium text-gray-900">{{ $t('analytics.noCriticalReviews') }}</h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ $t('analytics.noCriticalReviewsMessage') }}
            </p>
          </div>
          <div v-else class="space-y-4">
            <div
              v-for="review in criticalReviews.slice(0, 5)"
              :key="review.id"
              class="border-l-4 border-red-400 pl-4 py-2"
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
              <div class="mt-2 flex items-center space-x-2">
                <span class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-red-100 text-red-800">
                  {{ $t('analytics.highUrgency') }}
                </span>
                <span
                  v-for="topic in review.classification?.topics || []"
                  :key="topic"
                  class="inline-flex items-center px-2 py-1 rounded-full text-xs font-medium bg-gray-100 text-gray-800"
                >
                  {{ $t(`topics.${topic}`) }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Cost Breakdown -->
      <div class="bg-white shadow rounded-lg">
        <div class="px-6 py-4 border-b border-gray-200">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('analytics.costBreakdown') }}
          </h3>
        </div>
        <div class="p-6">
          <div class="space-y-4">
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-900">{{ $t('analytics.reviewClassification') }}</span>
              <span class="text-sm text-gray-500">${{ costData.breakdown?.classification?.toFixed(2) || '0.00' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-900">{{ $t('analytics.chatInteractions') }}</span>
              <span class="text-sm text-gray-500">${{ costData.breakdown?.chat?.toFixed(2) || '0.00' }}</span>
            </div>
            <div class="flex items-center justify-between">
              <span class="text-sm font-medium text-gray-900">{{ $t('analytics.reportGeneration') }}</span>
              <span class="text-sm text-gray-500">${{ costData.breakdown?.reports?.toFixed(2) || '0.00' }}</span>
            </div>
            <div class="border-t pt-4">
              <div class="flex items-center justify-between">
                <span class="text-base font-medium text-gray-900">{{ $t('analytics.totalThisMonth') }}</span>
                <span class="text-base font-medium text-gray-900">${{ costData.current_month?.toFixed(2) || '0.00' }}</span>
              </div>
              <div class="flex items-center justify-between mt-1">
                <span class="text-sm text-gray-500">{{ $t('analytics.monthlyLimit') }}</span>
                <span class="text-sm text-gray-500">${{ costData.limit?.toFixed(2) || '0.00' }}</span>
              </div>
            </div>
            
            <!-- Budget Progress Bar -->
            <div class="mt-4">
              <div class="flex items-center justify-between text-sm">
                <span class="text-gray-500">{{ $t('analytics.budgetUsage') }}</span>
                <span :class="getCostWarningColor(costData.usage_percentage)">
                  {{ costData.usage_percentage?.toFixed(0) || 0 }}%
                </span>
              </div>
              <div class="mt-1 w-full bg-gray-200 rounded-full h-2">
                <div
                  :class="getBudgetBarColor(costData.usage_percentage)"
                  class="h-2 rounded-full transition-all duration-300"
                  :style="{ width: `${Math.min(costData.usage_percentage || 0, 100)}%` }"
                ></div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Auto-refresh indicator -->
    <div class="text-center text-sm text-gray-500">
      {{ $t('analytics.lastUpdated') }}: {{ formatDate(lastUpdated) }}
      <span class="ml-2">•</span>
      {{ $t('analytics.autoRefresh') }}
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  StarIcon,
  ChatBubbleLeftRightIcon,
  FaceSmileIcon,
  CurrencyDollarIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'
import { Line, Doughnut } from 'vue-chartjs'
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
} from 'chart.js'
import { useAuthStore } from '@/stores/auth'
import { useBusinessStore } from '@/stores/business'
import { analyticsService } from '@/services/analytics'
import { formatDistanceToNow } from 'date-fns'
import type { DashboardMetrics, Review } from '@/types'

// Register Chart.js components
ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  ArcElement
)

const { t } = useI18n()
const authStore = useAuthStore()
const businessStore = useBusinessStore()

const user = computed(() => authStore.user)
const businesses = computed(() => businessStore.businesses)

// Reactive data
const selectedBusinessId = ref<string>('all')
const dashboardData = ref<Partial<DashboardMetrics>>({})
const costData = ref<any>({})
const criticalReviews = ref<Review[]>([])
const lastUpdated = ref<string>(new Date().toISOString())
const refreshInterval = ref<NodeJS.Timeout | null>(null)

// Chart data
const sentimentPeriod = ref('30d')
const topicPeriod = ref('30d')
const sentimentChartData = ref<any>({ datasets: [] })
const topicChartData = ref<any>({ datasets: [] })

// Chart options
const sentimentChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: false,
    },
  },
  scales: {
    y: {
      beginAtZero: true,
      max: 100,
      ticks: {
        callback: function(value: any) {
          return value + '%'
        }
      }
    }
  }
}

const topicChartOptions = {
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'right' as const,
    },
    title: {
      display: false,
    },
  },
}

// Helper functions
const formatDate = (dateString: string) => {
  return formatDistanceToNow(new Date(dateString), { addSuffix: true })
}

const formatTrend = (trend?: number) => {
  if (!trend) return ''
  const sign = trend > 0 ? '+' : ''
  return `${sign}${trend.toFixed(1)}%`
}

const getRatingTrendColor = (trend?: number) => {
  if (!trend) return 'text-gray-500'
  return trend > 0 ? 'text-green-600' : 'text-red-600'
}

const getReviewTrendColor = (trend?: number) => {
  if (!trend) return 'text-gray-500'
  return trend > 0 ? 'text-green-600' : 'text-red-600'
}

const getSentimentTrendColor = (trend?: number) => {
  if (!trend) return 'text-gray-500'
  return trend > 0 ? 'text-green-600' : 'text-red-600'
}

const getCostWarningColor = (percentage?: number) => {
  if (!percentage) return 'text-gray-500'
  if (percentage >= 90) return 'text-red-600 font-medium'
  if (percentage >= 80) return 'text-yellow-600 font-medium'
  return 'text-green-600'
}

const getBudgetBarColor = (percentage?: number) => {
  if (!percentage) return 'bg-gray-300'
  if (percentage >= 90) return 'bg-red-500'
  if (percentage >= 80) return 'bg-yellow-500'
  return 'bg-green-500'
}

// Data loading functions
const loadDashboardData = async () => {
  try {
    const businessId = selectedBusinessId.value === 'all' ? null : selectedBusinessId.value
    const currentBusiness = businessId || businessStore.currentBusiness?.id
    
    if (!currentBusiness) return

    const [dashboard, costs, critical] = await Promise.all([
      analyticsService.getDashboardData(currentBusiness),
      analyticsService.getCostSummary(currentBusiness),
      // Simulate critical reviews - in real app this would be an API call
      Promise.resolve([])
    ])

    dashboardData.value = dashboard
    costData.value = costs
    criticalReviews.value = critical
    lastUpdated.value = new Date().toISOString()
  } catch (error) {
    console.error('Failed to load dashboard data:', error)
  }
}

const loadSentimentTrends = async () => {
  try {
    const businessId = selectedBusinessId.value === 'all' ? null : selectedBusinessId.value
    const currentBusiness = businessId || businessStore.currentBusiness?.id
    
    if (!currentBusiness) return

    const sentimentData = await analyticsService.getSentimentAnalysis(currentBusiness, sentimentPeriod.value)
    
    // Transform data for Chart.js
    sentimentChartData.value = {
      labels: sentimentData.trends?.map((item: any) => item.date) || [],
      datasets: [
        {
          label: t('analytics.positive'),
          data: sentimentData.trends?.map((item: any) => item.positive) || [],
          borderColor: 'rgb(34, 197, 94)',
          backgroundColor: 'rgba(34, 197, 94, 0.1)',
          tension: 0.1
        },
        {
          label: t('analytics.neutral'),
          data: sentimentData.trends?.map((item: any) => item.neutral) || [],
          borderColor: 'rgb(234, 179, 8)',
          backgroundColor: 'rgba(234, 179, 8, 0.1)',
          tension: 0.1
        },
        {
          label: t('analytics.negative'),
          data: sentimentData.trends?.map((item: any) => item.negative) || [],
          borderColor: 'rgb(239, 68, 68)',
          backgroundColor: 'rgba(239, 68, 68, 0.1)',
          tension: 0.1
        }
      ]
    }
  } catch (error) {
    console.error('Failed to load sentiment trends:', error)
  }
}

const loadTopicAnalysis = async () => {
  try {
    const businessId = selectedBusinessId.value === 'all' ? null : selectedBusinessId.value
    const currentBusiness = businessId || businessStore.currentBusiness?.id
    
    if (!currentBusiness) return

    const topicData = await analyticsService.getTopicAnalysis(currentBusiness, topicPeriod.value)
    
    // Transform data for Chart.js
    const colors = [
      'rgb(59, 130, 246)',
      'rgb(34, 197, 94)',
      'rgb(234, 179, 8)',
      'rgb(239, 68, 68)',
      'rgb(168, 85, 247)',
      'rgb(236, 72, 153)'
    ]
    
    topicChartData.value = {
      labels: topicData.topics?.map((topic: any) => t(`topics.${topic.name}`)) || [],
      datasets: [
        {
          data: topicData.topics?.map((topic: any) => topic.count) || [],
          backgroundColor: colors.slice(0, topicData.topics?.length || 0),
          borderWidth: 2,
          borderColor: '#ffffff'
        }
      ]
    }
  } catch (error) {
    console.error('Failed to load topic analysis:', error)
  }
}

const onBusinessChange = () => {
  loadDashboardData()
  loadSentimentTrends()
  loadTopicAnalysis()
}

const setupAutoRefresh = () => {
  // Refresh data every 4 hours (14400000 ms)
  refreshInterval.value = setInterval(() => {
    loadDashboardData()
    loadSentimentTrends()
    loadTopicAnalysis()
  }, 14400000)
}

// Lifecycle
onMounted(async () => {
  await businessStore.fetchBusinesses()
  
  if (businesses.value.length > 0) {
    selectedBusinessId.value = businessStore.currentBusiness?.id || businesses.value[0].id
  }
  
  await loadDashboardData()
  await loadSentimentTrends()
  await loadTopicAnalysis()
  
  setupAutoRefresh()
})

onUnmounted(() => {
  if (refreshInterval.value) {
    clearInterval(refreshInterval.value)
  }
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