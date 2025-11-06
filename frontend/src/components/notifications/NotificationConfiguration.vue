<template>
  <div class="space-y-6">
    <!-- Notification Preferences -->
    <div class="bg-white shadow rounded-lg p-6">
      <div class="flex items-center justify-between mb-6">
        <div>
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('notifications.preferences') }}
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            {{ $t('notifications.preferencesDescription') }}
          </p>
        </div>
        <button
          @click="testNotifications"
          :disabled="testing"
          class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          <svg class="h-4 w-4 mr-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 17h5l-5 5v-5zM4.828 7l6.586 6.586a2 2 0 002.828 0l6.586-6.586A2 2 0 0019.414 5H4.586A2 2 0 003.172 7z" />
          </svg>
          {{ testing ? $t('notifications.testing') : $t('notifications.testNotification') }}
        </button>
      </div>

      <form @submit.prevent="savePreferences" class="space-y-6">
        <!-- Notification Channels -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            {{ $t('notifications.notificationChannels') }}
          </label>
          <div class="space-y-4">
            <!-- Email Notifications -->
            <div class="flex items-start">
              <div class="flex items-center h-5">
                <input
                  v-model="preferences.email_enabled"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </div>
              <div class="ml-3">
                <label class="text-sm font-medium text-gray-700">
                  {{ $t('notifications.emailNotifications') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ $t('notifications.emailNotificationsDescription') }}
                </p>
                <div v-if="preferences.email_enabled" class="mt-2">
                  <input
                    v-model="preferences.email_address"
                    type="email"
                    :placeholder="$t('auth.email')"
                    class="block w-full max-w-sm px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
              </div>
            </div>

            <!-- SMS Notifications -->
            <div class="flex items-start">
              <div class="flex items-center h-5">
                <input
                  v-model="preferences.sms_enabled"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </div>
              <div class="ml-3">
                <label class="text-sm font-medium text-gray-700">
                  {{ $t('notifications.smsNotifications') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ $t('notifications.smsNotificationsDescription') }}
                </p>
                <div v-if="preferences.sms_enabled" class="mt-2">
                  <input
                    v-model="preferences.phone_number"
                    type="tel"
                    :placeholder="$t('notifications.phoneNumber')"
                    class="block w-full max-w-sm px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
                  />
                </div>
              </div>
            </div>

            <!-- Push Notifications -->
            <div class="flex items-start">
              <div class="flex items-center h-5">
                <input
                  v-model="preferences.push_enabled"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
              </div>
              <div class="ml-3">
                <label class="text-sm font-medium text-gray-700">
                  {{ $t('notifications.pushNotifications') }}
                </label>
                <p class="text-xs text-gray-500">
                  {{ $t('notifications.pushNotificationsDescription') }}
                </p>
              </div>
            </div>
          </div>
        </div>

        <!-- Notification Types -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-3">
            {{ $t('notifications.notificationTypes') }}
          </label>
          <div class="space-y-3">
            <label
              v-for="channel in availableChannels"
              :key="channel"
              class="flex items-center"
            >
              <input
                v-model="preferences.notification_channels"
                :value="channel"
                type="checkbox"
                class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
              />
              <span class="ml-2 text-sm text-gray-700">
                {{ $t(`notifications.channels.${channel}`) }}
              </span>
            </label>
          </div>
        </div>

        <!-- Save Button -->
        <div class="flex justify-end pt-4 border-t border-gray-200">
          <button
            type="submit"
            :disabled="loading"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <span v-if="loading" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ $t('common.saving') }}
            </span>
            <span v-else>
              {{ $t('notifications.savePreferences') }}
            </span>
          </button>
        </div>
      </form>
    </div>

    <!-- Alert Thresholds (Admin+ only) -->
    <div v-if="canManageAlerts" class="bg-white shadow rounded-lg p-6">
      <div class="mb-6">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('notifications.alertSettings') }}
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          {{ $t('notifications.alertSettingsDescription') }}
        </p>
      </div>

      <form @submit.prevent="saveAlertThresholds" class="space-y-6">
        <!-- Critical Rating Threshold -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('notifications.criticalRatingThreshold') }}
          </label>
          <div class="flex items-center space-x-3">
            <input
              v-model.number="alertThresholds.critical_rating_threshold"
              type="number"
              min="1"
              max="5"
              step="0.1"
              class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-500">{{ $t('notifications.starsOrBelow') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            {{ $t('notifications.criticalRatingThresholdHelp') }}
          </p>
        </div>

        <!-- Sentiment Drop Threshold -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('notifications.sentimentDropThreshold') }}
          </label>
          <div class="flex items-center space-x-3">
            <input
              v-model.number="alertThresholds.sentiment_drop_threshold"
              type="number"
              min="0.1"
              max="1"
              step="0.05"
              class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-500">{{ $t('notifications.percentageDrop') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            {{ $t('notifications.sentimentDropThresholdHelp') }}
          </p>
        </div>

        <!-- Competitor Mention Alerts -->
        <div class="flex items-start">
          <div class="flex items-center h-5">
            <input
              v-model="alertThresholds.competitor_mention_alerts"
              type="checkbox"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
          </div>
          <div class="ml-3">
            <label class="text-sm font-medium text-gray-700">
              {{ $t('notifications.competitorMentionAlerts') }}
            </label>
            <p class="text-xs text-gray-500">
              {{ $t('notifications.competitorMentionAlertsHelp') }}
            </p>
          </div>
        </div>

        <!-- Crisis Mode Threshold -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('notifications.crisisModeThreshold') }}
          </label>
          <div class="flex items-center space-x-3">
            <input
              v-model.number="alertThresholds.crisis_mode_threshold"
              type="number"
              min="1"
              max="10"
              class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-500">{{ $t('notifications.criticalReviewsIn24Hours') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            {{ $t('notifications.crisisModeThresholdHelp') }}
          </p>
        </div>

        <!-- Alert Frequency Limit -->
        <div>
          <label class="block text-sm font-medium text-gray-700 mb-2">
            {{ $t('notifications.alertFrequencyLimit') }}
          </label>
          <div class="flex items-center space-x-3">
            <input
              v-model.number="alertThresholds.alert_frequency_limit"
              type="number"
              min="1"
              max="50"
              class="block w-20 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500"
            />
            <span class="text-sm text-gray-500">{{ $t('notifications.alertsPerHour') }}</span>
          </div>
          <p class="mt-1 text-xs text-gray-500">
            {{ $t('notifications.alertFrequencyLimitHelp') }}
          </p>
        </div>

        <!-- Save Button -->
        <div class="flex justify-end pt-4 border-t border-gray-200">
          <button
            type="submit"
            :disabled="loadingThresholds"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
          >
            <span v-if="loadingThresholds" class="flex items-center">
              <svg class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
              </svg>
              {{ $t('common.saving') }}
            </span>
            <span v-else>
              {{ $t('notifications.saveAlertSettings') }}
            </span>
          </button>
        </div>
      </form>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { notificationConfigService } from '@/services/notificationConfig'
import type { NotificationPreferencesRequest, AlertThresholdsRequest } from '@/types'

interface Props {
  businessId?: string
}

const props = defineProps<Props>()

const { t } = useI18n()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()

const loading = ref(false)
const loadingThresholds = ref(false)
const testing = ref(false)

const canManageAlerts = computed(() => {
  return authStore.user?.role === 'super_admin' || authStore.user?.role === 'admin'
})

const availableChannels = ref(['email', 'in_app', 'critical_reviews', 'competitor_mentions', 'weekly_reports', 'budget_alerts'])

const preferences = ref<NotificationPreferencesRequest>({
  email_enabled: true,
  sms_enabled: false,
  push_enabled: true,
  email_address: '',
  phone_number: '',
  notification_channels: ['email', 'in_app']
})

const alertThresholds = ref<AlertThresholdsRequest>({
  critical_rating_threshold: 3.5,
  sentiment_drop_threshold: 0.2,
  competitor_mention_alerts: true,
  crisis_mode_threshold: 3,
  alert_frequency_limit: 5
})

const loadPreferences = async () => {
  try {
    const prefs = await notificationConfigService.getNotificationPreferences(props.businessId)
    if (prefs) {
      preferences.value = {
        email_enabled: prefs.email_enabled,
        sms_enabled: prefs.sms_enabled,
        push_enabled: prefs.push_enabled,
        email_address: prefs.email_address || '',
        phone_number: prefs.phone_number || '',
        notification_channels: prefs.notification_channels
      }
    }
  } catch (error) {
    console.error('Failed to load notification preferences:', error)
  }
}

const loadAlertThresholds = async () => {
  if (!props.businessId || !canManageAlerts.value) return

  try {
    const thresholds = await notificationConfigService.getAlertThresholds(props.businessId)
    if (thresholds) {
      alertThresholds.value = {
        critical_rating_threshold: thresholds.critical_rating_threshold,
        sentiment_drop_threshold: thresholds.sentiment_drop_threshold,
        competitor_mention_alerts: thresholds.competitor_mention_alerts,
        crisis_mode_threshold: thresholds.crisis_mode_threshold,
        alert_frequency_limit: thresholds.alert_frequency_limit
      }
    }
  } catch (error) {
    console.error('Failed to load alert thresholds:', error)
  }
}

const savePreferences = async () => {
  try {
    loading.value = true
    
    if (!preferences.value.email_address && authStore.user?.email) {
      preferences.value.email_address = authStore.user.email
    }

    await notificationConfigService.updateNotificationPreferences(
      preferences.value,
      props.businessId
    )
    
    notificationsStore.showSuccess(t('notifications.preferencesUpdated'))
  } catch (error) {
    console.error('Failed to save notification preferences:', error)
    notificationsStore.showError(t('notifications.preferencesUpdateError'))
  } finally {
    loading.value = false
  }
}

const saveAlertThresholds = async () => {
  if (!props.businessId) return

  try {
    loadingThresholds.value = true
    
    await notificationConfigService.updateAlertThresholds(
      props.businessId,
      alertThresholds.value
    )
    
    notificationsStore.showSuccess(t('notifications.alertSettingsUpdated'))
  } catch (error) {
    console.error('Failed to save alert thresholds:', error)
    notificationsStore.showError(t('notifications.alertSettingsUpdateError'))
  } finally {
    loadingThresholds.value = false
  }
}

const testNotifications = async () => {
  if (!props.businessId) return

  try {
    testing.value = true
    
    // Test each enabled channel
    const channels = []
    if (preferences.value.email_enabled) channels.push('email')
    if (preferences.value.sms_enabled) channels.push('sms')
    if (preferences.value.push_enabled) channels.push('push')
    
    for (const channel of channels) {
      await notificationConfigService.sendTestNotification(props.businessId, channel as any)
    }
    
    notificationsStore.showSuccess(t('notifications.testNotificationSent'))
  } catch (error) {
    console.error('Failed to send test notification:', error)
    notificationsStore.showError(t('notifications.testNotificationError'))
  } finally {
    testing.value = false
  }
}

// Watch for business ID changes
watch(() => props.businessId, () => {
  if (props.businessId) {
    loadPreferences()
    loadAlertThresholds()
  }
}, { immediate: true })

onMounted(() => {
  loadPreferences()
  if (props.businessId) {
    loadAlertThresholds()
  }
})
</script>