<template>
  <div class="fixed inset-0 bg-gray-600 bg-opacity-50 overflow-y-auto h-full w-full z-50">
    <div class="relative top-20 mx-auto p-5 border w-full max-w-md shadow-lg rounded-md bg-white">
      <!-- Modal Header -->
      <div class="flex items-center justify-between pb-4 border-b border-gray-200">
        <h3 class="text-lg font-medium text-gray-900">
          {{ title }}
        </h3>
        <button
          @click="$emit('cancel')"
          class="text-gray-400 hover:text-gray-600"
        >
          <XMarkIcon class="h-6 w-6" />
        </button>
      </div>

      <!-- Modal Body -->
      <div class="mt-6">
        <div class="flex items-start">
          <div
            :class="[
              'flex-shrink-0 w-10 h-10 rounded-full flex items-center justify-center',
              confirmVariant === 'danger' 
                ? 'bg-red-100' 
                : 'bg-yellow-100'
            ]"
          >
            <ExclamationTriangleIcon
              :class="[
                'h-6 w-6',
                confirmVariant === 'danger' 
                  ? 'text-red-600' 
                  : 'text-yellow-600'
              ]"
            />
          </div>
          <div class="ml-4">
            <p class="text-sm text-gray-700">
              {{ message }}
            </p>
          </div>
        </div>
      </div>

      <!-- Modal Footer -->
      <div class="mt-8 flex justify-end space-x-3 border-t border-gray-200 pt-4">
        <button
          @click="$emit('cancel')"
          class="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-500"
        >
          {{ cancelText }}
        </button>
        <button
          @click="$emit('confirm')"
          :class="[
            'px-4 py-2 text-sm font-medium border border-transparent rounded-md focus:outline-none focus:ring-2',
            confirmVariant === 'danger'
              ? 'text-white bg-red-600 hover:bg-red-700 focus:ring-red-500'
              : 'text-white bg-yellow-600 hover:bg-yellow-700 focus:ring-yellow-500'
          ]"
        >
          {{ confirmText }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ExclamationTriangleIcon, XMarkIcon } from '@heroicons/vue/24/outline'

interface Props {
  title: string
  message: string
  confirmText: string
  cancelText: string
  confirmVariant?: 'danger' | 'warning'
}

withDefaults(defineProps<Props>(), {
  confirmVariant: 'warning'
})

defineEmits<{
  confirm: []
  cancel: []
}>()
</script>