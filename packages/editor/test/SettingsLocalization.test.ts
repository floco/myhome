import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import { locale as i18nLocale, waitLocale } from "svelte-i18n";
import SettingsLocalization from "../src/lib/components/settings/SettingsLocalization.svelte";

describe("SettingsLocalization", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(async () => {
    target.remove();
    i18nLocale.set("en");
    await waitLocale();
  });

  it("renders all four fields with the mockup copy", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Customize language, date format, and regional preferences for your account.");
    expect(target.textContent).toContain("Select your preferred language");
    expect(target.textContent).toContain("Choose how dates should be displayed throughout the application");
    expect(target.textContent).toContain("Select 12-hour or 24-hour time format");
    expect(target.textContent).toContain("Select which day starts your week");
    unmount(app);
  });

  it("shows the default English date/time preview", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    expect(target.textContent).toContain("Preview: 01/15/2024");
    expect(target.textContent).toContain("Preview: 2:30 PM");
    unmount(app);
  });

  it("changing the language select persists the locale", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    const select = target.querySelector(".lang-select") as HTMLSelectElement;
    expect(select.value).toBe("en");
    select.value = "fr";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(localStorage.getItem("myhome-locale")).toBe("fr");
    unmount(app);
  });

  it("changing the date format select persists the override and updates the preview", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    const select = target.querySelector(".dateformat-select") as HTMLSelectElement;
    select.value = "ISO";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(localStorage.getItem("myhome-localization")).toContain('"dateFormat":"ISO"');
    expect(target.textContent).toContain("Preview: 2024-01-15");
    unmount(app);
  });

  it("changing the time format select persists the override and updates the preview", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    const select = target.querySelector(".timeformat-select") as HTMLSelectElement;
    select.value = "24h";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(localStorage.getItem("myhome-localization")).toContain('"timeFormat":"24h"');
    expect(target.textContent).toContain("Preview: 14:30");
    unmount(app);
  });

  it("changing the first-day-of-week select persists the override", () => {
    const app = mount(SettingsLocalization, { target, props: {} });
    flushSync();
    const select = target.querySelector(".weekstart-select") as HTMLSelectElement;
    select.value = "1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(localStorage.getItem("myhome-localization")).toContain('"weekStart":1');
    unmount(app);
  });
});
