<template>
  <div class="space-y-6">
    <div class="sm:flex sm:items-center">
      <div class="sm:flex-auto">
        <h1 class="text-2xl font-semibold text-gray-900">{{ $t('dashboard.overview') }}</h1>
        <p class="mt-2 text-sm text-gray-700">
          {{ $t('dashboard.overviewDescription') }}
        </p>
      </div>
      <div class="mt-4 sm:mt-0 sm:ml-16 sm:flex-none">
        <BusinessSelector />
      </div>
    </div>

    <!-- Key Metrics -->
    <div class="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-4">
      <MetricCard
        v-for="metric in metrics"
        :key="metric.name"
        :title="metric.name"
        :value="metric.value"
        :change="metric.change"
        :trend="metric.trend"
        :icon="metric.icon"
      />
    </div>

    <!-- Charts Section -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            {{ $t('dashboard.sentimentTrend') }}
          </h3>
          <SentimentChart :data="sentimentData" />
        </div>
      </div>

      <div class="bg-white overflow-hidden shadow rounded-lg">
        <div class="p-6">
          <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
            {{ $t('dashboard.topTopics') }}
          </h3>
          <TopicsChart :data="topicsData" />
        </div>
      </div>
    </div>

    <!-- Recent Reviews -->
    <div class="bg-white shadow rounded-lg">
      <div class="px-4 py-5 sm:p-6">
        <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
          {{ $t('dashboard.recentReviews') }}
        </h3>
        <RecentReviewsList :reviews="recentReviews" />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue'
import { useBusinessStore } from '@/stores/business'
import { analyticsService } from '@/services/analytics'
import BusinessSelector from '@/components/common/BusinessSelector.vue'
import MetricCard from '@/components/common/MetricCard.vue'
import SentimentChart from '@/components/charts/SentimentChart.vue'
import TopicsChart from '@/components/charts/TopicsChart.vue'
import RecentReviewsList from '@/components/review/RecentReviewsList.vue'

const businessStore = useBusinessStore()
const dashboardData = ref(null)
const loading = ref(false)

const metrics = computed(() => {
  if (!dashboardData.value) return []
  
  return [
    {
      name: 'Average Rating',
      value: dashboardData.value.avg_rating?.toFixed(1) || '0.0',
      change: '+0.2',
      trend: 'up',
      icon: 'star'
    },
    {
      name: 'Total Reviews',
      value: dashboardData.value.total_reviews || 0,
      change: '+12',
      trend: 'up',
      icon: 'chat'
    },
    {
      name: 'Positive Sentiment',
      value: `${dashboardData.value.sentiment_distribution?.positive?.toFixed(0) || 0}%`,
      change: '+5%',
      trend: 'up',
      icon: 'thumb-up'
    },
    {
      name: 'Response Rate',
      value: `${dashboardData.value.response_rate?.toFixed(0) || 0}%`,
      change: '+3%',
      trend: 'up',
      icon: 'reply'
    }
  ]
})

const sentimentData = computed(() => dashboardData.value?.trend_data || [])
const topicsData = computed(() => dashboardData.value?.top_topics || [])
const recentReviews = computed(() => dashboardData.value?.recent_reviews || [])

async function fetchDashboardData() {
  if (!businessStore.currentBusiness) return
  
  loading.value = true
  try {
    dashboardData.value = await analyticsService.getDashboardData(businessStore.currentBusiness.id)
  } catch (error) {
    console.error('Failed to fetch dashboard data:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
})

// Watch for business changes
watch(() => businessStore.currentBusiness, fetchDashboardData)
</script>