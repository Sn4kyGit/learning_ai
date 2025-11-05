import { describe, it, expect, vi, beforeEach } from 'vitest'
import { reviewService } from '@/services/review'
import { apiClient } from '@/services/api'

// Mock the API client
vi.mock('@/services/api', () => ({
  apiClient: {
    get: vi.fn(),
    post: vi.fn(),
    patch: vi.fn()
  }
}))

describe('Review Service', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  describe('getReviews', () => {
    it('fetches reviews with default parameters', async () => {
      const mockResponse = {
        data: {
          reviews: [
            {
              id: 'rev1',
              business_id: 'business123',
              author_name: 'John Doe',
              rating: 5,
              text: 'Great food!',
              classification: {
                sentiment: 'positive',
                topics: ['food_quality'],
                urgency: 'low'
              }
            }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getReviews('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123',
        { params: {} }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches reviews with custom parameters', async () => {
      const mockResponse = { data: { reviews: [] } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const params = {
        include_classifications: true,
        sentiment: 'positive',
        urgency: 'high'
      }
      
      await reviewService.getReviews('business123', params)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123',
        { params }
      )
    })
  })

  describe('getReview', () => {
    it('fetches single review by ID', async () => {
      const mockResponse = {
        data: {
          id: 'rev123',
          business_id: 'business123',
          author_name: 'Jane Smith',
          rating: 4,
          text: 'Good service'
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getReview('rev123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/detail/rev123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('classifyReviews', () => {
    it('classifies reviews for a business', async () => {
      const mockResponse = {
        data: {
          success: true,
          classifications: [
            {
              review_id: 'rev1',
              sentiment: 'positive',
              topics: ['food_quality'],
              urgency: 'low'
            }
          ]
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const reviews = ['Great food!', 'Terrible service']
      const result = await reviewService.classifyReviews('business123', reviews)
      
      expect(apiClient.post).toHaveBeenCalledWith('/reviews/classify', {
        business_id: 'business123',
        reviews
      })
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getClassifications', () => {
    it('fetches classifications with default filters', async () => {
      const mockResponse = {
        data: {
          classifications: [
            {
              id: 'class1',
              review_id: 'rev1',
              sentiment: 'positive',
              topics: ['food_quality'],
              urgency: 'low'
            }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getClassifications('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123/classifications',
        { params: {} }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches classifications with filters', async () => {
      const mockResponse = { data: { classifications: [] } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const filters = { sentiment: 'negative', urgency: 'high' }
      await reviewService.getClassifications('business123', filters)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123/classifications',
        { params: filters }
      )
    })
  })

  describe('getCriticalReviews', () => {
    it('fetches critical reviews with default hours', async () => {
      const mockResponse = {
        data: {
          critical_reviews: [
            {
              id: 'rev1',
              rating: 1,
              text: 'Terrible experience',
              classification: { urgency: 'high' }
            }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getCriticalReviews('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123/critical',
        { params: { hours_back: 24 } }
      )
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches critical reviews with custom hours', async () => {
      const mockResponse = { data: { critical_reviews: [] } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      await reviewService.getCriticalReviews('business123', 48)
      
      expect(apiClient.get).toHaveBeenCalledWith(
        '/reviews/business123/critical',
        { params: { hours_back: 48 } }
      )
    })
  })

  describe('getSentimentDistribution', () => {
    it('fetches sentiment distribution', async () => {
      const mockResponse = {
        data: {
          positive: 0.7,
          neutral: 0.2,
          negative: 0.1
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getSentimentDistribution('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/business123/sentiment')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getTopicAnalysis', () => {
    it('fetches topic analysis', async () => {
      const mockResponse = {
        data: {
          topics: [
            { topic: 'food_quality', count: 45, percentage: 0.6 },
            { topic: 'service', count: 30, percentage: 0.4 }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getTopicAnalysis('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/business123/topics')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('markReviewAsHandled', () => {
    it('marks review as handled', async () => {
      const mockResponse = {
        data: {
          success: true,
          review_id: 'rev123'
        }
      }
      
      vi.mocked(apiClient.patch).mockResolvedValue(mockResponse)
      
      const result = await reviewService.markReviewAsHandled('rev123')
      
      expect(apiClient.patch).toHaveBeenCalledWith('/reviews/rev123/handled')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('addReviewResponse', () => {
    it('adds response to review', async () => {
      const mockResponse = {
        data: {
          success: true,
          response_id: 'resp123'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const result = await reviewService.addReviewResponse('rev123', 'Thank you for your feedback!')
      
      expect(apiClient.post).toHaveBeenCalledWith('/reviews/rev123/response', {
        response: 'Thank you for your feedback!'
      })
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getResponseSuggestions', () => {
    it('fetches response suggestions for review', async () => {
      const mockResponse = {
        data: {
          suggestion: 'Thank you for your feedback. We appreciate your business.',
          tone_analysis: 'Professional and courteous tone recommended.',
          templates: [
            { tone: 'professional', text: 'Thank you for your review.' },
            { tone: 'friendly', text: 'Thanks so much for the feedback!' }
          ]
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getResponseSuggestions('rev123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/rev123/response-suggestions')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('searchReviews', () => {
    it('searches reviews with query and filters', async () => {
      const mockResponse = {
        data: {
          reviews: [
            {
              id: 'rev1',
              text: 'Great food and excellent service!',
              rating: 5
            }
          ],
          total: 1
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const filters = { sentiment: 'positive', rating_min: 4 }
      const result = await reviewService.searchReviews('business123', 'excellent', filters)
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/business123/search', {
        params: { query: 'excellent', ...filters }
      })
      
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getReviewFilters', () => {
    it('fetches available review filters', async () => {
      const mockResponse = {
        data: {
          sentiments: ['positive', 'neutral', 'negative'],
          topics: ['food_quality', 'service', 'ambiance', 'price', 'cleanliness'],
          urgency_levels: ['low', 'medium', 'high'],
          sources: ['google', 'yelp', 'manual']
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getReviewFilters('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/business123/filters')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getUnclassifiedReviews', () => {
    it('fetches unclassified reviews with default limit', async () => {
      const mockResponse = {
        data: {
          unclassified_reviews: [
            {
              id: 'rev1',
              text: 'New review without classification',
              rating: 4
            }
          ],
          count: 1
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getUnclassifiedReviews('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/unclassified/business123', {
        params: { limit: 100 }
      })
      
      expect(result).toEqual(mockResponse.data)
    })

    it('fetches unclassified reviews with custom limit', async () => {
      const mockResponse = { data: { unclassified_reviews: [], count: 0 } }
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      await reviewService.getUnclassifiedReviews('business123', 50)
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/unclassified/business123', {
        params: { limit: 50 }
      })
    })
  })

  describe('processReviews', () => {
    it('processes reviews for a business', async () => {
      const mockResponse = {
        data: {
          business_id: 'business123',
          processed_count: 10,
          success_count: 9,
          error_count: 1,
          critical_reviews_found: 2,
          processing_time_ms: 5000
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const result = await reviewService.processReviews('business123')
      
      expect(apiClient.post).toHaveBeenCalledWith('/reviews/process/business123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('processSingleReview', () => {
    it('processes a single review', async () => {
      const mockResponse = {
        data: {
          review_id: 'rev123',
          status: 'processed',
          message: 'Review processed successfully'
        }
      }
      
      vi.mocked(apiClient.post).mockResolvedValue(mockResponse)
      
      const result = await reviewService.processSingleReview('rev123')
      
      expect(apiClient.post).toHaveBeenCalledWith('/reviews/process/single/rev123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('getReviewStatistics', () => {
    it('fetches review statistics for a business', async () => {
      const mockResponse = {
        data: {
          review_statistics: {
            total_reviews: 156,
            avg_rating: 4.2,
            response_rate: 78.5,
            avg_response_time_hours: 2.3,
            sentiment_distribution: {
              positive: 0.7,
              neutral: 0.2,
              negative: 0.1
            }
          },
          classification_statistics: {
            total_classified: 150,
            pending_classification: 6,
            critical_reviews: 8,
            competitor_mentions: 3
          }
        }
      }
      
      vi.mocked(apiClient.get).mockResolvedValue(mockResponse)
      
      const result = await reviewService.getReviewStatistics('business123')
      
      expect(apiClient.get).toHaveBeenCalledWith('/reviews/statistics/business123')
      expect(result).toEqual(mockResponse.data)
    })
  })

  describe('Error Handling', () => {
    it('propagates API errors for getReviews', async () => {
      const error = new Error('API Error')
      vi.mocked(apiClient.get).mockRejectedValue(error)
      
      await expect(
        reviewService.getReviews('business123')
      ).rejects.toThrow('API Error')
    })

    it('propagates API errors for processReviews', async () => {
      const error = new Error('Processing Error')
      vi.mocked(apiClient.post).mockRejectedValue(error)
      
      await expect(
        reviewService.processReviews('business123')
      ).rejects.toThrow('Processing Error')
    })

    it('propagates API errors for addReviewResponse', async () => {
      const error = new Error('Response Error')
      vi.mocked(apiClient.post).mockRejectedValue(error)
      
      await expect(
        reviewService.addReviewResponse('rev123', 'Test response')
      ).rejects.toThrow('Response Error')
    })

    it('propagates API errors for getResponseSuggestions', async () => {
      const error = new Error('Suggestion Error')
      vi.mocked(apiClient.get).mockRejectedValue(error)
      
      await expect(
        reviewService.getResponseSuggestions('rev123')
      ).rejects.toThrow('Suggestion Error')
    })
  })
})