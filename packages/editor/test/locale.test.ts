import { describe, it, expect, beforeEach, vi } from "vitest";

vi.mock("svelte-i18n", () => ({
  locale: { set: vi.fn() },
}));

import { locale as i18nLocale } from "svelte-i18n";
import { getStoredLocale, setLocale } from "../src/lib/locale";

beforeEach(() => {
  localStorage.clear();
  vi.mocked(i18nLocale.set).mockClear();
});

describe("locale", () => {
  it("defaults to en when nothing is stored and the browser is not French", () => {
    Object.defineProperty(navigator, "language", { value: "en-US", configurable: true });
    expect(getStoredLocale()).toBe("en");
  });

  it("defaults to fr when nothing is stored and the browser is French", () => {
    Object.defineProperty(navigator, "language", { value: "fr-FR", configurable: true });
    expect(getStoredLocale()).toBe("fr");
  });

  it("returns the stored locale when present, ignoring the browser language", () => {
    Object.defineProperty(navigator, "language", { value: "fr-FR", configurable: true });
    localStorage.setItem("myhome-locale", "en");
    expect(getStoredLocale()).toBe("en");
  });

  it("ignores an invalid stored value and falls back to detection", () => {
    localStorage.setItem("myhome-locale", "de");
    Object.defineProperty(navigator, "language", { value: "en-US", configurable: true });
    expect(getStoredLocale()).toBe("en");
  });

  it("setLocale persists to localStorage and calls svelte-i18n's locale.set", () => {
    setLocale("fr");
    expect(localStorage.getItem("myhome-locale")).toBe("fr");
    expect(i18nLocale.set).toHaveBeenCalledWith("fr");
  });
});
