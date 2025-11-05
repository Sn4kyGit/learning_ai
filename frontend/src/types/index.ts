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
  id: string
  role: 'user' | 'assistant'
  content: string
  timestamp: string
  business_id?: string
}

export interface ChatResponse {
  message: string
  suggestions?: string[]
  data?: any
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

// Utility Types
export type DeepPartial<T> = {
  [P in keyof T]?: T[P] extends object ? DeepPartial<T[P]> : T[P]
}

export type Optional<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>

export type RequiredFields<T, K extends keyof T> = T & Required<Pick<T, K>>