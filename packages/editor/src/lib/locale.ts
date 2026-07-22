import { locale as i18nLocale } from "svelte-i18n";

/** Supported UI locales. */
export type Locale = "en" | "fr";

const STORAGE_KEY = "myhome-locale";

/** Reads the persisted locale from localStorage, falling back to browser-language
 *  detection (French if navigator.language starts with "fr", else English). */
export function getStoredLocale(): Locale {
  const stored = localStorage.getItem(STORAGE_KEY);
  if (stored === "en" || stored === "fr") return stored;
  return navigator.language.toLowerCase().startsWith("fr") ? "fr" : "en";
}

/** Persists the locale to localStorage and applies it via svelte-i18n. */
export function setLocale(locale: Locale): void {
  localStorage.setItem(STORAGE_KEY, locale);
  i18nLocale.set(locale);
}
