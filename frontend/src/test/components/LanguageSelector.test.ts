import { describe, it, expect, beforeEach, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createI18n } from 'vue-i18n'
import LanguageSelector from '@/components/common/LanguageSelector.vue'

const i18n = createI18n({
  legacy: false,
  locale: 'en',
  messages: {
    en: { test: 'test' },
    de: { test: 'test' },
    tr: { test: 'test' },
    ar: { test: 'test' }
  }
})

describe('LanguageSelector', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders current language correctly', () => {
    const wrapper = mount(LanguageSelector, {
      global: {
        plugins: [i18n]
      }
    })

    expect(wrapper.find('button').exists()).toBe(true)
    expect(wrapper.text()).toContain('English')
  })

  it('shows language options when clicked', async () => {
    const wrapper = mount(LanguageSelector, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('button').trigger('click')
    
    const options = wrapper.findAll('button')
    expect(options.length).toBeGreaterThan(1)
  })

  it('changes language when option is selected', async () => {
    const wrapper = mount(LanguageSelector, {
      global: {
        plugins: [i18n]
      }
    })

    await wrapper.find('button').trigger('click')
    
    const germanOption = wrapper.findAll('button').find(btn => 
      btn.text().includes('Deutsch')
    )
    
    if (germanOption) {
      await germanOption.trigger('click')
      expect(i18n.global.locale.value).toBe('de')
    }
  })

  it('saves language preference to localStorage', async () => {
    // Mock localStorage
    const mockSetItem = vi.fn()
    Object.defineProperty(window, 'localStorage', {
      value: {
        setItem: mockSetItem,
        getItem: vi.fn(),
        removeItem: vi.fn()
      },
      writable: true
    })
    
    const wrapper = mount(LanguageSelector, {
      global: {
        plugins: [i18n]
      }
    })

    // Wait for component to mount
    await wrapper.vm.$nextTick()
    
    // Test the changeLanguage method directly
    wrapper.vm.changeLanguage('de')
    
    expect(mockSetItem).toHaveBeenCalledWith('preferred-language', 'de')
  })
})