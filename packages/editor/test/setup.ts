// Polyfill ResizeObserver for jsdom environment
(globalThis as any).ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

// Polyfill matchMedia for jsdom (used by App.svelte's mobile-viewport check)
(globalThis as any).matchMedia = (globalThis as any).matchMedia || function (query: string) {
  return {
    matches: false,
    media: query,
    addEventListener: () => {},
    removeEventListener: () => {},
  };
};

import { addMessages, init } from "svelte-i18n";
import en from "../src/lib/locales/en.json";
import fr from "../src/lib/locales/fr.json";

// addMessages populates the dictionary synchronously (unlike register(), which
// queues an async loader) so init()'s locale.set() below resolves synchronously
// too -- no waitLocale()/race to worry about in tests.
addMessages("en", en);
addMessages("fr", fr);
init({ fallbackLocale: "en", initialLocale: "en" });
