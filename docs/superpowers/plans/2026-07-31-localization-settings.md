# Localization Settings Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a "Localization" settings category (right after "General") with Language (moved from General), Date Format, Time Format, and First Day of Week — and make those preferences actually change how dates/times render throughout the app.

**Architecture:** Two new client-side-only modules (`lib/localization.ts` for storage/defaults, `lib/dateFormat.ts` for shared formatting) sit alongside the existing `lib/locale.ts`. A new `SettingsLocalization.svelte` panel is registered in `SettingsPage.svelte` right after General. `DatePicker.svelte`'s calendar grid is rewired to honor the week-start preference. ~13 existing components/modules that currently roll their own `toLocaleDateString`/`toLocaleString` calls are rewired to the shared formatter.

**Tech Stack:** Svelte 5 (runes), TypeScript, svelte-i18n, Vitest.

## Global Constraints

- All four preferences (language, date format, time format, first day of week) are stored client-side in `localStorage` only — no backend/API changes.
- Date format / time format / week-start default to a value derived from the current language (English → MDY/12h/Sunday, French → DMY/24h/Monday) until the user explicitly overrides that specific field; an explicit override survives later language changes.
- Shared formatters return `"—"` for null/undefined/empty-string/invalid-date input.
- Run tests from `packages/editor/` with `npx vitest run <path>` (or `npm test` for the whole suite).
- Commit after each task.
- **Deviation from the design doc's rewiring list:** `ScheduleEditor.svelte`'s `Intl.DateTimeFormat` call only generates *month names* for its restrict-to-months toggle buttons (e.g. "January", "February", …) — it has no weekday grid and never renders an actual date *value*. It's already correctly locale-aware via `$locale`, and none of the four Date Format patterns (MDY/DMY/ISO/LONG) apply to "list of month names for a button row." It is intentionally left untouched by this plan.

---

### Task 1: `localization.ts` — storage & defaults module

**Files:**
- Create: `packages/editor/src/lib/localization.ts`
- Test: `packages/editor/test/localization.test.ts`

**Interfaces:**
- Consumes: `getStoredLocale` from `packages/editor/src/lib/locale.ts` (existing, returns `"en" | "fr"`).
- Produces (used by Task 2 and Task 3):
  - `type DateFormat = "MDY" | "DMY" | "ISO" | "LONG"`
  - `type TimeFormat = "12h" | "24h"`
  - `type WeekStart = 0 | 1 | 6`
  - `getDateFormat(): DateFormat`, `setDateFormat(format: DateFormat): void`
  - `getTimeFormat(): TimeFormat`, `setTimeFormat(format: TimeFormat): void`
  - `getWeekStart(): WeekStart`, `setWeekStart(weekStart: WeekStart): void`

- [ ] **Step 1: Write the failing tests**

```typescript
// packages/editor/test/localization.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import {
  getDateFormat, setDateFormat,
  getTimeFormat, setTimeFormat,
  getWeekStart, setWeekStart,
} from "../src/lib/localization";

beforeEach(() => {
  localStorage.clear();
});

describe("localization defaults (derived from language)", () => {
  it("defaults to MDY/12h/Sunday for English", () => {
    localStorage.setItem("myhome-locale", "en");
    expect(getDateFormat()).toBe("MDY");
    expect(getTimeFormat()).toBe("12h");
    expect(getWeekStart()).toBe(0);
  });

  it("defaults to DMY/24h/Monday for French", () => {
    localStorage.setItem("myhome-locale", "fr");
    expect(getDateFormat()).toBe("DMY");
    expect(getTimeFormat()).toBe("24h");
    expect(getWeekStart()).toBe(1);
  });
});

describe("localization explicit overrides", () => {
  it("setDateFormat persists an override that getDateFormat returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("ISO");
    expect(getDateFormat()).toBe("ISO");
  });

  it("setTimeFormat persists an override that getTimeFormat returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setTimeFormat("24h");
    expect(getTimeFormat()).toBe("24h");
  });

  it("setWeekStart persists an override that getWeekStart returns", () => {
    localStorage.setItem("myhome-locale", "en");
    setWeekStart(6);
    expect(getWeekStart()).toBe(6);
  });

  it("an explicit override survives a later language change", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("DMY");
    localStorage.setItem("myhome-locale", "fr");
    expect(getDateFormat()).toBe("DMY");
    // timeFormat was never overridden, so it still follows the new language
    expect(getTimeFormat()).toBe("24h");
  });

  it("setting one field does not clobber the others", () => {
    localStorage.setItem("myhome-locale", "en");
    setDateFormat("ISO");
    setWeekStart(1);
    expect(getDateFormat()).toBe("ISO");
    expect(getWeekStart()).toBe(1);
    expect(getTimeFormat()).toBe("12h");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/localization.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/localization'`

- [ ] **Step 3: Write the implementation**

```typescript
// packages/editor/src/lib/localization.ts
import { getStoredLocale } from "./locale";

export type DateFormat = "MDY" | "DMY" | "ISO" | "LONG";
export type TimeFormat = "12h" | "24h";
export type WeekStart = 0 | 1 | 6;

const STORAGE_KEY = "myhome-localization";

interface LocalizationOverrides {
  dateFormat: DateFormat | null;
  timeFormat: TimeFormat | null;
  weekStart: WeekStart | null;
}

const EMPTY_OVERRIDES: LocalizationOverrides = { dateFormat: null, timeFormat: null, weekStart: null };

const LANGUAGE_DEFAULTS: Record<"en" | "fr", { dateFormat: DateFormat; timeFormat: TimeFormat; weekStart: WeekStart }> = {
  en: { dateFormat: "MDY", timeFormat: "12h", weekStart: 0 },
  fr: { dateFormat: "DMY", timeFormat: "24h", weekStart: 1 },
};

function readOverrides(): LocalizationOverrides {
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return { ...EMPTY_OVERRIDES };
  try {
    const parsed = JSON.parse(raw) as Partial<LocalizationOverrides>;
    return {
      dateFormat: parsed.dateFormat ?? null,
      timeFormat: parsed.timeFormat ?? null,
      weekStart: parsed.weekStart ?? null,
    };
  } catch {
    return { ...EMPTY_OVERRIDES };
  }
}

function writeOverrides(overrides: LocalizationOverrides): void {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(overrides));
}

function languageDefaults() {
  return LANGUAGE_DEFAULTS[getStoredLocale()];
}

export function getDateFormat(): DateFormat {
  return readOverrides().dateFormat ?? languageDefaults().dateFormat;
}

export function setDateFormat(format: DateFormat): void {
  writeOverrides({ ...readOverrides(), dateFormat: format });
}

export function getTimeFormat(): TimeFormat {
  return readOverrides().timeFormat ?? languageDefaults().timeFormat;
}

export function setTimeFormat(format: TimeFormat): void {
  writeOverrides({ ...readOverrides(), timeFormat: format });
}

export function getWeekStart(): WeekStart {
  return readOverrides().weekStart ?? languageDefaults().weekStart;
}

export function setWeekStart(weekStart: WeekStart): void {
  writeOverrides({ ...readOverrides(), weekStart });
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/localization.test.ts`
Expected: PASS (9 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/localization.ts packages/editor/test/localization.test.ts
git commit -m "feat(localization): add date/time format and week-start storage module"
```

---

### Task 2: `dateFormat.ts` — shared date/time formatter

**Files:**
- Create: `packages/editor/src/lib/dateFormat.ts`
- Test: `packages/editor/test/dateFormat.test.ts`

**Interfaces:**
- Consumes: `getDateFormat`, `getTimeFormat`, `type DateFormat`, `type TimeFormat` from `./localization` (Task 1); `getStoredLocale`, `type Locale` from `./locale`.
- Produces (used by Task 3 and Tasks 5-9):
  - `formatDate(value: string | Date | null | undefined): string`
  - `formatTime(value: string | Date | null | undefined): string`
  - `formatDateTime(value: string | Date | null | undefined): string`
  - `formatDateWithOptions(value: string | Date | null | undefined, format: DateFormat, loc: Locale): string` (used by Task 3's live preview)
  - `formatTimeWithOptions(value: string | Date | null | undefined, timeFormat: TimeFormat, loc: Locale): string` (used by Task 3's live preview)

- [ ] **Step 1: Write the failing tests**

```typescript
// packages/editor/test/dateFormat.test.ts
import { describe, it, expect, beforeEach } from "vitest";
import {
  formatDate, formatTime, formatDateTime,
  formatDateWithOptions, formatTimeWithOptions,
} from "../src/lib/dateFormat";

beforeEach(() => {
  localStorage.clear();
  localStorage.setItem("myhome-locale", "en");
});

describe("formatDateWithOptions", () => {
  const d = new Date(2024, 0, 15); // Jan 15 2024

  it("formats MDY", () => {
    expect(formatDateWithOptions(d, "MDY", "en")).toBe("01/15/2024");
  });

  it("formats DMY", () => {
    expect(formatDateWithOptions(d, "DMY", "en")).toBe("15/01/2024");
  });

  it("formats ISO", () => {
    expect(formatDateWithOptions(d, "ISO", "en")).toBe("2024-01-15");
  });

  it("formats LONG in English", () => {
    expect(formatDateWithOptions(d, "LONG", "en")).toBe("January 15, 2024");
  });

  it("formats LONG in French", () => {
    expect(formatDateWithOptions(d, "LONG", "fr")).toBe("15 janvier 2024");
  });

  it("returns em dash for null/undefined/empty/invalid input", () => {
    expect(formatDateWithOptions(null, "MDY", "en")).toBe("—");
    expect(formatDateWithOptions(undefined, "MDY", "en")).toBe("—");
    expect(formatDateWithOptions("", "MDY", "en")).toBe("—");
    expect(formatDateWithOptions("not-a-date", "MDY", "en")).toBe("—");
  });
});

describe("formatTimeWithOptions", () => {
  const d = new Date(2024, 0, 15, 14, 30);

  it("formats 12h", () => {
    expect(formatTimeWithOptions(d, "12h", "en")).toBe("2:30 PM");
  });

  it("formats 24h", () => {
    expect(formatTimeWithOptions(d, "24h", "en")).toBe("14:30");
  });

  it("returns em dash for invalid input", () => {
    expect(formatTimeWithOptions("nope", "12h", "en")).toBe("—");
  });
});

describe("formatDate / formatTime / formatDateTime (read current settings)", () => {
  it("formatDate uses the current locale's derived date format", () => {
    expect(formatDate("2024-01-15T00:00:00")).toBe("01/15/2024");
  });

  it("formatTime uses the current locale's derived time format", () => {
    expect(formatTime("2024-01-15T14:30:00")).toBe("2:30 PM");
  });

  it("formatDateTime composes date and time with a space", () => {
    expect(formatDateTime("2024-01-15T14:30:00")).toBe("01/15/2024 2:30 PM");
  });

  it("formatDate accepts a Date instance directly", () => {
    expect(formatDate(new Date(2024, 0, 15))).toBe("01/15/2024");
  });

  it("respects an explicit override over the language default", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: "ISO", timeFormat: null, weekStart: null }));
    expect(formatDate("2024-01-15T00:00:00")).toBe("2024-01-15");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/dateFormat.test.ts`
Expected: FAIL — `Cannot find module '../src/lib/dateFormat'`

- [ ] **Step 3: Write the implementation**

```typescript
// packages/editor/src/lib/dateFormat.ts
import type { Locale } from "./locale";
import { getStoredLocale } from "./locale";
import type { DateFormat, TimeFormat } from "./localization";
import { getDateFormat, getTimeFormat } from "./localization";

function toDate(value: string | Date | null | undefined): Date | null {
  if (!value) return null;
  const d = value instanceof Date ? value : new Date(value);
  return isNaN(d.getTime()) ? null : d;
}

function pad(n: number): string {
  return String(n).padStart(2, "0");
}

export function formatDateWithOptions(
  value: string | Date | null | undefined,
  format: DateFormat,
  loc: Locale,
): string {
  const d = toDate(value);
  if (!d) return "—";
  const year = d.getFullYear();
  const month = d.getMonth() + 1;
  const day = d.getDate();
  if (format === "MDY") return `${pad(month)}/${pad(day)}/${year}`;
  if (format === "DMY") return `${pad(day)}/${pad(month)}/${year}`;
  if (format === "ISO") return `${year}-${pad(month)}-${pad(day)}`;
  return new Intl.DateTimeFormat(loc, { month: "long", day: "numeric", year: "numeric" }).format(d);
}

export function formatTimeWithOptions(
  value: string | Date | null | undefined,
  timeFormat: TimeFormat,
  loc: Locale,
): string {
  const d = toDate(value);
  if (!d) return "—";
  return new Intl.DateTimeFormat(loc, {
    hour: "numeric",
    minute: "2-digit",
    hour12: timeFormat === "12h",
  }).format(d);
}

export function formatDate(value: string | Date | null | undefined): string {
  return formatDateWithOptions(value, getDateFormat(), getStoredLocale());
}

export function formatTime(value: string | Date | null | undefined): string {
  return formatTimeWithOptions(value, getTimeFormat(), getStoredLocale());
}

export function formatDateTime(value: string | Date | null | undefined): string {
  const d = toDate(value);
  if (!d) return "—";
  return `${formatDate(d)} ${formatTime(d)}`;
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/dateFormat.test.ts`
Expected: PASS (16 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/dateFormat.ts packages/editor/test/dateFormat.test.ts
git commit -m "feat(localization): add shared date/time formatting utility"
```

---

### Task 3: `SettingsLocalization.svelte` panel (standalone, not yet wired into nav)

**Files:**
- Create: `packages/editor/src/lib/components/settings/SettingsLocalization.svelte`
- Test: `packages/editor/test/SettingsLocalization.test.ts`
- Modify: `packages/editor/src/lib/locales/en.json:884` (insert `"localization": "Localization"` after `"general": "General"` in the `settings.nav` block), and add a new `settings.localization` block after the `settings.general` block (after line 919's closing `},`).
- Modify: `packages/editor/src/lib/locales/fr.json` — same two edits, French text.

**Interfaces:**
- Consumes: `getStoredLocale`, `setLocale`, `type Locale` from `../../locale`; `getDateFormat`, `setDateFormat`, `type DateFormat`, `getTimeFormat`, `setTimeFormat`, `type TimeFormat`, `getWeekStart`, `setWeekStart`, `type WeekStart` from `../../localization` (Task 1); `formatDateWithOptions`, `formatTimeWithOptions` from `../../dateFormat` (Task 2); `Card` from `../ui/Card.svelte`.
- Produces: default-exported Svelte component with no props, used standalone in this task and wired into `SettingsPage.svelte` in Task 4.

- [ ] **Step 1: Add the i18n keys**

In `packages/editor/src/lib/locales/en.json`, change line 884 from:
```json
      "general": "General",
```
to:
```json
      "general": "General",
      "localization": "Localization",
```
Then, immediately after the `"general": { ... }` block closes (the `},` currently at line 919, right before `"security": {`), insert a new block:
```json
    "localization": {
      "description": "Customize language, date format, and regional preferences for your account.",
      "language": "Language",
      "languageDescription": "Select your preferred language",
      "dateFormat": "Date Format",
      "dateFormatDescription": "Choose how dates should be displayed throughout the application",
      "timeFormat": "Time Format",
      "timeFormatDescription": "Select 12-hour or 24-hour time format",
      "time12": "12-hour",
      "time24": "24-hour",
      "firstDayOfWeek": "First Day of Week",
      "firstDayOfWeekDescription": "Select which day starts your week",
      "preview": "Preview: {value}",
      "weekday": {
        "sunday": "Sunday",
        "monday": "Monday",
        "saturday": "Saturday"
      }
    },
```
Then remove the now-superseded `"language": "Language",` line from the `"general"` block (line 903) — Language moves to the new `localization` block above.

Apply the equivalent three edits to `packages/editor/src/lib/locales/fr.json`: insert `"localization": "Localisation",` after `"general": "Général",` (line 884), insert the French block after `"general": { ... }` closes:
```json
    "localization": {
      "description": "Personnalisez la langue, le format de date et les préférences régionales de votre compte.",
      "language": "Langue",
      "languageDescription": "Choisissez votre langue préférée",
      "dateFormat": "Format de date",
      "dateFormatDescription": "Choisissez comment les dates doivent s'afficher dans l'application",
      "timeFormat": "Format de l'heure",
      "timeFormatDescription": "Choisissez le format 12 heures ou 24 heures",
      "time12": "12 heures",
      "time24": "24 heures",
      "firstDayOfWeek": "Premier jour de la semaine",
      "firstDayOfWeekDescription": "Choisissez le jour de début de votre semaine",
      "preview": "Aperçu : {value}",
      "weekday": {
        "sunday": "Dimanche",
        "monday": "Lundi",
        "saturday": "Samedi"
      }
    },
```
and remove `"language": "Langue",` (line 903) from the French `"general"` block.

- [ ] **Step 2: Write the failing component test**

```typescript
// packages/editor/test/SettingsLocalization.test.ts
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
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsLocalization.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 4: Write the component**

```svelte
<!-- packages/editor/src/lib/components/settings/SettingsLocalization.svelte -->
<script lang="ts">
  import { _ } from "svelte-i18n";
  import Card from "../ui/Card.svelte";
  import { getStoredLocale, setLocale, type Locale } from "../../locale";
  import {
    getDateFormat, setDateFormat, type DateFormat,
    getTimeFormat, setTimeFormat, type TimeFormat,
    getWeekStart, setWeekStart, type WeekStart,
  } from "../../localization";
  import { formatDateWithOptions, formatTimeWithOptions } from "../../dateFormat";

  let currentLocale = $state<Locale>(getStoredLocale());
  let currentDateFormat = $state<DateFormat>(getDateFormat());
  let currentTimeFormat = $state<TimeFormat>(getTimeFormat());
  let currentWeekStart = $state<WeekStart>(getWeekStart());

  const PREVIEW_DATE = new Date(2024, 0, 15, 14, 30);

  function changeLocale(next: Locale): void {
    currentLocale = next;
    setLocale(next);
  }

  function changeDateFormat(next: DateFormat): void {
    currentDateFormat = next;
    setDateFormat(next);
  }

  function changeTimeFormat(next: TimeFormat): void {
    currentTimeFormat = next;
    setTimeFormat(next);
  }

  function changeWeekStart(next: WeekStart): void {
    currentWeekStart = next;
    setWeekStart(next);
  }

  const datePreview = $derived(formatDateWithOptions(PREVIEW_DATE, currentDateFormat, currentLocale));
  const timePreview = $derived(formatTimeWithOptions(PREVIEW_DATE, currentTimeFormat, currentLocale));
</script>

<Card>
  <div class="section-header">
    <h2>{$_('settings.nav.localization')}</h2>
  </div>
  <p class="section-desc">{$_('settings.localization.description')}</p>

  <div class="loc-field">
    <label class="loc-label" for="loc-language">{$_('settings.localization.language')}</label>
    <p class="loc-field-desc">{$_('settings.localization.languageDescription')}</p>
    <select
      id="loc-language"
      class="loc-select lang-select"
      value={currentLocale}
      onchange={(e) => changeLocale((e.target as HTMLSelectElement).value as Locale)}
    >
      <option value="en">English</option>
      <option value="fr">Français</option>
    </select>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-date-format">{$_('settings.localization.dateFormat')}</label>
    <p class="loc-field-desc">{$_('settings.localization.dateFormatDescription')}</p>
    <select
      id="loc-date-format"
      class="loc-select dateformat-select"
      value={currentDateFormat}
      onchange={(e) => changeDateFormat((e.target as HTMLSelectElement).value as DateFormat)}
    >
      <option value="MDY">MM/DD/YYYY</option>
      <option value="DMY">DD/MM/YYYY</option>
      <option value="ISO">YYYY-MM-DD</option>
      <option value="LONG">Month DD, YYYY</option>
    </select>
    <p class="loc-preview">{$_('settings.localization.preview', { values: { value: datePreview } })}</p>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-time-format">{$_('settings.localization.timeFormat')}</label>
    <p class="loc-field-desc">{$_('settings.localization.timeFormatDescription')}</p>
    <select
      id="loc-time-format"
      class="loc-select timeformat-select"
      value={currentTimeFormat}
      onchange={(e) => changeTimeFormat((e.target as HTMLSelectElement).value as TimeFormat)}
    >
      <option value="12h">{$_('settings.localization.time12')}</option>
      <option value="24h">{$_('settings.localization.time24')}</option>
    </select>
    <p class="loc-preview">{$_('settings.localization.preview', { values: { value: timePreview } })}</p>
  </div>

  <div class="loc-field">
    <label class="loc-label" for="loc-week-start">{$_('settings.localization.firstDayOfWeek')}</label>
    <p class="loc-field-desc">{$_('settings.localization.firstDayOfWeekDescription')}</p>
    <select
      id="loc-week-start"
      class="loc-select weekstart-select"
      value={currentWeekStart}
      onchange={(e) => changeWeekStart(parseInt((e.target as HTMLSelectElement).value, 10) as WeekStart)}
    >
      <option value={0}>{$_('settings.localization.weekday.sunday')}</option>
      <option value={1}>{$_('settings.localization.weekday.monday')}</option>
      <option value={6}>{$_('settings.localization.weekday.saturday')}</option>
    </select>
  </div>
</Card>

<style>
  .section-header { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--space-2); }
  h2 { margin: 0; font-size: 13px; color: var(--text-muted); font-weight: 600; text-transform: uppercase; letter-spacing: .05em; }
  .section-desc { font-size: 13px; color: var(--text-muted); margin: 0 0 16px; }
  .loc-field { padding: 10px 0; border-top: 1px solid var(--border); }
  .loc-field:first-of-type { border-top: none; }
  .loc-label { display: block; font-size: 13px; font-weight: 500; color: var(--text); margin-bottom: 2px; }
  .loc-field-desc { font-size: 12px; color: var(--text-muted); margin: 0 0 8px; }
  .loc-select { font-size: 13px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); }
  .loc-preview { font-size: 12px; color: var(--text-muted); margin: 6px 0 0; }
</style>
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsLocalization.test.ts`
Expected: PASS (6 tests)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsLocalization.svelte packages/editor/test/SettingsLocalization.test.ts packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json
git commit -m "feat(localization): add SettingsLocalization panel with i18n copy"
```

---

### Task 4: Wire into `SettingsPage.svelte`, remove Language from `SettingsGeneral.svelte`

**Files:**
- Modify: `packages/editor/src/lib/components/SettingsPage.svelte:6-14,33-42,66-82`
- Modify: `packages/editor/src/lib/components/settings/SettingsGeneral.svelte:9,16-21,167-176,252`
- Modify: `packages/editor/test/SettingsGeneral.test.ts:93-105` (remove the language test)
- Modify: `packages/editor/test/SettingsPage.test.ts:63-76` (9 groups, add Localization)

**Interfaces:**
- Consumes: `SettingsLocalization` component from Task 3.
- Produces: nothing new — this task only wires existing pieces together.

- [ ] **Step 1: Update `SettingsPage.svelte`'s failing expectations first**

Edit `packages/editor/test/SettingsPage.test.ts`, replacing the test at lines 63-76:
```typescript
  it("shows all 8 groups for an admin, including Integrations, Activity Log, and About", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });
```
with:
```typescript
  it("shows all 9 groups for an admin, including Localization, Integrations, Activity Log, and About", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent);
    expect(labels.some((l) => l?.includes("General"))).toBe(true);
    expect(labels.some((l) => l?.includes("Localization"))).toBe(true);
    expect(labels.some((l) => l?.includes("Categories"))).toBe(true);
    expect(labels.some((l) => l?.includes("Notifications"))).toBe(true);
    expect(labels.some((l) => l?.includes("Security & Access"))).toBe(true);
    expect(labels.some((l) => l?.includes("Integrations"))).toBe(true);
    expect(labels.some((l) => l?.includes("Backup & Restore"))).toBe(true);
    expect(labels.some((l) => l?.includes("Activity Log"))).toBe(true);
    expect(labels.some((l) => l?.includes("About"))).toBe(true);
    unmount(app);
  });

  it("places Localization immediately after General in the nav order", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore("admin"), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const labels = [...target.querySelectorAll(".nav-item")].map((b) => b.textContent?.trim());
    const generalIdx = labels.findIndex((l) => l?.includes("General"));
    expect(labels[generalIdx + 1]).toContain("Localization");
    unmount(app);
  });

  it("switching to Localization via the nav shows the language and date format fields", () => {
    const app = mount(SettingsPage, { target, props: { store: makeStore(), authStore: makeAuthStore(), importFromDonetick: vi.fn(async () => 0) } });
    flushSync();
    const localizationBtn = [...target.querySelectorAll<HTMLButtonElement>(".nav-item")].find((b) => b.textContent?.includes("Localization"))!;
    localizationBtn.click();
    flushSync();
    expect(target.textContent).toContain("Select your preferred language");
    expect(target.textContent).toContain("Choose how dates should be displayed throughout the application");
    unmount(app);
  });
```

Also remove the now-obsolete language test from `packages/editor/test/SettingsGeneral.test.ts` (lines 93-105):
```typescript
  it("changing the language select persists the locale", () => {
    seedHome();
    localStorage.removeItem("myhome-locale");
    const app = mount(SettingsGeneral, { target, props: {} });
    flushSync();
    const select = target.querySelector(".lang-select") as HTMLSelectElement;
    expect(select.value).toBe("en");
    select.value = "fr";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    flushSync();
    expect(localStorage.getItem("myhome-locale")).toBe("fr");
    unmount(app);
  });

```
(delete this whole block — Language now lives in `SettingsLocalization.test.ts`, added in Task 3).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts test/SettingsGeneral.test.ts`
Expected: FAIL — "shows all 9 groups" and "places Localization..." and "switching to Localization..." fail because `SettingsLocalization` isn't registered yet; `SettingsGeneral.test.ts` still passes since the source hasn't changed (the removed test simply no longer runs — no failure there, this is expected).

- [ ] **Step 3: Wire `SettingsLocalization` into `SettingsPage.svelte`**

In `packages/editor/src/lib/components/SettingsPage.svelte`, add the import after line 7 (`import SettingsGeneral from "./settings/SettingsGeneral.svelte";`):
```typescript
  import SettingsLocalization from "./settings/SettingsLocalization.svelte";
```

Change the `ALL_GROUPS` array (lines 33-42) from:
```typescript
  const ALL_GROUPS: SettingsGroupDef[] = [
    { id: "general", icon: "⚙️" },
    { id: "categories", icon: "🏷️" },
```
to:
```typescript
  const ALL_GROUPS: SettingsGroupDef[] = [
    { id: "general", icon: "⚙️" },
    { id: "localization", icon: "🌐" },
    { id: "categories", icon: "🏷️" },
```

Add a branch to the panel switch (lines 66-68), changing:
```svelte
      {#if activeGroup === "general"}
        <SettingsGeneral {reloadAllStores} />
      {:else if activeGroup === "categories"}
```
to:
```svelte
      {#if activeGroup === "general"}
        <SettingsGeneral {reloadAllStores} />
      {:else if activeGroup === "localization"}
        <SettingsLocalization />
      {:else if activeGroup === "categories"}
```

- [ ] **Step 4: Remove Language from `SettingsGeneral.svelte`**

In `packages/editor/src/lib/components/settings/SettingsGeneral.svelte`:

Remove the import at line 9:
```typescript
  import { getStoredLocale, setLocale, type Locale } from "../../locale";
```

Remove the state and function at lines 16-21:
```typescript
  let currentLocale = $state<Locale>(getStoredLocale());

  function changeLocale(next: Locale): void {
    currentLocale = next;
    setLocale(next);
  }

```

Remove the Language `<Card>` block at lines 167-176:
```svelte
<Card>
  <h2 class="section-title">{$_('settings.general.language')}</h2>
  <div class="home-row">
    <span class="home-label">{$_('settings.general.language')}</span>
    <select class="lang-select" value={currentLocale} onchange={(e) => changeLocale((e.target as HTMLSelectElement).value as Locale)}>
      <option value="en">English</option>
      <option value="fr">Français</option>
    </select>
  </div>
</Card>

```

Remove the now-unused `.lang-select` style rule at line 252:
```css
  .lang-select { font-size: 13px; padding: 4px 8px; border: 1px solid var(--border); border-radius: var(--radius-sm); background: var(--surface); color: var(--text); }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsPage.test.ts test/SettingsGeneral.test.ts test/SettingsLocalization.test.ts`
Expected: PASS (all tests, including the 2 new SettingsPage tests and the trimmed SettingsGeneral suite)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/SettingsPage.svelte packages/editor/src/lib/components/settings/SettingsGeneral.svelte packages/editor/test/SettingsPage.test.ts packages/editor/test/SettingsGeneral.test.ts
git commit -m "feat(localization): register Localization settings group, move Language out of General"
```

---

### Task 5: `DatePicker.svelte` — honor first-day-of-week

**Files:**
- Modify: `packages/editor/src/lib/components/DatePicker.svelte:2,21-41`
- Test: Create `packages/editor/test/DatePicker.test.ts`

**Interfaces:**
- Consumes: `getWeekStart` from `../localization` (Task 1).
- Produces: nothing new — internal behavior change only.

- [ ] **Step 1: Write the failing tests**

```typescript
// packages/editor/test/DatePicker.test.ts
import { describe, it, expect, beforeEach, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import DatePicker from "../src/lib/components/DatePicker.svelte";

describe("DatePicker week start", () => {
  let target: HTMLDivElement;

  beforeEach(() => {
    localStorage.clear();
    localStorage.setItem("myhome-locale", "en");
    target = document.createElement("div");
    document.body.appendChild(target);
  });

  afterEach(() => {
    target.remove();
  });

  it("defaults to a Sunday-first grid", () => {
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Sun");
    unmount(app);
  });

  it("starts the grid on Monday when the week-start preference is Monday", () => {
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: {} });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const headers = [...target.querySelectorAll(".dp-dh")].map((h) => h.textContent);
    expect(headers[0]).toBe("Mon");
    unmount(app);
  });

  it("shifts the leading blank cells to match a Monday-first grid", () => {
    // January 2024: the 1st is a Monday. Sunday-first grid needs 1 leading blank
    // (Jan 1 falls in column index 1); Monday-first grid needs 0 leading blanks.
    localStorage.setItem("myhome-localization", JSON.stringify({ dateFormat: null, timeFormat: null, weekStart: 1 }));
    const app = mount(DatePicker, { target, props: { value: "2024-01-15" } });
    flushSync();
    (target.querySelector(".dp-field") as HTMLElement).click();
    flushSync();
    const cells = [...target.querySelectorAll(".dp-cell")];
    expect(cells[0].classList.contains("dp-empty")).toBe(false);
    expect(cells[0].textContent).toBe("1");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/DatePicker.test.ts`
Expected: FAIL — the second and third tests fail because the grid is still hardcoded Sunday-first (first test already passes, since Sunday is the current hardcoded/default behavior).

- [ ] **Step 3: Rewire the component**

In `packages/editor/src/lib/components/DatePicker.svelte`, add the import after line 2 (`import { _, locale } from "svelte-i18n";`):
```typescript
  import { getWeekStart } from "../localization";
```

Replace `dayHeaders` (lines 21-27) with a version that takes the week-start offset:
```typescript
  function dayHeaders(loc: string, weekStart: number): string[] {
    // Jan 7 2024 was a Sunday, matching Date#getDay()'s 0=Sunday convention
    // used below to index into this array.
    const sundayFirst = Array.from({ length: 7 }, (_unused, i) =>
      new Intl.DateTimeFormat(loc, { weekday: "short" }).format(new Date(2024, 0, 7 + i))
    );
    return [...sundayFirst.slice(weekStart), ...sundayFirst.slice(0, weekStart)];
  }
```

Replace line 30 (`const DAY_HEADERS = $derived(dayHeaders($locale ?? "en"));`) with:
```typescript
  const weekStart = $derived(getWeekStart());
  const DAY_HEADERS = $derived(dayHeaders($locale ?? "en", weekStart));
```

Replace the `monthGrid` derivation (lines 33-41):
```typescript
  const monthGrid = $derived((() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < firstDay; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  })());
```
with:
```typescript
  const monthGrid = $derived((() => {
    const firstDay = new Date(viewYear, viewMonth, 1).getDay();
    const leading = (firstDay - weekStart + 7) % 7;
    const daysInMonth = new Date(viewYear, viewMonth + 1, 0).getDate();
    const cells: (number | null)[] = [];
    for (let i = 0; i < leading; i++) cells.push(null);
    for (let d = 1; d <= daysInMonth; d++) cells.push(d);
    while (cells.length % 7 !== 0) cells.push(null);
    return cells;
  })());
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/DatePicker.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/DatePicker.svelte packages/editor/test/DatePicker.test.ts
git commit -m "feat(localization): DatePicker calendar grid honors first-day-of-week"
```

---

### Task 6: Rewire chores displays to the shared formatter

**Files:**
- Modify: `packages/editor/src/lib/choreFormat.ts:22`
- Modify: `packages/editor/src/lib/components/ChoresPage.svelte:160-168`
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte:51-59`
- Modify: `packages/editor/src/lib/components/BadgePopup.svelte:18-21`

**Interfaces:**
- Consumes: `formatDate`, `formatDateTime` from `../dateFormat` (Task 2) — `choreFormat.ts` uses `./dateFormat` (same directory).
- Produces: nothing new.

- [ ] **Step 1: Confirm the existing tests that must keep passing**

Run: `cd packages/editor && npx vitest run test/choreFormat.test.ts test/ChoresPage.test.ts test/ChoreEditModal.test.ts`
Expected: PASS (baseline, before changes — no test in these files asserts on the exact >7-day-fallback or modal date-string output, so no test edits are needed for this task; this step is a baseline check, not a TDD red step).

- [ ] **Step 2: Rewire `choreFormat.ts`**

In `packages/editor/src/lib/choreFormat.ts`, add the import after line 2 (`import { get } from "svelte/store";`):
```typescript
import { formatDate } from "./dateFormat";
```
Replace line 22:
```typescript
  return d.toLocaleDateString(undefined, { month: "short", day: "numeric" });
```
with:
```typescript
  return formatDate(d);
```

- [ ] **Step 3: Rewire `ChoresPage.svelte`**

In `packages/editor/src/lib/components/ChoresPage.svelte`, add the import after line 13 (`import StatTile from "./ui/StatTile.svelte";`):
```typescript
  import { formatDate, formatDateTime } from "../dateFormat";
```
Remove the local functions at lines 160-168:
```typescript
  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

```
(the rest of the file calls `formatDate(...)`/`formatDateTime(...)` unchanged — those call sites now resolve to the imported functions).

- [ ] **Step 4: Rewire `ChoreEditModal.svelte`**

In `packages/editor/src/lib/components/ChoreEditModal.svelte`, add the import after line 14 (`import ScheduleEditor from "./ScheduleEditor.svelte";`):
```typescript
  import { formatDate, formatDateTime } from "../dateFormat";
```
Remove the local functions at lines 51-59:
```typescript
  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

  function formatDateTime(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleString(undefined, { month: "short", day: "numeric", hour: "2-digit", minute: "2-digit" });
  }

```

- [ ] **Step 5: Rewire `BadgePopup.svelte`**

In `packages/editor/src/lib/components/BadgePopup.svelte`, add the import after line 3 (`import type { Chore, Assignment } from "../choreStore.svelte";`):
```typescript
  import { formatDate } from "../dateFormat";
```
Remove the local function at lines 18-21:
```typescript
  function formatDate(iso: string): string {
    const d = new Date(iso);
    return d.toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/choreFormat.test.ts test/ChoresPage.test.ts test/ChoreEditModal.test.ts`
Expected: PASS (unchanged test count, no regressions)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/choreFormat.ts packages/editor/src/lib/components/ChoresPage.svelte packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/src/lib/components/BadgePopup.svelte
git commit -m "refactor(localization): rewire chores date displays to shared formatter"
```

---

### Task 7: Rewire search index, works displays to the shared formatter

**Files:**
- Modify: `packages/editor/src/lib/searchIndex.ts:41-43`
- Modify: `packages/editor/src/lib/components/HomeWorksWidget.svelte:23-26`
- Modify: `packages/editor/src/lib/components/WorksTimeline.svelte:106-109`
- Modify: `packages/editor/test/searchIndex.test.ts:1,34,96`

**Interfaces:**
- Consumes: `formatDate` from `./dateFormat` (searchIndex.ts) / `../dateFormat` (the two components).
- Produces: nothing new.

- [ ] **Step 1: Update the two searchIndex assertions that must change, and add a localStorage guard**

In `packages/editor/test/searchIndex.test.ts`, add a `beforeEach` after line 2's imports:
```typescript
import { describe, it, expect, beforeEach } from "vitest";
import { buildSearchIndex, filterResults, MODULE_ORDER } from "../src/lib/searchIndex";

beforeEach(() => {
  localStorage.clear();
});
```
(replacing the current `import { describe, it, expect } from "vitest";` line, which lacks `beforeEach`).

Change line 34 from:
```typescript
        subtitle: "Aug 1, 2026",
```
to:
```typescript
        subtitle: "08/01/2026",
```

Change line 96 from:
```typescript
      subtitle: "In progress · Jun 10, 2026",
```
to:
```typescript
      subtitle: "In progress · 06/10/2026",
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/searchIndex.test.ts`
Expected: FAIL — `fmtDate` still produces `"Aug 1, 2026"` / `"Jun 10, 2026"`, not matching the new numeric-format assertions yet.

- [ ] **Step 3: Rewire `searchIndex.ts`**

In `packages/editor/src/lib/searchIndex.ts`, add the import after line 1 (`import { _ } from "svelte-i18n";`):
```typescript
import { formatDate } from "./dateFormat";
```
Remove the local function at lines 41-43:
```typescript
function fmtDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
}

```
Replace both call sites (`fmtDate(chore.nextDueDate)` and `fmtDate(work.date)`) with `formatDate(chore.nextDueDate)` and `formatDate(work.date)` respectively.

- [ ] **Step 4: Rewire `HomeWorksWidget.svelte`**

In `packages/editor/src/lib/components/HomeWorksWidget.svelte`, add the import after line 4 (`import Card from "./ui/Card.svelte";`):
```typescript
  import { formatDate } from "../dateFormat";
```
Remove the local function at lines 23-26:
```typescript
  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" });
  }

```

- [ ] **Step 5: Rewire `WorksTimeline.svelte`**

In `packages/editor/src/lib/components/WorksTimeline.svelte`, add the import after line 3 (`import type { Work } from "../worksStore.svelte";`):
```typescript
  import { formatDate } from "../dateFormat";
```
Remove the local function at lines 106-109:
```typescript
  function formatDate(iso: string): string {
    if (!iso) return "—";
    return new Date(iso).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" });
  }

```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/searchIndex.test.ts test/HomeWorksWidget.test.ts test/WorksTimeline.test.ts`
Expected: PASS (no regressions, searchIndex assertions now match)

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/searchIndex.ts packages/editor/src/lib/components/HomeWorksWidget.svelte packages/editor/src/lib/components/WorksTimeline.svelte packages/editor/test/searchIndex.test.ts
git commit -m "refactor(localization): rewire search index and works date displays to shared formatter"
```

---

### Task 8: Rewire consumables, insurance, KB trash displays to the shared formatter

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumableModal.svelte:127-134`
- Modify: `packages/editor/src/lib/components/InsurancePage.svelte:96-100`
- Modify: `packages/editor/src/lib/components/ui/KBTrash.svelte:22-24`

**Interfaces:**
- Consumes: `formatDateTime` (ConsumableModal), `formatDate` (InsurancePage, KBTrash) from `../dateFormat` / `../../dateFormat`.
- Produces: nothing new.

- [ ] **Step 1: Baseline check**

Run: `cd packages/editor && npx vitest run test/ConsumableModal.test.ts test/InsurancePage.test.ts test/KBTrash.test.ts`
Expected: PASS (baseline — confirmed earlier these files have no rendered-date-text assertions, so no test edits are needed).

- [ ] **Step 2: Rewire `ConsumableModal.svelte`**

In `packages/editor/src/lib/components/ConsumableModal.svelte`, add the import after line 4 (`import type { createSettingsStore } from "../settingsStore.svelte";`):
```typescript
  import { formatDateTime } from "../dateFormat";
```
Remove the local function at lines 127-134:
```typescript
  function formatTs(iso: string): string {
    return new Date(iso).toLocaleString(undefined, {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  }
```
Replace all call sites of `formatTs(...)` in the template with `formatDateTime(...)`.

- [ ] **Step 3: Rewire `InsurancePage.svelte`**

In `packages/editor/src/lib/components/InsurancePage.svelte`, add the import after line 4 (`import type { createSettingsStore } from "../settingsStore.svelte";`):
```typescript
  import { formatDate } from "../dateFormat";
```
Replace the `nextRenewalLabel` derivation (lines 96-100):
```typescript
  const nextRenewalLabel = $derived(
    nextRenewalDate
      ? new Date(nextRenewalDate).toLocaleDateString(undefined, { year: "numeric", month: "short", day: "numeric" })
      : "—"
  );
```
with:
```typescript
  const nextRenewalLabel = $derived(formatDate(nextRenewalDate));
```

- [ ] **Step 4: Rewire `KBTrash.svelte`**

In `packages/editor/src/lib/components/ui/KBTrash.svelte`, add the import after line 4 (`import type { KBEntry } from "../../kbStore.svelte";`):
```typescript
  import { formatDate } from "../../dateFormat";
```
Replace the local function at lines 22-24:
```typescript
  function fmtDate(iso: string | null | undefined): string {
    return iso ? new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric", year: "numeric" }) : "";
  }
```
with:
```typescript
  function fmtDate(iso: string | null | undefined): string {
    return formatDate(iso);
  }
```
(kept as a thin wrapper rather than replacing the call site directly, since `fmtDate`'s parameter type is `string | null | undefined` and it's referenced by name in the template at line 52 — this is the minimal diff).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/ConsumableModal.test.ts test/InsurancePage.test.ts test/KBTrash.test.ts`
Expected: PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ConsumableModal.svelte packages/editor/src/lib/components/InsurancePage.svelte packages/editor/src/lib/components/ui/KBTrash.svelte
git commit -m "refactor(localization): rewire consumables, insurance, and KB trash date displays to shared formatter"
```

---

### Task 9: Rewire settings backup/activity log timestamps and inventory dates to the shared formatter

**Files:**
- Modify: `packages/editor/src/lib/components/settings/SettingsBackup.svelte:287`
- Modify: `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte:110`
- Modify: `packages/editor/src/lib/components/InventoryPage.svelte:71-74`

**Interfaces:**
- Consumes: `formatDateTime` (SettingsBackup, SettingsActivityLog), `formatDate` (InventoryPage) from `../../dateFormat` / `../dateFormat`.
- Produces: nothing new.

- [ ] **Step 1: Baseline check**

Run: `cd packages/editor && npx vitest run test/SettingsBackup.test.ts test/SettingsActivityLog.test.ts test/InventoryPage.test.ts`
Expected: PASS (baseline — confirmed earlier no rendered-date-text assertions in these files).

- [ ] **Step 2: Rewire `SettingsBackup.svelte`**

In `packages/editor/src/lib/components/settings/SettingsBackup.svelte`, add the import after line 3 (`import { _ } from "svelte-i18n";`):
```typescript
  import { formatDateTime } from "../../dateFormat";
```
Replace line 287:
```svelte
        {new Date(backup.createdAt).toLocaleString()}
```
with:
```svelte
        {formatDateTime(backup.createdAt)}
```

- [ ] **Step 3: Rewire `SettingsActivityLog.svelte`**

In `packages/editor/src/lib/components/settings/SettingsActivityLog.svelte`, add the import after line 3 (`import { _ } from "svelte-i18n";`):
```typescript
  import { formatDateTime } from "../../dateFormat";
```
Replace line 110:
```svelte
                <td>{new Date(entry.timestamp).toLocaleString()}</td>
```
with:
```svelte
                <td>{formatDateTime(entry.timestamp)}</td>
```

- [ ] **Step 4: Rewire `InventoryPage.svelte`**

In `packages/editor/src/lib/components/InventoryPage.svelte`, add the import after line 4 (`import type { createHouseStore } from "../houseStore.svelte";`):
```typescript
  import { formatDate } from "../dateFormat";
```
Replace the local function at lines 71-74:
```typescript
  function formatDate(d: string | null): string {
    if (!d) return "—";
    return d.slice(0, 10);
  }

```
(delete it entirely — the imported `formatDate` now handles this, and also fixes the pre-existing bug where inventory dates were always shown as raw `YYYY-MM-DD` regardless of locale).

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/SettingsBackup.test.ts test/SettingsActivityLog.test.ts test/InventoryPage.test.ts`
Expected: PASS (no regressions)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/settings/SettingsBackup.svelte packages/editor/src/lib/components/settings/SettingsActivityLog.svelte packages/editor/src/lib/components/InventoryPage.svelte
git commit -m "refactor(localization): rewire backup/activity timestamps and inventory dates to shared formatter"
```

---

### Task 10: Full-suite verification

**Files:** None (verification only).

- [ ] **Step 1: Run the full frontend test suite**

Run: `cd packages/editor && npx vitest run`
Expected: PASS — all tests green, no regressions across the full suite.

- [ ] **Step 2: Manual smoke check**

Start the dev server (see project's `run` skill/README for the exact command) and in a browser:
1. Open Settings → confirm "Localization" appears directly after "General" in the nav.
2. Confirm Language no longer appears on the General panel, and does appear on Localization with the current selection preserved.
3. Change Date Format to each of the four options and confirm the preview text updates live.
4. Change Time Format and confirm the preview updates live.
5. Change First Day of Week to Monday, then open a `DatePicker` (e.g. Chores → add/edit a chore's due date) and confirm the calendar's leftmost column is Monday and the day-of-month grid shifts accordingly.
6. Visit Chores, Works, Inventory, Insurance, KB (trash), and Settings → Backup/Activity Log, and confirm dates now render in the selected Date Format.

- [ ] **Step 3: Commit (only if the smoke check surfaced fixes)**

If manual verification finds no issues, no commit is needed for this task — Task 9's commit is the last code change.
