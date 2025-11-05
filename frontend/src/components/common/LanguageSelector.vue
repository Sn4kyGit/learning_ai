<template>
  <div class="relative">
    <button
      @click="isOpen = !isOpen"
      class="flex items-center space-x-2 px-3 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500"
    >
      <span class="text-lg">{{ currentLanguage.flag }}</span>
      <span class="hidden sm:block">{{ currentLanguage.nativeName }}</span>
      <ChevronDownIcon class="h-4 w-4" />
    </button>

    <div
      v-if="isOpen"
      class="absolute right-0 mt-2 w-48 bg-white rounded-md shadow-lg ring-1 ring-black ring-opacity-5 z-50"
      @click.stop
    >
      <div class="py-1">
        <button
          v-for="language in languages"
          :key="language.code"
          @click="changeLanguage(language.code)"
          :class="[
            'flex items-center w-full px-4 py-2 text-sm text-gray-700 hover:bg-gray-100',
            currentLanguage.code === language.code ? 'bg-blue-50 text-blue-900' : ''
          ]"
        >
          <span class="text-lg mr-3">{{ language.flag }}</span>
          <div class="flex flex-col items-start">
            <span class="font-medium">{{ language.name }}</span>
            <span class="text-xs text-gray-500">{{ language.nativeName }}</span>
          </div>
          <CheckIcon
            v-if="currentLanguage.code === language.code"
            class="ml-auto h-4 w-4 text-blue-600"
          />
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ChevronDownIcon, CheckIcon } from '@heroicons/vue/24/outline'
import { setI18nLanguage } from '@/i18n'
import type { LanguageOption, SupportedLanguage } from '@/types'

const { locale } = useI18n()
const isOpen = ref(false)

const languages: LanguageOption[] = [
  { code: 'en', name: 'English', nativeName: 'English', flag: '🇺🇸' },
  { code: 'de', name: 'German', nativeName: 'Deutsch', flag: '🇩🇪' },
  { code: 'tr', name: 'Turkish', nativeName: 'Türkçe', flag: '🇹🇷' },
  { code: 'ar', name: 'Arabic', nativeName: 'العربية', flag: '🇸🇦' }
]

const currentLanguage = computed(() => {
  return languages.find(lang => lang.code === locale.value) || languages[0]
})

const changeLanguage = (languageCode: SupportedLanguage) => {
  locale.value = languageCode
  setI18nLanguage({ global: { locale } }, languageCode)
  localStorage.setItem('preferred-language', languageCode)
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
  
  // Load saved language preference
  const savedLanguage = localStorage.getItem('preferred-language') as SupportedLanguage
  if (savedLanguage && languages.some(lang => lang.code === savedLanguage)) {
    changeLanguage(savedLanguage)
  }
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>