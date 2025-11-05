<template>
  <div class="flex h-full">
    <!-- Sidebar with conversation history -->
    <div class="w-80 bg-white border-r border-gray-200 flex flex-col">
      <!-- Header -->
      <div class="p-4 border-b border-gray-200">
        <div class="flex items-center justify-between mb-4">
          <h2 class="text-lg font-semibold text-gray-900">
            {{ $t('chat.title') }}
          </h2>
          <button
            @click="startNewConversation"
            class="inline-flex items-center px-3 py-2 border border-transparent text-sm leading-4 font-medium rounded-md text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
          >
            <PlusIcon class="h-4 w-4 mr-1" />
            {{ $t('chat.newConversation') }}
          </button>
        </div>
        
        <!-- Business selector -->
        <div class="flex items-center space-x-2">
          <label class="text-sm font-medium text-gray-700">{{ $t('dashboard.selectBusiness') }}:</label>
          <select
            v-model="selectedBusinessId"
            @change="onBusinessChange"
            class="block w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:outline-none focus:ring-blue-500 focus:border-blue-500 text-sm"
          >
            <option value="">{{ $t('chat.selectBusiness') }}</option>
            <option v-for="business in (businessStore.businesses as Business[])" :key="business.id" :value="business.id">
              {{ business.name }}
            </option>
          </select>
        </div>
      </div>

      <!-- Conversation list -->
      <div class="flex-1 overflow-y-auto">
        <div class="p-4">
          <h3 class="text-sm font-medium text-gray-700 mb-3">
            {{ $t('chat.conversationHistory') }}
          </h3>
          
          <div v-if="loading.conversations" class="space-y-2">
            <div v-for="i in 3" :key="i" class="animate-pulse">
              <div class="h-16 bg-gray-200 rounded-lg"></div>
            </div>
          </div>
          
          <div v-else-if="conversations.length === 0" class="text-center py-8">
            <ChatBubbleLeftRightIcon class="mx-auto h-12 w-12 text-gray-400" />
            <p class="mt-2 text-sm text-gray-500">{{ $t('chat.noConversations') }}</p>
            <p class="text-xs text-gray-400">{{ $t('chat.startChatting') }}</p>
          </div>
          
          <div v-else class="space-y-2">
            <div
              v-for="conversation in conversations"
              :key="conversation.conversation_id"
              @click="selectConversation(conversation)"
              class="p-3 rounded-lg cursor-pointer transition-colors"
              :class="[
                currentConversationId === conversation.conversation_id
                  ? 'bg-blue-50 border border-blue-200'
                  : 'hover:bg-gray-50 border border-transparent'
              ]"
            >
              <div class="flex items-center justify-between">
                <div class="flex-1 min-w-0">
                  <p class="text-sm font-medium text-gray-900 truncate">
                    {{ $t('chat.messageCount', { count: conversation.message_count }) }}
                  </p>
                  <p class="text-xs text-gray-500">
                    {{ $t('chat.lastMessage') }}: {{ formatDate(conversation.last_message_at) }}
                  </p>
                </div>
                <div class="flex items-center space-x-1">
                  <button
                    @click.stop="clearConversationContext(conversation.conversation_id)"
                    class="p-1 text-gray-400 hover:text-gray-600"
                    :title="$t('chat.clearContext')"
                  >
                    <ArrowPathIcon class="h-4 w-4" />
                  </button>
                  <button
                    @click.stop="deleteConversation(conversation.conversation_id)"
                    class="p-1 text-gray-400 hover:text-red-600"
                    :title="$t('chat.deleteConversation')"
                  >
                    <TrashIcon class="h-4 w-4" />
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Main chat area -->
    <div class="flex-1 flex flex-col">
      <!-- Chat header -->
      <div class="bg-white border-b border-gray-200 px-6 py-4">
        <div class="flex items-center justify-between">
          <div>
            <h1 class="text-xl font-semibold text-gray-900">
              {{ selectedBusiness?.name || $t('chat.title') }}
            </h1>
            <p class="text-sm text-gray-500">
              {{ $t('chat.welcomeMessage') }}
            </p>
          </div>
          
          <div class="flex items-center space-x-2">
            <!-- Context summary button -->
            <button
              @click="showContextSummary = !showContextSummary"
              class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <InformationCircleIcon class="h-4 w-4 mr-1" />
              {{ $t('chat.contextSummary') }}
            </button>
            
            <!-- Usage stats button -->
            <button
              @click="showUsageStats = !showUsageStats"
              class="inline-flex items-center px-3 py-2 border border-gray-300 shadow-sm text-sm leading-4 font-medium rounded-md text-gray-700 bg-white hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500"
            >
              <ChartBarIcon class="h-4 w-4 mr-1" />
              {{ $t('chat.usageStats') }}
            </button>
          </div>
        </div>
      </div>

      <!-- Messages area -->
      <div class="flex-1 overflow-y-auto bg-gray-50 p-6">
        <div class="max-w-4xl mx-auto space-y-4">
          <div v-if="loading.messages" class="space-y-4">
            <div v-for="i in 3" :key="i" class="animate-pulse">
              <div class="flex space-x-3">
                <div class="h-8 w-8 bg-gray-300 rounded-full"></div>
                <div class="flex-1 space-y-2">
                  <div class="h-4 bg-gray-300 rounded w-3/4"></div>
                  <div class="h-4 bg-gray-300 rounded w-1/2"></div>
                </div>
              </div>
            </div>
          </div>
          
          <div v-else-if="messages.length === 0" class="text-center py-12">
            <ChatBubbleLeftRightIcon class="mx-auto h-16 w-16 text-gray-400" />
            <p class="mt-4 text-lg text-gray-500">{{ $t('chat.welcomeMessage') }}</p>
          </div>
          
          <div v-else>
            <div
              v-for="message in messages"
              :key="message.message_id"
              class="flex space-x-3"
              :class="message.role === 'user' ? 'justify-end' : 'justify-start'"
            >
              <div
                v-if="message.role === 'assistant'"
                class="flex-shrink-0 h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center"
              >
                <span class="text-white text-sm font-medium">AI</span>
              </div>
              
              <div
                class="max-w-xs lg:max-w-md px-4 py-2 rounded-lg"
                :class="[
                  message.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-white text-gray-900 shadow-sm border border-gray-200'
                ]"
              >
                <p class="text-sm whitespace-pre-wrap">{{ message.content }}</p>
                <p class="text-xs mt-1 opacity-75">
                  {{ formatTime(message.created_at) }}
                </p>
              </div>
              
              <div
                v-if="message.role === 'user'"
                class="flex-shrink-0 h-8 w-8 rounded-full bg-gray-500 flex items-center justify-center"
              >
                <UserIcon class="h-5 w-5 text-white" />
              </div>
            </div>
          </div>
          
          <!-- Typing indicator -->
          <div v-if="isTyping" class="flex space-x-3">
            <div class="flex-shrink-0 h-8 w-8 rounded-full bg-blue-500 flex items-center justify-center">
              <span class="text-white text-sm font-medium">AI</span>
            </div>
            <div class="bg-white px-4 py-2 rounded-lg shadow-sm border border-gray-200">
              <div class="flex space-x-1">
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.1s"></div>
                <div class="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style="animation-delay: 0.2s"></div>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Message input -->
      <div class="bg-white border-t border-gray-200 px-6 py-4">
        <form @submit.prevent="sendMessage" class="flex space-x-4">
          <div class="flex-1">
            <textarea
              v-model="newMessage"
              :placeholder="$t('chat.placeholder')"
              :disabled="!selectedBusinessId || isTyping"
              rows="2"
              class="block w-full border-gray-300 rounded-md shadow-sm focus:ring-blue-500 focus:border-blue-500 sm:text-sm resize-none"
              @keydown.enter.exact.prevent="sendMessage"
              @keydown.enter.shift.exact="newMessage += '\n'"
            ></textarea>
          </div>
          <button
            type="submit"
            :disabled="!newMessage.trim() || !selectedBusinessId || isTyping"
            class="inline-flex items-center px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm text-white bg-blue-600 hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed"
          >
            <PaperAirplaneIcon class="h-4 w-4" />
            <span class="ml-2">{{ $t('chat.send') }}</span>
          </button>
        </form>
      </div>
    </div>

    <!-- Context Summary Modal -->
    <div v-if="showContextSummary" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showContextSummary = false"></div>
        
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-lg sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
              {{ $t('chat.contextSummary') }}
            </h3>
            <div v-if="contextSummary" class="text-sm text-gray-600">
              <pre class="whitespace-pre-wrap">{{ JSON.stringify(contextSummary.context_summary, null, 2) }}</pre>
            </div>
            <div v-else class="text-sm text-gray-500">
              {{ $t('common.loading') }}
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              @click="showContextSummary = false"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              {{ $t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Usage Stats Modal -->
    <div v-if="showUsageStats" class="fixed inset-0 z-50 overflow-y-auto">
      <div class="flex items-end justify-center min-h-screen pt-4 px-4 pb-20 text-center sm:block sm:p-0">
        <div class="fixed inset-0 bg-gray-500 bg-opacity-75 transition-opacity" @click="showUsageStats = false"></div>
        
        <div class="inline-block align-bottom bg-white rounded-lg text-left overflow-hidden shadow-xl transform transition-all sm:my-8 sm:align-middle sm:max-w-2xl sm:w-full">
          <div class="bg-white px-4 pt-5 pb-4 sm:p-6 sm:pb-4">
            <h3 class="text-lg leading-6 font-medium text-gray-900 mb-4">
              {{ $t('chat.usageStats') }}
            </h3>
            <div v-if="usageStats" class="grid grid-cols-2 gap-4">
              <div class="bg-gray-50 p-3 rounded-lg">
                <p class="text-sm font-medium text-gray-900">{{ $t('chat.totalConversations') }}</p>
                <p class="text-2xl font-bold text-blue-600">{{ usageStats.total_conversations }}</p>
              </div>
              <div class="bg-gray-50 p-3 rounded-lg">
                <p class="text-sm font-medium text-gray-900">{{ $t('chat.totalMessages') }}</p>
                <p class="text-2xl font-bold text-green-600">{{ usageStats.total_messages }}</p>
              </div>
              <div class="bg-gray-50 p-3 rounded-lg">
                <p class="text-sm font-medium text-gray-900">{{ $t('chat.avgMessagesPerConversation') }}</p>
                <p class="text-2xl font-bold text-purple-600">{{ usageStats.avg_messages_per_conversation?.toFixed(1) }}</p>
              </div>
              <div class="bg-gray-50 p-3 rounded-lg">
                <p class="text-sm font-medium text-gray-900">{{ $t('chat.totalCost') }}</p>
                <p class="text-2xl font-bold text-red-600">${{ usageStats.total_cost?.toFixed(2) }}</p>
              </div>
            </div>
            <div v-else class="text-sm text-gray-500">
              {{ $t('common.loading') }}
            </div>
          </div>
          <div class="bg-gray-50 px-4 py-3 sm:px-6 sm:flex sm:flex-row-reverse">
            <button
              @click="showUsageStats = false"
              class="mt-3 w-full inline-flex justify-center rounded-md border border-gray-300 shadow-sm px-4 py-2 bg-white text-base font-medium text-gray-700 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 sm:mt-0 sm:ml-3 sm:w-auto sm:text-sm"
            >
              {{ $t('common.close') }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { useBusinessStore } from '@/stores/business'
import type { Business } from '@/types'
import { useNotificationsStore } from '@/stores/notifications'
import { chatService } from '@/services/chat'

import type { 
  Conversation, 
  ChatMessage, 
  ChatUsageStats, 
  BusinessContextSummary
} from '@/types'
import {
  PlusIcon,
  ChatBubbleLeftRightIcon,
  ArrowPathIcon,
  TrashIcon,
  InformationCircleIcon,
  ChartBarIcon,
  PaperAirplaneIcon,
  UserIcon
} from '@heroicons/vue/24/outline'

const { t } = useI18n()
const businessStore = useBusinessStore()
const notificationsStore = useNotificationsStore()

// Reactive state
const selectedBusinessId = ref<string>('')
const conversations = ref<Conversation[]>([])
const messages = ref<ChatMessage[]>([])
const currentConversationId = ref<string | null>(null)
const newMessage = ref('')
const isTyping = ref(false)
const showContextSummary = ref(false)
const showUsageStats = ref(false)
const contextSummary = ref<BusinessContextSummary | null>(null)
const usageStats = ref<ChatUsageStats | null>(null)

const loading = reactive({
  conversations: false,
  messages: false,
  sending: false
})

// Computed properties
const selectedBusiness = computed(() => 
  (businessStore.businesses as Business[]).find((b: Business) => b.id === selectedBusinessId.value)
)

// Methods
const onBusinessChange = async () => {
  currentConversationId.value = null
  messages.value = []
  await loadConversations()
}

const loadConversations = async () => {
  if (!selectedBusinessId.value) return
  
  loading.conversations = true
  try {
    const response = await chatService.getConversations(selectedBusinessId.value)
    conversations.value = response
  } catch (error) {
    console.error('Failed to load conversations:', error)
    notificationsStore.showError(t('chat.error'))
  } finally {
    loading.conversations = false
  }
}

const selectConversation = async (conversation: Conversation) => {
  currentConversationId.value = conversation.conversation_id
  await loadMessages()
}

const loadMessages = async () => {
  if (!selectedBusinessId.value || !currentConversationId.value) return
  
  loading.messages = true
  try {
    const response = await chatService.getConversationMessages(
      selectedBusinessId.value,
      currentConversationId.value
    )
    messages.value = response.messages.reverse() // Show oldest first
  } catch (error) {
    console.error('Failed to load messages:', error)
    notificationsStore.showError(t('chat.error'))
  } finally {
    loading.messages = false
  }
}

const sendMessage = async () => {
  if (!newMessage.value.trim() || !selectedBusinessId.value || isTyping.value) return
  
  const messageText = newMessage.value.trim()
  newMessage.value = ''
  isTyping.value = true
  
  // Add user message to UI immediately
  const userMessage: ChatMessage = {
    message_id: Date.now().toString(),
    role: 'user',
    content: messageText,
    created_at: new Date().toISOString(),
    language: 'en'
  }
  messages.value.push(userMessage)
  
  try {
    const response = await (chatService as any).sendMessage(
      selectedBusinessId.value,
      messageText,
      currentConversationId.value
    )
    
    // Update conversation ID if this was a new conversation
    if (!currentConversationId.value) {
      currentConversationId.value = response.conversation_id
      await loadConversations() // Refresh conversation list
    }
    
    // Add AI response
    const aiMessage: ChatMessage = {
      message_id: response.message_id,
      role: 'assistant',
      content: response.response,
      created_at: new Date().toISOString(),
      language: response.language,
      cost_info: response.cost_info
    }
    messages.value.push(aiMessage)
    
  } catch (error) {
    console.error('Failed to send message:', error)
    notificationsStore.showError(t('chat.error'))
    // Remove the user message if sending failed
    messages.value.pop()
  } finally {
    isTyping.value = false
  }
}

const startNewConversation = () => {
  currentConversationId.value = null
  messages.value = []
}

const clearConversationContext = async (conversationId: string) => {
  try {
    await chatService.clearConversationContext(selectedBusinessId.value, conversationId)
    notificationsStore.showSuccess(t('chat.contextCleared'))
  } catch (error) {
    console.error('Failed to clear context:', error)
    notificationsStore.showError(t('chat.error'))
  }
}

const deleteConversation = async (conversationId: string) => {
  if (!confirm(t('chat.confirmDelete'))) return
  
  try {
    await chatService.deleteConversation(selectedBusinessId.value, conversationId)
    notificationsStore.showSuccess(t('chat.conversationDeleted'))
    
    // Remove from local list
    conversations.value = conversations.value.filter(c => c.conversation_id !== conversationId)
    
    // Clear current conversation if it was deleted
    if (currentConversationId.value === conversationId) {
      currentConversationId.value = null
      messages.value = []
    }
  } catch (error) {
    console.error('Failed to delete conversation:', error)
    notificationsStore.showError(t('chat.error'))
  }
}

const loadContextSummary = async () => {
  if (!selectedBusinessId.value) return
  
  try {
    const response = await chatService.getBusinessContextSummary(selectedBusinessId.value)
    contextSummary.value = response
  } catch (error) {
    console.error('Failed to load context summary:', error)
  }
}

const loadUsageStats = async () => {
  if (!selectedBusinessId.value) return
  
  try {
    const response = await chatService.getChatUsageStats(selectedBusinessId.value)
    usageStats.value = response
  } catch (error) {
    console.error('Failed to load usage stats:', error)
  }
}

const formatDate = (dateString: string) => {
  return new Date(dateString).toLocaleDateString()
}

const formatTime = (dateString: string) => {
  return new Date(dateString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// Watchers
watch(showContextSummary, (show) => {
  if (show) loadContextSummary()
})

watch(showUsageStats, (show) => {
  if (show) loadUsageStats()
})

// Lifecycle
onMounted(async () => {
  await businessStore.fetchBusinesses()
  const businesses = businessStore.businesses as Business[]
  if (businesses.length > 0) {
    selectedBusinessId.value = (businessStore.currentBusiness as Business | null)?.id || businesses[0].id
    await loadConversations()
  }
})
</script>