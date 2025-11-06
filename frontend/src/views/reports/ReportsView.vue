<template>
  <div class="space-y-6">
    <!-- Header -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between">
        <div>
          <h1 class="text-2xl font-bold text-gray-900">
            {{ $t('reports.title') }}
          </h1>
          <p class="mt-1 text-sm text-gray-500">
            {{ $t('reports.description') }}
          </p>
        </div>
        <div class="flex items-center space-x-3">
          <button
            @click="generateReport"
            :disabled="!selectedBusinessId || generating"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
            </svg>
            {{ generating ? $t('reports.generating') : $t('reports.generateWeeklyReport') }}
          </button>
          <button
            @click="showCustomReportModal = true"
            :disabled="!selectedBusinessId"
            class="inline-flex items-center px-4 py-2 border border-gray-300 shadow-sm text-sm font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6v6m0 0v6m0-6h6m-6 0H6" />
            </svg>
            {{ $t('reports.customReport') }}
          </button>
        </div>
      </div>
    </div>

    <!-- Business Selector -->
    <BusinessSelector
      v-model="selectedBusinessId"
      :required="true"
      class="bg-white shadow rounded-lg p-6"
    />

    <!-- Tabs -->
    <div class="bg-white shadow rounded-lg">
      <div class="border-b border-gray-200">
        <nav class="-mb-px flex space-x-8 px-6">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'py-4 px-1 border-b-2 font-medium text-sm',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            {{ $t(tab.label) }}
          </button>
        </nav>
      </div>

      <div class="p-6">
        <!-- Configuration Tab -->
        <div v-if="activeTab === 'configuration'" class="space-y-6">
          <ReportConfiguration
            v-if="selectedBusinessId"
            :business-id="selectedBusinessId"
            @saved="handleConfigurationSaved"
          />
          <div v-else class="text-center text-gray-500 py-8">
            {{ $t('reports.selectBusinessFirst') }}
          </div>
        </div>

        <!-- Reports Tab -->
        <div v-else-if="activeTab === 'reports'" class="space-y-6">
          <div v-if="selectedBusinessId">
            <!-- Current Report -->
            <div v-if="currentReport">
              <h3 class="text-lg font-medium text-gray-900 mb-4">
                {{ $t('reports.currentReport') }}
              </h3>
              <ReportViewer
                :report="currentReport"
                :business-id="selectedBusinessId"
              />
            </div>

            <!-- Report History -->
            <div>
              <div class="flex items-center justify-between mb-4">
                <h3 class="text-lg font-medium text-gray-900">
                  {{ $t('reports.reportHistory') }}
                </h3>
                <button
                  @click="loadReports"
                  :disabled="loadingReports"
                  class="text-sm text-blue-600 hover:text-blue-800"
                >
                  {{ $t('common.refresh') }}
                </button>
              </div>

              <div v-if="loadingReports" class="text-center py-8">
                <div class="inline-flex items-center">
                  <svg class="animate-spin -ml-1 mr-3 h-5 w-5 text-gray-500" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                  {{ $t('common.loading') }}
                </div>
              </div>

              <div v-else-if="reportHistory.length === 0" class="text-center text-gray-500 py-8">
                {{ $t('reports.noReportsYet') }}
              </div>

              <div v-else class="space-y-4">
                <div
                  v-for="report in reportHistory"
                  :key="report.report_id"
                  class="border border-gray-200 rounded-lg p-4 hover:bg-gray-50 cursor-pointer"
                  @click="viewReport(report)"
                >
                  <div class="flex items-center justify-between">
                    <div>
                      <h4 class="text-sm font-medium text-gray-900">
                        {{ $t('reports.weeklyReport') }}
                      </h4>
                      <p class="text-sm text-gray-500">
                        {{ formatDateRange(report.report_period_start, report.report_period_end) }}
                      </p>
                    </div>
                    <div class="text-right">
                      <p class="text-sm text-gray-500">
                        {{ formatDateTime(report.generated_at) }}
                      </p>
                      <p class="text-xs text-gray-400">
                        {{ getLanguageName(report.language) }}
                      </p>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div v-else class="text-center text-gray-500 py-8">
            {{ $t('reports.selectBusinessFirst') }}
          </div>
        </div>

        <!-- Notifications Tab -->
        <div v-else-if="activeTab === 'notifications'">
          <NotificationConfiguration :business-id="selectedBusinessId" />
        </div>

        <!-- User Management Tab (Super-Admin only) -->
        <div v-else-if="activeTab === 'users' && canManageUsers">
          <UserManagement />
        </div>
      </div>
    </div>

    <!-- Custom Report Modal -->
    <CustomReportModal
      v-if="showCustomReportModal"
      :business-id="selectedBusinessId!"
      @close="showCustomReportModal = false"
      @generated="handleCustomReportGenerated"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { reportsService } from '@/services/reports'
import type { WeeklyReport, ReportConfiguration as ReportConfigurationType, CustomReport } from '@/types/reports'
import BusinessSelector from '@/components/dashboard/BusinessSelector.vue'
import ReportConfiguration from '@/components/reports/ReportConfiguration.vue'
import ReportViewer from '@/components/reports/ReportViewer.vue'
import NotificationConfiguration from '@/components/notifications/NotificationConfiguration.vue'
import UserManagement from '@/components/admin/UserManagement.vue'
import CustomReportModal from '@/components/reports/CustomReportModal.vue'

const { t } = useI18n()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()

const selectedBusinessId = ref<string>('')
const activeTab = ref('configuration')
const generating = ref(false)
const loadingReports = ref(false)
const showCustomReportModal = ref(false)

const currentReport = ref<WeeklyReport | null>(null)
const reportHistory = ref<WeeklyReport[]>([])

const canManageUsers = computed(() => {
  return authStore.user?.role === 'super_admin'
})

const tabs = computed(() => {
  const baseTabs = [
    { id: 'configuration', label: 'reports.tabs.configuration' },
    { id: 'reports', label: 'reports.tabs.reports' },
    { id: 'notifications', label: 'reports.tabs.notifications' }
  ]

  if (canManageUsers.value) {
    baseTabs.push({ id: 'users', label: 'reports.tabs.userManagement' })
  }

  return baseTabs
})

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

const loadReports = async () => {
  if (!selectedBusinessId.value) return

  try {
    loadingReports.value = true
    const reports = await reportsService.getWeeklyReports(selectedBusinessId.value, 0, 20)
    reportHistory.value = reports
    
    // Set the most recent report as current
    if (reports.length > 0) {
      currentReport.value = reports[0]
    }
  } catch (error) {
    console.error('Failed to load reports:', error)
    notificationsStore.showError(t('reports.loadError'))
  } finally {
    loadingReports.value = false
  }
}

const generateReport = async () => {
  if (!selectedBusinessId.value) return

  try {
    generating.value = true
    const report = await reportsService.generateWeeklyReport(selectedBusinessId.value)
    currentReport.value = report
    
    // Refresh report history
    await loadReports()
    
    notificationsStore.showSuccess(t('reports.generateSuccess'))
  } catch (error) {
    console.error('Failed to generate report:', error)
    notificationsStore.showError(t('reports.generateError'))
  } finally {
    generating.value = false
  }
}

const viewReport = (report: WeeklyReport) => {
  currentReport.value = report
}

const handleConfigurationSaved = (config: ReportConfigurationType) => {
  notificationsStore.showSuccess(t('reports.configurationSaved'))
}

const handleCustomReportGenerated = (report: CustomReport) => {
  notificationsStore.showSuccess(t('reports.customReportGenerated'))
  showCustomReportModal.value = false
}

// Watch for business selection changes
watch(selectedBusinessId, (newBusinessId) => {
  if (newBusinessId) {
    loadReports()
  } else {
    currentReport.value = null
    reportHistory.value = []
  }
})

onMounted(() => {
  // Load reports if business is already selected
  if (selectedBusinessId.value) {
    loadReports()
  }
})
</script>