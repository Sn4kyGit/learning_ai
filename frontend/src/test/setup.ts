import { vi } from 'vitest'
import { config } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'

// Mock i18n
const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: {
      'auth.login': 'Login',
      'auth.register': 'Register',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.loginTitle': 'Sign in to your account',
      'auth.loginSubtitle': 'Welcome back! Please sign in to continue.',
      'auth.rememberMe': 'Remember me',
      'auth.forgotPassword': 'Forgot Password?',
      'auth.signIn': 'Sign in',
      'auth.signUp': 'Sign up',
      'auth.dontHaveAccount': "Don't have an account?",
      'auth.emailRequired': 'Email is required',
      'auth.passwordRequired': 'Password is required',
      'auth.invalidEmail': 'Please enter a valid email address',
      'auth.loginError': 'Invalid email or password',
      'auth.loginSuccess': 'Login successful',
      'common.loading': 'Loading...',
      'common.save': 'Save',
      'common.cancel': 'Cancel',
      'home.title': 'Local Business Intelligence Bot',
      'navigation.dashboard': 'Dashboard'
    }
  }
})

// Global test configuration
config.global.plugins = [i18n]
config.global.stubs = {
  'router-link': {
    template: '<a><slot /></a>',
    props: ['to']
  }
}

// Mock localStorage with proper implementation
const localStorageMock = {
  store: {} as Record<string, string>,
  getItem: vi.fn((key: string) => localStorageMock.store[key] || null),
  setItem: vi.fn((key: string, value: string) => {
    localStorageMock.store[key] = value
  }),
  removeItem: vi.fn((key: string) => {
    delete localStorageMock.store[key]
  }),
  clear: vi.fn(() => {
    localStorageMock.store = {}
  }),
}

Object.defineProperty(window, 'localStorage', {
  value: localStorageMock,
  writable: true,
})

// Mock fetch
global.fetch = vi.fn()

// Mock router
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: vi.fn(),
    replace: vi.fn(),
    go: vi.fn(),
    back: vi.fn(),
    forward: vi.fn(),
  }),
  useRoute: () => ({
    path: '/',
    params: {},
    query: {},
    meta: {},
  }),
}))