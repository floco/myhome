# KB editing fixes — design

Date: 2026-08-09

## Summary

Four related UX fixes to the Knowledge Base (KB) editor (`packages/editor/src/lib/components/KBPage.svelte` + `ui/MarkdownEditor.svelte`):

1. **Autosave** — replaces the manual Save/Cancel flow.
2. **Block navigation until saved** — both within KB and when leaving the module entirely.
3. **Reopen the last-viewed page** when returning to bare `#/kb`.
4. **Double-click to edit** — replaces the explicit ✏️ Edit button.

Frontend-only (`packages/editor`), no API/schema changes. `kbStore.updateEntry` (existing PUT `/api/homes/{homeId}/kb/{id}`) is reused as-is.

## 1. Autosave

`KBPage.svelte` currently tracks `editing`, `draftTitle`, `draftContent` and only persists on an explicit 💾 Save click (`handleSave`, line 209), with ✕ Cancel (`handleCancel`, line 227) discarding the draft. Both buttons are removed.

- While `editing` is true, an `$effect` watches `draftTitle`/`draftContent`. Whenever either differs from the currently-loaded `selectedEntry.title`/`.content`, it (re)starts a 1.2s debounce timer. Each further keystroke resets the timer.
- `flushSave()`: cancels any pending timer; if there's nothing dirty, no-ops; otherwise calls `store.updateEntry(selectedId, { title: draftTitle.trim(), content: draftContent })`. If a save is already in flight when called again, it waits for that save to finish and then re-checks dirtiness (no overlapping requests).
- `saveStatus` state (`"idle" | "pending" | "saving" | "saved" | "error"`) drives a small inline indicator in `.header-actions`, replacing the Save/Cancel buttons: "Saving…" / "Saved" (fades back to idle after ~2s) / "Save failed" (persists, reusing the existing `.content-error` block for the message).
- Empty-title guard (`draftTitle.trim()` check, currently in `handleSave`) moves into `flushSave`: an empty title blocks the save and shows the existing `kb.page.titleEmpty` error instead of silently saving a blank title.
- `flushSave()` is awaited (not just fired) before: switching to another KB page (`navigate`), creating a new page/child, opening Trash, and switching to the Media tab — i.e. everywhere `editing` could currently be force-reset to `false` without going through Save. If the flush fails, the action that triggered it is aborted and the user stays put with the error shown.
- Icon changes (`handleIconChange`) already save immediately server-side and are unaffected.

No more "Cancel" / discard-draft path — since edits are persisted moments after typing, there is nothing meaningful left to revert to (matches the Notion/Google-Docs autosave model already discussed with the user).

## 2. Block navigation until saved

**Within KB** (page-to-page, trash, tab switches): already covered by §1 — these are internal calls that now await `flushSave()` first.

**Leaving the KB module for another part of the app**: today, all navigation — `<a href="#/...">` clicks in `NavMenu.svelte` and various `window.location.hash = "#/..."` assignments scattered across `App.svelte` — funnels through one chokepoint: the `hashchange` listener registered in `App.svelte`'s `$effect` (~line 346-350), which sets `currentRoute`. There is currently no nav-guard or `beforeunload` precedent anywhere in the app (confirmed by search); this is new territory, and the floor-plan module's own autosave (`App.svelte:466-479`) is silent/non-blocking, not a pattern to copy for this part.

Design: a small guard-registry module, `packages/editor/src/lib/navGuard.ts`, exporting:
```ts
setNavGuard(fn: (() => Promise<boolean>) | null): void
```
(`true` = safe to proceed, `false` = blocked/failed). Only one guard is ever active at a time (only one top-level module is mounted at once), so a single module-level variable is sufficient — no stack needed.

- `KBPage.svelte` registers its guard (`flushSave` wrapped to return `true`/`false`) in an `$effect` on mount and clears it (`setNavGuard(null)`) on unmount.
- `App.svelte`'s `hashchange` handler: on each event, if a guard is registered, immediately revert `window.location.hash` back to the current (pre-navigation) route — capturing the attempted target hash first — then call the guard and await it:
  - success → set `window.location.hash` to the originally-attempted target (completing the navigation the user asked for; a second `hashchange` fires and proceeds normally since the guard has nothing pending by then).
  - failure → stay on the current route; the existing `.content-error` block already shows why.
  - A re-entrancy flag prevents the listener from treating its own revert/replay hash assignments as fresh navigation attempts to guard against.
- Tab close/refresh while a save is pending, in-flight, or failed: a `beforeunload` listener (added/removed alongside the nav guard registration) sets `event.returnValue` to trigger the browser's native "leave site?" confirmation. This is the browser's only mechanism here — it cannot be a custom dialog, and cannot literally block, only warn.

## 3. Reopen the last-viewed page

No existing localStorage-backed "last item" precedent in KB (only simple preference keys like `theme.ts`'s `myhome-theme`). Add the same pattern, namespaced per home (KB entries are per-home):

- Key: `` `myhome-kb-last-page-${homeId}` ``.
- Written whenever `selectEntry()` runs (i.e. every time the selected page changes), storing `entry.id`.
- On mount, if the route is bare `#/kb` (no `kbRouteId`) and `store.loaded` is true (must wait for `store.entries` to actually be populated — it's fetched async): look up the stored id for the active home. If it matches a live (non-deleted) entry, navigate to it (`window.location.hash = "#/kb/" + id`, replacing the placeholder view). If the stored id is missing or no longer exists (page was deleted), clear the stale key and fall back to today's "select or create a page" placeholder — no further fallback (e.g. to the first page) per the earlier decision that this should reflect personal navigation history, not global recency.

## 4. Double-click to edit

`MarkdownEditor.svelte` currently only supports single-click-to-edit via `clickToEdit` (default `true`), which `KBPage.svelte` explicitly disables (`clickToEdit={false}`) in favor of an explicit ✏️ Edit button. `WorkModal.svelte` and `InsuranceModal.svelte` are the only other consumers, both using the default single-click behavior for their notes fields — that behavior must not change.

- Add a new prop, `editTrigger: "click" | "dblclick" = "click"`, alongside the existing `clickToEdit`. When `clickToEdit` is true, the preview `<div>`'s handler is wired to `onclick` or `ondblclick` based on `editTrigger` (keyboard activation via Enter/Space is unchanged and still works regardless of `editTrigger`, since it's not a pointer gesture).
- `KBPage.svelte` passes `clickToEdit={true} editTrigger="dblclick"` and drops the ✏️ Edit button.
- Exiting edit mode back to preview: a small ✓ "Done" button replaces where Save/Cancel used to be (shown whenever `editing` is true), calling `flushSave()` then setting `editing = false`. This is deliberately a button rather than blur-to-exit: blur fires when clicking a formatting-toolbar button (bold, heading, etc.) inside the editor, which would prematurely kick the user out of edit mode mid-formatting.
- `WorkModal`/`InsuranceModal` are unaffected (they don't pass `editTrigger`, keep single-click, and already have their own "Done editing" buttons using the same pattern).

## Out of scope

- Any change to `WorkModal`/`InsuranceModal` notes editors beyond the new no-op-by-default `editTrigger` prop.
- A "discard changes" / undo affordance beyond what autosave + KB's existing Trash (page-level) already provides.
- Persisting anything beyond the single last-viewed page id (e.g. scroll position, cursor position).
- Any server/API changes — `updateEntry`'s existing PUT endpoint and full-list refetch (`init()`) are reused unchanged.

## Testing

Existing Vitest suites for `KBPage.svelte` and `MarkdownEditor.svelte` get updated/added coverage for: debounced autosave firing and status transitions, save-failure blocking navigation with the error shown, flush-before-navigate on page switch/new-page/trash/media-tab, the `navGuard` module (register/clear, revert-then-replay-on-success, block-on-failure, re-entrancy), last-page persistence (write on select, redirect on bare `#/kb`, stale-id fallback), and `editTrigger="dblclick"` vs the default `"click"` behavior (including that `WorkModal`/`InsuranceModal` are unaffected).
