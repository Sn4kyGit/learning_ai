<template>
  <div class="space-y-2">
    <!-- Status Display -->
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-2">
        <div
          :class="[
            'w-2 h-2 rounded-full',
            statusColor
          ]"
        ></div>
        <span class="text-xs font-medium text-gray-700">
          {{ statusText }}
        </span>
      </div>
      <div class="flex items-center space-x-1">
        <button
          @click="refreshStatus"
          :disabled="loading"
          class="text-xs text-gray-500 hover:text-gray-700 disabled:opacity-50"
          :title="$t('businesses.refreshStatus')"
        >
          <ArrowPathIcon
            :class="[
              'h-3 w-3',
              loading ? 'animate-spin' : ''
            ]"
          />
        </button>
        <button
          @click="startManualSync"
          :disabled="loading || isImportActive"
          class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
          :title="$t('businesses.manualSync')"
        >
          <CloudArrowDownIcon class="h-3 w-3" />
        </button>
      </div>
    </div>

    <!-- Active Import Progress -->
    <div v-if="isImportActive && realTimeStatus" class="mt-2">
      <div class="text-xs text-blue-600 font-medium mb-1">
        {{ $t('businesses.importInProgress') }}
      </div>
      
      <!-- Progress Bar -->
      <div class="w-full bg-gray-200 rounded-full h-1.5 mb-2">
        <div
          class="bg-blue-600 h-1.5 rounded-full transition-all duration-300"
          :style="{ width: `${realTimeStatus.progress_percent || 0}%` }"
        ></div>
      </div>
      
      <!-- Progress Details -->
      <div class="text-xs text-gray-600 space-y-1">
        <div class="flex justify-between">
          <span>{{ $t('businesses.currentStep') }}:</span>
          <span>{{ formatStep(realTimeStatus.current_step) }}</span>
        </div>
        <div v-if="realTimeStatus.total_expected > 0" class="flex justify-between">
          <span>{{ $t('businesses.progress') }}:</span>
          <span>{{ realTimeStatus.processed || 0 }} / {{ realTimeStatus.total_expected }}</span>
        </div>
        <div v-if="realTimeStatus.estimated_completion" class="flex justify-between">
          <span>{{ $t('businesses.estimatedCompletion') }}:</span>
          <span>{{ formatDate(realTimeStatus.estimated_completion) }}</span>
        </div>
      </div>
    </div>

    <!-- Last Import Info -->
    <div v-if="importStatus && !isImportActive" class="text-xs text-gray-500 space-y-1">
      <div v-if="importStatus.last_import" class="flex justify-between">
        <span>{{ $t('businesses.lastImport') }}:</span>
        <span>{{ formatDate(importStatus.last_import) }}</span>
      </div>
      <div v-if="importStatus.last_import_count > 0" class="flex justify-between">
        <span>{{ $t('businesses.lastCount') }}:</span>
        <span>{{ importStatus.last_import_count }} {{ $t('businesses.reviews') }}</span>
      </div>
      <div class="flex justify-between">
        <span>{{ $t('businesses.totalImported') }}:</span>
        <span>{{ importStatus.total_imported || 0 }} {{ $t('businesses.reviews') }}</span>
      </div>
    </div>

    <!-- Import Errors -->
    <div v-if="importStatus?.import_errors && importStatus.import_errors.length > 0" class="mt-2">
      <button
        @click="showErrors = !showErrors"
        class="flex items-center text-xs text-red-600 hover:text-red-800"
      >
        <ExclamationTriangleIcon class="h-3 w-3 mr-1" />
        {{ importStatus.import_errors.length }} {{ $t('businesses.importErrors') }}
        <ChevronDownIcon
          :class="[
            'h-3 w-3 ml-1 transition-transform',
            showErrors ? 'rotate-180' : ''
          ]"
        />
      </button>
      
      <div v-if="showErrors" class="mt-1 space-y-1">
        <div
          v-for="(error, index) in importStatus.import_errors"
          :key="index"
          class="text-xs text-red-600 bg-red-50 p-2 rounded border border-red-200"
        >
          {{ error }}
        </div>
      </div>
    </div>

    <!-- Import History Toggle -->
    <div v-if="importStatus?.import_history && importStatus.import_history.length > 0" class="mt-2">
      <button
        @click="showHistory = !showHistory"
        class="flex items-center text-xs text-gray-600 hover:text-gray-800"
      >
        <ClockIcon class="h-3 w-3 mr-1" />
        {{ $t('businesses.importHistory') }}
        <ChevronDownIcon
          :class="[
            'h-3 w-3 ml-1 transition-transform',
            showHistory ? 'rotate-180' : ''
          ]"
        />
      </button>
      
      <div v-if="showHistory" class="mt-1 space-y-1">
        <div
          v-for="(entry, index) in (importStatus?.import_history || []).slice(0, 3)"
          :key="index"
          class="text-xs text-gray-600 bg-gray-50 p-2 rounded border border-gray-200"
        >
          <div class="flex justify-between">
            <span>{{ formatDate(entry.timestamp) }}</span>
            <span>{{ entry.imported_count }} {{ $t('businesses.reviews') }}</span>
          </div>
          <div v-if="entry.errors?.length > 0" class="text-red-600 mt-1">
            {{ entry.errors.length }} {{ $t('businesses.errors') }}
          </div>
        </div>
      </div>
    </div>

    <!-- Next Scheduled Import -->
    <div v-if="importStatus?.next_scheduled_import && !isImportActive" class="text-xs text-gray-500">
      <div class="flex justify-between">
        <span>{{ $t('businesses.nextImport') }}:</span>
        <span>{{ formatDate(importStatus.next_scheduled_import) }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { businessService } from '@/services/business'
import { useNotificationsStore } from '@/stores/notifications'
import type { ImportStatus } from '@/types'

// Icons
import {
  ArrowPathIcon,
  ExclamationTriangleIcon,
  ChevronDownIcon,
  CloudArrowDownIcon,
  ClockIcon
} from '@heroicons/vue/24/outline'

interface Props {
  businessId: string
}

const props = defineProps<Props>()

const emit = defineEmits<{
  refresh: []
  importStarted: []
  importCompleted: [result: any]
}>()

const { t } = useI18n()
const notificationsStore = useNotificationsStore()

// Reactive state
const loading = ref(false)
const importStatus = ref<ImportStatus | null>(null)
const realTimeStatus = ref<any>(null)
const showErrors = ref(false)
const showHistory = ref(false)
const pollInterval = ref<number | null>(null)

// Computed properties
const isImportActive = computed(() => {
  return realTimeStatus.value?.is_active || false
})

const statusColor = computed(() => {
  if (isImportActive.value) {
    return 'bg-blue-500 animate-pulse'
  }
  
  if (!importStatus.value) return 'bg-gray-400'
  
  if (importStatus.value.import_errors?.length > 0) {
    return 'bg-red-500'
  }
  
  if (importStatus.value.last_import) {
    const lastImport = new Date(importStatus.value.last_import)
    const now = new Date()
    const hoursSinceLastImport = (now.getTime() - lastImport.getTime()) / (1000 * 60 * 60)
    
    if (hoursSinceLastImport > 48) {
      return 'bg-yellow-500'
    }
    
    return 'bg-green-500'
  }
  
  return 'bg-gray-400'
})

const statusText = computed(() => {
  if (isImportActive.value) {
    return t('businesses.statusImporting')
  }
  
  if (!importStatus.value) return t('businesses.statusUnknown')
  
  if (importStatus.value.import_errors?.length > 0) {
    return t('businesses.statusError')
  }
  
  if (importStatus.value.last_import) {
    const lastImport = new Date(importStatus.value.last_import)
    const now = new Date()
    const hoursSinceLastImport = (now.getTime() - lastImport.getTime()) / (1000 * 60 * 60)
    
    if (hoursSinceLastImport > 48) {
      return t('businesses.statusStale')
    }
    
    return t('businesses.statusCurrent')
  }
  
  return t('businesses.statusNeverImported')
})

// Methods
const loadImportStatus = async () => {
  loading.value = true
  
  try {
    const response = await businessService.getImportStatus(props.businessId)
    importStatus.value = response
    
    // Also check real-time status
    await loadRealTimeStatus()
  } catch (error) {
    console.error('Failed to load import status:', error)
    importStatus.value = null
  } finally {
    loading.value = false
  }
}

const loadRealTimeStatus = async () => {
  try {
    const response = await businessService.getRealTimeImportStatus(props.businessId)
    realTimeStatus.value = response
    
    // Start polling if import is active
    if (response.is_active && !pollInterval.value) {
      startPolling()
    } else if (!response.is_active && pollInterval.value) {
      stopPolling()
    }
  } catch (error) {
    console.error('Failed to load real-time status:', error)
    realTimeStatus.value = null
  }
}

const startPolling = () => {
  if (pollInterval.value) return
  
  pollInterval.value = window.setInterval(async () => {
    await loadRealTimeStatus()
  }, 2000) // Poll every 2 seconds
}

const stopPolling = () => {
  if (pollInterval.value) {
    clearInterval(pollInterval.value)
    pollInterval.value = null
  }
}

const refreshStatus = async () => {
  await loadImportStatus()
  emit('refresh')
}

const startManualSync = async () => {
  if (isImportActive.value) return
  
  try {
    loading.value = true
    emit('importStarted')
    
    const result = await businessService.startManualImport(props.businessId, {
      max_reviews: 500
    })
    
    // Start polling for progress
    await loadRealTimeStatus()
    
    notificationsStore.showSuccess(t('businesses.importStarted'))
    
    // Wait for completion
    await waitForImportCompletion()
    
    emit('importCompleted', result)
    notificationsStore.showSuccess(
      t('businesses.importCompleted', { count: result.imported_count })
    )
    
  } catch (error: any) {
    console.error('Failed to start manual import:', error)
    
    if (error.response?.status === 409) {
      notificationsStore.showWarning(t('businesses.importAlreadyInProgress'))
    } else {
      notificationsStore.showError(t('businesses.importFailed'))
    }
  } finally {
    loading.value = false
    await loadImportStatus() // Refresh final status
  }
}

const waitForImportCompletion = async () => {
  return new Promise<void>((resolve) => {
    const checkCompletion = async () => {
      const status = await businessService.getRealTimeImportStatus(props.businessId)
      
      if (!status.is_active) {
        stopPolling()
        resolve()
      }
    }
    
    // Check completion every 3 seconds
    const completionInterval = setInterval(checkCompletion, 3000)
    
    // Cleanup after 5 minutes max
    setTimeout(() => {
      clearInterval(completionInterval)
      resolve()
    }, 300000)
  })
}

const formatDate = (dateString: string): string => {
  const date = new Date(dateString)
  const now = new Date()
  const diffInHours = (now.getTime() - date.getTime()) / (1000 * 60 * 60)
  
  if (diffInHours < 1) {
    const minutes = Math.floor(diffInHours * 60)
    return t('businesses.minutesAgo', { minutes })
  } else if (diffInHours < 24) {
    const hours = Math.floor(diffInHours)
    return t('businesses.hoursAgo', { hours })
  } else if (diffInHours < 48) {
    return t('businesses.yesterday')
  } else {
    return date.toLocaleDateString()
  }
}

const formatStep = (step: string): string => {
  const stepTranslations: Record<string, string> = {
    'initializing': t('businesses.stepInitializing'),
    'validating_business': t('businesses.stepValidating'),
    'fetching_reviews': t('businesses.stepFetching'),
    'processing_reviews': t('businesses.stepProcessing'),
    'saving_to_database': t('businesses.stepSaving'),
    'completed': t('businesses.stepCompleted'),
    'failed': t('businesses.stepFailed')
  }
  
  return stepTranslations[step] || step
}

// Lifecycle
onMounted(() => {
  loadImportStatus()
})

onUnmounted(() => {
  stopPolling()
})
</script>