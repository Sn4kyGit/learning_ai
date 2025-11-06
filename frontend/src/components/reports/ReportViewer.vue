<template>
  <div class="bg-white shadow rounded-lg">
    <!-- Report Header -->
    <div class="px-6 py-4 border-b border-gray-200">
      <div class="flex items-center justify-between">
        <div>
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('reports.viewer.title') }}
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            {{ formatDateRange(report.report_period_start, report.report_period_end) }}
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <button
            @click="downloadReport"
            :disabled="downloading"
            class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {{ downloading ? $t('reports.viewer.downloading') : $t('reports.viewer.download') }}
          </button>
          <button
            @click="emailReport"
            :disabled="emailing"
            class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 4.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
            </svg>
            {{ emailing ? $t('reports.viewer.emailing') : $t('reports.viewer.email') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Report Content -->
    <div class="p-6">
      <!-- Report Metadata -->
      <div class="mb-6 grid grid-cols-1 md:grid-cols-3 gap-4">
        <div class="bg-gray-50 p-4 rounded-lg">
          <dt class="text-sm font-medium text-gray-500">{{ $t('reports.viewer.language') }}</dt>
          <dd class="mt-1 text-sm text-gray-900">{{ getLanguageName(report.language) }}</dd>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <dt class="text-sm font-medium text-gray-500">{{ $t('reports.viewer.generatedAt') }}</dt>
          <dd class="mt-1 text-sm text-gray-900">{{ formatDateTime(report.generated_at) }}</dd>
        </div>
        <div class="bg-gray-50 p-4 rounded-lg">
          <dt class="text-sm font-medium text-gray-500">{{ $t('reports.viewer.reportId') }}</dt>
          <dd class="mt-1 text-sm text-gray-900 font-mono">{{ report.report_id.slice(-8) }}</dd>
        </div>
      </div>

      <!-- Report Sections -->
      <div class="space-y-8">
        <!-- Sentiment Analysis -->
        <div v-if="report.sections.sentiment_analysis" class="report-section">
          <h4 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reports.sections.sentiment_analysis.name') }}
          </h4>
          <div class="bg-gray-50 p-4 rounded-lg">
            <div class="grid grid-cols-3 gap-4 text-center">
              <div>
                <div class="text-2xl font-bold text-green-600">
                  {{ report.sections.sentiment_analysis.positive }}%
                </div>
                <div class="text-sm text-gray-500">{{ $t('reviews.positive') }}</div>
              </div>
              <div>
                <div class="text-2xl font-bold text-gray-600">
                  {{ report.sections.sentiment_analysis.neutral }}%
                </div>
                <div class="text-sm text-gray-500">{{ $t('reviews.neutral') }}</div>
              </div>
              <div>
                <div class="text-2xl font-bold text-red-600">
                  {{ report.sections.sentiment_analysis.negative }}%
                </div>
                <div class="text-sm text-gray-500">{{ $t('reviews.negative') }}</div>
              </div>
            </div>
          </div>
        </div>

        <!-- Top Topics -->
        <div v-if="report.sections.top_topics" class="report-section">
          <h4 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reports.sections.top_topics.name') }}
          </h4>
          <div class="space-y-2">
            <div
              v-for="topic in report.sections.top_topics"
              :key="topic.name"
              class="flex items-center justify-between p-3 bg-gray-50 rounded-lg"
            >
              <span class="font-medium text-gray-900">{{ topic.name }}</span>
              <div class="flex items-center space-x-2">
                <div class="w-24 bg-gray-200 rounded-full h-2">
                  <div
                    class="bg-blue-600 h-2 rounded-full"
                    :style="{ width: `${topic.percentage}%` }"
                  ></div>
                </div>
                <span class="text-sm text-gray-500 w-12 text-right">{{ topic.percentage }}%</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Competitor Mentions -->
        <div v-if="report.sections.competitor_mentions" class="report-section">
          <h4 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reports.sections.competitor_mentions.name') }}
          </h4>
          <div v-if="report.sections.competitor_mentions.count > 0" class="space-y-3">
            <div class="bg-yellow-50 border border-yellow-200 rounded-lg p-4">
              <div class="flex">
                <div class="flex-shrink-0">
                  <svg class="h-5 w-5 text-yellow-400" fill="currentColor" viewBox="0 0 20 20">
                    <path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd" />
                  </svg>
                </div>
                <div class="ml-3">
                  <h5 class="text-sm font-medium text-yellow-800">
                    {{ $t('reports.viewer.competitorMentionsFound', { count: report.sections.competitor_mentions.count }) }}
                  </h5>
                  <div class="mt-2 text-sm text-yellow-700">
                    <ul class="list-disc list-inside space-y-1">
                      <li v-for="mention in report.sections.competitor_mentions.mentions" :key="mention">
                        {{ mention }}
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-sm text-gray-500 italic">
            {{ $t('reports.viewer.noCompetitorMentions') }}
          </div>
        </div>

        <!-- Action Items -->
        <div v-if="report.action_items && report.action_items.length > 0" class="report-section">
          <h4 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reports.sections.action_items.name') }}
          </h4>
          <div class="space-y-3">
            <div
              v-for="(item, index) in report.action_items"
              :key="index"
              class="flex items-start p-4 bg-blue-50 border border-blue-200 rounded-lg"
            >
              <div class="flex-shrink-0">
                <div class="flex items-center justify-center w-6 h-6 bg-blue-600 text-white text-xs font-bold rounded-full">
                  {{ index + 1 }}
                </div>
              </div>
              <div class="ml-3">
                <p class="text-sm text-gray-900">{{ item }}</p>
              </div>
            </div>
          </div>
        </div>

        <!-- Cost Summary -->
        <div v-if="report.cost_summary" class="report-section">
          <h4 class="text-lg font-medium text-gray-900 mb-4">
            {{ $t('reports.viewer.costSummary') }}
          </h4>
          <div class="bg-gray-50 p-4 rounded-lg">
            <dl class="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div>
                <dt class="text-sm font-medium text-gray-500">{{ $t('reports.viewer.reportGenerationCost') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">${{ report.cost_summary.generation_cost?.toFixed(4) || '0.0000' }}</dd>
              </div>
              <div>
                <dt class="text-sm font-medium text-gray-500">{{ $t('reports.viewer.totalTokens') }}</dt>
                <dd class="mt-1 text-sm text-gray-900">{{ report.cost_summary.total_tokens?.toLocaleString() || '0' }}</dd>
              </div>
            </dl>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { reportsService } from '@/services/reports'
import type { WeeklyReport } from '@/types/reports'

interface Props {
  report: WeeklyReport
  businessId: string
}

const props = defineProps<Props>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

const downloading = ref(false)
const emailing = ref(false)

const availableLanguages = {
  en: 'English',
  de: 'Deutsch',
  tr: 'Türkçe',
  ar: 'العربية'
}

const getLanguageName = (code: string) => {
  return availableLanguages[code as keyof typeof availableLanguages] || code
}

const formatDateRange = (start: string, end: string) => {
  const startDate = new Date(start)
  const endDate = new Date(end)
  
  return `${startDate.toLocaleDateString()} - ${endDate.toLocaleDateString()}`
}

const formatDateTime = (dateString: string) => {
  return new Date(dateString).toLocaleString()
}

const downloadReport = async () => {
  try {
    downloading.value = true
    const blob = await reportsService.downloadReport(props.businessId, props.report.report_id)
    
    // Create download link
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `weekly-report-${props.report.report_id.slice(-8)}.pdf`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    window.URL.revokeObjectURL(url)
    
    notificationsStore.showSuccess(t('reports.viewer.downloadSuccess'))
  } catch (error) {
    console.error('Failed to download report:', error)
    notificationsStore.showError(t('reports.viewer.downloadError'))
  } finally {
    downloading.value = false
  }
}

const emailReport = async () => {
  try {
    emailing.value = true
    await reportsService.sendReportEmail(props.businessId, props.report.report_id)
    notificationsStore.showSuccess(t('reports.viewer.emailSuccess'))
  } catch (error) {
    console.error('Failed to email report:', error)
    notificationsStore.showError(t('reports.viewer.emailError'))
  } finally {
    emailing.value = false
  }
}
</script>

<style scoped>
.report-section {
  @apply border-b border-gray-200 pb-6 last:border-b-0 last:pb-0;
}
</style>