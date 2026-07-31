# Localization Settings — Design

**Date:** 2026-07-31
**Status:** Approved, ready for planning

## Problem

Language currently lives in `SettingsGeneral.svelte`, stored purely client-side in `localStorage` via `lib/locale.ts` (no backend involvement). There is no way to control date format, time format, or first day of week — every component that renders a date/time rolls its own `toLocaleDateString`/`toLocaleString` call, and the calendar grid in `DatePicker.svelte` hardcodes Sunday as the first column. Users want a dedicated Localization settings category (placed right after General) that groups Language with three new preferences — Date Format, Time Format, First Day of Week — and have those preferences actually change how dates/times render across the app.

## Scope

**In scope:**
- New "Localization" settings category, positioned immediately after "General" in the settings nav.
- Move the existing Language selector out of `SettingsGeneral.svelte` into the new category.
- Three new preferences: Date Format, Time Format, First Day of Week, each with a live preview, matching the copy already approved:
  - "Customize language, date format, and regional preferences for your account."
  - Language — "Select your preferred language"
  - Date Format — "Choose how dates should be displayed throughout the application" (preview: `01/15/2024`)
  - Time Format — "Select 12-hour or 24-hour time format" (preview: `2:30 PM`)
  - First Day of Week — "Select which day starts your week"
- A shared date/time formatting utility that all four preferences flow through, and rewiring every existing date/time display in the app to use it (see File-by-file rewiring below), including fixing the DatePicker calendar grid's week-start logic.

**Out of scope:**
- Backend persistence. All four preferences stay client-side in `localStorage`, consistent with how Language already works — no `SettingsDocument` changes, no new API routes.
- Per-account (multi-user) preferences — this is per-browser, same trust/scope model as the existing language setting.
- Retroactive reformatting of stored data — nothing about how dates are *stored* changes, only how they're *displayed*.

## Storage & defaults model

New module `lib/localization.ts`, sibling to the existing `lib/locale.ts`, storing three *optional* overrides in a single `localStorage` key (`myhome-localization`, JSON-encoded):

```ts
type DateFormat = "MDY" | "DMY" | "ISO" | "LONG"; // MM/DD/YYYY, DD/MM/YYYY, YYYY-MM-DD, "Jan 15, 2024"
type TimeFormat = "12h" | "24h";
type WeekStart = 0 | 1 | 6; // Date#getDay() convention: Sunday, Monday, Saturday

interface LocalizationOverrides {
  dateFormat: DateFormat | null;
  timeFormat: TimeFormat | null;
  weekStart: WeekStart | null;
}
```

`null` means "not explicitly set — derive from the current language." Derived defaults:

| Language | Date Format | Time Format | Week Start |
|---|---|---|---|
| English (`en`) | MDY | 12h | Sunday (0) |
| French (`fr`) | DMY | 24h | Monday (1) |

`getDateFormat()` / `getTimeFormat()` / `getWeekStart()` return the explicit override if set, otherwise the language-derived default (reading the current locale via `getStoredLocale()` from `locale.ts`). `setDateFormat()` / `setTimeFormat()` / `setWeekStart()` persist an explicit override. Once a user picks a value explicitly, it sticks even if they later change the language — changing language only affects fields the user has never touched. There is no "reset to automatic" control in this iteration (YAGNI — not requested).

## Shared formatter

New module `lib/dateFormat.ts`, exporting:

```ts
function formatDate(value: string | Date): string
function formatTime(value: string | Date): string
function formatDateTime(value: string | Date): string
```

- `formatDate` builds the string manually per `getDateFormat()` (MDY/DMY/ISO are simple zero-padded numeric assembly; LONG uses `Intl.DateTimeFormat(locale, {month:"long", day:"numeric", year:"numeric"})`).
- `formatTime` uses `Intl.DateTimeFormat(locale, {hour:"numeric", minute:"2-digit", hour12: getTimeFormat() === "12h"})`.
- `formatDateTime` composes both with a space separator, matching the existing `toLocaleString` call sites' shape.
- All three accept an ISO string or `Date` and return `""` for null/invalid input (matching current ad hoc helpers' behavior where checked).

### File-by-file rewiring

Replace local ad hoc date/time formatting with the shared helper in:

`choreFormat.ts`, `searchIndex.ts`, `DatePicker.svelte` (labels only — grid logic below), `ScheduleEditor.svelte` (month-name labels), `HomeWorksWidget.svelte`, `BadgePopup.svelte`, `ConsumableModal.svelte`, `ChoresPage.svelte`, `ChoreEditModal.svelte`, `WorksTimeline.svelte`, `InsurancePage.svelte`, `KBTrash.svelte`, `SettingsBackup.svelte`, `SettingsActivityLog.svelte`, `InventoryPage.svelte` (replaces its raw `d.slice(0,10)` with `formatDate`, fixing a pre-existing bug where inventory dates ignore locale entirely).

### DatePicker week-start

`DatePicker.svelte` currently hardcodes Sunday-first in two places:
- `dayHeaders()` builds weekday labels starting from a known Sunday.
- `monthGrid()` uses `new Date(...).getDay()` directly as the leading-blank-cell count.

Both are rewired to offset by `getWeekStart()`: `dayHeaders()` rotates its 7-day array by the offset, and `monthGrid()`'s leading-blank count becomes `(firstDay - weekStart + 7) % 7`.

## Settings UI

New `lib/components/settings/SettingsLocalization.svelte`:

- Registered in `SettingsPage.svelte`'s `ALL_GROUPS` array with `{ id: "localization", icon: "🌐" }`, placed immediately after `{ id: "general", icon: "⚙️" }`, plus the matching `{:else if activeGroup === "localization"}` branch and import.
- Layout mirrors the pasted mockup: category description line, then four `Card`/row blocks — Language (select, moved verbatim from `SettingsGeneral.svelte`, same `changeLocale` behavior), Date Format (select + live preview of today's date), Time Format (select + live preview of current time), First Day of Week (select, no preview needed).
- Selecting a Date/Time Format option calls the new setter and updates local `$state` driving the preview text immediately (no page reload needed).
- `SettingsGeneral.svelte` loses its Language block entirely (home info, module toggles, delete/reset modals are unaffected).

## i18n

New keys in `locales/en.json` and `locales/fr.json`:
- `settings.nav.localization` — nav label ("Localization" / "Localisation").
- `settings.localization.title`, `.description`, `.language`, `.dateFormat`, `.dateFormatDescription`, `.timeFormat`, `.timeFormatDescription`, `.firstDayOfWeek`, `.firstDayOfWeekDescription`, `.preview`.
- Translated option labels for the three First Day of Week choices (Sunday/Monday/Saturday): `settings.localization.weekday.sunday/monday/saturday`.
- The four Date Format `<select>` options are labeled with the locale-invariant pattern itself ("MM/DD/YYYY", "DD/MM/YYYY", "YYYY-MM-DD", "Month DD, YYYY") — these are format patterns, not prose, so they don't need translation. The Time Format options ("12-hour" / "24-hour") do need translation: `settings.localization.time12` / `.time24`.
- The existing `settings.general.language` key is renamed to `settings.localization.language` (both locale files) since it moves category; no other `settings.general.*` keys change.

## Testing

- `lib/dateFormat.test.ts` (new): each `DateFormat` × representative dates, each `TimeFormat`, `formatDateTime` composition, empty/invalid input.
- `lib/localization.test.ts` (new): override get/set round-trip via `localStorage`, language-derived defaults for `en`/`fr` when no override is set, override persists across a language change.
- `SettingsLocalization.test.ts` (new): renders all four fields, moving Language works (select + change fires `setLocale`), Date/Time Format previews update on selection, category appears in nav right after General.
- `SettingsGeneral.test.ts`: remove now-obsolete Language assertions.
- `DatePicker.test.ts`: add a case asserting the grid's first column matches `getWeekStart()` for a non-default (Monday) setting.
- Spot-check existing tests in the ~14 rewired files still pass with the shared formatter's output (format strings should match what the old ad hoc calls produced for the default en/MDY/12h/Sunday case, so no behavior change for users who never touch the new settings).

## Non-goals

- No backend/account-level sync of these preferences across devices.
- No additional date-format or week-start options beyond what's listed above.
- No retroactive changes to stored date values, only display formatting.
