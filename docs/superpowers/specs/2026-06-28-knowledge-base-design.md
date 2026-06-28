# Knowledge Base Module — Design Spec

**Date:** 2026-06-28
**Status:** Approved for implementation

---

## Overview

A simple wiki-style Knowledge Base module. Users create named entries (e.g. "How to paint") each with a full-page Markdown body. The page is rendered by default; clicking Edit switches to a textarea. The markdown edit/preview toggle is extracted into a shared `MarkdownEditor` UI component so that `WorkModal`'s notes tab and any future module can reuse it without duplicating code.

The KB does not appear on the floor map. No attachments, no tags, no categories — YAGNI.

---

## Data Model

### Backend (`kb.json`)

```python
class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""          # raw Markdown
    createdAt: str             # ISO-8601 date-time
    updatedAt: str             # ISO-8601 date-time

class KBDocument(BaseModel):
    version: int = 1
    entries: list[KBEntry] = []

class KBCreate(BaseModel):
    title: str
    content: str = ""

class KBUpdate(BaseModel):
    title: str | None = None
    content: str | None = None
```

### Frontend (`kbStore.svelte.ts`)

```ts
interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}
interface KBDocument { version: number; entries: KBEntry[]; }
```

Store exposes: `entries`, `loaded`, `loadError`, `createEntry`, `updateEntry`, `deleteEntry`.

---

## API Endpoints

All registered under the existing FastAPI app in `main.py`.

| Method | Path | Body | Response |
|--------|------|------|----------|
| GET | `/api/kb` | — | `KBDocument` |
| POST | `/api/kb` | `KBCreate` | `KBEntry` 201 |
| PUT | `/api/kb/{id}` | `KBUpdate` | 204 |
| DELETE | `/api/kb/{id}` | — | 204 |

No attachment or placement endpoints.

---

## Shared Component: `MarkdownEditor`

**Path:** `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`

### Props

```ts
interface Props {
  value: string;         // bindable — the raw markdown string
  editing: boolean;      // bindable — caller toggles edit mode
  placeholder?: string;  // shown in preview when content is empty
  minHeight?: string;    // CSS value, default "200px"
}
```

### Behaviour

- **Preview mode** (default, `editing = false`): renders `DOMPurify.sanitize(marked(value))` as `{@html}`. Hover shows accent border + "Click to edit" cursor. Clicking sets `editing = true`.
- **Edit mode** (`editing = true`): renders a `<textarea>` with monospace font. No "Done" button inside — the parent controls commit/cancel.
- `notesHtml` is a `$derived` value so the preview stays live with the bound value.
- All markdown prose styles (headings, code, blockquote, lists, links) live in this component's `<style>` block.

### WorkModal refactor

`WorkModal.svelte` currently inlines the edit/preview block and ~35 lines of markdown CSS. After this change:
- Replace the `{#if editingNotes}…{:else}…{/if}` block with `<MarkdownEditor bind:value={notes} bind:editing={editingNotes} placeholder="Markdown notes…" minHeight="260px" />`
- Keep the existing "Done editing" `<Button>` just below the component (it sets `editingNotes = false`; this is caller-side state, MarkdownEditor doesn't own it)
- Delete all `.notes-preview`, `.notes-area`, `.notes-placeholder`, and `.notes-empty` CSS from WorkModal

No behavioural change to WorkModal — just moving code to where it belongs.

---

## KBPage Layout

**Path:** `packages/editor/src/lib/components/KBPage.svelte`

Two-panel layout, fills 100% height. No modal.

```
┌────────────────────┬──────────────────────────────────────────────┐
│ 🔍 Search…         │ [title — h1 or <input>]      [Edit]  [🗑]   │
│ ＋ New entry       ├──────────────────────────────────────────────┤
│────────────────────│                                              │
│ How to paint  ●    │  <MarkdownEditor                            │
│ Jun 28             │    bind:value={draftContent}                │
│                    │    bind:editing={editing}                   │
│ Replace boiler     │    minHeight="100%"                         │
│ Jun 15             │  />                                         │
│                    │                                              │
│ …                  ├──────────────────────────────────────────────│
│                    │  [Save]  [Cancel]  (visible when editing)   │
└────────────────────┴──────────────────────────────────────────────┘
```

### Left panel (~260px fixed width)

- `<Input placeholder="🔍 Search…">` — filters entry list by title (case-insensitive substring)
- `＋ New entry` button — POSTs `{ title: "New entry", content: "" }`, selects the new entry, sets `editing = true` with cursor in title field
- Scrollable list of `KBEntry` rows: title + formatted date, active entry has accent left-border highlight

### Right panel (flex: 1)

- **No selection**: centered empty state — "Select an entry or create one"
- **Entry selected**:
  - **Header**: title shown as `<h1>` in view mode; `<input type="text">` in edit mode. `[Edit]` button on right toggles `editing`. Delete button (🗑) shows inline confirmation ("Delete? ✓ ✕") before calling `deleteEntry`.
  - **Content**: `<MarkdownEditor bind:value={draftContent} bind:editing={editing} placeholder="Start writing in Markdown…" />`
  - **Footer** (only when `editing = true`): `[Save]` calls `updateEntry(id, { title: draftTitle, content: draftContent })` then sets `editing = false`; `[Cancel]` resets drafts and sets `editing = false`

### Local state in KBPage

```ts
let selectedId = $state<string | null>(null);
let editing = $state(false);
let draftTitle = $state("");
let draftContent = $state("");
let confirmDelete = $state(false);
let saving = $state(false);
let error = $state<string | null>(null);
let searchQuery = $state("");
```

When an entry is selected (clicking list row or after create), `draftTitle` and `draftContent` are initialised from the entry. `Cancel` resets them back to the live store value.

The list always reflects `store.entries` (reactive). After a successful save the store refreshes via `init()`, so the list title updates automatically.

---

## Integration

### NavMenu

New entry inserted between Works and Costs:

```ts
{ href: "#/kb", icon: "📖", label: "Knowledge Base" }
```

### App.svelte

```ts
import { createKBStore } from "./lib/kbStore.svelte";
import KBPage from "./lib/components/KBPage.svelte";

const kbStore = createKBStore();
```

Route block added alongside the other `{:else if}` branches:

```svelte
{:else if currentRoute === "#/kb"}
  <KBPage store={kbStore} />
```

---

## Backend File Summary

| File | Purpose |
|------|---------|
| `packages/backend/src/myhome/models_kb.py` | Pydantic models |
| `packages/backend/src/myhome/persistence_kb.py` | `load_kb()` / `save_kb()` → `/data/kb.json` |
| `packages/backend/src/myhome/routes/kb.py` | CRUD router |
| `packages/backend/src/myhome/main.py` | `include_router(kb.router)` |

### Persistence

`kb.json` lives in the same `DATA_DIR` as all other module files. `save_kb()` uses the atomic write-to-tmp-then-replace pattern used by every other persistence module.

---

## Frontend File Summary

| File | Action |
|------|--------|
| `packages/editor/src/lib/kbStore.svelte.ts` | New store |
| `packages/editor/src/lib/components/ui/MarkdownEditor.svelte` | New shared component |
| `packages/editor/src/lib/components/KBPage.svelte` | New page |
| `packages/editor/src/lib/components/WorkModal.svelte` | Refactor notes tab to use `MarkdownEditor` |
| `packages/editor/src/lib/components/NavMenu.svelte` | Add `#/kb` entry |
| `packages/editor/src/App.svelte` | Wire store + route |

---

## Tests

| File | What it covers |
|------|---------------|
| `packages/editor/test/kbStore.test.ts` | init, createEntry, updateEntry, deleteEntry; same fetch-stub pattern as `worksStore.test.ts` |
| `packages/editor/test/MarkdownEditor.test.ts` | preview renders HTML, click enters edit mode, value stays in sync, placeholder shown when empty |
| `packages/editor/test/KBPage.test.ts` | list renders, clicking entry shows content, Edit→Save round-trip, Cancel reverts, delete confirm flow, search filtering |

Target: all existing 207 tests continue passing; new tests bring the total to ~240+.

---

## Out of Scope

- Tags / categories (easy to add later)
- Entry ordering / drag-to-reorder
- Floor map pin
- Image uploads or attachments
- Entry history / versioning
- Cross-linking between entries
