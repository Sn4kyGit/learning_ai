<template>
  <div class="fixed inset-0 z-50 overflow-y-auto">
    <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
      <!-- Background overlay -->
      <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="$emit('close')"></div>

      <!-- Modal panel -->
      <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
        <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
          <div class="sm:flex sm:items-start">
            <div class="mt-3 text-center sm:mt-0 sm:text-left w-full">
              <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
                {{ $t('reports.customReport') }}
              </h3>

              <form @submit.prevent="generateReport" class="space-y-4">
                <!-- Date Range -->
                <div class="grid grid-cols-2 gap-4">
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ $t('reports.custom.startDate') }}
                    </label>
                    <input
                      v-model="form.start_date"
                      type="date"
                      required
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                  <div>
                    <label class="block text-sm font-medium text-gray-700 mb-1">
                      {{ $t('reports.custom.endDate') }}
                    </label>
                    <input
                      v-model="form.end_date"
                      type="date"
                      required
                      class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                    />
                  </div>
                </div>

                <!-- Report Type -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    {{ $t('reports.custom.reportType') }}
                  </label>
                  <select
                    v-model="form.report_type"
                    required
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option
                      v-for="type in REPORT_TYPES"
                      :key="type.value"
                      :value="type.value"
                    >
                      {{ $t(`reports.types.${type.value}`) }}
                    </option>
                  </select>
                </div>

                <!-- Language -->
                <div>
                  <label class="block text-sm font-medium text-gray-700 mb-2">
                    {{ $t('reports.custom.language') }}
                  </label>
                  <select
                    v-model="form.language"
                    required
                    class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
                  >
                    <option
                      v-for="lang in availableLanguages"
                      :key="lang.code"
                      :value="lang.code"
                    >
                      {{ lang.name }}
                    </option>
                  </select>
                </div>

                <!-- Include Recommendations -->
                <div class="flex items-start">
                  <div class="flex items-center h-5">
                    <input
                      v-model="form.include_recommendations"
                      type="checkbox"
                      class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                    />
                  </div>
                  <div class="ml-3">
                    <label class="text-sm font-medium text-gray-700">
                      {{ $t('reports.custom.includeRecommendations') }}
                    </label>
                    <p class="text-xs text-gray-500">
                      {{ $t('reports.custom.includeRecommendationsHelp') }}
                    </p>
                  </div>
                </div>
              </form>
            </div>
          </div>
        </div>

        <!-- Modal actions -->
        <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
          <button
            @click="generateReport"
            :disabled="loading || !isFormValid"
            class="w-full inline-flex justify-center rounded-md border border-transparent shadow-sm px-4 py-2 bg-blue-600 text-base font-medium text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:ml-3 sm:w-auto sm:text-sm disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ $t('reports.custom.generating') }}
            </span>
            <span v-else>
              {{ $t('reports.custom.generate') }}
            </span>
          </button>
          <button
            @click="$emit('close')"
            type="button"
            class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
          >
            {{ $t('common.cancel') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { reportsService } from '@/services/reports'
import type { CustomReportRequest, CustomReport } from '@/types/reports'
import { REPORT_TYPES } from '@/types/reports'

interface Props {
  businessId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  close: []
  generated: [report: CustomReport]
}>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

const loading = ref(false)

const availableLanguages = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'ar', name: 'العربية' }
]

// Set default dates (last 30 days)
const today = new Date()
const thirtyDaysAgo = new Date(today.getTime() - 30 * 24 * 60 * 60 * 1000)

const form = ref<CustomReportRequest>({
  start_date: thirtyDaysAgo.toISOString().split('T')[0],
  end_date: today.toISOString().split('T')[0],
  report_type: 'comprehensive',
  language: 'en',
  include_recommendations: true
})

const isFormValid = computed(() => {
  return (
    form.value.start_date &&
    form.value.end_date &&
    form.value.report_type &&
    form.value.language &&
    new Date(form.value.start_date) < new Date(form.value.end_date)
  )
})

const generateReport = async () => {
  if (!isFormValid.value) return

  try {
    loading.value = true
    const report = await reportsService.generateCustomReport(props.businessId, form.value)
    emit('generated', report)
  } catch (error) {
    console.error('Failed to generate custom report:', error)
    notificationsStore.showError(t('reports.custom.generateError'))
  } finally {
    loading.value = false
  }
}
</script>