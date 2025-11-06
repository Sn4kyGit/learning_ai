import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import type { RouteRecordRaw } from 'vue-router'

// Layout components
import AppLayout from '@/components/layout/AppLayout.vue'

// Views
import HomeView from '@/views/HomeView.vue'
import LoginView from '@/views/auth/LoginView.vue'
import RegisterView from '@/views/auth/RegisterView.vue'
import DashboardView from '@/views/dashboard/DashboardView.vue'

const routes: RouteRecordRaw[] = [
  {
    path: '/',
    name: 'Home',
    component: HomeView,
    meta: { requiresAuth: false }
  },
  {
    path: '/login',
    name: 'Login',
    component: LoginView,
    meta: { requiresAuth: false, hideForAuth: true }
  },
  {
    path: '/register',
    name: 'Register',
    component: RegisterView,
    meta: { requiresAuth: false, hideForAuth: true }
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: () => import('@/views/auth/ForgotPasswordView.vue'),
    meta: { requiresAuth: false, hideForAuth: true }
  },
  {
    path: '/reset-password',
    name: 'ResetPassword',
    component: () => import('@/views/auth/ResetPasswordView.vue'),
    meta: { requiresAuth: false, hideForAuth: true }
  },
  {
    path: '/app',
    component: AppLayout,
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/app/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: DashboardView,
        meta: { requiresAuth: true }
      },
      {
        path: 'reviews',
        name: 'Reviews',
        component: () => import('@/views/reviews/ReviewsView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/chat/ChatView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'analytics',
        name: 'Analytics',
        component: () => import('@/views/analytics/AnalyticsView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'reports',
        name: 'Reports',
        component: () => import('@/views/reports/ReportsView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SettingsView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'profile',
        name: 'Profile',
        component: () => import('@/views/profile/ProfileView.vue'),
        meta: { requiresAuth: true }
      },
      {
        path: 'businesses',
        name: 'Businesses',
        component: () => import('@/views/businesses/BusinessManagementView.vue'),
        meta: { requiresAuth: true }
      }
    ]
  },
  // Redirect authenticated users to dashboard
  {
    path: '/dashboard',
    redirect: '/app/dashboard'
  },
  {
    path: '/reviews',
    redirect: '/app/reviews'
  },
  {
    path: '/chat',
    redirect: '/app/chat'
  },
  {
    path: '/analytics',
    redirect: '/app/analytics'
  },
  {
    path: '/reports',
    redirect: '/app/reports'
  },
  {
    path: '/settings',
    redirect: '/app/settings'
  },
  {
    path: '/profile',
    redirect: '/app/profile'
  },
  {
    path: '/businesses',
    redirect: '/app/businesses'
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guards
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // Check if route requires authentication
  if (to.meta.requiresAuth) {
    if (!authStore.isAuthenticated) {
      next('/login')
      return
    }
    
    // Fetch user data if not already loaded
    if (!authStore.user && authStore.token) {
      try {
        await authStore.fetchUser()
      } catch (error) {
        console.error('Failed to fetch user:', error)
        next('/login')
        return
      }
    }
  }
  
  // Redirect authenticated users away from auth pages
  if (to.meta.hideForAuth && authStore.isAuthenticated) {
    next('/app/dashboard')
    return
  }
  
  next()
})

export default router