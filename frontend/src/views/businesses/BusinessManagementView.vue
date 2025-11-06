<template>
  <div class="min-h-screen bg-gray-50 py-8">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <!-- Header -->
      <div class="mb-8">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-3xl font-bold text-gray-900">
              {{ $t('businesses.title') }}
            </h1>
            <p class="mt-2 text-gray-600">
              {{ $t('businesses.subtitle') }}
            </p>
          </div>
          <button
            @click="showAddBusinessModal = true"
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon class="h-5 w-5 mr-2" />
            {{ $t('businesses.addBusiness') }}
          </button>
        </div>
      </div>

      <!-- Loading State -->
      <div v-if="loading" class="flex justify-center items-center py-12">
        <div class="animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"></div>
      </div>

      <!-- Error State -->
      <div v-else-if="error" class="bg-red-50 border border-red-200 rounded-md p-4 mb-6">
        <div class="flex">
          <ExclamationTriangleIcon class="h-5 w-5 text-red-400" />
          <div class="ml-3">
            <h3 class="text-sm font-medium text-red-800">
              {{ $t('common.error') }}
            </h3>
            <div class="mt-2 text-sm text-red-700">
              {{ error }}
            </div>
          </div>
        </div>
      </div>

      <!-- Empty State -->
      <div v-else-if="!businesses.length" class="text-center py-12">
        <BuildingOfficeIcon class="mx-auto h-12 w-12 text-gray-400" />
        <h3 class="mt-2 text-sm font-medium text-gray-900">
          {{ $t('businesses.noBusinesses') }}
        </h3>
        <p class="mt-1 text-sm text-gray-500">
          {{ $t('businesses.noBusinessesDescription') }}
        </p>
        <div class="mt-6">
          <button
            @click="showAddBusinessModal = true"
            class="inline-flex items-center px-4 py-2 border border-transparent rounded-md shadow-sm text-sm font-medium text-white bg-blue-600 hover:bg-blue-700"
          >
            <PlusIcon class="h-5 w-5 mr-2" />
            {{ $t('businesses.addFirstBusiness') }}
          </button>
        </div>
      </div>

      <!-- Business Grid -->
      <div v-else class="grid grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
        <div
          v-for="business in businesses"
          :key="business.id"
          class="bg-white overflow-hidden shadow rounded-lg hover:shadow-md transition-shadow duration-200"
        >
          <div class="p-6">
            <!-- Business Header -->
            <div class="flex items-center justify-between mb-4">
              <div class="flex items-center">
                <BuildingOfficeIcon class="h-8 w-8 text-gray-400 mr-3" />
                <div>
                  <h3 class="text-lg font-medium text-gray-900 truncate">
                    {{ business.name }}
                  </h3>
                  <p class="text-sm text-gray-500">
                    {{ business.category }}
                  </p>
                </div>
              </div>
              <div class="flex items-center space-x-2">
                <button
                  @click="editBusiness(business)"
                  class="text-gray-400 hover:text-gray-600"
                  :title="$t('common.edit')"
                >
                  <PencilIcon class="h-5 w-5" />
                </button>
                <button
                  @click="confirmDeleteBusiness(business)"
                  class="text-gray-400 hover:text-red-600"
                  :title="$t('common.delete')"
                >
                  <TrashIcon class="h-5 w-5" />
                </button>
              </div>
            </div>

            <!-- Business Details -->
            <div class="space-y-3">
              <div class="flex items-center text-sm text-gray-600">
                <MapPinIcon class="h-4 w-4 mr-2 text-gray-400" />
                <span class="truncate">{{ business.address }}</span>
              </div>
              
              <div class="flex items-center justify-between">
                <div class="flex items-center text-sm text-gray-600">
                  <StarIcon class="h-4 w-4 mr-1 text-yellow-400" />
                  <span>{{ business.avg_rating?.toFixed(1) || '0.0' }}</span>
                </div>
                <div class="text-sm text-gray-600">
                  {{ business.total_reviews || 0 }} {{ $t('businesses.reviews') }}
                </div>
              </div>

              <!-- Import Status -->
              <div class="pt-3 border-t border-gray-200">
                <ImportStatusIndicator
                  :business-id="business.id"
                  @refresh="refreshImportStatus"
                  @import-started="handleImportStarted(business)"
                  @import-completed="handleImportCompleted(business, $event)"
                />
              </div>
            </div>

            <!-- Actions -->
            <div class="mt-6 flex space-x-3">
              <button
                @click="viewBusiness(business)"
                class="flex-1 bg-blue-600 text-white text-sm font-medium py-2 px-3 rounded-md hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500"
              >
                {{ $t('businesses.viewDashboard') }}
              </button>
              <button
                @click="syncReviews(business)"
                :disabled="syncingBusinessId === business.id"
                class="flex-1 bg-gray-100 text-gray-700 text-sm font-medium py-2 px-3 rounded-md hover:bg-gray-200 focus:outline-none focus:ring-2 focus:ring-gray-500 disabled:opacity-50"
              >
                <span v-if="syncingBusinessId === business.id" class="flex items-center justify-center">
                  <div class="animate-spin rounded-full h-4 w-4 border-b-2 border-gray-600 mr-2"></div>
                  {{ $t('businesses.syncing') }}
                </span>
                <span v-else>
                  {{ $t('businesses.syncReviews') }}
                </span>
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- Add Business Modal -->
      <BusinessRegistrationModal
        v-if="showAddBusinessModal"
        @close="showAddBusinessModal = false"
        @business-created="handleBusinessCreated"
      />

      <!-- Edit Business Modal -->
      <BusinessEditModal
        v-if="showEditBusinessModal && selectedBusiness"
        :business="selectedBusiness"
        @close="showEditBusinessModal = false"
        @business-updated="handleBusinessUpdated"
      />

      <!-- Delete Confirmation Modal -->
      <ConfirmationModal
        v-if="showDeleteModal && businessToDelete"
        :title="$t('businesses.deleteConfirmTitle')"
        :message="$t('businesses.deleteConfirmMessage', { name: businessToDelete.name })"
        :confirm-text="$t('common.delete')"
        :cancel-text="$t('common.cancel')"
        confirm-variant="danger"
        @confirm="handleDeleteBusiness"
        @cancel="showDeleteModal = false"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { useBusinessStore } from '@/stores/business'
import { useNotificationsStore } from '@/stores/notifications'
import type { Business } from '@/types'

// Icons
import {
  PlusIcon,
  BuildingOfficeIcon,
  PencilIcon,
  TrashIcon,
  MapPinIcon,
  StarIcon,
  ExclamationTriangleIcon
} from '@heroicons/vue/24/outline'

// Components
import BusinessRegistrationModal from '@/components/businesses/BusinessRegistrationModal.vue'
import BusinessEditModal from '@/components/businesses/BusinessEditModal.vue'
import ImportStatusIndicator from '@/components/businesses/ImportStatusIndicator.vue'
import ConfirmationModal from '@/components/common/ConfirmationModal.vue'

const { t } = useI18n()
const router = useRouter()
const businessStore = useBusinessStore()
const notificationsStore = useNotificationsStore()

// Reactive state
const showAddBusinessModal = ref(false)
const showEditBusinessModal = ref(false)
const showDeleteModal = ref(false)
const selectedBusiness = ref<Business | null>(null)
const businessToDelete = ref<Business | null>(null)
const syncingBusinessId = ref<string | null>(null)

// Computed properties
const businesses = computed(() => businessStore.businesses)
const loading = computed(() => businessStore.loading)
const error = computed(() => businessStore.error)

// Methods
const loadBusinesses = async () => {
  try {
    await businessStore.fetchBusinesses()
  } catch (error) {
    console.error('Failed to load businesses:', error)
  }
}

const handleBusinessCreated = (business: Business) => {
  showAddBusinessModal.value = false
  notificationsStore.showSuccess(t('businesses.businessCreated', { name: business.name }))
}

const editBusiness = (business: Business) => {
  selectedBusiness.value = business
  showEditBusinessModal.value = true
}

const handleBusinessUpdated = (business: Business) => {
  showEditBusinessModal.value = false
  selectedBusiness.value = null
  notificationsStore.showSuccess(t('businesses.businessUpdated', { name: business.name }))
}

const confirmDeleteBusiness = (business: Business) => {
  businessToDelete.value = business
  showDeleteModal.value = true
}

const handleDeleteBusiness = async () => {
  if (!businessToDelete.value) return

  try {
    await businessStore.deleteBusiness(businessToDelete.value.id)
    notificationsStore.showSuccess(
      t('businesses.businessDeleted', { name: businessToDelete.value.name })
    )
  } catch (error) {
    console.error('Failed to delete business:', error)
    notificationsStore.showError(t('businesses.deleteError'))
  } finally {
    showDeleteModal.value = false
    businessToDelete.value = null
  }
}

const viewBusiness = (business: Business) => {
  businessStore.setCurrentBusiness(business)
  router.push('/app/dashboard')
}

const syncReviews = async (business: Business) => {
  syncingBusinessId.value = business.id
  
  try {
    await businessStore.importReviews(business.id)
    notificationsStore.showSuccess(
      t('businesses.reviewsSynced', { name: business.name })
    )
  } catch (error) {
    console.error('Failed to sync reviews:', error)
    notificationsStore.showError(t('businesses.syncError'))
  } finally {
    syncingBusinessId.value = null
  }
}

const refreshImportStatus = () => {
  // This will be called by the ImportStatusIndicator component
  // when import status needs to be refreshed
}

const handleImportStarted = (business: Business) => {
  notificationsStore.showInfo(
    t('businesses.importStarted', { name: business.name })
  )
}

const handleImportCompleted = (business: Business, result: any) => {
  notificationsStore.showSuccess(
    t('businesses.importCompleted', { 
      name: business.name, 
      count: result.imported_count 
    })
  )
  // Refresh business list to update stats
  loadBusinesses()
}

// Lifecycle
onMounted(() => {
  loadBusinesses()
})
</script>