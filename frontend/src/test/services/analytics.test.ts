import { describe, it, expect, vi, beforeEach } from 'vitest'
import { analyticsService } from '@/services/analytics'
import { apiClient } from '@/services/api'

// Mock the API client
vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn()
  }
}))

describe('Analytics Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getDashboardData', () => {
    it('fetches dashboard data for a business', async () => {
      const mockData = {
        avg_rating: 4.2,
        total_reviews: 156,
        sentiment_positive: 78,
        sentiment_negative: 12,
        sentiment_neutral: 10
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockData })
      
      const result = await analyticsService.getDashboardData('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/dashboard')
      expect(result).toEqual(mockData)
    })

    it('handles API errors gracefully', async () => {
      vi.mocked(apiClient.get).mockRejectedValue(new Error('API Error'))
      
      await expect(analyticsService.getDashboardData('business-123')).rejects.toThrow('API Error')
    })
  })

  describe('getTrends', () => {
    it('fetches trend data with default period', async () => {
      const mockTrends = [
        { date: '2024-01-01', value: 4.1 },
        { date: '2024-01-02', value: 4.3 }
      ]
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTrends })
      
      const result = await analyticsService.getTrends('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/trends', {
        params: { days: 30 }
      })
      expect(result).toEqual(mockTrends)
    })

    it('fetches trend data with custom period', async () => {
      const mockTrends = []
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTrends })
      
      await analyticsService.getTrends('business-123', 7)
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/trends', {
        params: { days: 7 }
      })
    })
  })

  describe('getSentimentAnalysis', () => {
    it('fetches sentiment analysis data', async () => {
      const mockSentiment = {
        positive: 65,
        neutral: 25,
        negative: 10,
        trends: []
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockSentiment })
      
      const result = await analyticsService.getSentimentAnalysis('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/sentiment', {
        params: { period: '30d' }
      })
      expect(result).toEqual(mockSentiment)
    })

    it('accepts custom period parameter', async () => {
      vi.mocked(apiClient.get).mockResolvedValue({ data: {} })
      
      await analyticsService.getSentimentAnalysis('business-123', '7d')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/sentiment', {
        params: { period: '7d' }
      })
    })
  })

  describe('getTopicAnalysis', () => {
    it('fetches topic analysis data', async () => {
      const mockTopics = {
        topics: [
          { name: 'food_quality', count: 45, sentiment: 'positive' },
          { name: 'service', count: 32, sentiment: 'neutral' }
        ]
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockTopics })
      
      const result = await analyticsService.getTopicAnalysis('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/topics', {
        params: { period: '30d' }
      })
      expect(result).toEqual(mockTopics)
    })
  })

  describe('getCostSummary', () => {
    it('fetches cost summary data', async () => {
      const mockCosts = {
        current_month: 45.67,
        limit: 100.00,
        usage_percentage: 45.67,
        breakdown: {
          classification: 25.30,
          chat: 20.37
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCosts })
      
      const result = await analyticsService.getCostSummary('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/costs')
      expect(result).toEqual(mockCosts)
    })
  })

  describe('getCompetitorAnalysis', () => {
    it('fetches competitor analysis data', async () => {
      const mockCompetitors = {
        mentions: 5,
        competitors: ['Restaurant A', 'Restaurant B'],
        sentiment: 'neutral'
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockCompetitors })
      
      const result = await analyticsService.getCompetitorAnalysis('business-123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/competitors')
      expect(result).toEqual(mockCompetitors)
    })
  })

  describe('getPerformanceMetrics', () => {
    it('fetches performance metrics with date range', async () => {
      const mockMetrics = {
        response_rate: 85,
        avg_response_time: 2.5,
        customer_satisfaction: 4.2
      }
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockMetrics })
      
      const result = await analyticsService.getPerformanceMetrics(
        'business-123',
        '2024-01-01',
        '2024-01-31'
      )
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/performance', {
        params: {
          start_date: '2024-01-01',
          end_date: '2024-01-31'
        }
      })
      expect(result).toEqual(mockMetrics)
    })
  })

  describe('exportReport', () => {
    it('exports report with default format', async () => {
      const mockBlob = new Blob(['PDF content'], { type: 'application/pdf' })
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob })
      
      const result = await analyticsService.exportReport('business-123', 'weekly')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/export', {
        params: { type: 'weekly', format: 'pdf' },
        responseType: 'blob'
      })
      expect(result).toEqual(mockBlob)
    })

    it('exports report with custom format', async () => {
      const mockBlob = new Blob(['CSV content'], { type: 'text/csv' })
      
      vi.mocked(apiClient.get).mockResolvedValue({ data: mockBlob })
      
      await analyticsService.exportReport('business-123', 'monthly', 'csv')
      
      expect(apiClient.get).toHaveBeenCalledWith('/analytics/business-123/export', {
        params: { type: 'monthly', format: 'csv' },
        responseType: 'blob'
      })
    })
  })
})