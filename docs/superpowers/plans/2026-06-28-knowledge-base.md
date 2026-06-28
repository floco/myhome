# Knowledge Base Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a wiki-style Knowledge Base module with markdown entries, a two-panel page layout, and a shared `MarkdownEditor` component that also replaces the inline markdown code in `WorkModal`.

**Architecture:** Backend CRUD over `kb.json` (same pattern as works). Frontend store + `KBPage` (two-panel: entry list left, markdown content right). `MarkdownEditor.svelte` is a new shared UI component in `ui/` that handles the edit/preview toggle; `WorkModal` is refactored to use it immediately so the component isn't orphaned.

**Tech Stack:** FastAPI (Python), Pydantic v2, Svelte 5 runes, TypeScript, Vitest 4, `marked`, `dompurify`

---

## File Map

**New — backend**
- `packages/backend/src/myhome/models_kb.py` — Pydantic models
- `packages/backend/src/myhome/persistence_kb.py` — load/save `kb.json`
- `packages/backend/src/myhome/routes/kb.py` — CRUD router

**Modified — backend**
- `packages/backend/src/myhome/main.py` — register kb router

**New — frontend**
- `packages/editor/src/lib/kbStore.svelte.ts` — reactive store (fetch/CRUD)
- `packages/editor/src/lib/components/ui/MarkdownEditor.svelte` — shared edit/preview component
- `packages/editor/src/lib/components/KBPage.svelte` — two-panel page
- `packages/editor/test/kbStore.test.ts`
- `packages/editor/test/MarkdownEditor.test.ts`
- `packages/editor/test/KBPage.test.ts`

**Modified — frontend**
- `packages/editor/src/lib/components/WorkModal.svelte` — use `MarkdownEditor`, remove inline markdown code
- `packages/editor/src/lib/components/NavMenu.svelte` — add `#/kb` entry
- `packages/editor/src/App.svelte` — wire store + route

---

## Task 1: Backend models, persistence, and routes

**Files:**
- Create: `packages/backend/src/myhome/models_kb.py`
- Create: `packages/backend/src/myhome/persistence_kb.py`
- Create: `packages/backend/src/myhome/routes/kb.py`
- Modify: `packages/backend/src/myhome/main.py`

- [ ] **Step 1: Create the Pydantic models**

Create `packages/backend/src/myhome/models_kb.py`:

```python
from __future__ import annotations
from pydantic import BaseModel


class KBEntry(BaseModel):
    id: str
    title: str
    content: str = ""
    createdAt: str
    updatedAt: str


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

- [ ] **Step 2: Create the persistence layer**

Create `packages/backend/src/myhome/persistence_kb.py`:

```python
import json
import os
from pathlib import Path

from .models_kb import KBDocument


def _kb_file() -> Path:
    data_dir = Path(os.environ.get("DATA_DIR", "/data"))
    return data_dir / "kb.json"


def load_kb() -> KBDocument:
    path = _kb_file()
    if not path.exists():
        return KBDocument()
    with path.open() as f:
        return KBDocument.model_validate(json.load(f))


def save_kb(doc: KBDocument) -> None:
    path = _kb_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w") as f:
        json.dump(doc.model_dump(), f, indent=2)
    tmp.replace(path)
```

- [ ] **Step 3: Create the routes**

Create `packages/backend/src/myhome/routes/kb.py`:

```python
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ..models_kb import KBCreate, KBDocument, KBEntry, KBUpdate
from ..persistence_kb import load_kb, save_kb

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


@router.get("/api/kb", response_model=KBDocument)
def get_kb() -> KBDocument:
    return load_kb()


@router.post("/api/kb", response_model=KBEntry, status_code=201)
def create_entry(body: KBCreate) -> KBEntry:
    doc = load_kb()
    now = _now()
    entry = KBEntry(
        id=str(uuid.uuid4()),
        title=body.title,
        content=body.content,
        createdAt=now,
        updatedAt=now,
    )
    doc.entries.append(entry)
    save_kb(doc)
    return entry


@router.put("/api/kb/{id}", status_code=204)
def update_entry(id: str, body: KBUpdate) -> None:
    doc = load_kb()
    entry = next((e for e in doc.entries if e.id == id), None)
    if not entry:
        raise HTTPException(status_code=404)
    if body.title is not None:
        entry.title = body.title
    if body.content is not None:
        entry.content = body.content
    entry.updatedAt = _now()
    save_kb(doc)


@router.delete("/api/kb/{id}", status_code=204)
def delete_entry(id: str) -> None:
    doc = load_kb()
    before = len(doc.entries)
    doc.entries = [e for e in doc.entries if e.id != id]
    if len(doc.entries) == before:
        raise HTTPException(status_code=404)
    save_kb(doc)
```

- [ ] **Step 4: Register the router in main.py**

In `packages/backend/src/myhome/main.py`, change:

```python
from .routes import house, svg, ha, chores, inventory, settings, costs, works
```
to:
```python
from .routes import house, svg, ha, chores, inventory, settings, costs, works, kb
```

And add after `app.include_router(works.router)`:
```python
app.include_router(kb.router)
```

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/models_kb.py \
        packages/backend/src/myhome/persistence_kb.py \
        packages/backend/src/myhome/routes/kb.py \
        packages/backend/src/myhome/main.py
git commit -m "feat(kb): add backend models, persistence, and CRUD routes"
```

---

## Task 2: kbStore + tests (TDD)

All commands run from `packages/editor/`.

**Files:**
- Create: `packages/editor/test/kbStore.test.ts`
- Create: `packages/editor/src/lib/kbStore.svelte.ts`

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/kbStore.test.ts`:

```typescript
import { describe, it, expect, afterEach, vi } from "vitest";
import { createKBStore } from "../src/lib/kbStore.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    ...overrides,
  };
}

const emptyDoc = { version: 1, entries: [] };

describe("kbStore — init", () => {
  it("loads entries from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, entries: [makeEntry()] }));
    const store = createKBStore();
    await tick();
    expect(store.entries.length).toBe(1);
    expect(store.entries[0].id).toBe("e1");
    expect(store.loaded).toBe(true);
  });

  it("marks loaded and sets loadError on network failure", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("net fail")));
    const store = createKBStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("net fail");
  });

  it("marks loaded and sets loadError on HTTP error", async () => {
    vi.stubGlobal("fetch", makeFetch(500));
    const store = createKBStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("HTTP 500");
  });
});

describe("kbStore — createEntry", () => {
  it("POSTs to /api/kb, returns new entry, and refreshes", async () => {
    const created = makeEntry({ id: "e2", title: "New entry", content: "" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => created })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [created] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    const entry = await store.createEntry({ title: "New entry", content: "" });
    await tick();
    expect(entry.id).toBe("e2");
    expect(entry.title).toBe("New entry");
    expect(store.entries.length).toBe(1);
    const [, postCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(postCall[0]).toBe("/api/kb");
    expect(postCall[1].method).toBe("POST");
    expect(JSON.parse(postCall[1].body as string)).toEqual({ title: "New entry", content: "" });
  });

  it("throws on HTTP error", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: false, status: 422, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.createEntry({ title: "x", content: "" })).rejects.toThrow("HTTP 422");
  });
});

describe("kbStore — updateEntry", () => {
  it("PUTs to /api/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const updated = makeEntry({ title: "Updated title" });
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [updated] }) });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await store.updateEntry("e1", { title: "Updated title" });
    await tick();
    expect(store.entries[0].title).toBe("Updated title");
    const [, putCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(putCall[0]).toBe("/api/kb/e1");
    expect(putCall[1].method).toBe("PUT");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.updateEntry("e1", { title: "x" })).rejects.toThrow("HTTP 404");
  });
});

describe("kbStore — deleteEntry", () => {
  it("DELETEs /api/kb/{id} and refreshes", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => null })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    expect(store.entries.length).toBe(1);
    await store.deleteEntry("e1");
    await tick();
    expect(store.entries.length).toBe(0);
    const [, delCall] = fetchFn.mock.calls as [unknown, [string, RequestInit]][];
    expect(delCall[0]).toBe("/api/kb/e1");
    expect(delCall[1].method).toBe("DELETE");
  });

  it("throws on HTTP error", async () => {
    const entry = makeEntry();
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => ({ version: 1, entries: [entry] }) })
      .mockResolvedValueOnce({ ok: false, status: 404, json: async () => null });
    vi.stubGlobal("fetch", fetchFn);
    const store = createKBStore();
    await tick();
    await expect(store.deleteEntry("e1")).rejects.toThrow("HTTP 404");
  });
});
```

- [ ] **Step 2: Run tests — expect failure (file not found)**

```bash
npx vitest run test/kbStore.test.ts
```

Expected: all tests FAIL with "Cannot find module '../src/lib/kbStore.svelte'"

- [ ] **Step 3: Implement kbStore.svelte.ts**

Create `packages/editor/src/lib/kbStore.svelte.ts`:

```typescript
export interface KBEntry {
  id: string;
  title: string;
  content: string;
  createdAt: string;
  updatedAt: string;
}

export interface KBDocument {
  version: number;
  entries: KBEntry[];
}

export function createKBStore() {
  const entries = $state<KBEntry[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/kb");
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: KBDocument = await resp.json();
      entries.length = 0;
      for (const e of doc.entries) entries.push(e);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createEntry(data: { title: string; content: string }): Promise<KBEntry> {
    const resp = await fetch("/api/kb", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    const entry: KBEntry = await resp.json();
    await init();
    return entry;
  }

  async function updateEntry(
    id: string,
    patch: { title?: string; content?: string },
  ): Promise<void> {
    const resp = await fetch(`/api/kb/${id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteEntry(id: string): Promise<void> {
    const resp = await fetch(`/api/kb/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get entries() { return entries as KBEntry[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createEntry,
    updateEntry,
    deleteEntry,
  };
}
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
npx vitest run test/kbStore.test.ts
```

Expected: `Tests  12 passed (12)`

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/kbStore.svelte.ts packages/editor/test/kbStore.test.ts
git commit -m "feat(kb): add kbStore with CRUD operations and tests"
```

---

## Task 3: Shared MarkdownEditor component + tests (TDD)

All commands run from `packages/editor/`.

**Files:**
- Create: `packages/editor/test/MarkdownEditor.test.ts`
- Create: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/MarkdownEditor.test.ts`:

```typescript
import { describe, it, expect } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import MarkdownEditor from "../src/lib/components/ui/MarkdownEditor.svelte";

describe("MarkdownEditor — preview mode", () => {
  it("renders markdown as HTML in preview mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "# Hello\n\nWorld", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview")).not.toBeNull();
    expect(target.querySelector(".md-preview h1")?.textContent?.trim()).toBe("Hello");
    expect(target.querySelector(".md-preview p")?.textContent?.trim()).toBe("World");
    unmount(app);
    target.remove();
  });

  it("shows placeholder when value is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: false, placeholder: "Start writing…" },
    });
    flushSync();
    expect(target.querySelector(".md-placeholder")?.textContent?.trim()).toBe("Start writing…");
    unmount(app);
    target.remove();
  });

  it("applies md-empty class when value is empty", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: false },
    });
    flushSync();
    expect(target.querySelector(".md-preview.md-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking preview switches to edit mode (textarea appears)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "some content", editing: false },
    });
    flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("MarkdownEditor — edit mode", () => {
  it("renders textarea with current value in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "# Hello", editing: true },
    });
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea).not.toBeNull();
    expect(textarea.value).toBe("# Hello");
    unmount(app);
    target.remove();
  });

  it("does not show preview div in edit mode", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: true },
    });
    flushSync();
    expect(target.querySelector(".md-preview")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("applies minHeight style to textarea", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "", editing: true, minHeight: "400px" },
    });
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    expect(textarea.style.minHeight).toBe("400px");
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests — expect failure (file not found)**

```bash
npx vitest run test/MarkdownEditor.test.ts
```

Expected: all tests FAIL with "Cannot find module"

- [ ] **Step 3: Implement MarkdownEditor.svelte**

Create `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`:

```svelte
<script lang="ts">
  import { marked } from "marked";
  import DOMPurify from "dompurify";

  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
  }

  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder = "Click to add markdown content…",
    minHeight = "200px",
  }: Props = $props();

  const renderedHtml = $derived(
    value.trim() ? DOMPurify.sanitize(marked(value) as string) : "",
  );
</script>

{#if editing}
  <textarea
    class="md-editor"
    style="min-height: {minHeight}"
    bind:value
    placeholder="Write in Markdown…"
  ></textarea>
{:else}
  <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
  <div
    class="md-preview {renderedHtml ? '' : 'md-empty'}"
    style="min-height: {minHeight}"
    onclick={() => { editing = true; }}
    title="Click to edit"
  >
    {#if renderedHtml}
      {@html renderedHtml}
    {:else}
      <span class="md-placeholder">{placeholder}</span>
    {/if}
  </div>
{/if}

<style>
  .md-editor {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; resize: vertical;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); color: var(--text);
    font-family: monospace; font-size: 12px; line-height: 1.5;
  }
  .md-editor:focus { outline: none; border-color: var(--accent); }

  .md-preview {
    width: 100%; box-sizing: border-box;
    padding: 10px 12px; overflow-y: auto;
    background: var(--surface-alt); border: 1px solid var(--border);
    border-radius: var(--radius-md); cursor: pointer;
    color: var(--text); font-family: var(--font-sans); font-size: 13px; line-height: 1.65;
  }
  .md-preview:hover { border-color: var(--accent); }
  .md-preview.md-empty { border-style: dashed; }

  .md-placeholder { color: var(--text-faint); font-size: 12px; font-style: italic; }

  .md-preview :global(h1) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 16px; }
  .md-preview :global(h2) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 14px; }
  .md-preview :global(h3) { color: var(--text); margin: 0.6em 0 0.3em; font-size: 13px; }
  .md-preview :global(p) { margin: 0.4em 0; }
  .md-preview :global(ul), .md-preview :global(ol) { margin: 0.4em 0; padding-left: 1.4em; }
  .md-preview :global(li) { margin: 0.2em 0; }
  .md-preview :global(code) {
    background: var(--surface-hover); border: 1px solid var(--border);
    border-radius: 3px; padding: 0 4px; font-size: 11px; font-family: monospace; color: var(--text);
  }
  .md-preview :global(pre) {
    background: var(--surface-hover); border: 1px solid var(--border);
    border-radius: var(--radius-sm); padding: 10px; overflow-x: auto; margin: 0.5em 0;
  }
  .md-preview :global(pre code) { background: none; border: none; padding: 0; }
  .md-preview :global(blockquote) {
    border-left: 3px solid var(--border); margin: 0.5em 0; padding: 2px 12px; color: var(--text-muted);
  }
  .md-preview :global(hr) { border: none; border-top: 1px solid var(--border); margin: 0.8em 0; }
  .md-preview :global(a) { color: var(--accent); }
  .md-preview :global(strong) { color: var(--text); }
  .md-preview :global(em) { color: var(--text-muted); }
  .md-preview :global(table) { border-collapse: collapse; width: 100%; margin: 0.5em 0; font-size: 12px; }
  .md-preview :global(th), .md-preview :global(td) { border: 1px solid var(--border); padding: 4px 8px; }
  .md-preview :global(th) { background: var(--surface-hover); }
</style>
```

- [ ] **Step 4: Run tests — expect all pass**

```bash
npx vitest run test/MarkdownEditor.test.ts
```

Expected: `Tests  7 passed (7)`

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte \
        packages/editor/test/MarkdownEditor.test.ts
git commit -m "feat(shared): add MarkdownEditor UI component with edit/preview toggle"
```

---

## Task 4: Refactor WorkModal to use MarkdownEditor

All commands run from `packages/editor/`.

**Files:**
- Modify: `packages/editor/src/lib/components/WorkModal.svelte`

- [ ] **Step 1: Replace imports in WorkModal script block**

In `packages/editor/src/lib/components/WorkModal.svelte`, replace the two markdown imports:

```typescript
  import { marked } from "marked";
  import DOMPurify from "dompurify";
```

with:

```typescript
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
```

- [ ] **Step 2: Remove the notesHtml derived**

Delete this block (around line 115):

```typescript
  const notesHtml = $derived(
    notes.trim() ? DOMPurify.sanitize(marked(notes) as string) : ""
  );
```

- [ ] **Step 3: Replace the notes tab template block**

Replace (lines 178–196 of WorkModal.svelte):

```svelte
  {:else if activeTab === "notes"}
    {#if editingNotes}
      <textarea class="native-input notes-area" bind:value={notes} placeholder="Markdown notes…"></textarea>
      {#if !isCreate}
        <Button variant="secondary" onclick={() => { editingNotes = false; }}>Done editing</Button>
      {/if}
    {:else}
      <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
      <div
        class="notes-preview {notes.trim() ? '' : 'notes-empty'}"
        onclick={() => { editingNotes = true; }}
        title="Click to edit"
      >
        {#if notes.trim()}
          {@html notesHtml}
        {:else}
          <span class="notes-placeholder">Click to add markdown notes…</span>
        {/if}
      </div>
    {/if}
```

with:

```svelte
  {:else if activeTab === "notes"}
    <MarkdownEditor
      bind:value={notes}
      bind:editing={editingNotes}
      placeholder="Click to add markdown notes…"
      minHeight="260px"
    />
    {#if editingNotes && !isCreate}
      <Button variant="secondary" onclick={() => { editingNotes = false; }}>Done editing</Button>
    {/if}
```

- [ ] **Step 4: Remove the markdown CSS from WorkModal's style block**

Delete these lines from WorkModal's `<style>` block (keeping everything else):

```css
  .notes-area { resize: none; min-height: 260px; font-family: monospace; font-size: 12px; line-height: 1.5; }

  .notes-preview {
    min-height: 260px; padding: 10px 12px; border-radius: var(--radius-md);
    background: var(--surface-alt); border: 1px solid var(--border); cursor: pointer; overflow-y: auto;
    color: var(--text); font-family: var(--font-sans); font-size: 13px; line-height: 1.65;
  }
  .notes-preview:hover { border-color: var(--accent); }
  .notes-preview.notes-empty { border-style: dashed; }
  .notes-placeholder { color: var(--text-faint); font-size: 12px; font-style: italic; }
  .notes-preview :global(h1), .notes-preview :global(h2), .notes-preview :global(h3) {
    color: var(--text); margin: 0.6em 0 0.3em; font-size: 14px;
  }
  .notes-preview :global(h1) { font-size: 16px; }
  .notes-preview :global(p) { margin: 0.4em 0; }
  .notes-preview :global(ul), .notes-preview :global(ol) { margin: 0.4em 0; padding-left: 1.4em; }
  .notes-preview :global(li) { margin: 0.2em 0; }
  .notes-preview :global(code) {
    background: var(--surface-hover); border: 1px solid var(--border); border-radius: 3px;
    padding: 0 4px; font-size: 11px; font-family: monospace; color: var(--text);
  }
  .notes-preview :global(pre) {
    background: var(--surface-hover); border: 1px solid var(--border); border-radius: var(--radius-sm);
    padding: 10px; overflow-x: auto; margin: 0.5em 0;
  }
  .notes-preview :global(pre code) { background: none; border: none; padding: 0; }
  .notes-preview :global(blockquote) {
    border-left: 3px solid var(--border); margin: 0.5em 0; padding: 2px 12px; color: var(--text-muted);
  }
  .notes-preview :global(hr) { border: none; border-top: 1px solid var(--border); margin: 0.8em 0; }
  .notes-preview :global(a) { color: var(--accent); }
  .notes-preview :global(strong) { color: var(--text); }
  .notes-preview :global(em) { color: var(--text-muted); }
```

- [ ] **Step 5: Run the full test suite to confirm no regressions**

```bash
npx vitest run
```

Expected: all 214 tests pass (207 existing + 7 MarkdownEditor tests)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/WorkModal.svelte
git commit -m "refactor(WorkModal): use shared MarkdownEditor component for notes tab"
```

---

## Task 5: KBPage component + tests (TDD)

All commands run from `packages/editor/`.

**Files:**
- Create: `packages/editor/test/KBPage.test.ts`
- Create: `packages/editor/src/lib/components/KBPage.svelte`

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/KBPage.test.ts`:

```typescript
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import KBPage from "../src/lib/components/KBPage.svelte";
import type { KBEntry } from "../src/lib/kbStore.svelte";

function makeEntry(overrides: Partial<KBEntry> = {}): KBEntry {
  return {
    id: "e1",
    title: "How to paint",
    content: "# Painting\n\nUse good brushes.",
    createdAt: "2026-06-28T10:00:00Z",
    updatedAt: "2026-06-28T10:00:00Z",
    ...overrides,
  };
}

function makeStore(entries: KBEntry[] = [], overrides: Partial<ReturnType<typeof makeStore>> = {}) {
  return {
    entries,
    loaded: true,
    loadError: null as string | null,
    createEntry: vi.fn().mockResolvedValue(
      makeEntry({ id: "new1", title: "New entry", content: "" }),
    ),
    updateEntry: vi.fn().mockResolvedValue(undefined),
    deleteEntry: vi.fn().mockResolvedValue(undefined),
    ...overrides,
  };
}

describe("KBPage — entry list", () => {
  it("shows empty state when nothing is selected", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(KBPage, { target, props: { store: makeStore([makeEntry()]) } });
    flushSync();
    expect(target.querySelector(".content-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("renders all entries in the sidebar", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([
      makeEntry({ id: "e1", title: "How to paint" }),
      makeEntry({ id: "e2", title: "Replace boiler" }),
    ]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const rows = target.querySelectorAll(".entry-row");
    expect(rows.length).toBe(2);
    expect(rows[0].textContent).toContain("How to paint");
    expect(rows[1].textContent).toContain("Replace boiler");
    unmount(app);
    target.remove();
  });

  it("filters entries by search query", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([
      makeEntry({ id: "e1", title: "How to paint" }),
      makeEntry({ id: "e2", title: "Replace boiler" }),
    ]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const searchInput = target.querySelector(".kb-sidebar input") as HTMLInputElement;
    searchInput.value = "paint";
    searchInput.dispatchEvent(new Event("input"));
    flushSync();
    const rows = target.querySelectorAll(".entry-row");
    expect(rows.length).toBe(1);
    expect(rows[0].textContent).toContain("How to paint");
    unmount(app);
    target.remove();
  });

  it("shows 'No matching entries.' when search has no results", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const searchInput = target.querySelector(".kb-sidebar input") as HTMLInputElement;
    searchInput.value = "zzz";
    searchInput.dispatchEvent(new Event("input"));
    flushSync();
    expect(target.querySelector(".list-empty")?.textContent).toContain("No matching entries.");
    unmount(app);
    target.remove();
  });
});

describe("KBPage — entry selection", () => {
  it("clicking an entry shows its title and content preview", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    expect(target.querySelector(".content-title")?.textContent?.trim()).toBe("How to paint");
    expect(target.querySelector(".md-preview")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("clicking Edit shows title input and textarea", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    const editBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Edit",
    ) as HTMLButtonElement;
    editBtn.click();
    flushSync();
    expect(target.querySelector(".title-input")).not.toBeNull();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — save / cancel", () => {
  it("Save calls updateEntry with draft values and exits edit mode", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Save",
      ) as HTMLButtonElement
    ).click();
    await tick();
    flushSync();
    expect(store.updateEntry).toHaveBeenCalledWith("e1", {
      title: "How to paint",
      content: "# Painting\n\nUse good brushes.",
    });
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(target.querySelector(".content-title")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("Cancel reverts drafts and exits edit mode without saving", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Edit",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "Changed content";
    textarea.dispatchEvent(new Event("input"));
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Cancel",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(store.updateEntry).not.toHaveBeenCalled();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(target.querySelector(".md-preview")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — delete", () => {
  it("delete button shows confirmation then calls deleteEntry", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.title === "Delete entry",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(target.querySelector(".confirm-text")).not.toBeNull();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "✓",
      ) as HTMLButtonElement
    ).click();
    await tick();
    flushSync();
    expect(store.deleteEntry).toHaveBeenCalledWith("e1");
    expect(target.querySelector(".content-empty")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("cancel delete hides confirmation without deleting", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore([makeEntry()]);
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    (target.querySelector(".entry-row") as HTMLElement).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.title === "Delete entry",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    (
      Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "✕",
      ) as HTMLButtonElement
    ).click();
    flushSync();
    expect(store.deleteEntry).not.toHaveBeenCalled();
    expect(target.querySelector(".confirm-text")).toBeNull();
    unmount(app);
    target.remove();
  });
});

describe("KBPage — create new entry", () => {
  it("＋ New button calls createEntry and enters edit mode", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const newEntry = makeEntry({ id: "new1", title: "New entry", content: "" });
    const store = makeStore([], {
      createEntry: vi.fn().mockResolvedValue(newEntry),
    });
    // After createEntry resolves, store.entries will have the new item
    // (in real app init() refreshes; here we mutate entries manually to simulate)
    const app = mount(KBPage, { target, props: { store } });
    flushSync();
    const newBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "＋ New",
    ) as HTMLButtonElement;
    newBtn.click();
    await tick();
    flushSync();
    expect(store.createEntry).toHaveBeenCalledWith({ title: "New entry", content: "" });
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests — expect failure (file not found)**

```bash
npx vitest run test/KBPage.test.ts
```

Expected: all tests FAIL with "Cannot find module '../src/lib/components/KBPage.svelte'"

- [ ] **Step 3: Implement KBPage.svelte**

Create `packages/editor/src/lib/components/KBPage.svelte`:

```svelte
<script lang="ts">
  import type { createKBStore, KBEntry } from "../kbStore.svelte";
  import MarkdownEditor from "./ui/MarkdownEditor.svelte";
  import Button from "./ui/Button.svelte";
  import Input from "./ui/Input.svelte";

  type KBStore = ReturnType<typeof createKBStore>;
  interface Props { store: KBStore; }
  let { store }: Props = $props();

  let selectedId = $state<string | null>(null);
  let editing = $state(false);
  let draftTitle = $state("");
  let draftContent = $state("");
  let confirmDelete = $state(false);
  let saving = $state(false);
  let error = $state<string | null>(null);
  let searchQuery = $state("");

  const filteredEntries = $derived(
    store.entries.filter((e) =>
      e.title.toLowerCase().includes(searchQuery.toLowerCase()),
    ),
  );

  const selectedEntry = $derived(
    selectedId ? (store.entries.find((e) => e.id === selectedId) ?? null) : null,
  );

  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    editing = false;
    confirmDelete = false;
    error = null;
  }

  async function handleNew(): Promise<void> {
    try {
      const entry = await store.createEntry({ title: "New entry", content: "" });
      selectEntry(entry);
      editing = true;
    } catch (e) {
      error = e instanceof Error ? e.message : "Create failed";
    }
  }

  async function handleSave(): Promise<void> {
    if (!selectedId || !draftTitle.trim()) return;
    saving = true;
    error = null;
    try {
      await store.updateEntry(selectedId, {
        title: draftTitle.trim(),
        content: draftContent,
      });
      editing = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Save failed";
    } finally {
      saving = false;
    }
  }

  function handleCancel(): void {
    if (selectedEntry) {
      draftTitle = selectedEntry.title;
      draftContent = selectedEntry.content;
    }
    editing = false;
    error = null;
  }

  async function handleDelete(): Promise<void> {
    if (!selectedId) return;
    try {
      await store.deleteEntry(selectedId);
      selectedId = null;
      editing = false;
      confirmDelete = false;
    } catch (e) {
      error = e instanceof Error ? e.message : "Delete failed";
    }
  }

  function fmtDate(iso: string): string {
    return new Date(iso).toLocaleDateString(undefined, { month: "short", day: "numeric" });
  }
</script>

<div class="kb-page">
  <div class="kb-sidebar">
    <div class="sidebar-toolbar">
      <Input placeholder="🔍 Search…" bind:value={searchQuery} />
      <Button onclick={handleNew}>＋ New</Button>
    </div>
    <div class="entry-list">
      {#each filteredEntries as entry (entry.id)}
        <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_static_element_interactions -->
        <div
          class="entry-row"
          class:active={entry.id === selectedId}
          onclick={() => selectEntry(entry)}
        >
          <div class="entry-title">{entry.title}</div>
          <div class="entry-date">{fmtDate(entry.updatedAt)}</div>
        </div>
      {:else}
        <div class="list-empty">
          {searchQuery ? "No matching entries." : "No entries yet."}
        </div>
      {/each}
    </div>
  </div>

  <div class="kb-content">
    {#if !selectedEntry}
      <div class="content-empty">Select an entry or create one</div>
    {:else}
      <div class="content-header">
        {#if editing}
          <input class="title-input" bind:value={draftTitle} placeholder="Entry title" />
        {:else}
          <h1 class="content-title">{selectedEntry.title}</h1>
        {/if}
        <div class="header-actions">
          {#if !editing}
            <Button variant="secondary" onclick={() => { editing = true; }}>Edit</Button>
          {/if}
          {#if confirmDelete}
            <span class="confirm-text">Delete?</span>
            <Button variant="danger" onclick={handleDelete}>✓</Button>
            <Button variant="ghost" onclick={() => { confirmDelete = false; }}>✕</Button>
          {:else}
            <Button variant="ghost" onclick={() => { confirmDelete = true; }} title="Delete entry">🗑</Button>
          {/if}
        </div>
      </div>

      <div class="content-body">
        <MarkdownEditor
          bind:value={draftContent}
          bind:editing
          placeholder="Start writing in Markdown…"
        />
      </div>

      {#if error}
        <div class="content-error">{error}</div>
      {/if}

      {#if editing}
        <div class="content-footer">
          <Button variant="primary" disabled={saving} onclick={handleSave}>
            {saving ? "Saving…" : "Save"}
          </Button>
          <Button variant="secondary" onclick={handleCancel}>Cancel</Button>
        </div>
      {/if}
    {/if}
  </div>
</div>

<style>
  .kb-page { display: flex; height: 100%; background: var(--bg); font-family: var(--font-sans); }

  .kb-sidebar {
    width: 260px; flex-shrink: 0;
    display: flex; flex-direction: column;
    border-right: 1px solid var(--border);
  }
  .sidebar-toolbar {
    display: flex; gap: var(--space-2); padding: var(--space-3);
    border-bottom: 1px solid var(--border); flex-shrink: 0; align-items: center;
  }
  .sidebar-toolbar :global(.ui-input) { flex: 1; }

  .entry-list {
    flex: 1; overflow-y: auto; padding: var(--space-2);
    display: flex; flex-direction: column; gap: 2px;
  }
  .entry-row {
    padding: 8px 10px; border-radius: var(--radius-md);
    cursor: pointer; border-left: 3px solid transparent;
  }
  .entry-row:hover { background: var(--surface-hover); }
  .entry-row.active { background: var(--surface-alt); border-left-color: var(--accent); }
  .entry-title { font-size: 13px; color: var(--text); font-weight: 500; }
  .entry-date { font-size: 11px; color: var(--text-faint); margin-top: 2px; }
  .list-empty { font-size: 12px; color: var(--text-faint); text-align: center; padding: 20px 0; }

  .kb-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
  .content-empty {
    flex: 1; display: flex; align-items: center; justify-content: center;
    color: var(--text-faint); font-size: 13px;
  }

  .content-header {
    display: flex; align-items: center; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-bottom: 1px solid var(--border); flex-shrink: 0;
  }
  .content-title { flex: 1; font-size: 18px; font-weight: 600; color: var(--text); margin: 0; }
  .title-input {
    flex: 1; background: var(--surface-alt); border: 1px solid var(--accent);
    border-radius: var(--radius-md); color: var(--text);
    font-size: 16px; font-weight: 600; padding: 6px 10px; font-family: var(--font-sans);
  }
  .title-input:focus { outline: none; }
  .header-actions { display: flex; align-items: center; gap: var(--space-1); flex-shrink: 0; }
  .confirm-text { font-size: 11px; color: var(--danger); }

  .content-body {
    flex: 1; overflow: hidden; padding: var(--space-4);
    display: flex; flex-direction: column;
  }
  .content-body :global(.md-preview),
  .content-body :global(.md-editor) { flex: 1; }

  .content-error { padding: 0 var(--space-4); font-size: 11px; color: var(--danger); }
  .content-footer {
    display: flex; gap: var(--space-2);
    padding: var(--space-3) var(--space-4);
    border-top: 1px solid var(--border); flex-shrink: 0;
  }
</style>
```

- [ ] **Step 4: Run KBPage tests — expect all pass**

```bash
npx vitest run test/KBPage.test.ts
```

Expected: `Tests  11 passed (11)`

- [ ] **Step 5: Run full suite to confirm no regressions**

```bash
npx vitest run
```

Expected: all tests pass (214 existing + 11 KBPage tests = 225+)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): add two-panel KBPage component with edit/preview and delete"
```

---

## Task 6: Wire NavMenu, App.svelte routing, and final verification

All commands run from `packages/editor/`.

**Files:**
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`
- Modify: `packages/editor/src/App.svelte`

- [ ] **Step 1: Add the KB nav entry to NavMenu**

In `packages/editor/src/lib/components/NavMenu.svelte`, add `#/kb` after Works in the `modules` array:

```typescript
  const modules = [
    { href: "#/",            icon: "🏡", label: "Home"             },
    { href: "#/plan",        icon: "📐", label: "Floor Plan"       },
    { href: "#/chores",      icon: "✅", label: "Chores"           },
    { href: "#/inventory",   icon: "📦", label: "Inventory"        },
    { href: "#/consumables", icon: "🛒", label: "Consumables"      },
    { href: "#/works",       icon: "🔧", label: "Works"            },
    { href: "#/kb",          icon: "📖", label: "Knowledge Base"   },
    { href: "#/costs",       icon: "💶", label: "Costs"            },
  ];
```

- [ ] **Step 2: Add store import and instantiation to App.svelte**

In `packages/editor/src/App.svelte`, add these two lines after the `worksStore` imports (around lines 39–52):

After the existing import block (around line 42):
```typescript
  import { createKBStore } from "./lib/kbStore.svelte";
  import KBPage from "./lib/components/KBPage.svelte";
```

After `const worksStore = createWorksStore();` (around line 52):
```typescript
  const kbStore = createKBStore();
```

- [ ] **Step 3: Add the #/kb route block to App.svelte**

In `packages/editor/src/App.svelte`, find the Works route block:

```svelte
      {:else if currentRoute === "#/works"}
        <WorksPage
          store={worksStore}
          ...
        />

      {:else if currentRoute === "#/costs"}
```

Add the KB route between Works and Costs:

```svelte
      {:else if currentRoute === "#/works"}
        <WorksPage
          store={worksStore}
          {settingsStore}
          onplaceonmap={(workId) => {
            placingWorkId = workId;
            const next = new Set(activeLayers);
            next.add("works");
            activeLayers = next;
            window.location.hash = "#/";
          }}
        />

      {:else if currentRoute === "#/kb"}
        <KBPage store={kbStore} />

      {:else if currentRoute === "#/costs"}
```

- [ ] **Step 4: Run the full test suite**

```bash
npx vitest run
```

Expected: all tests pass. The count should be 207 (pre-existing) + 7 (MarkdownEditor) + 12 (kbStore) + 11 (KBPage) = 237 tests.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/NavMenu.svelte packages/editor/src/App.svelte
git commit -m "feat(kb): wire KBPage into nav and routing"
```

---

## Self-Review

**Spec coverage check:**
- ✅ Data model (`KBEntry`, `KBDocument`, `KBCreate`, `KBUpdate`) — Task 1
- ✅ API endpoints (GET, POST, PUT, DELETE `/api/kb`) — Task 1
- ✅ Persistence to `kb.json` with atomic write — Task 1
- ✅ `kbStore` with `createEntry` returning `KBEntry` — Task 2
- ✅ `MarkdownEditor` shared component (preview/edit toggle, placeholder, minHeight, styles) — Task 3
- ✅ `WorkModal` refactored to use `MarkdownEditor`, no duplicate markdown CSS — Task 4
- ✅ `KBPage` two-panel layout (sidebar + content) — Task 5
- ✅ Entry list with search filter — Task 5
- ✅ Select entry → show title + rendered content — Task 5
- ✅ Edit → title input + textarea + Save/Cancel footer — Task 5
- ✅ Delete with inline confirm — Task 5
- ✅ Create new entry → select + enter edit mode — Task 5
- ✅ NavMenu `#/kb` entry with 📖 icon — Task 6
- ✅ App.svelte store + route wiring — Task 6
- ✅ Tests: kbStore (12), MarkdownEditor (7), KBPage (11) — Tasks 2, 3, 5

**No placeholders, no TBDs found.**

**Type consistency:**
- `KBEntry.id/title/content/createdAt/updatedAt` used consistently across backend, store, and components
- `store.createEntry({ title, content })` returns `KBEntry` — used in `handleNew` to call `selectEntry(entry)`
- `store.updateEntry(id, { title?, content? })` — matches `KBUpdate` model
- `store.deleteEntry(id)` — void, no return value
- `.entry-row`, `.content-empty`, `.content-title`, `.title-input`, `.confirm-text`, `.md-preview`, `.md-editor`, `.list-empty` — all CSS class names match what tests query for
