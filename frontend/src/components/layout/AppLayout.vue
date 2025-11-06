<template>
  <div class="min-h-screen bg-gray-50">
    <!-- Mobile menu overlay -->
    <div
      v-if="mobileMenuOpen"
      class="fixed inset-0 z-40 lg:hidden"
      @click="mobileMenuOpen = false"
    >
      <div class="fixed inset-0 bg-gray-600 bg-opacity-75"></div>
    </div>

    <!-- Mobile menu -->
    <div
      :class="[
        'fixed inset-y-0 left-0 z-50 w-64 bg-white shadow-lg transform transition-transform duration-300 ease-in-out lg:hidden',
        mobileMenuOpen ? 'translate-x-0' : '-translate-x-full'
      ]"
    >
      <div class="flex items-center justify-between h-16 px-4 border-b border-gray-200">
        <h1 class="text-lg font-semibold text-gray-900">{{ $t('home.title') }}</h1>
        <button
          @click="mobileMenuOpen = false"
          class="p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>
      <nav class="mt-5 px-2">
        <router-link
          v-for="item in navigation"
          :key="item.name"
          :to="item.href"
          :class="[
            'group flex items-center px-2 py-2 text-base font-medium rounded-md mb-1',
            $route.path === item.href
              ? 'bg-blue-100 text-blue-900'
              : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
          ]"
          @click="mobileMenuOpen = false"
        >
          <component
            :is="item.icon"
            :class="[
              'mr-4 h-6 w-6',
              $route.path === item.href ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
            ]"
          />
          {{ $t(item.name) }}
        </router-link>
      </nav>
    </div>

    <!-- Desktop sidebar -->
    <div class="hidden lg:fixed lg:inset-y-0 lg:flex lg:w-64 lg:flex-col">
      <div class="flex min-h-0 flex-1 flex-col bg-white shadow">
        <div class="flex h-16 flex-shrink-0 items-center px-4 border-b border-gray-200">
          <h1 class="text-lg font-semibold text-gray-900">{{ $t('home.title') }}</h1>
        </div>
        <div class="flex flex-1 flex-col overflow-y-auto">
          <nav class="flex-1 space-y-1 px-2 py-4">
            <router-link
              v-for="item in navigation"
              :key="item.name"
              :to="item.href"
              :class="[
                'group flex items-center px-2 py-2 text-sm font-medium rounded-md',
                $route.path === item.href
                  ? 'bg-blue-100 text-blue-900'
                  : 'text-gray-600 hover:bg-gray-50 hover:text-gray-900'
              ]"
            >
              <component
                :is="item.icon"
                :class="[
                  'mr-3 h-6 w-6',
                  $route.path === item.href ? 'text-blue-500' : 'text-gray-400 group-hover:text-gray-500'
                ]"
              />
              {{ $t(item.name) }}
            </router-link>
          </nav>
        </div>
      </div>
    </div>

    <!-- Main content -->
    <div class="lg:pl-64 flex flex-col flex-1">
      <!-- Top navigation -->
      <div class="sticky top-0 z-10 bg-white shadow-sm border-b border-gray-200">
        <div class="flex h-16 justify-between items-center px-4 sm:px-6 lg:px-8">
          <!-- Mobile menu button -->
          <button
            @click="mobileMenuOpen = true"
            class="lg:hidden p-2 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100"
          >
            <Bars3Icon class="h-6 w-6" />
          </button>

          <!-- Page title -->
          <div class="flex-1 lg:flex-none">
            <h1 class="text-xl font-semibold text-gray-900">
              {{ pageTitle }}
            </h1>
          </div>

          <!-- Right side items -->
          <div class="flex items-center space-x-4">
            <!-- Language selector -->
            <LanguageSelector />
            
            <!-- Notifications -->
            <NotificationDropdown />
            
            <!-- User menu -->
            <UserDropdown />
          </div>
        </div>
      </div>

      <!-- Page content -->
      <main class="flex-1">
        <div class="py-6">
          <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
            <router-view />
          </div>
        </div>
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRoute } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  Bars3Icon,
  XMarkIcon,
  HomeIcon,
  ChatBubbleLeftRightIcon,
  ChartBarIcon,
  DocumentTextIcon,
  StarIcon,
  Cog6ToothIcon,
  BuildingOfficeIcon
} from '@heroicons/vue/24/outline'
import LanguageSelector from '@/components/common/LanguageSelector.vue'
import NotificationDropdown from '@/components/common/NotificationDropdown.vue'
import UserDropdown from '@/components/common/UserDropdown.vue'

const { t } = useI18n()
const route = useRoute()

const mobileMenuOpen = ref(false)

const navigation = [
  { name: 'navigation.dashboard', href: '/dashboard', icon: HomeIcon },
  { name: 'navigation.businesses', href: '/businesses', icon: BuildingOfficeIcon },
  { name: 'navigation.reviews', href: '/reviews', icon: StarIcon },
  { name: 'navigation.chat', href: '/chat', icon: ChatBubbleLeftRightIcon },
  { name: 'navigation.analytics', href: '/analytics', icon: ChartBarIcon },
  { name: 'navigation.reports', href: '/reports', icon: DocumentTextIcon },
  { name: 'navigation.settings', href: '/settings', icon: Cog6ToothIcon }
]

const pageTitle = computed(() => {
  const currentNav = navigation.find(item => item.href === route.path)
  return currentNav ? t(currentNav.name) : t('navigation.dashboard')
})
</script>