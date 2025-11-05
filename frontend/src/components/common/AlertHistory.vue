<template>
  <div class="space-y-4">
    <!-- Header -->
    <div class="flex items-center justify-between">
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        {{ $t('notifications.alertHistory') }}
      </h3>
      <button
        @click="loadAlerts"
        :disabled="loading"
        class="text-sm text-blue-600 hover:text-blue-800 disabled:opacity-50"
      >
        {{ $t('common.refresh') }}
      </button>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-3">
      <div v-for="i in 5" :key="i" class="animate-pulse">
        <div class="flex space-x-3">
          <div class="h-10 w-10 bg-gray-300 rounded-full"></div>
          <div class="flex-1 space-y-2">
            <div class="h-4 bg-gray-300 rounded w-3/4"></div>
            <div class="h-3 bg-gray-300 rounded w-1/2"></div>
          </div>
        </div>
      </div>
    </div>

    <!-- Empty state -->
    <div v-else-if="alerts.length === 0" class="text-center py-8">
      <BellIcon class="mx-auto h-12 w-12 text-gray-400" />
      <p class="mt-2 text-sm text-gray-500">{{ $t('notifications.noRecentAlerts') }}</p>
    </div>

    <!-- Alerts list -->
    <div v-else class="space-y-3">
      <div
        v-for="alert in alerts"
        :key="alert.id"
        class="flex items-start space-x-3 p-4 rounded-lg border"
        :class="[
          alert.read ? 'bg-white border-gray-200' : 'bg-blue-50 border-blue-200',
          getAlertBorderClass(alert.type)
        ]"
      >
        <!-- Alert icon -->
        <div class="flex-shrink-0">
          <div class="h-10 w-10 rounded-full flex items-center justify-center"
               :class="getAlertIconClass(alert.type)">
            <component :is="getAlertIcon(alert.type)" class="h-5 w-5" />
          </div>
        </div>

        <!-- Alert content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center justify-between">
            <p class="text-sm font-medium text-gray-900">
              {{ getAlertTitle(alert.type) }}
            </p>
            <div class="flex items-center space-x-2">
              <span class="text-xs text-gray-500">
                {{ formatTime(alert.timestamp) }}
              </span>
              <button
                v-if="!alert.read"
                @click="markAsRead(alert.id)"
                class="text-xs text-blue-600 hover:text-blue-800"
              >
                Mark as read
              </button>
            </div>
          </div>
          
          <p class="text-sm text-gray-600 mt-1">
            {{ alert.message }}
          </p>

          <!-- Alert actions -->
          <div v-if="alert.data" class="mt-2 flex items-center space-x-2">
            <button
              v-if="alert.type === 'critical_review' && alert.data.review_id"
              @click="viewReview(alert.data.review_id)"
              class="text-xs text-blue-600 hover:text-blue-800"
            >
              {{ $t('notifications.viewReview') }}
            </button>
            <button
              v-if="alert.type === 'budget_warning'"
              @click="manageBudget"
              class="text-xs text-blue-600 hover:text-blue-800"
            >
              {{ $t('analytics.adjustBudget') }}
            </button>
          </div>

          <!-- Severity indicator -->
          <div class="mt-2">
            <span class="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium"
                  :class="getSeverityClass(alert.severity)">
              {{ alert.severity.toUpperCase() }}
            </span>
          </div>
        </div>
      </div>
    </div>

    <!-- Load more button -->
    <div v-if="hasMore" class="text-center">
      <button
        @click="loadMore"
        :disabled="loadingMore"
        class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
      >
        {{ loadingMore ? $t('common.loading') : 'Load More' }}
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useRouter } from 'vue-router'
import { useNotificationsStore } from '@/stores/notifications'
import { notificationService } from '@/services/notifications'
import {
  BellIcon,
  ExclamationTriangleIcon,
  EyeIcon,
  CurrencyDollarIcon,
  UserGroupIcon
} from '@heroicons/vue/24/outline'

interface Props {
  businessId?: string
  limit?: number
}

const props = withDefaults(defineProps<Props>(), {
  limit: 20
})

const { t } = useI18n()
const router = useRouter()
const notificationsStore = useNotificationsStore()

// Reactive state
const alerts = ref([])
const loading = ref(true)
const loadingMore = ref(false)
const hasMore = ref(false)
const skip = ref(0)

// Methods
const loadAlerts = async (append = false) => {
  if (append) {
    loadingMore.value = true
  } else {
    loading.value = true
    skip.value = 0
    alerts.value = []
  }

  try {
    const response = await notificationService.getNotifications(
      skip.value,
      props.limit,
      false // Include read notifications
    )
    
    if (append) {
      alerts.value.push(...response.notifications)
    } else {
      alerts.value = response.notifications
    }
    
    hasMore.value = response.notifications.length === props.limit
    skip.value += response.notifications.length
  } catch (error) {
    console.error('Failed to load alerts:', error)
    notificationsStore.showError('Failed to load alert history')
  } finally {
    loading.value = false
    loadingMore.value = false
  }
}

const loadMore = () => {
  loadAlerts(true)
}

const markAsRead = async (alertId: string | number) => {
  try {
    await notificationService.markAsRead(alertId)
    const alert = alerts.value.find(a => a.id === alertId)
    if (alert) {
      alert.read = true
    }
  } catch (error) {
    console.error('Failed to mark alert as read:', error)
  }
}

const viewReview = (reviewId: string) => {
  router.push(`/reviews?review=${reviewId}`)
}

const manageBudget = () => {
  router.push('/settings?tab=budget')
}

// Utility functions
const getAlertIcon = (type: string) => {
  const icons = {
    critical_review: ExclamationTriangleIcon,
    competitor_mention: UserGroupIcon,
    budget_warning: CurrencyDollarIcon,
    default: BellIcon
  }
  return icons[type] || icons.default
}

const getAlertIconClass = (type: string) => {
  const classes = {
    critical_review: 'bg-red-100 text-red-600',
    competitor_mention: 'bg-yellow-100 text-yellow-600',
    budget_warning: 'bg-orange-100 text-orange-600',
    default: 'bg-blue-100 text-blue-600'
  }
  return classes[type] || classes.default
}

const getAlertBorderClass = (type: string) => {
  const classes = {
    critical_review: 'border-l-4 border-l-red-400',
    competitor_mention: 'border-l-4 border-l-yellow-400',
    budget_warning: 'border-l-4 border-l-orange-400',
    default: 'border-l-4 border-l-blue-400'
  }
  return classes[type] || classes.default
}

const getAlertTitle = (type: string) => {
  const titles = {
    critical_review: t('notifications.criticalReviewAlert'),
    competitor_mention: t('notifications.competitorMentionAlert'),
    budget_warning: t('notifications.budgetWarningAlert'),
    default: 'Notification'
  }
  return titles[type] || titles.default
}

const getSeverityClass = (severity: string) => {
  const classes = {
    low: 'bg-blue-100 text-blue-800',
    medium: 'bg-yellow-100 text-yellow-800',
    high: 'bg-red-100 text-red-800'
  }
  return classes[severity] || classes.low
}

const formatTime = (timestamp: string | Date) => {
  const date = new Date(timestamp)
  const now = new Date()
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
  
  if (diffInHours < 1) {
    return 'Just now'
  } else if (diffInHours < 24) {
    return `${Math.floor(diffInHours)}h ago`
  } else {
    return date.toLocaleDateString()
  }
}

// Lifecycle
onMounted(() => {
  loadAlerts()
})
</script>