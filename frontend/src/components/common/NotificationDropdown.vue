<template>
  <div class="relative">
    <button
      @click="isOpen = !isOpen"
      class="relative p-2 text-gray-400 hover:text-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 rounded-full"
    >
      <BellIcon class="h-6 w-6" />
      <span
        v-if="unreadCount > 0"
        class="absolute -top-1 -right-1 h-5 w-5 bg-red-500 text-white text-xs rounded-full flex items-center justify-center"
      >
        {{ unreadCount > 99 ? '99+' : unreadCount }}
      </span>
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-80 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50"
      @click.stop
    >
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between">
          <h3 class="text-lg font-medium text-gray-900">
            {{ $t('navigation.notifications') }}
          </h3>
          <button
            v-if="unreadCount > 0"
            @click="markAllAsRead"
            class="text-sm text-blue-600 hover:text-blue-800"
          >
            {{ $t('common.markAllRead') }}
          </button>
        </div>
      </div>

      <div class="max-h-96 overflow-y-auto">
        <div v-if="notifications.length === 0" class="p-4 text-center text-gray-500">
          {{ $t('notifications.noNotifications') }}
        </div>
        
        <div v-else>
          <div
            v-for="notification in notifications.slice(0, 10)"
            :key="notification.id"
            :class="[
              'p-4 border-b border-gray-100 hover:bg-gray-50 cursor-pointer',
              !notification.read ? 'bg-blue-50' : ''
            ]"
            @click="markAsRead(notification.id)"
          >
            <div class="flex items-start space-x-3">
              <div
                :class="[
                  'flex-shrink-0 w-2 h-2 rounded-full mt-2',
                  getNotificationColor(notification.type)
                ]"
              ></div>
              <div class="flex-1 min-w-0">
                <p
                  v-if="notification.title"
                  class="text-sm font-medium text-gray-900 truncate"
                >
                  {{ notification.title }}
                </p>
                <p class="text-sm text-gray-600">
                  {{ notification.message }}
                </p>
                <p class="text-xs text-gray-400 mt-1">
                  {{ formatTime(notification.timestamp) }}
                </p>
              </div>
              <button
                @click.stop="removeNotification(notification.id)"
                class="flex-shrink-0 text-gray-400 hover:text-gray-600"
              >
                <XMarkIcon class="h-4 w-4" />
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-if="notifications.length > 10" class="p-4 border-t border-gray-200">
        <button
          @click="viewAllNotifications"
          class="w-full text-center text-sm text-blue-600 hover:text-blue-800"
        >
          {{ $t('notifications.viewAll') }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { BellIcon, XMarkIcon } from '@heroicons/vue/24/outline'
import { useNotificationsStore } from '@/stores/notifications'
import { formatDistanceToNow } from 'date-fns'
import type { Notification } from '@/types'

const { t } = useI18n()
const notificationsStore = useNotificationsStore()
const isOpen = ref(false)

const notifications = computed(() => notificationsStore.notifications)
const unreadCount = computed(() => notificationsStore.unreadCount)

const getNotificationColor = (type: Notification['type']) => {
  const colors = {
    success: 'bg-green-400',
    error: 'bg-red-400',
    warning: 'bg-yellow-400',
    info: 'bg-blue-400',
    critical_review: 'bg-red-500',
    competitor_mention: 'bg-orange-400'
  }
  return colors[type] || 'bg-gray-400'
}

const formatTime = (timestamp: Date) => {
  return formatDistanceToNow(timestamp, { addSuffix: true })
}

const markAsRead = (notificationId: string | number) => {
  notificationsStore.markAsRead(notificationId)
}

const markAllAsRead = () => {
  notificationsStore.markAllAsRead()
}

const removeNotification = (notificationId: string | number) => {
  notificationsStore.removeNotification(notificationId)
}

const viewAllNotifications = () => {
  isOpen.value = false
  // Navigate to notifications page if it exists
  // router.push('/notifications')
}

const handleClickOutside = (event: Event) => {
  const target = event.target as Element
  if (!target.closest('.relative')) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>