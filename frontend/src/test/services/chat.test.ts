import { describe, it, expect, vi, beforeEach } from 'vitest'
import { chatService } from '@/services/chat'
import { apiClient } from '@/services/api'

// Mock the API client
vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    delete: vi.fn()
  }
}))

describe('Chat Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('sendMessage', () => {
    it('sends message with correct parameters', async () => {
      const mockResponse = {
        data: {
          response: 'AI response',
          conversation_id: 'conv123',
          message_id: 'msg456',
          language: 'en',
          cost_info: { tokens: 150, cost: 0.003 },
          context_used: true,
          processing_time_ms: 1200
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const result = await chatService.sendMessage(
        'business123',
        'How is my restaurant performing?',
        'conv123',
        'en'
      )
      
      expect(apiClient.post).toHaveBeenCalledWith(
        '/chat/business123',
        {
          message: 'How is my restaurant performing?',
          language: 'en'
        },
        {
          params: { conversation_id: 'conv123' }
        }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('sends message without conversation ID', async () => {
      const mockResponse = {
        data: {
          response: 'AI response',
          conversation_id: 'new_conv',
          message_id: 'msg789',
          language: 'en'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      await chatService.sendMessage('business123', 'Hello')
      
      expect(apiClient.post).toHaveBeenCalledWith(
        '/chat/business123',
        {
          message: 'Hello',
          language: 'en'
        },
        {
          params: {}
        }
      )
    })

    it('uses default language when not provided', async () => {
      const mockResponse = { data: {} }
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      await chatService.sendMessage('business123', 'Test message')
      
      expect(apiClient.post).toHaveBeenCalledWith(
        '/chat/business123',
        {
          message: 'Test message',
          language: 'en'
        },
        {
          params: {}
        }
      )
    })
  })

  describe('getConversations', () => {
    it('fetches conversations with default parameters', async () => {
      const mockResponse = {
        data: [
          {
            conversation_id: 'conv1',
            business_id: 'business123',
            message_count: 5,
            created_at: '2024-01-01T10:00:00Z',
            last_message_at: '2024-01-01T11:00:00Z',
            language: 'en'
          }
        ]
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await chatService.getConversations('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/business123/conversations',
        {
          params: { skip: 0, limit: 50 }
        }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches conversations with custom parameters', async () => {
      const mockResponse = { data: [] }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      await chatService.getConversations('business123', 10, 25)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/business123/conversations',
        {
          params: { skip: 10, limit: 25 }
        }
      )
    })
  })

  describe('getConversationMessages', () => {
    it('fetches conversation messages with default parameters', async () => {
      const mockResponse = {
        data: {
          conversation_id: 'conv123',
          business_id: 'business123',
          messages: [
            {
              message_id: 'msg1',
              role: 'user',
              content: 'Hello',
              created_at: '2024-01-01T10:00:00Z',
              language: 'en'
            },
            {
              message_id: 'msg2',
              role: 'assistant',
              content: 'Hi there!',
              created_at: '2024-01-01T10:01:00Z',
              language: 'en'
            }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await chatService.getConversationMessages('business123', 'conv123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/business123/conversations/conv123',
        {
          params: { skip: 0, limit: 100 }
        }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches conversation messages with custom parameters', async () => {
      const mockResponse = { data: { messages: [] } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      await chatService.getConversationMessages('business123', 'conv123', 20, 50)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/business123/conversations/conv123',
        {
          params: { skip: 20, limit: 50 }
        }
      )
    })
  })

  describe('deleteConversation', () => {
    it('deletes conversation', async () => {
      const mockResponse = { data: { success: true } }
      vi.mocked(apiClient.delete).mockResolvedValue(mockResponse)
      
      const result = await chatService.deleteConversation('business123', 'conv123')
      
      expect(apiClient.delete).toHaveBeenCalledWith(
        '/chat/business123/conversations/conv123'
      )
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('clearConversationContext', () => {
    it('clears conversation context', async () => {
      const mockResponse = {
        data: {
          message: 'Conversation context cleared successfully',
          conversation_id: 'conv123'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const result = await chatService.clearConversationContext('business123', 'conv123')
      
      expect(apiClient.post).toHaveBeenCalledWith(
        '/chat/business123/conversations/conv123/clear'
      )
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getBusinessContextSummary', () => {
    it('fetches business context summary', async () => {
      const mockResponse = {
        data: {
          business_id: 'business123',
          context_summary: {
            total_reviews: 150,
            avg_rating: 4.2,
            sentiment_distribution: {
              positive: 0.7,
              neutral: 0.2,
              negative: 0.1
            }
          }
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await chatService.getBusinessContextSummary('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/business123/context-summary'
      )
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getChatUsageStats', () => {
    it('fetches chat usage stats with default days', async () => {
      const mockResponse = {
        data: {
          business_id: 'business123',
          period_days: 30,
          total_conversations: 15,
          total_messages: 75,
          avg_messages_per_conversation: 5.0,
          total_cost: 2.50,
          avg_cost_per_message: 0.033
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await chatService.getChatUsageStats('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/usage-stats/business123',
        {
          params: { days: 30 }
        }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches chat usage stats with custom days', async () => {
      const mockResponse = { data: {} }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      await chatService.getChatUsageStats('business123', 7)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/chat/usage-stats/business123',
        {
          params: { days: 7 }
        }
      )
    })
  })

  describe('Error Handling', () => {
    it('propagates API errors for sendMessage', async () => {
      const error = new Error('API Error')
      vi.mocked(apiClient.post).mockRejectedValue(error)
      
      await expect(
        chatService.sendMessage('business123', 'Test message')
      ).rejects.toThrow('API Error')
    })

    it('propagates API errors for getConversations', async () => {
      const error = new Error('Network Error')
      vi.mocked(apiClient.get).mockRejectedValue(error)
      
      await expect(
        chatService.getConversations('business123')
      ).rejects.toThrow('Network Error')
    })

    it('propagates API errors for deleteConversation', async () => {
      const error = new Error('Delete Error')
      vi.mocked(apiClient.delete).mockRejectedValue(error)
      
      await expect(
        chatService.deleteConversation('business123', 'conv123')
      ).rejects.toThrow('Delete Error')
    })
  })
})