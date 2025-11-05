<template>
  <div class="bg-white shadow rounded-lg p-6">
    <div class="flex items-center justify-between mb-4">
      <h3 class="text-lg font-medium text-gray-900">
        {{ title }}
      </h3>
      <select
        :value="period"
        @change="$emit('periodChange', $event.target.value)"
        class="text-sm border border-gray-300 rounded-md px-2 py-1"
      >
        <option value="7d">{{ $t('analytics.last7Days') }}</option>
        <option value="30d">{{ $t('analytics.last30Days') }}</option>
        <option value="90d">{{ $t('analytics.last90Days') }}</option>
      </select>
    </div>
    <div class="h-64">
      <Line
        v-if="chartData.datasets.length > 0"
        :data="chartData"
        :options="chartOptions"
      />
      <div v-else class="flex items-center justify-center h-full text-gray-500">
        <div class="text-center">
          <ChartBarIcon class="mx-auto h-12 w-12 text-gray-400" />
          <p class="mt-2">{{ $t('analytics.noData') }}</p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Line } from 'vue-chartjs'
import { ChartBarIcon } from '@heroicons/vue/24/outline'

interface Props {
  title: string
  period: string
  chartData: any
  loading?: boolean
}

const props = withDefaults(defineProps<Props>(), {
  loading: false
})

const emit = defineEmits<{
  periodChange: [period: string]
}>()

const { t } = useI18n()

const chartOptions = computed(() => ({
  responsive: true,
  maintainAspectRatio: false,
  plugins: {
    legend: {
      position: 'top' as const,
    },
    title: {
      display: false,
    },
    tooltip: {
      mode: 'index' as const,
      intersect: false,
      callbacks: {
        label: function(context: any) {
          return `${context.dataset.label}: ${context.parsed.y.toFixed(1)}%`
        }
      }
    }
  },
  scales: {
    x: {
      display: true,
      title: {
        display: true,
        text: t('analytics.date')
      }
    },
    y: {
      display: true,
      title: {
        display: true,
        text: t('analytics.percentage')
      },
      beginAtZero: true,
      max: 100,
      ticks: {
        callback: function(value: any) {
          return value + '%'
        }
      }
    }
  },
  interaction: {
    mode: 'nearest' as const,
    axis: 'x' as const,
    intersect: false
  }
}))
</script>