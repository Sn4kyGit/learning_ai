<template>
  <div class="bg-white shadow rounded-lg">
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('analytics.costTracking') }}
        </h3>
        <CurrencyDollarIcon class="h-5 w-5 text-gray-400" />
      </div>
    </div>
    <div class="p-6">
      <!-- Current Month Summary -->
      <div class="mb-6">
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm font-medium text-gray-900">{{ $t('analytics.currentMonth') }}</span>
          <span class="text-2xl font-bold text-gray-900">${{ costData.current_month?.toFixed(2) || '0.00' }}</span>
        </div>
        <div class="flex items-center justify-between text-sm text-gray-500 mb-3">
          <span>{{ $t('analytics.monthlyLimit') }}: ${{ costData.limit?.toFixed(2) || '0.00' }}</span>
          <span :class="getCostWarningColor(costData.usage_percentage)">
            {{ costData.usage_percentage?.toFixed(0) || 0 }}% {{ $t('analytics.used') }}
          </span>
        </div>
        
        <!-- Progress Bar -->
        <div class="w-full bg-gray-200 rounded-full h-3">
          <div
            :class="getBudgetBarColor(costData.usage_percentage)"
            class="h-3 rounded-full transition-all duration-300"
            :style="{ width: `${Math.min(costData.usage_percentage || 0, 100)}%` }"
          ></div>
        </div>
      </div>

      <!-- Budget Warning -->
      <div v-if="costData.usage_percentage >= 80" class="mb-6 p-3 rounded-md" :class="getWarningBgColor(costData.usage_percentage)">
        <div class="flex">
          <ExclamationTriangleIcon :class="getWarningIconColor(costData.usage_percentage)" class="h-5 w-5 mt-0.5" />
          <div class="ml-3">
            <h4 class="text-sm font-medium" :class="getWarningTextColor(costData.usage_percentage)">
              {{ getWarningTitle(costData.usage_percentage) }}
            </h4>
            <p class="text-sm mt-1" :class="getWarningTextColor(costData.usage_percentage)">
              {{ getWarningMessage(costData.usage_percentage) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Cost Breakdown -->
      <div class="space-y-4">
        <h4 class="text-sm font-medium text-gray-900">{{ $t('analytics.costBreakdown') }}</h4>
        
        <div class="space-y-3">
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-blue-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-700">{{ $t('analytics.reviewClassification') }}</span>
            </div>
            <span class="text-sm font-medium text-gray-900">
              ${{ costData.breakdown?.classification?.toFixed(2) || '0.00' }}
            </span>
          </div>
          
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-green-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-700">{{ $t('analytics.chatInteractions') }}</span>
            </div>
            <span class="text-sm font-medium text-gray-900">
              ${{ costData.breakdown?.chat?.toFixed(2) || '0.00' }}
            </span>
          </div>
          
          <div class="flex items-center justify-between">
            <div class="flex items-center">
              <div class="w-3 h-3 bg-purple-500 rounded-full mr-3"></div>
              <span class="text-sm text-gray-700">{{ $t('analytics.reportGeneration') }}</span>
            </div>
            <span class="text-sm font-medium text-gray-900">
              ${{ costData.breakdown?.reports?.toFixed(2) || '0.00' }}
            </span>
          </div>
        </div>
      </div>

      <!-- Usage Statistics -->
      <div class="mt-6 pt-6 border-t border-gray-200">
        <h4 class="text-sm font-medium text-gray-900 mb-3">{{ $t('analytics.usageStats') }}</h4>
        <div class="grid grid-cols-2 gap-4 text-sm">
          <div>
            <span class="text-gray-500">{{ $t('analytics.reviewsProcessed') }}</span>
            <div class="font-medium text-gray-900">{{ costData.stats?.reviews_processed || 0 }}</div>
          </div>
          <div>
            <span class="text-gray-500">{{ $t('analytics.chatMessages') }}</span>
            <div class="font-medium text-gray-900">{{ costData.stats?.chat_messages || 0 }}</div>
          </div>
          <div>
            <span class="text-gray-500">{{ $t('analytics.reportsGenerated') }}</span>
            <div class="font-medium text-gray-900">{{ costData.stats?.reports_generated || 0 }}</div>
          </div>
          <div>
            <span class="text-gray-500">{{ $t('analytics.avgCostPerReview') }}</span>
            <div class="font-medium text-gray-900">
              ${{ costData.stats?.avg_cost_per_review?.toFixed(3) || '0.000' }}
            </div>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="mt-6 pt-6 border-t border-gray-200 flex space-x-3">
        <button
          @click="$emit('adjustBudget')"
          class="flex-1 bg-blue-600 text-white text-sm font-medium py-2 px-4 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2"
        >
          {{ $t('analytics.adjustBudget') }}
        </button>
        <button
          @click="$emit('viewDetails')"
          class="flex-1 bg-gray-100 text-gray-700 text-sm font-medium py-2 px-4 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 focus:ring-offset-2"
        >
          {{ $t('analytics.viewDetails') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { CurrencyDollarIcon, ExclamationTriangleIcon } from '@heroicons/vue/24/outline'

interface Props {
  costData: {
    current_month?: number
    limit?: number
    usage_percentage?: number
    breakdown?: {
      classification?: number
      chat?: number
      reports?: number
    }
    stats?: {
      reviews_processed?: number
      chat_messages?: number
      reports_generated?: number
      avg_cost_per_review?: number
    }
  }
}

const props = withDefaults(defineProps<Props>(), {
  costData: () => ({})
})

const emit = defineEmits<{
  adjustBudget: []
  viewDetails: []
}>()

const { t } = useI18n()

const getCostWarningColor = (percentage?: number) => {
  if (!percentage) return 'text-gray-500'
  if (percentage >= 90) return 'text-red-600 font-semibold'
  if (percentage >= 80) return 'text-yellow-600 font-semibold'
  return 'text-green-600'
}

const getBudgetBarColor = (percentage?: number) => {
  if (!percentage) return 'bg-gray-300'
  if (percentage >= 90) return 'bg-red-500'
  if (percentage >= 80) return 'bg-yellow-500'
  return 'bg-green-500'
}

const getWarningBgColor = (percentage?: number) => {
  if (!percentage) return ''
  if (percentage >= 90) return 'bg-red-50 border border-red-200'
  return 'bg-yellow-50 border border-yellow-200'
}

const getWarningIconColor = (percentage?: number) => {
  if (!percentage) return ''
  if (percentage >= 90) return 'text-red-400'
  return 'text-yellow-400'
}

const getWarningTextColor = (percentage?: number) => {
  if (!percentage) return ''
  if (percentage >= 90) return 'text-red-800'
  return 'text-yellow-800'
}

const getWarningTitle = (percentage?: number) => {
  if (!percentage) return ''
  if (percentage >= 90) return t('analytics.budgetCritical')
  return t('analytics.budgetWarning')
}

const getWarningMessage = (percentage?: number) => {
  if (!percentage) return ''
  if (percentage >= 90) {
    return t('analytics.budgetCriticalMessage', { percentage: percentage.toFixed(0) })
  }
  return t('analytics.budgetWarningMessage', { percentage: percentage.toFixed(0) })
}
</script>