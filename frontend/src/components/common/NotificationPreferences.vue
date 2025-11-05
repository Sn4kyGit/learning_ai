<template>
  <div class="space-y-6">
    <!-- Header -->
    <div>
      <h3 class="text-lg leading-6 font-medium text-gray-900">
        {{ $t('notifications.preferences') }}
      </h3>
      <p class="mt-1 text-sm text-gray-500">
        Configure how and when you receive notifications for your business.
      </p>
    </div>

    <!-- Loading state -->
    <div v-if="loading" class="space-y-4">
      <div v-for="i in 4" :key="i" class="animate-pulse">
        <div class="h-16 bg-gray-200 rounded-lg"></div>
      </div>
    </div>

    <!-- Preferences form -->
    <form v-else @submit.prevent="savePreferences" class="space-y-6">
      <!-- Notification Channels -->
      <div>
        <h4 class="text-base font-medium text-gray-900 mb-4">
          {{ $t('notifications.notificationChannels') }}
        </h4>
        <div class="space-y-4">
          <div class="flex items-center">
            <input
              id="email-notifications"
              v-model="preferences.email_notifications"
              type="checkbox"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label for="email-notifications" class="ml-3 text-sm text-gray-700">
              {{ $t('notifications.emailNotifications') }}
            </label>
          </div>
          
          <div class="flex items-center">
            <input
              id="sms-notifications"
              v-model="preferences.sms_notifications"
              type="checkbox"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label for="sms-notifications" class="ml-3 text-sm text-gray-700">
              {{ $t('notifications.smsNotifications') }}
            </label>
          </div>
          
          <div class="flex items-center">
            <input
              id="push-notifications"
              v-model="preferences.push_notifications"
              type="checkbox"
              class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
            />
            <label for="push-notifications" class="ml-3 text-sm text-gray-700">
              {{ $t('notifications.pushNotifications') }}
            </label>
          </div>
        </div>
      </div>

      <!-- Alert Types -->
      <div>
        <h4 class="text-base font-medium text-gray-900 mb-4">
          {{ $t('notifications.alertSettings') }}
        </h4>
        <div class="space-y-4">
          <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <div class="flex items-center">
                <input
                  id="critical-reviews"
                  v-model="preferences.critical_alerts"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="critical-reviews" class="ml-3 text-sm font-medium text-gray-700">
                  {{ $t('notifications.criticalReviews') }}
                </label>
              </div>
              <p class="ml-7 text-xs text-gray-500">
                Get notified immediately when critical reviews are detected
              </p>
            </div>
            <div class="flex items-center space-x-2">
              <button
                type="button"
                @click="testNotification('critical_review')"
                :disabled="testingNotifications"
                class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                {{ $t('notifications.testNotification') }}
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <div class="flex items-center">
                <input
                  id="competitor-mentions"
                  v-model="preferences.competitor_mentions"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="competitor-mentions" class="ml-3 text-sm font-medium text-gray-700">
                  {{ $t('notifications.competitorMentions') }}
                </label>
              </div>
              <p class="ml-7 text-xs text-gray-500">
                Get notified when competitors are mentioned in reviews
              </p>
            </div>
            <div class="flex items-center space-x-2">
              <button
                type="button"
                @click="testNotification('competitor_mention')"
                :disabled="testingNotifications"
                class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                {{ $t('notifications.testNotification') }}
              </button>
            </div>
          </div>

          <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <div class="flex items-center">
                <input
                  id="weekly-reports"
                  v-model="preferences.weekly_reports"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="weekly-reports" class="ml-3 text-sm font-medium text-gray-700">
                  {{ $t('notifications.weeklyReports') }}
                </label>
              </div>
              <p class="ml-7 text-xs text-gray-500">
                Receive weekly performance reports via email
              </p>
            </div>
          </div>

          <div class="flex items-center justify-between p-4 border border-gray-200 rounded-lg">
            <div>
              <div class="flex items-center">
                <input
                  id="budget-alerts"
                  v-model="preferences.budget_alerts"
                  type="checkbox"
                  class="h-4 w-4 text-blue-600 focus:ring-blue-500 border-gray-300 rounded"
                />
                <label for="budget-alerts" class="ml-3 text-sm font-medium text-gray-700">
                  {{ $t('notifications.budgetAlerts') }}
                </label>
              </div>
              <p class="ml-7 text-xs text-gray-500">
                Get notified when AI usage approaches budget limits
              </p>
            </div>
            <div class="flex items-center space-x-2">
              <button
                type="button"
                @click="testNotification('budget_warning')"
                :disabled="testingNotifications"
                class="text-xs text-blue-600 hover:text-blue-800 disabled:opacity-50"
              >
                {{ $t('notifications.testNotification') }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Alert Thresholds -->
      <div>
        <h4 class="text-base font-medium text-gray-900 mb-4">
          {{ $t('notifications.alertThreshold') }}
        </h4>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
          <div>
            <label for="rating-threshold" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('notifications.ratingThreshold') }}
            </label>
            <select
              id="rating-threshold"
              v-model="preferences.rating_threshold"
              class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="1">1 star or below</option>
              <option value="2">2 stars or below</option>
              <option value="3">3 stars or below</option>
              <option value="4">4 stars or below</option>
            </select>
          </div>

          <div>
            <label for="urgency-level" class="block text-sm font-medium text-gray-700 mb-2">
              {{ $t('notifications.urgencyLevel') }}
            </label>
            <select
              id="urgency-level"
              v-model="preferences.urgency_threshold"
              class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm"
            >
              <option value="low">{{ $t('reviews.low') }}</option>
              <option value="medium">{{ $t('reviews.medium') }}</option>
              <option value="high">{{ $t('reviews.high') }}</option>
            </select>
          </div>
        </div>
      </div>

      <!-- Save button -->
      <div class="flex justify-end">
        <button
          type="submit"
          :disabled="saving"
          class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50"
        >
          {{ saving ? $t('common.loading') : $t('notifications.savePreferences') }}
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { useNotificationsStore } from '@/stores/notifications'
import { notificationService } from '@/services/notifications'

interface Props {
  businessId: string
}

const props = defineProps<Props>()
const { t } = useI18n()
const notificationsStore = useNotificationsStore()

// Reactive state
const loading = ref(true)
const saving = ref(false)
const testingNotifications = ref(false)

const preferences = reactive({
  email_notifications: true,
  sms_notifications: false,
  push_notifications: true,
  critical_alerts: true,
  competitor_mentions: true,
  weekly_reports: true,
  budget_alerts: true,
  rating_threshold: 3,
  urgency_threshold: 'medium'
})

// Methods
const loadPreferences = async () => {
  loading.value = true
  try {
    const response = await notificationService.getNotificationPreferences(props.businessId)
    Object.assign(preferences, response)
  } catch (error) {
    console.error('Failed to load preferences:', error)
    notificationsStore.showError('Failed to load notification preferences')
  } finally {
    loading.value = false
  }
}

const savePreferences = async () => {
  saving.value = true
  try {
    await notificationService.updateNotificationPreferences(props.businessId, preferences)
    notificationsStore.showSuccess(t('notifications.preferencesUpdated'))
  } catch (error) {
    console.error('Failed to save preferences:', error)
    notificationsStore.showError('Failed to save notification preferences')
  } finally {
    saving.value = false
  }
}

const testNotification = async (type: string) => {
  testingNotifications.value = true
  try {
    await notificationService.testNotification(props.businessId, type, 'email')
    notificationsStore.showSuccess(t('notifications.testSent'))
  } catch (error) {
    console.error('Failed to send test notification:', error)
    notificationsStore.showError('Failed to send test notification')
  } finally {
    testingNotifications.value = false
  }
}

// Lifecycle
onMounted(() => {
  loadPreferences()
})
</script>