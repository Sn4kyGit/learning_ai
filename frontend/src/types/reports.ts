// Report Types
export interface ReportConfiguration {
  business_id: string
  report_day: number // 1=Monday, 7=Sunday
  delivery_method: 'web_only' | 'web_and_email'
  language: string
  include_sections: string[]
  next_report_date: string
  created_at: string
  updated_at: string
}

export interface ReportConfigurationRequest {
  report_day: number
  delivery_method: 'web_only' | 'web_and_email'
  language: string
  include_sections: string[]
}

export interface WeeklyReport {
  report_id: string
  business_id: string
  report_period_start: string
  report_period_end: string
  language: string
  sections: Record<string, any>
  action_items: string[]
  cost_summary: Record<string, any>
  generated_at: string
}

export interface CustomReportRequest {
  start_date: string
  end_date: string
  report_type: 'sentiment' | 'topics' | 'trends' | 'comprehensive'
  language: string
  include_recommendations: boolean
}

export interface CustomReport {
  business_id: string
  report_type: string
  period_start: string
  period_end: string
  language: string
  report_data: Record<string, any>
  recommendations: string[]
  cost_info: Record<string, any>
  generated_at: string
}

export interface ReportHistory {
  report_id: string
  report_type: 'weekly' | 'custom'
  generated_at: string
  period_start: string
  period_end: string
  language: string
  status: 'completed' | 'failed' | 'generating'
}

export interface ReportSection {
  id: string
  name: string
  description: string
  enabled: boolean
}

export const AVAILABLE_REPORT_SECTIONS: ReportSection[] = [
  {
    id: 'sentiment_analysis',
    name: 'Sentiment Analysis',
    description: 'Overall sentiment trends and distribution',
    enabled: true
  },
  {
    id: 'top_topics',
    name: 'Top Topics',
    description: 'Most frequently mentioned topics in reviews',
    enabled: true
  },
  {
    id: 'competitor_mentions',
    name: 'Competitor Mentions',
    description: 'Reviews mentioning competitors',
    enabled: true
  },
  {
    id: 'action_items',
    name: 'Action Items',
    description: 'AI-generated recommendations and action items',
    enabled: true
  },
  {
    id: 'rating_trends',
    name: 'Rating Trends',
    description: 'Rating changes over time',
    enabled: false
  },
  {
    id: 'response_metrics',
    name: 'Response Metrics',
    description: 'Review response rates and times',
    enabled: false
  }
]

export const DAYS_OF_WEEK = [
  { value: 1, label: 'Monday' },
  { value: 2, label: 'Tuesday' },
  { value: 3, label: 'Wednesday' },
  { value: 4, label: 'Thursday' },
  { value: 5, label: 'Friday' },
  { value: 6, label: 'Saturday' },
  { value: 7, label: 'Sunday' }
]

export const DELIVERY_METHODS = [
  { value: 'web_only', label: 'Web Only' },
  { value: 'web_and_email', label: 'Web + Email' }
]

export const REPORT_TYPES = [
  { value: 'sentiment', label: 'Sentiment Analysis' },
  { value: 'topics', label: 'Topic Analysis' },
  { value: 'trends', label: 'Trend Analysis' },
  { value: 'comprehensive', label: 'Comprehensive Report' }
]