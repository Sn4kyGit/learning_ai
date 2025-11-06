<template>
  <div class="bg-white shadow rounded-lg p-6">
    <div class="flex items-center justify-between mb-6">
      <div>
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('reports.configuration.title') }}
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          {{ $t('reports.configuration.description') }}
        </p>
      </div>
      <button
        v-if="hasConfiguration"
        @click="resetToDefaults"
        class="text-sm text-gray-500 hover:text-gray-700"
      >
        {{ $t('reports.configuration.resetDefaults') }}
      </button>
    </div>

    <form @submit.prevent="saveConfiguration" class="space-y-6">
      <!-- Report Day Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ $t('reports.configuration.reportDay') }}
        </label>
        <select
          v-model="form.report_day"
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          required
        >
          <option
            v-for="day in DAYS_OF_WEEK"
            :key="day.value"
            :value="day.value"
          >
            {{ $t(`common.days.${day.label.toLowerCase()}`) }}
          </option>
        </select>
        <p class="mt-1 text-xs text-gray-500">
          {{ $t('reports.configuration.reportDayHelp') }}
        </p>
      </div>

      <!-- Delivery Method -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ $t('reports.configuration.deliveryMethod') }}
        </label>
        <div class="space-y-2">
          <label
            v-for="method in DELIVERY_METHODS"
            :key="method.value"
            class="flex items-center"
          >
            <input
              v-model="form.delivery_method"
              :value="method.value"
              type="radio"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300"
              required
            />
            <span class="ml-2 text-sm text-gray-700">
              {{ $t(`reports.configuration.delivery.${method.value}`) }}
            </span>
          </label>
        </div>
      </div>

      <!-- Language Selection -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-2">
          {{ $t('reports.configuration.language') }}
        </label>
        <select
          v-model="form.language"
          class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
          required
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

      <!-- Report Sections -->
      <div>
        <label class="block text-sm font-medium text-gray-700 mb-3">
          {{ $t('reports.configuration.includeSections') }}
        </label>
        <div class="space-y-3">
          <label
            v-for="section in AVAILABLE_REPORT_SECTIONS"
            :key="section.id"
            class="flex items-start"
          >
            <input
              v-model="form.include_sections"
              :value="section.id"
              type="checkbox"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded mt-0.5"
            />
            <div class="ml-3">
              <span class="text-sm font-medium text-gray-700">
                {{ $t(`reports.sections.${section.id}.name`) }}
              </span>
              <p class="text-xs text-gray-500">
                {{ $t(`reports.sections.${section.id}.description`) }}
              </p>
            </div>
          </label>
        </div>
      </div>

      <!-- Next Report Date Display -->
      <div v-if="nextReportDate" class="bg-blue-50 p-4 rounded-md">
        <div class="flex">
          <div class="flex-shrink-0">
            <svg class="h-5 w-5 text-blue-400" fill="currentColor" viewBox="0 0 20 20">
              <path fill-rule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clip-rule="evenodd" />
            </svg>
          </div>
          <div class="ml-3">
            <h4 class="text-sm font-medium text-blue-800">
              {{ $t('reports.configuration.nextReport') }}
            </h4>
            <p class="text-sm text-blue-700">
              {{ formatDate(nextReportDate) }}
            </p>
          </div>
        </div>
      </div>

      <!-- Action Buttons -->
      <div class="flex justify-end space-x-3 pt-4 border-t border-gray-200">
        <button
          type="button"
          @click="$emit('cancel')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          {{ $t('common.cancel') }}
        </button>
        <button
          type="submit"
          :disabled="loading || !isFormValid"
          class="px-4 py-2 text-sm font-medium text-white bg-blue-600 border border-transparent rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          <span v-if="loading" class="flex items-center">
            <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
            </svg>
            {{ $t('common.saving') }}
          </span>
          <span v-else>
            {{ hasConfiguration ? $t('common.update') : $t('common.save') }}
          </span>
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { reportsService } from '@/services/reports'
import type { ReportConfiguration, ReportConfigurationRequest } from '@/types/reports'
import { DAYS_OF_WEEK, DELIVERY_METHODS, AVAILABLE_REPORT_SECTIONS } from '@/types/reports'

interface Props {
  businessId: string
}

const props = defineProps<Props>()
const emit = defineEmits<{
  saved: [config: ReportConfiguration]
  cancel: []
}>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

const loading = ref(false)
const hasConfiguration = ref(false)
const nextReportDate = ref<string | null>(null)

const availableLanguages = [
  { code: 'en', name: 'English' },
  { code: 'de', name: 'Deutsch' },
  { code: 'tr', name: 'Türkçe' },
  { code: 'ar', name: 'العربية' }
]

const form = ref<ReportConfigurationRequest>({
  report_day: 1, // Monday
  delivery_method: 'web_only',
  language: 'en',
  include_sections: ['sentiment_analysis', 'top_topics', 'competitor_mentions', 'action_items']
})

const isFormValid = computed(() => {
  return (
    form.value.report_day >= 1 &&
    form.value.report_day <= 7 &&
    form.value.delivery_method &&
    form.value.language &&
    form.value.include_sections.length > 0
  )
})

const loadConfiguration = async () => {
  try {
    loading.value = true
    const config = await reportsService.getReportConfiguration(props.businessId)
    
    if (config) {
      hasConfiguration.value = true
      nextReportDate.value = config.next_report_date
      form.value = {
        report_day: config.report_day,
        delivery_method: config.delivery_method,
        language: config.language,
        include_sections: config.include_sections
      }
    }
  } catch (error) {
    console.error('Failed to load report configuration:', error)
    notificationsStore.showError(t('reports.configuration.loadError'))
  } finally {
    loading.value = false
  }
}

const saveConfiguration = async () => {
  if (!isFormValid.value) return

  try {
    loading.value = true
    
    let config: ReportConfiguration
    if (hasConfiguration.value) {
      config = await reportsService.updateReportConfiguration(props.businessId, form.value)
      notificationsStore.showSuccess(t('reports.configuration.updateSuccess'))
    } else {
      config = await reportsService.configureWeeklyReports(props.businessId, form.value)
      notificationsStore.showSuccess(t('reports.configuration.createSuccess'))
    }
    
    hasConfiguration.value = true
    nextReportDate.value = config.next_report_date
    emit('saved', config)
  } catch (error) {
    console.error('Failed to save report configuration:', error)
    notificationsStore.showError(t('reports.configuration.saveError'))
  } finally {
    loading.value = false
  }
}

const resetToDefaults = () => {
  form.value = {
    report_day: 1,
    delivery_method: 'web_only',
    language: 'en',
    include_sections: ['sentiment_analysis', 'top_topics', 'competitor_mentions', 'action_items']
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString(undefined, {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

// Watch for business ID changes
watch(() => props.businessId, () => {
  if (props.businessId) {
    loadConfiguration()
  }
}, { immediate: true })

onMounted(() => {
  if (props.businessId) {
    loadConfiguration()
  }
})
</script>