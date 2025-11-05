<template>
  <div class="min-h-screen bg-gray-50 py-12 px-4 sm:px-6 lg:px-8">
    <div class="max-w-4xl mx-auto">
      <div class="text-center">
        <h1 class="text-4xl font-bold text-gray-900 mb-8">
          {{ $t('home.title') }}
        </h1>
        <p class="text-xl text-gray-600 mb-12">
          {{ $t('home.subtitle') }}
        </p>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
        <!-- Feature Cards -->
        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="text-center">
            <div class="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <ChartBarIcon class="w-6 h-6 text-blue-600" />
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{ $t('home.features.reviewAnalysis.title') }}
            </h3>
            <p class="text-gray-600">
              {{ $t('home.features.reviewAnalysis.description') }}
            </p>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="text-center">
            <div class="w-12 h-12 bg-green-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <ChatBubbleLeftRightIcon class="w-6 h-6 text-green-600" />
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{ $t('home.features.businessAdvisory.title') }}
            </h3>
            <p class="text-gray-600">
              {{ $t('home.features.businessAdvisory.description') }}
            </p>
          </div>
        </div>

        <div class="bg-white rounded-lg shadow-md p-6">
          <div class="text-center">
            <div class="w-12 h-12 bg-purple-100 rounded-lg flex items-center justify-center mx-auto mb-4">
              <DocumentTextIcon class="w-6 h-6 text-purple-600" />
            </div>
            <h3 class="text-lg font-semibold text-gray-900 mb-2">
              {{ $t('home.features.weeklyReports.title') }}
            </h3>
            <p class="text-gray-600">
              {{ $t('home.features.weeklyReports.description') }}
            </p>
          </div>
        </div>
      </div>

      <div class="mt-12 text-center">
        <div class="bg-white rounded-lg shadow-md p-8">
          <h2 class="text-2xl font-bold text-gray-900 mb-4">
            {{ $t('home.apiStatus') }}
          </h2>
          <div class="flex items-center justify-center space-x-4">
            <div class="flex items-center">
              <div :class="apiStatus ? 'bg-green-400' : 'bg-red-400'" class="w-3 h-3 rounded-full mr-2"></div>
              <span class="text-gray-700">
                {{ $t('home.backendApi') }}: {{ apiStatus ? $t('home.connected') : $t('home.disconnected') }}
              </span>
            </div>
          </div>
          <button 
            @click="checkApiStatus" 
            class="mt-4 bg-blue-600 hover:bg-blue-700 text-white font-medium py-2 px-4 rounded-md transition-colors"
          >
            {{ $t('home.checkStatus') }}
          </button>
        </div>
      </div>

      <!-- Auth Actions -->
      <div class="mt-8 text-center space-x-4">
        <router-link
          to="/login"
          class="inline-flex items-center px-6 py-3 border border-transparent text-base font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          {{ $t('auth.login') }}
        </router-link>
        <router-link
          to="/register"
          class="inline-flex items-center px-6 py-3 border border-gray-300 text-base font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
        >
          {{ $t('auth.register') }}
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import {
  ChartBarIcon,
  ChatBubbleLeftRightIcon,
  DocumentTextIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()
const apiStatus = ref(false)

const checkApiStatus = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/health')
    apiStatus.value = response.ok
  } catch (error) {
    console.error('API check failed:', error)
    apiStatus.value = false
  }
}

onMounted(() => {
  checkApiStatus()
})
</script>