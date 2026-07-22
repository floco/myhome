# Multi-language Support (i18n) + French — Design Spec

**Date:** 2026-07-22
**Status:** Approved

## Overview

The editor frontend (`packages/editor`, ~95 Svelte components, no existing
i18n) is entirely hardcoded in English. This adds a general internationalization
mechanism and a complete French translation, covering every static UI string
across all modules (Home, Chores, Costs, Inventory, Works, KB, Properties,
Consumables, Settings, Auth, shared/common components, nav, topbar).

Out of scope: backend-generated strings (activity log descriptions, API
error/validation messages returned from `packages/backend`) — these stay
English for now and are a candidate for a later pass, since they're dynamic/
interpolated server-side and would need a locale parameter threaded through
API calls. Also out of scope: user-entered content (chore names, KB page
bodies, notes, property addresses, etc.) — that's data, never translated.

---

## 1. Library & Setup

Adopt `svelte-i18n` (confirmed Svelte 5 + plain-Vite compatible — store-based
`$_`, no SvelteKit required). Added as a new dependency of `@myhome/editor`.

`main.ts` registers both locale catalogs as lazy-loaded JSON modules, calls
`init({ fallbackLocale: 'en', initialLocale: getStoredLocale() })`, and
awaits `waitLocale()` before mounting `App` — avoiding a flash of missing-key
text on first paint.

```ts
import { register, init, waitLocale } from "svelte-i18n";
import { getStoredLocale } from "./lib/locale";

register("en", () => import("./lib/locales/en.json"));
register("fr", () => import("./lib/locales/fr.json"));

init({ fallbackLocale: "en", initialLocale: getStoredLocale() });
await waitLocale();
```

## 2. Locale Persistence

New `packages/editor/src/lib/locale.ts`, mirroring the existing `theme.ts`
pattern:

- `getStoredLocale()` — reads `localStorage["myhome-locale"]`; if unset,
  defaults to `"fr"` when `navigator.language` starts with `"fr"`, else
  `"en"`.
- `setLocale(locale)` — persists to `localStorage` and calls svelte-i18n's
  `locale.set(locale)`.
- `initLocale()` — called once at startup; returns the resolved locale
  (used to seed `init()`'s `initialLocale`).

## 3. Language Selector

A dropdown (English / Français) added to `SettingsGeneral.svelte`, alongside
other app-wide preferences (same section as the existing theme toggle
pattern conceptually, though theme itself lives in the topbar). Calls
`setLocale()` on change. No topbar toggle.

## 4. Message Catalogs

`packages/editor/src/lib/locales/en.json` and `fr.json`, both nested by
module namespace mirroring the component tree:

```
common, nav, topbar, auth,
settings.general, settings.security, settings.integrations,
settings.categories, settings.backup, settings.activityLog,
settings.notifications,
home, chores, costs, inventory, works, kb, properties, consumables
```

Keys within a namespace are flat and descriptive, e.g. `chores.emptyState`,
`chores.form.title`, `common.save`, `common.cancel`. Shared/generic strings
(Save, Cancel, Delete, Edit, Close, Loading…, empty-state fallback) live in
`common` and are reused across modules rather than duplicated per-namespace.

Interpolation and pluralization (e.g. "3 items", "{n} days ago") use ICU
MessageFormat syntax, which svelte-i18n parses natively via
`$_('key', { values: { n } })`.

## 5. Component Migration Pattern

- Markup/attributes: `import { _ } from "svelte-i18n"` then
  `{$_('chores.emptyState')}`, including in `aria-label`, `placeholder`,
  `title` attributes.
- `.ts` logic (alert/confirm text, validation messages, toast content):
  `import { _, get } from "svelte-i18n"` (or the local `get` from `svelte/store`)
  and call `get(_)('key')` to read the current translation outside a
  component's reactive context.
- Every static string identified during migration gets a catalog key in
  both `en.json` and `fr.json` — no partial/placeholder translations.

## 6. Testing & Rollout

- Default locale stays `en`; the English catalog is an exact copy of the
  current hardcoded strings, so all existing frontend tests (which assert on
  rendered English text) keep passing unchanged once components are migrated
  to `$_('key')`.
- New tests:
  - `locale.ts` unit tests (detection from `navigator.language`, persistence
    round-trip, default fallback).
  - A translation-completeness check: every key present in `en.json` exists
    in `fr.json` and vice versa (flat-diff over both catalogs), failing loudly
    on drift.
  - A French smoke test on one representative module (renders with
    `locale='fr'`, asserts French text appears) to confirm the mechanism
    works end-to-end, not just that keys exist.
- Migration order:
  1. i18n infra (`main.ts`, `locale.ts`, catalog scaffolding) + shared/common
     components (Button, Modal, Input, Tabs, StatTile, etc.) + nav/topbar +
     all Settings panels.
  2. Each feature module in turn: Home, Chores, Costs, Inventory, Works, KB,
     Properties, Consumables, Auth/login.
  3. Final grep sweep (`grep -rn` for capitalized English phrases / common
     words in `.svelte` markup) to catch stragglers, plus a final run of the
     completeness check.
- French translations are real, reviewed copy (domain-appropriate for home
  management/household terminology), written as each module is migrated —
  not machine-translated placeholders.

## 7. Non-Goals

- Backend-generated strings (activity log, API errors) — future work.
- Locale-aware number/date/currency formatting beyond what's already
  hardcoded (app already hardcodes € and m² elsewhere; unchanged here).
- Additional languages beyond French — catalog structure supports adding
  more later (`register('xx', ...)` + a new JSON file), but only `en`/`fr`
  ship now.
- Right-to-left layout support (not needed for French).
