import { describe, it, expect, vi } from 'vitest'
import { setupI18n, setI18nLanguage, SUPPORT_LOCALES } from '@/i18n'

// Mock document
Object.defineProperty(document, 'querySelector', {
  value: vi.fn(() => ({
    setAttribute: vi.fn()
  })),
  writable: true
})

describe('i18n Configuration', () => {
  it('creates i18n instance with default locale', () => {
    const i18n = setupI18n()
    
    expect(i18n.global.locale.value).toBe('en')
    expect(i18n.global.fallbackLocale.value).toBe('en')
  })

  it('creates i18n instance with custom locale', () => {
    const i18n = setupI18n({ locale: 'de' })
    
    expect(i18n.global.locale.value).toBe('de')
  })

  it('has all supported locales', () => {
    expect(SUPPORT_LOCALES).toEqual(['en', 'de', 'tr', 'ar'])
  })

  it('sets language and updates document attributes', () => {
    const mockSetAttribute = vi.fn()
    const mockQuerySelector = vi.fn(() => ({
      setAttribute: mockSetAttribute
    }))
    
    document.querySelector = mockQuerySelector
    
    const i18n = setupI18n()
    setI18nLanguage(i18n, 'ar')
    
    expect(i18n.global.locale.value).toBe('ar')
    expect(mockQuerySelector).toHaveBeenCalledWith('html')
    expect(mockSetAttribute).toHaveBeenCalledWith('lang', 'ar')
    expect(mockSetAttribute).toHaveBeenCalledWith('dir', 'rtl')
  })

  it('sets LTR direction for non-Arabic languages', () => {
    const mockSetAttribute = vi.fn()
    const mockQuerySelector = vi.fn(() => ({
      setAttribute: mockSetAttribute
    }))
    
    document.querySelector = mockQuerySelector
    
    const i18n = setupI18n()
    setI18nLanguage(i18n, 'de')
    
    expect(mockSetAttribute).toHaveBeenCalledWith('dir', 'ltr')
  })

  it('loads message files correctly', () => {
    const i18n = setupI18n()
    
    // Check that messages are loaded for all locales
    expect(i18n.global.messages.value.en).toBeDefined()
    expect(i18n.global.messages.value.de).toBeDefined()
    expect(i18n.global.messages.value.tr).toBeDefined()
    expect(i18n.global.messages.value.ar).toBeDefined()
  })

  it('has common translation keys in all locales', () => {
    const i18n = setupI18n()
    const messages = i18n.global.messages.value
    
    SUPPORT_LOCALES.forEach(locale => {
      expect(messages[locale].common).toBeDefined()
      expect(messages[locale].auth).toBeDefined()
      expect(messages[locale].navigation).toBeDefined()
    })
  })
})