import { createI18n } from 'vue-i18n'
import en from './locales/en.json'
import de from './locales/de.json'
import tr from './locales/tr.json'
import ar from './locales/ar.json'

export type MessageLanguages = keyof typeof en

export const SUPPORT_LOCALES = ['en', 'de', 'tr', 'ar']

export function setupI18n(options: { locale?: string } = {}) {
  const i18n = createI18n({
    legacy: false,
    locale: options.locale || 'en',
    fallbackLocale: 'en',
    messages: {
      en,
      de,
      tr,
      ar
    }
  })
  return i18n
}

export function setI18nLanguage(i18n: any, locale: string) {
  if (i18n.mode === 'legacy') {
    i18n.global.locale = locale
  } else {
    i18n.global.locale.value = locale
  }
  document.querySelector('html')?.setAttribute('lang', locale)
  document.querySelector('html')?.setAttribute('dir', locale === 'ar' ? 'rtl' : 'ltr')
}