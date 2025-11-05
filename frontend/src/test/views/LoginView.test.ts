import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import LoginView from '@/views/auth/LoginView.vue'
import { useAuthStore } from '@/stores/auth'

// Mock router
const mockPush = vi.fn()
vi.mock('vue-router', () => ({
  useRouter: () => ({
    push: mockPush
  })
}))

// Mock stores
vi.mock('@/stores/auth')
vi.mock('@/stores/notifications', () => ({
  useNotificationsStore: () => ({
    showSuccess: vi.fn(),
    showError: vi.fn()
  })
}))

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: {
      'auth.loginTitle': 'Sign in to your account',
      'auth.loginSubtitle': 'Welcome back! Please sign in to continue.',
      'auth.email': 'Email',
      'auth.password': 'Password',
      'auth.rememberMe': 'Remember me',
      'auth.forgotPassword': 'Forgot Password?',
      'auth.signIn': 'Sign in',
      'auth.dontHaveAccount': "Don't have an account?",
      'auth.signUp': 'Sign up',
      'common.loading': 'Loading...',
      'auth.emailRequired': 'Email is required',
      'auth.passwordRequired': 'Password is required',
      'auth.invalidEmail': 'Please enter a valid email address'
    }
  }
})

describe('LoginView', () => {
  let mockAuthStore: any

  beforeEach(() => {
    setActivePinia(createPinia())
    vi.clearAllMocks()
    
    mockAuthStore = {
      login: vi.fn(),
      loading: false,
      error: null
    }
    
    vi.mocked(useAuthStore).mockReturnValue(mockAuthStore)
  })

  it('renders login form correctly', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    expect(wrapper.find('h2').text()).toBe('Sign in to your account')
    expect(wrapper.find('input[type="email"]').exists()).toBe(true)
    expect(wrapper.find('input[type="password"]').exists()).toBe(true)
    expect(wrapper.find('input[type="checkbox"]').exists()).toBe(true)
    expect(wrapper.find('button[type="submit"]').exists()).toBe(true)
  })

  it('validates required fields', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Email is required')
    expect(wrapper.text()).toContain('Password is required')
    expect(mockAuthStore.login).not.toHaveBeenCalled()
  })

  it('validates email format', async () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('input[type="email"]').setValue('invalid-email')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit.prevent')

    expect(wrapper.text()).toContain('Please enter a valid email address')
    expect(mockAuthStore.login).not.toHaveBeenCalled()
  })

  it('submits form with valid data', async () => {
    mockAuthStore.login.mockResolvedValue({})
    
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('input[type="checkbox"]').setChecked(true)
    await wrapper.find('form').trigger('submit.prevent')

    expect(mockAuthStore.login).toHaveBeenCalledWith({
      email: 'test@example.com',
      password: 'password123',
      remember_me: true
    })
  })

  it('handles login success', async () => {
    mockAuthStore.login.mockResolvedValue({})
    
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('password123')
    await wrapper.find('form').trigger('submit.prevent')

    await wrapper.vm.$nextTick()

    expect(mockPush).toHaveBeenCalledWith('/dashboard')
  })

  it('handles login error', async () => {
    const errorMessage = 'Invalid credentials'
    mockAuthStore.login.mockRejectedValue({ 
      response: { status: 401 },
      message: errorMessage 
    })
    
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('input[type="email"]').setValue('test@example.com')
    await wrapper.find('input[type="password"]').setValue('wrongpassword')
    await wrapper.find('form').trigger('submit.prevent')

    await wrapper.vm.$nextTick()

    expect(wrapper.text()).toContain('Invalid email or password')
  })

  it('shows loading state during submission', async () => {
    mockAuthStore.loading = true
    
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    const submitButton = wrapper.find('button[type="submit"]')
    expect(submitButton.text()).toContain('Loading...')
    expect(submitButton.attributes('disabled')).toBeDefined()
  })

  it('has links to register and forgot password', () => {
    const wrapper = mount(LoginView, {
      global: {
        plugins: [i18n]
      }
    })

    expect(wrapper.find('a[href="/register"]').exists()).toBe(true)
    expect(wrapper.find('a[href="/forgot-password"]').exists()).toBe(true)
  })
})