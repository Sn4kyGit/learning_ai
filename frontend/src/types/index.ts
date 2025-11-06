// User and Authentication Types
export interface User {
  id: string
  email: string
  name: string
  role: UserRole
  language_preference: string
  organization_id?: string
  created_at: string
  last_login?: string
}

export type UserRole = 'super_admin' | 'admin' | 'viewer'

export interface LoginCredentials {
  email: string
  password: string
  remember_me?: boolean
}

export interface RegisterData {
  email: string
  password: string
  name: string
  language_preference?: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: User
}

// Business Types
export interface Business {
  id: string
  name: string
  google_place_id: string
  category: string
  address: string
  organization_id?: string
  avg_rating: number
  total_reviews: number
  created_at: string
  updated_at: string
}

export interface GooglePlaceSearchResult {
  place_id: string
  name: string
  address: string
  rating?: number
  user_ratings_total?: number
  types: string[]
  geometry: {
    location: {
      lat: number
      lng: number
    }
  }
  photos?: Array<{
    photo_reference: string
    height: number
    width: number
  }>
  price_level?: number
  business_status?: string
}

export interface GooglePlaceDetails extends GooglePlaceSearchResult {
  formatted_address: string
  formatted_phone_number?: string
  international_phone_number?: string
  website?: string
  opening_hours?: {
    open_now: boolean
    periods: Array<{
      close: { day: number; time: string }
      open: { day: number; time: string }
    }>
    weekday_text: string[]
  }
  reviews?: Array<{
    author_name: string
    author_url: string
    language: string
    profile_photo_url: string
    rating: number
    relative_time_description: string
    text: string
    time: number
  }>
}

export interface GooglePlacesSearchResponse {
  results: GooglePlaceSearchResult[]
  query: string
  location?: string
  radius: number
}

export interface BusinessFormData {
  name: string
  google_place_id: string
  category: string
  address: string
  organization_id?: string
}

export interface ImportStatus {
  business_id: string
  status: 'idle' | 'in_progress' | 'completed' | 'failed' | 'error'
  last_import?: string
  total_imported: number
  last_import_count: number
  next_scheduled_import?: string
  import_errors: string[]
  import_history?: ImportHistoryEntry[]
  is_active: boolean
  current_step?: string
  progress?: {
    processed: number
    imported: number
    duplicates: number
    total_expected: number
  }
  started_at?: string
  estimated_completion?: string
}

export interface ImportHistoryEntry {
  timestamp: string
  imported_count: number
  source: string
  errors: string[]
  status: 'completed' | 'failed'
}

export interface RealTimeImportStatus {
  is_active: boolean
  status: 'idle' | 'in_progress' | 'completed' | 'failed'
  current_step: string
  progress_percent: number
  processed: number
  imported: number
  duplicates: number
  total_expected: number
  started_at?: string
  errors: string[]
  estimated_completion?: string
}

// Review Types
export interface Review {
  id: string
  business_id: string
  author_name: string
  rating: number
  text: string
  language: string
  published_at: string
  source: string
  created_at: string
  classification?: Classification
}

export interface Classification {
  id: string
  review_id: string
  sentiment: 'positive' | 'negative' | 'neutral'
  topics: string[]
  urgency: 'low' | 'medium' | 'high'
  competitor_mentioned: boolean
  confidence_score: number
  ai_model: string
  processing_time_ms: number
  created_at: string
}

// Analytics Types
export interface DashboardMetrics {
  business_id: string
  date: string
  avg_rating: number
  sentiment_positive: number
  sentiment_neutral: number
  sentiment_negative: number
  review_count: number
  top_topics: string[]
  competitor_mentions: number
  response_rate: number
  avg_response_time_hours: number
}

export interface TrendData {
  date: string
  value: number
  label?: string
}

export interface SentimentDistribution {
  positive: number
  neutral: number
  negative: number
}

// Chat Types
export interface ChatMessage {
  message_id: string
  role: 'user' | 'assistant'
  content: string
  created_at: string
  language: string
  cost_info?: {
    tokens: number
    cost: number
  }
}

export interface Conversation {
  conversation_id: string
  business_id: string
  message_count: number
  last_message_at: string
  created_at: string
}

export interface ConversationMessages {
  conversation_id: string
  business_id: string
  messages: ChatMessage[]
}

export interface ChatResponse {
  response: string
  conversation_id: string
  message_id: string
  language: string
  cost_info?: {
    tokens: number
    cost: number
  }
}

export interface ChatUsageStats {
  total_conversations: number
  total_messages: number
  avg_messages_per_conversation: number
  total_cost: number
}

export interface BusinessContextSummary {
  context_summary: any
}

// Notification Types
export interface Notification {
  id: string | number
  type: 'success' | 'error' | 'warning' | 'info' | 'critical_review' | 'competitor_mention'
  title?: string
  message: string
  severity: 'low' | 'medium' | 'high'
  read: boolean
  timestamp: Date
  autoClose?: boolean
  duration?: number
  data?: any
}

// API Types
export interface ApiError {
  message: string
  code?: string
  details?: any
}

export interface ApiResponse<T = any> {
  data: T
  message?: string
  success: boolean
}

export interface PaginatedResponse<T> {
  data: T[]
  total: number
  page: number
  per_page: number
  total_pages: number
}

// Form Types
export interface FormField {
  name: string
  label: string
  type: 'text' | 'email' | 'password' | 'select' | 'textarea' | 'checkbox'
  required?: boolean
  placeholder?: string
  options?: { value: string; label: string }[]
  validation?: {
    min?: number
    max?: number
    pattern?: RegExp
    message?: string
  }
}

// Language Types
export type SupportedLanguage = 'en' | 'de' | 'tr' | 'ar'

export interface LanguageOption {
  code: SupportedLanguage
  name: string
  nativeName: string
  flag: string
}

// Settings Types
export interface UserSettings {
  language: SupportedLanguage
  email_notifications: boolean
  sms_notifications: boolean
  critical_alerts: boolean
  weekly_reports: boolean
  competitor_mentions: boolean
}

export interface BusinessSettings {
  name: string
  address: string
  google_place_id: string
  notification_preferences: NotificationPreferences
}

export interface NotificationPreferences {
  email: boolean
  sms: boolean
  critical_threshold: number
  weekly_report_day: number
  weekly_report_email: boolean
}

// Route Types
export interface RouteConfig {
  path: string
  name: string
  component: any
  meta?: {
    requiresAuth?: boolean
    roles?: UserRole[]
    title?: string
  }
}

// Component Props Types
export interface BaseComponentProps {
  loading?: boolean
  disabled?: boolean
  variant?: 'primary' | 'secondary' | 'success' | 'warning' | 'error'
  size?: 'sm' | 'md' | 'lg'
}

export interface ButtonProps extends BaseComponentProps {
  type?: 'button' | 'submit' | 'reset'
  fullWidth?: boolean
  icon?: string
}

export interface InputProps extends BaseComponentProps {
  modelValue?: string | number
  placeholder?: string
  type?: string
  required?: boolean
  error?: string
}

// Store Types
export interface AuthState {
  user: User | null
  token: string | null
  loading: boolean
  error: string | null
}

export interface BusinessState {
  businesses: Business[]
  currentBusiness: Business | null
  loading: boolean
  error: string | null
}

export interface NotificationState {
  notifications: Notification[]
  unreadCount: number
}

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

// User Management Types
export interface UserBusinessAccess {
  user: User
  permission_level: 'read_only' | 'full_access'
}

export interface OrganizationUser {
  id: string
  email: string
  name: string
  role: UserRole
  language_preference: string
  organization_id?: string
  created_at: string
  last_login?: string
}

export interface BulkAccessRequest {
  user_ids: string[]
  business_id: string
  permission_level: 'read_only' | 'full_access'
}

// Notification Configuration Types
export interface NotificationPreferences {
  user_id: string
  business_id?: string
  email_enabled: boolean
  sms_enabled: boolean
  push_enabled: boolean
  email_address?: string
  phone_number?: string
  notification_channels: string[]
  created_at: string
  updated_at: string
}

export interface NotificationPreferencesRequest {
  email_enabled: boolean
  sms_enabled: boolean
  push_enabled: boolean
  email_address?: string
  phone_number?: string
  notification_channels: string[]
}

export interface AlertThresholds {
  business_id: string
  critical_rating_threshold: number
  sentiment_drop_threshold: number
  competitor_mention_alerts: boolean
  crisis_mode_threshold: number
  alert_frequency_limit: number
  created_at: string
  updated_at: string
}

export interface AlertThresholdsRequest {
  critical_rating_threshold: number
  sentiment_drop_threshold: number
  competitor_mention_alerts: boolean
  crisis_mode_threshold: number
  alert_frequency_limit: number
}

export interface NotificationHistory {
  notification_id: string
  business_id: string
  alert_type: string
  channel: string
  recipient: string
  status: string
  sent_at: string
  delivered_at?: string
  error_message?: string
}

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>