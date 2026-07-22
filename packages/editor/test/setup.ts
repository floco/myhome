// Polyfill ResizeObserver for jsdom environment
(globalThis as any).ResizeObserver = class ResizeObserver {
  constructor(_callback: ResizeObserverCallback) {}
  observe() {}
  unobserve() {}
  disconnect() {}
};

import { register, init, waitLocale } from "svelte-i18n";
import en from "../src/lib/locales/en.json";
import fr from "../src/lib/locales/fr.json";

register("en", () => Promise.resolve({ default: en }));
register("fr", () => Promise.resolve({ default: fr }));
init({ fallbackLocale: "en", initialLocale: "en" });
await waitLocale();
