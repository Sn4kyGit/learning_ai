import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import type { Notification } from '@/types'

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref<Notification[]>([])
  const unreadCount = ref(0)

  const hasUnread = computed(() => unreadCount.value > 0)
  const criticalNotifications = computed(() => 
    notifications.value.filter(n => n.severity === 'high')
  )

  function addNotification(notification: Partial<Notification>): Notification {
    const newNotification: Notification = {
      id: Date.now() + Math.random(),
      timestamp: new Date(),
      read: false,
      type: 'info',
      message: '',
      severity: 'low',
      ...notification
    }
    
    notifications.value.unshift(newNotification)
    
    if (!newNotification.read) {
      unreadCount.value++
    }
    
    return newNotification
  }

  function markAsRead(notificationId: string | number) {
    const notification = notifications.value.find(n => n.id === notificationId)
    if (notification && !notification.read) {
      notification.read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  function markAllAsRead() {
    notifications.value.forEach(notification => {
      notification.read = true
    })
    unreadCount.value = 0
  }

  function removeNotification(notificationId: string | number) {
    const index = notifications.value.findIndex(n => n.id === notificationId)
    if (index !== -1) {
      const notification = notifications.value[index]
      if (!notification.read) {
        unreadCount.value = Math.max(0, unreadCount.value - 1)
      }
      notifications.value.splice(index, 1)
    }
  }

  function clearAll() {
    notifications.value = []
    unreadCount.value = 0
  }

  // Notification types
  function showSuccess(message: string, options: Partial<Notification> = {}) {
    return addNotification({
      type: 'success',
      message,
      severity: 'low',
      autoClose: true,
      duration: 5000,
      ...options
    })
  }

  function showError(message: string, options: Partial<Notification> = {}) {
    return addNotification({
      type: 'error',
      message,
      severity: 'high',
      autoClose: false,
      ...options
    })
  }

  function showWarning(message: string, options: Partial<Notification> = {}) {
    return addNotification({
      type: 'warning',
      message,
      severity: 'medium',
      autoClose: true,
      duration: 8000,
      ...options
    })
  }

  function showInfo(message: string, options: Partial<Notification> = {}) {
    return addNotification({
      type: 'info',
      message,
      severity: 'low',
      autoClose: true,
      duration: 6000,
      ...options
    })
  }

  // Critical business notifications
  function showCriticalReview(reviewData: any) {
    return addNotification({
      type: 'critical_review',
      title: 'Critical Review Alert',
      message: `New ${reviewData.rating}-star review requires attention`,
      severity: 'high',
      autoClose: false,
      data: reviewData
    })
  }

  function showCompetitorMention(reviewData: any) {
    return addNotification({
      type: 'competitor_mention',
      title: 'Competitor Mentioned',
      message: 'A competitor was mentioned in a recent review',
      severity: 'medium',
      autoClose: false,
      data: reviewData
    })
  }

  return {
    notifications,
    unreadCount,
    hasUnread,
    criticalNotifications,
    addNotification,
    markAsRead,
    markAllAsRead,
    removeNotification,
    clearAll,
    showSuccess,
    showError,
    showWarning,
    showInfo,
    showCriticalReview,
    showCompetitorMention
  }
})