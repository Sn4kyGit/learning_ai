import { computed, onMounted, onUnmounted } from 'vue'
import { useNotificationsStore } from '@/stores/notifications'

export function useNotifications() {
  const notificationsStore = useNotificationsStore()

  const notifications = computed(() => notificationsStore.notifications)
  const unreadCount = computed(() => notificationsStore.unreadCount)
  const hasUnread = computed(() => notificationsStore.hasUnread)
  const criticalNotifications = computed(() => notificationsStore.criticalNotifications)

  // Auto-close notifications
  let autoCloseTimers = new Map()

  function startAutoCloseTimer(notification) {
    if (notification.autoClose && notification.duration) {
      const timer = setTimeout(() => {
        notificationsStore.removeNotification(notification.id)
        autoCloseTimers.delete(notification.id)
      }, notification.duration)
      
      autoCloseTimers.set(notification.id, timer)
    }
  }

  function clearAutoCloseTimer(notificationId) {
    const timer = autoCloseTimers.get(notificationId)
    if (timer) {
      clearTimeout(timer)
      autoCloseTimers.delete(notificationId)
    }
  }

  // Notification methods with auto-close handling
  function showSuccess(message, options = {}) {
    const notification = notificationsStore.showSuccess(message, options)
    startAutoCloseTimer(notification)
    return notification
  }

  function showError(message, options = {}) {
    const notification = notificationsStore.showError(message, options)
    startAutoCloseTimer(notification)
    return notification
  }

  function showWarning(message, options = {}) {
    const notification = notificationsStore.showWarning(message, options)
    startAutoCloseTimer(notification)
    return notification
  }

  function showInfo(message, options = {}) {
    const notification = notificationsStore.showInfo(message, options)
    startAutoCloseTimer(notification)
    return notification
  }

  function removeNotification(notificationId) {
    clearAutoCloseTimer(notificationId)
    notificationsStore.removeNotification(notificationId)
  }

  function markAsRead(notificationId) {
    notificationsStore.markAsRead(notificationId)
  }

  function markAllAsRead() {
    notificationsStore.markAllAsRead()
  }

  function clearAll() {
    // Clear all timers
    autoCloseTimers.forEach(timer => clearTimeout(timer))
    autoCloseTimers.clear()
    
    notificationsStore.clearAll()
  }

  // Real-time notifications (WebSocket or SSE)
  let eventSource = null

  function connectToNotifications() {
    // TODO: Implement WebSocket or Server-Sent Events connection
    // This would connect to the backend for real-time notifications
    
    // Example SSE implementation:
    // eventSource = new EventSource('/api/notifications/stream')
    // eventSource.onmessage = (event) => {
    //   const notification = JSON.parse(event.data)
    //   handleRealtimeNotification(notification)
    // }
  }

  function disconnectFromNotifications() {
    if (eventSource) {
      eventSource.close()
      eventSource = null
    }
  }

  function handleRealtimeNotification(notification) {
    switch (notification.type) {
      case 'critical_review':
        notificationsStore.showCriticalReview(notification.data)
        break
      case 'competitor_mention':
        notificationsStore.showCompetitorMention(notification.data)
        break
      case 'system_alert':
        showWarning(notification.message)
        break
      default:
        showInfo(notification.message)
    }
  }

  // Lifecycle
  onMounted(() => {
    connectToNotifications()
  })

  onUnmounted(() => {
    disconnectFromNotifications()
    // Clear all timers
    autoCloseTimers.forEach(timer => clearTimeout(timer))
    autoCloseTimers.clear()
  })

  return {
    // State
    notifications,
    unreadCount,
    hasUnread,
    criticalNotifications,
    
    // Methods
    showSuccess,
    showError,
    showWarning,
    showInfo,
    removeNotification,
    markAsRead,
    markAllAsRead,
    clearAll,
    
    // Real-time
    connectToNotifications,
    disconnectFromNotifications
  }
}