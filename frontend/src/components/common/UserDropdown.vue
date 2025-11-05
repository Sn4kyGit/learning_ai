<template>
  <div class="relative">
    <button
      @click="isOpen = !isOpen"
      class="flex items-center space-x-2 p-2 text-sm font-medium text-gray-700 rounded-full hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <div class="h-8 w-8 bg-blue-500 rounded-full flex items-center justify-center">
        <span class="text-white font-medium">
          {{ userInitials }}
        </span>
      </div>
      <ChevronDownIcon class="h-4 w-4 hidden sm:block" />
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50"
      @click.stop
    >
      <div class="py-1">
        <div class="px-4 py-2 border-b border-gray-100">
          <p class="text-sm font-medium text-gray-900">{{ user?.name }}</p>
          <p class="text-xs text-gray-500">{{ user?.email }}</p>
          <p class="text-xs text-gray-400 capitalize">{{ user?.role?.replace('_', ' ') }}</p>
        </div>
        
        <router-link
          to="/profile"
          class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          @click="isOpen = false"
        >
          <UserIcon class="mr-3 h-4 w-4" />
          {{ $t('navigation.profile') }}
        </router-link>
        
        <router-link
          to="/settings"
          class="flex items-center px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          @click="isOpen = false"
        >
          <Cog6ToothIcon class="mr-3 h-4 w-4" />
          {{ $t('navigation.settings') }}
        </router-link>
        
        <div class="border-t border-gray-100">
          <button
            @click="handleLogout"
            class="flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100"
          >
            <ArrowRightOnRectangleIcon class="mr-3 h-4 w-4" />
            {{ $t('auth.logout') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import {
  ChevronDownIcon,
  UserIcon,
  Cog6ToothIcon,
  ArrowRightOnRectangleIcon
} from '@heroicons/vue/24/outline'
import { useAuthStore } from '@/stores/auth'

const { t } = useI18n()
const router = useRouter()
const authStore = useAuthStore()
const isOpen = ref(false)

const user = computed(() => authStore.user)

const userInitials = computed(() => {
  if (!user.value?.name) return 'U'
  const names = user.value.name.split(' ')
  if (names.length >= 2) {
    return `${names[0][0]}${names[1][0]}`.toUpperCase()
  }
  return names[0][0].toUpperCase()
})

const handleLogout = async () => {
  try {
    await authStore.logout()
    router.push('/login')
  } catch (error) {
    console.error('Logout error:', error)
  }
  isOpen.value = false
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