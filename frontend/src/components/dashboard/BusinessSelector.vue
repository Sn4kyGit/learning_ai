<template>
  <div v-if="showSelector" class="bg-white shadow rounded-lg p-4 mb-6">
    <div class="flex items-center justify-between">
      <div class="flex items-center space-x-4">
        <h3 class="text-lg font-medium text-gray-900">
          {{ $t('dashboard.businessView') }}
        </h3>
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700">{{ $t('dashboard.selectBusiness') }}:</label>
          <select
            :value="selectedBusinessId"
            @change="handleBusinessChange"
            class="block w-64 px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="all">{{ $t('dashboard.allBusinesses') }}</option>
            <option v-for="business in businesses" :key="business.id" :value="business.id">
              {{ business.name }}
            </option>
          </select>
        </div>
      </div>
      
      <!-- View Toggle -->
      <div class="flex items-center space-x-2">
        <span class="text-sm text-gray-500">{{ $t('dashboard.view') }}:</span>
        <div class="flex bg-gray-100 rounded-lg p-1">
          <button
            @click="setViewMode('individual')"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-md transition-colors',
              viewMode === 'individual'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            ]"
          >
            {{ $t('dashboard.individual') }}
          </button>
          <button
            @click="setViewMode('consolidated')"
            :class="[
              'px-3 py-1 text-sm font-medium rounded-md transition-colors',
              viewMode === 'consolidated'
                ? 'bg-white text-gray-900 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            ]"
          >
            {{ $t('dashboard.consolidated') }}
          </button>
        </div>
      </div>
    </div>
    
    <!-- Selected Business Info -->
    <div v-if="selectedBusiness && selectedBusinessId !== 'all'" class="mt-4 p-3 bg-gray-50 rounded-md">
      <div class="flex items-center justify-between">
        <div>
          <h4 class="text-sm font-medium text-gray-900">{{ selectedBusiness.name }}</h4>
          <p class="text-sm text-gray-500">{{ selectedBusiness.address }}</p>
        </div>
        <div class="text-right">
          <div class="text-sm font-medium text-gray-900">
            {{ selectedBusiness.avg_rating?.toFixed(1) || '0.0' }} ⭐
          </div>
          <div class="text-sm text-gray-500">
            {{ selectedBusiness.total_reviews || 0 }} {{ $t('dashboard.reviews') }}
          </div>
        </div>
      </div>
    </div>
    
    <!-- Consolidated View Info -->
    <div v-else-if="selectedBusinessId === 'all'" class="mt-4 p-3 bg-blue-50 rounded-md">
      <div class="flex items-center justify-between">
        <div>
          <h4 class="text-sm font-medium text-blue-900">{{ $t('dashboard.consolidatedView') }}</h4>
          <p class="text-sm text-blue-700">{{ $t('dashboard.consolidatedViewDescription') }}</p>
        </div>
        <div class="text-right">
          <div class="text-sm font-medium text-blue-900">
            {{ businesses.length }} {{ $t('dashboard.businesses') }}
          </div>
          <div class="text-sm text-blue-700">
            {{ totalReviews }} {{ $t('dashboard.totalReviews') }}
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import type { Business } from '@/types'

interface Props {
  businesses: Business[]
  selectedBusinessId: string
  viewMode: 'individual' | 'consolidated'
  userRole?: string
}

const props = withDefaults(defineProps<Props>(), {
  userRole: 'admin'
})

const emit = defineEmits<{
  businessChange: [businessId: string]
  viewModeChange: [mode: 'individual' | 'consolidated']
}>()

const { t } = useI18n()

const showSelector = computed(() => {
  return props.userRole === 'super_admin' && props.businesses.length > 1
})

const selectedBusiness = computed(() => {
  return props.businesses.find(b => b.id === props.selectedBusinessId)
})

const totalReviews = computed(() => {
  return props.businesses.reduce((total, business) => total + (business.total_reviews || 0), 0)
})

const handleBusinessChange = (event: Event) => {
  const target = event.target as HTMLSelectElement
  emit('businessChange', target.value)
}

const setViewMode = (mode: 'individual' | 'consolidated') => {
  emit('viewModeChange', mode)
}
</script>