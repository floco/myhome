# KB Editing Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give the Knowledge Base editor autosave (with save-blocked navigation), double-click-to-edit, and "reopen the page you last viewed" behavior.

**Architecture:** Two new small standalone modules (`navGuard.ts` — a nav-guard registry plus a testable guarded hash-change router; `kbLastPage.ts` — a per-home localStorage helper), one new prop on the existing `MarkdownEditor.svelte`, and a rewrite of `KBPage.svelte`'s save/edit-mode logic from manual Save/Cancel/Edit buttons to a debounced autosave engine with a status indicator and a single "Done" button. `App.svelte`'s hash-change listener is swapped for the new guarded router so leaving the KB module while a save is pending/failing is blocked (and auto-completes once the save succeeds).

**Tech Stack:** Svelte 5 (runes: `$state`, `$derived`, `$effect`), TypeScript, Vitest + `svelte`'s `mount`/`unmount`/`flushSync` test helpers, svelte-i18n.

## Global Constraints

- Frontend-only (`packages/editor`) — no backend/API changes; reuse `kbStore.updateEntry`'s existing PUT endpoint as-is.
- `MarkdownEditor.svelte`'s two other consumers (`WorkModal.svelte`, `InsuranceModal.svelte`) must keep their exact current single-click behavior — the new `editTrigger` prop must default to `"click"`.
- Follow the existing i18n key convention: add new keys to **both** `packages/editor/src/lib/locales/en.json` and `fr.json`; reuse an existing key (e.g. cross-module keys like `works.modal.doneEditing`) where one already fits, matching the pattern already used elsewhere in `KBPage.svelte` (e.g. `chores.editModal.media`).
- Test files live in `packages/editor/test/<Name>.test.ts`; run with `cd packages/editor && npx vitest run test/<Name>.test.ts` for a single file or `npx vitest run` for the full suite from `packages/editor`.
- No placeholders/TODOs; every step below has the exact code to write.

---

## Task 1: `navGuard.ts` — nav-guard registry + guarded hash router

**Files:**
- Create: `packages/editor/src/lib/navGuard.ts`
- Test: `packages/editor/test/navGuard.test.ts`

**Interfaces:**
- Produces: `setNavGuard(fn: (() => Promise<boolean>) | null): void`, `getNavGuard(): (() => Promise<boolean>) | null`, `createGuardedHashRouter(opts: { getHash: () => string; setHash: (hash: string) => void; onRoute: (hash: string) => void }): { handleHashChange: () => void }` — all exported from `packages/editor/src/lib/navGuard.ts`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/navGuard.test.ts`:

```ts
import { describe, it, expect, afterEach } from "vitest";
import { setNavGuard, createGuardedHashRouter } from "../src/lib/navGuard";

afterEach(() => setNavGuard(null));

describe("navGuard — createGuardedHashRouter", () => {
  it("routes immediately when no guard is registered", () => {
    let hash = "#/kb/a";
    const routes: string[] = [];
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; },
      onRoute: (h) => { routes.push(h); },
    });
    hash = "#/costs";
    router.handleHashChange();
    expect(routes).toEqual(["#/costs"]);
    expect(hash).toBe("#/costs");
  });

  it("reverts the hash when a guard is registered, then replays the target hash once the guard resolves true", async () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; router.handleHashChange(); },
      onRoute: (h) => { routes.push(h); },
    });
    let resolveGuard!: (ok: boolean) => void;
    setNavGuard(() => new Promise((resolve) => { resolveGuard = resolve; }));

    hash = "#/costs"; // simulates the browser having already applied the navigation
    router.handleHashChange();

    // Reverted synchronously; the fake setHash echoes back into the router,
    // which recognizes its own revert and just resyncs onRoute.
    expect(hash).toBe("#/kb/a");
    expect(routes).toEqual(["#/kb/a"]);

    resolveGuard(true);
    await Promise.resolve();
    await Promise.resolve();

    expect(hash).toBe("#/costs");
    expect(routes).toEqual(["#/kb/a", "#/costs"]);
  });

  it("stays on the current route when the guard resolves false", async () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; router.handleHashChange(); },
      onRoute: (h) => { routes.push(h); },
    });
    setNavGuard(async () => false);

    hash = "#/costs";
    router.handleHashChange();
    await Promise.resolve();
    await Promise.resolve();

    expect(hash).toBe("#/kb/a");
    expect(routes).toEqual(["#/kb/a"]);
  });

  it("does nothing when the new hash equals the current route (no-op navigation)", () => {
    const routes: string[] = [];
    let hash = "#/kb/a";
    const router = createGuardedHashRouter({
      getHash: () => hash,
      setHash: (h) => { hash = h; },
      onRoute: (h) => { routes.push(h); },
    });
    setNavGuard(async () => false); // guard present but should never be consulted
    router.handleHashChange();
    expect(routes).toEqual(["#/kb/a"]);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/navGuard.test.ts`
Expected: FAIL — `../src/lib/navGuard` does not exist.

- [ ] **Step 3: Implement `navGuard.ts`**

Create `packages/editor/src/lib/navGuard.ts`:

```ts
export type NavGuardFn = () => Promise<boolean>;

let activeGuard: NavGuardFn | null = null;

/** Registers the single active nav guard (only one top-level module is ever mounted at a time). */
export function setNavGuard(fn: NavGuardFn | null): void {
  activeGuard = fn;
}

export function getNavGuard(): NavGuardFn | null {
  return activeGuard;
}

export interface GuardedHashRouterOptions {
  getHash: () => string;
  setHash: (hash: string) => void;
  onRoute: (hash: string) => void;
}

/**
 * Wraps hash-change handling so that, when a guard is registered, a route
 * change is provisionally reverted while the guard runs (e.g. flushing a
 * pending autosave); on success the originally-attempted route is replayed,
 * on failure the app stays on the current route.
 */
export function createGuardedHashRouter(opts: GuardedHashRouterOptions): { handleHashChange: () => void } {
  let currentRoute = opts.getHash();
  let suppress = false;

  function handleHashChange(): void {
    const newHash = opts.getHash();

    if (suppress) {
      suppress = false;
      currentRoute = newHash;
      opts.onRoute(newHash);
      return;
    }

    if (newHash === currentRoute) {
      opts.onRoute(newHash);
      return;
    }

    const guard = getNavGuard();
    if (!guard) {
      currentRoute = newHash;
      opts.onRoute(newHash);
      return;
    }

    const attempted = newHash;
    const previous = currentRoute;
    suppress = true;
    opts.setHash(previous);
    guard().then((ok) => {
      if (ok) {
        suppress = true;
        opts.setHash(attempted);
      }
    });
  }

  return { handleHashChange };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/navGuard.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/navGuard.ts packages/editor/test/navGuard.test.ts
git commit -m "feat(kb): add nav-guard registry and guarded hash router"
```

---

## Task 2: `kbLastPage.ts` — per-home last-viewed-page storage

**Files:**
- Create: `packages/editor/src/lib/kbLastPage.ts`
- Test: `packages/editor/test/kbLastPage.test.ts`

**Interfaces:**
- Produces: `getStoredLastPageId(homeId: string): string | null`, `setStoredLastPageId(homeId: string, pageId: string): void`, `clearStoredLastPageId(homeId: string): void` — all exported from `packages/editor/src/lib/kbLastPage.ts`.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/kbLastPage.test.ts`:

```ts
import { describe, it, expect, beforeEach } from "vitest";
import { getStoredLastPageId, setStoredLastPageId, clearStoredLastPageId } from "../src/lib/kbLastPage";

beforeEach(() => localStorage.clear());

describe("kbLastPage", () => {
  it("returns null when nothing is stored for a home", () => {
    expect(getStoredLastPageId("home-1")).toBeNull();
  });

  it("stores and retrieves a page id scoped to a home", () => {
    setStoredLastPageId("home-1", "page-a");
    expect(getStoredLastPageId("home-1")).toBe("page-a");
    expect(getStoredLastPageId("home-2")).toBeNull();
  });

  it("overwrites the previous value for the same home", () => {
    setStoredLastPageId("home-1", "page-a");
    setStoredLastPageId("home-1", "page-b");
    expect(getStoredLastPageId("home-1")).toBe("page-b");
  });

  it("clears the stored value for a home without affecting other homes", () => {
    setStoredLastPageId("home-1", "page-a");
    setStoredLastPageId("home-2", "page-c");
    clearStoredLastPageId("home-1");
    expect(getStoredLastPageId("home-1")).toBeNull();
    expect(getStoredLastPageId("home-2")).toBe("page-c");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/kbLastPage.test.ts`
Expected: FAIL — `../src/lib/kbLastPage` does not exist.

- [ ] **Step 3: Implement `kbLastPage.ts`**

Create `packages/editor/src/lib/kbLastPage.ts`:

```ts
const STORAGE_PREFIX = "myhome-kb-last-page-";

/** Reads the last-viewed KB page id for a home, or null if none is stored. */
export function getStoredLastPageId(homeId: string): string | null {
  return localStorage.getItem(STORAGE_PREFIX + homeId);
}

/** Persists the last-viewed KB page id for a home. */
export function setStoredLastPageId(homeId: string, pageId: string): void {
  localStorage.setItem(STORAGE_PREFIX + homeId, pageId);
}

/** Clears the stored last-viewed page id for a home (e.g. after it's deleted). */
export function clearStoredLastPageId(homeId: string): void {
  localStorage.removeItem(STORAGE_PREFIX + homeId);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/kbLastPage.test.ts`
Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/kbLastPage.ts packages/editor/test/kbLastPage.test.ts
git commit -m "feat(kb): add per-home last-viewed-page localStorage helper"
```

---

## Task 3: `MarkdownEditor.svelte` — `editTrigger` prop (click vs double-click)

**Files:**
- Modify: `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`
- Test: `packages/editor/test/MarkdownEditor.test.ts`

**Interfaces:**
- Consumes: nothing new.
- Produces: new optional prop `editTrigger?: "click" | "dblclick"` on `MarkdownEditor`, default `"click"`. When `clickToEdit` is true and `editTrigger` is `"click"`, behavior is identical to today (single click enters edit mode). When `editTrigger` is `"dblclick"`, a single click does nothing and a double-click enters edit mode. Keyboard activation (Enter/Space when the preview has focus) is unaffected by `editTrigger`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/MarkdownEditor.test.ts`, inside (or after) the existing `describe("MarkdownEditor — clickToEdit", ...)` block:

```ts
describe("MarkdownEditor — editTrigger", () => {
  it("double-click enters edit mode when editTrigger is dblclick", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, editTrigger: "dblclick" },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });

  it("a single click does not enter edit mode when editTrigger is dblclick", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false, editTrigger: "dblclick" },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    unmount(app);
    target.remove();
  });

  it("defaults to single-click behavior when editTrigger is omitted", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = mount(MarkdownEditor, {
      target,
      props: { value: "content", editing: false },
    });
    flushSync();
    (target.querySelector(".md-preview") as HTMLElement).click();
    flushSync();
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/MarkdownEditor.test.ts`
Expected: FAIL — the two new `editTrigger: "dblclick"` tests fail (single click still enters edit mode since `editTrigger` isn't wired yet).

- [ ] **Step 3: Add the `editTrigger` prop**

In `packages/editor/src/lib/components/ui/MarkdownEditor.svelte`, update the `Props` interface (around line 32-42):

```ts
  interface Props {
    value: string;
    editing: boolean;
    placeholder?: string;
    minHeight?: string;
    mediaItems?: MediaItem[];
    clickToEdit?: boolean;
    editTrigger?: "click" | "dblclick";
    resolveKbLink?: (id: string) => { title: string; icon: string } | null;
    onSlashPage?: () => Promise<{ id: string; title: string } | null>;
    onInsertBookmark?: () => Promise<string | null>;
  }
```

Update the destructure (around line 44-54):

```ts
  let {
    value = $bindable(),
    editing = $bindable(),
    placeholder,
    minHeight = "200px",
    mediaItems = [],
    clickToEdit = true,
    editTrigger = "click",
    resolveKbLink,
    onSlashPage,
    onInsertBookmark,
  }: Props = $props();
```

Update the preview `<div>` (around line 237-254) to split the enter-edit handler between `onclick` and `ondblclick` based on `editTrigger`:

```svelte
  <div
    role={clickToEdit ? "button" : undefined}
    tabindex={clickToEdit ? 0 : undefined}
    class="md-preview"
    class:md-clickable={clickToEdit}
    class:md-empty={!renderedHtml}
    style:min-height={minHeight}
    onclick={clickToEdit && editTrigger === "click" ? () => { editing = true; } : undefined}
    ondblclick={clickToEdit && editTrigger === "dblclick" ? () => { editing = true; } : undefined}
    onkeydown={clickToEdit ? (e) => { if (e.key === "Enter" || e.key === " ") editing = true; } : undefined}
    title={clickToEdit ? $_('markdownEditor.clickToEdit') : undefined}
  >
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/MarkdownEditor.test.ts`
Expected: PASS (all tests, including the 3 new `editTrigger` ones and the pre-existing `clickToEdit` ones unchanged)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/ui/MarkdownEditor.svelte packages/editor/test/MarkdownEditor.test.ts
git commit -m "feat(markdown-editor): add editTrigger prop for click vs double-click"
```

---

## Task 4: `KBPage.svelte` — reopen the last-viewed page

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `getStoredLastPageId`, `setStoredLastPageId`, `clearStoredLastPageId` from Task 2's `packages/editor/src/lib/kbLastPage.ts`; `homesStore.activeHomeId` (already imported in `KBPage.svelte`).
- Produces: navigating to bare `#/kb` (no `selectedItemId`) auto-redirects to the last-viewed page for the active home, if it still exists; every page selection persists as the new "last viewed" page.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/KBPage.test.ts`, after the `describe("KBPage — selection and deep links", ...)` block:

```ts
describe("KBPage — reopen last-viewed page", () => {
  beforeEach(() => localStorage.clear());

  it("redirects to the stored last-viewed page when opened with no page id", async () => {
    localStorage.setItem("myhome-kb-last-page-home-1", "e2");
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Second page", order: 1 })];
    const onnavigate = vi.fn();
    const { target, comp } = await setup(entries, { onnavigate });
    await tick(); flushSync();
    expect(onnavigate).toHaveBeenCalledWith("e2");
    unmount(comp); target.remove();
  });

  it("falls back to the empty-state placeholder and clears the stale id when the stored page no longer exists", async () => {
    localStorage.setItem("myhome-kb-last-page-home-1", "gone");
    const onnavigate = vi.fn();
    const { target, comp } = await setup([makeEntry()], { onnavigate });
    await tick(); flushSync();
    expect(onnavigate).not.toHaveBeenCalled();
    expect(localStorage.getItem("myhome-kb-last-page-home-1")).toBeNull();
    expect(target.textContent).toContain("Select a page or create one");
    unmount(comp); target.remove();
  });

  it("does not redirect when a page id is already given in the URL (deep link wins)", async () => {
    localStorage.setItem("myhome-kb-last-page-home-1", "e1");
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Second page", order: 1 })];
    const onnavigate = vi.fn();
    const { target, comp } = await setup(entries, { selectedItemId: "e2", onnavigate });
    await tick(); flushSync();
    expect(onnavigate).not.toHaveBeenCalled();
    expect(target.querySelector(".content-title")?.textContent).toBe("Second page");
    unmount(comp); target.remove();
  });

  it("persists the selected page as the new last-viewed page when a tree row is clicked", async () => {
    const entries = [makeEntry(), makeEntry({ id: "e2", title: "Second page", order: 1 })];
    const { target, comp } = await setup(entries);
    const rows = target.querySelectorAll(".tree-row");
    (rows[1] as HTMLElement).click();
    await tick(); flushSync();
    expect(localStorage.getItem("myhome-kb-last-page-home-1")).toBe("e2");
    unmount(comp); target.remove();
  });
});
```

Note: `setup()` in this test file creates the store with `createKBStore(() => HOME)` where `HOME = "home-1"` — but `KBPage.svelte` reads the active home id from `homesStore.activeHomeId` directly (not from the `store` prop), for building the localStorage key. `homesStore` (defined in `packages/editor/src/lib/homesStore.svelte.ts`) is a module-level singleton imported by `KBPage.svelte`, so the test file needs to set its `activeHomeId` before mounting. It exposes `setActiveHomeId(id: string): void` and `_reset(): void` (no `homes` array population is needed here, since `KBPage` only reads `activeHomeId`, not `homesStore.homes`).

Add this import at the top of `packages/editor/test/KBPage.test.ts` (immediately after the existing imports, before the `HOME` constant):

```ts
import { homesStore } from "../src/lib/homesStore.svelte";
```

And add a top-level `beforeEach`, next to the existing `afterEach(() => vi.unstubAllGlobals());` line:

```ts
beforeEach(() => {
  homesStore._reset();
  homesStore.setActiveHomeId(HOME);
});
```

(This requires importing `beforeEach` from `"vitest"` in the existing top import line, which today only imports `describe, it, expect, vi, afterEach`.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — the 4 new tests in `describe("KBPage — reopen last-viewed page", ...)` fail (no redirect logic exists yet); other existing tests still pass.

- [ ] **Step 3: Implement the redirect + persistence**

In `packages/editor/src/lib/components/KBPage.svelte`, add the import near the top (after the existing `import { homesStore } from "../homesStore.svelte";` line):

```ts
  import { getStoredLastPageId, setStoredLastPageId, clearStoredLastPageId } from "../kbLastPage";
```

Add persistence to `selectEntry` (the function currently reads, around line 74-84):

```ts
  function selectEntry(entry: KBEntry): void {
    selectedId = entry.id;
    draftTitle = entry.title;
    draftContent = entry.content;
    draftIcon = entry.icon;
    editing = false;
    confirmDelete = null;
    contentTab = "content";
    contentMode = "page";
    error = null;
    const homeId = homesStore.activeHomeId;
    if (homeId) setStoredLastPageId(homeId, entry.id);
  }
```

Add a new `$effect` for the redirect, placed after the existing reconciliation `$effect` (the one with the long comment about `pendingNavigateId`, ending around line 127):

```ts
  // On a bare "#/kb" open (no page id in the URL), redirect to whichever
  // page was last viewed in this browser for the active home, once entries
  // have actually loaded. Runs at most once per mount; a deep-linked
  // selectedItemId always wins and skips this entirely.
  let lastPageRedirectAttempted = $state(false);

  $effect(() => {
    if (lastPageRedirectAttempted) return;
    if (selectedItemId) { lastPageRedirectAttempted = true; return; }
    if (!store.loaded) return;
    lastPageRedirectAttempted = true;
    const homeId = homesStore.activeHomeId;
    if (!homeId) return;
    const storedId = getStoredLastPageId(homeId);
    if (!storedId) return;
    const found = store.entries.find((e) => e.id === storedId);
    if (found) {
      navigate(found);
    } else {
      clearStoredLastPageId(homeId);
    }
  });
```

This references `navigate`, which is a function declared later in the same `<script>` block — safe, since function declarations are hoisted and this effect only runs after the whole script has executed once.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests, including the 4 new ones)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): reopen the last-viewed page when returning to the KB module"
```

---

## Task 5: `KBPage.svelte` — autosave engine, double-click-to-edit, Done button

This is the core rewrite: replaces the manual Save/Cancel/Edit buttons with a debounced autosave, a save-status indicator, a double-click-to-edit preview, and a single "Done" button to return to preview.

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: Task 3's `MarkdownEditor` `editTrigger` prop.
- Produces: `flushSave(): Promise<boolean>` (module-private to `KBPage.svelte`, awaited by Task 6 and Task 7); `saveStatus` state (`"idle" | "pending" | "saving" | "saved" | "error"`, exposed only via rendered text/classes, not as a prop).

- [ ] **Step 1: Write the failing tests**

First, update the two existing tests in `packages/editor/test/KBPage.test.ts` that rely on the soon-to-be-removed explicit "Edit" button (`describe("KBPage — insert bookmark", ...)`, both `it` blocks use `target.querySelector('[title="Edit"]')`). Replace:

```ts
    const editBtn = target.querySelector('[title="Edit"]') as HTMLElement;
    editBtn.click();
    flushSync();
```

with:

```ts
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
```

in both of those two tests.

Then add a new `describe` block to `packages/editor/test/KBPage.test.ts`:

```ts
describe("KBPage — autosave", () => {
  function enterEditMode(target: HTMLElement): void {
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
  }

  it("double-click on the preview enters edit mode; there is no separate Edit button", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector('[title="Edit"]')).toBeNull();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    enterEditMode(target);
    expect(target.querySelector("textarea.md-editor")).not.toBeNull();
    unmount(comp); target.remove();
  });

  it("saves automatically ~1.2s after the user stops typing, without a Save button", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    expect(target.querySelector('[title="Save"]')).toBeNull();
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    expect(target.textContent).toContain("Saving");
    await new Promise((r) => setTimeout(r, 1300));
    flushSync();
    await tick(); flushSync();
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    unmount(comp); target.remove();
  });

  it("shows a Saved indicator after a successful autosave", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    await new Promise((r) => setTimeout(r, 1300));
    await tick(); flushSync();
    expect(target.textContent).toContain("Saved");
    unmount(comp); target.remove();
  });

  it("does not autosave when the draft is unchanged from the loaded entry", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    await new Promise((r) => setTimeout(r, 1300));
    flushSync();
    expect(target.textContent).not.toContain("Saving");
    unmount(comp); target.remove();
  });

  it("the Done button flushes any pending save and returns to preview", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    (target.querySelector('[title="Done editing"]') as HTMLElement).click();
    await tick(); flushSync(); await tick(); flushSync();
    expect(target.querySelector("textarea.md-editor")).toBeNull();
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    unmount(comp); target.remove();
  });

  it("blocks an empty title from being saved and shows an error instead", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const titleInput = target.querySelector(".title-input") as HTMLInputElement;
    titleInput.value = "   ";
    titleInput.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    await new Promise((r) => setTimeout(r, 1300));
    await tick(); flushSync();
    expect(target.textContent).toContain("Title cannot be empty");
    expect(store.entries.find((e) => e.id === "e1")?.title).toBe("How to paint");
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — the two updated "insert bookmark" tests fail (double-click doesn't enter edit mode yet, since `clickToEdit={false}` today), and all of the new `describe("KBPage — autosave", ...)` tests fail (no autosave/Done button exist yet).

- [ ] **Step 3: Implement the autosave engine**

In `packages/editor/src/lib/components/KBPage.svelte`, remove the `saving` state declaration (currently `let saving = $state(false);`, around line 34) and replace it with:

```ts
  let saveStatus = $state<"idle" | "pending" | "saving" | "saved" | "error">("idle");
```

Add these new variables near the other plain (non-`$state`) local variables (e.g. near `bookmarkResolve`, around line 49):

```ts
  let saveTimer: ReturnType<typeof setTimeout> | null = null;
  let savedStatusTimer: ReturnType<typeof setTimeout> | null = null;
  let inFlightSave: Promise<boolean> | null = null;
```

Add `isDraftDirty` and the debounce `$effect`, and replace `handleSave`/`handleCancel` with `flushSave`. Remove the existing `handleSave` and `handleCancel` functions (lines 209-234) entirely, and put this in their place:

```ts
  function isDraftDirty(): boolean {
    if (!selectedEntry) return false;
    return draftTitle !== selectedEntry.title || draftContent !== selectedEntry.content;
  }

  $effect(() => {
    if (!editing || !isDraftDirty()) return;
    saveStatus = "pending";
    if (saveTimer) clearTimeout(saveTimer);
    saveTimer = setTimeout(() => { flushSave(); }, 1200);
    return () => { if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; } };
  });

  async function flushSave(): Promise<boolean> {
    if (saveTimer) { clearTimeout(saveTimer); saveTimer = null; }
    if (inFlightSave) {
      const ok = await inFlightSave;
      return ok ? flushSave() : false;
    }
    if (!isDraftDirty()) { saveStatus = "idle"; return true; }
    if (!selectedId) return true;
    if (!draftTitle.trim()) {
      error = $_('kb.page.titleEmpty');
      saveStatus = "error";
      return false;
    }
    saveStatus = "saving";
    error = null;
    const id = selectedId;
    const title = draftTitle.trim();
    const content = draftContent;
    const p = (async (): Promise<boolean> => {
      try {
        await store.updateEntry(id, { title, content });
        draftTitle = title;
        saveStatus = "saved";
        if (savedStatusTimer) clearTimeout(savedStatusTimer);
        savedStatusTimer = setTimeout(() => { saveStatus = "idle"; }, 2000);
        return true;
      } catch (e) {
        error = e instanceof Error ? e.message : $_('kb.page.saveFailed');
        saveStatus = "error";
        return false;
      } finally {
        inFlightSave = null;
      }
    })();
    inFlightSave = p;
    return p;
  }

  async function handleDoneEditing(): Promise<void> {
    const ok = await flushSave();
    if (ok) editing = false;
  }
```

Update the media-tab switch button (around line 464-467) to flush before discarding edit mode:

```svelte
            <button class="content-tab" class:active={contentTab === "media"}
              onclick={handleSwitchToMedia}>
```

and add the handler next to `handleDoneEditing`:

```ts
  async function handleSwitchToMedia(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    contentTab = "media";
    editing = false;
  }
```

Replace the `header-actions` block (around line 470-480):

```svelte
        <div class="header-actions">
          {#if contentTab === "content" && editing}
            <span class="save-status" class:save-status-error={saveStatus === "error"}>
              {#if saveStatus === "saving" || saveStatus === "pending"}{$_('kb.page.saving')}
              {:else if saveStatus === "saved"}{$_('kb.page.saved')}
              {:else if saveStatus === "error"}{$_('kb.page.saveFailed')}
              {/if}
            </span>
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>✓</Button>
          {/if}
          <Button variant="ghost" onclick={() => handleAskDelete(selectedEntry.id)} title={$_('kb.page.deletePage')}>🗑</Button>
        </div>
```

Update the `MarkdownEditor` usage (around line 485-494) to enable double-click-to-edit:

```svelte
          <MarkdownEditor
            bind:value={draftContent}
            bind:editing
            mediaItems={contentTab === "content" ? mediaItems : []}
            clickToEdit={true}
            editTrigger="dblclick"
            placeholder={$_('kb.page.startWritingPlaceholder')}
            {resolveKbLink}
            onSlashPage={handleSlashPage}
            onInsertBookmark={handleInsertBookmark}
          />
```

Add the two new CSS rules to the `<style>` block, near `.content-error` (around line 648):

```css
  .save-status { font-size: 11px; color: var(--text-muted); white-space: nowrap; }
  .save-status-error { color: var(--danger); }
```

Add the two new i18n keys. In `packages/editor/src/lib/locales/en.json`, inside the existing `"kb"."page"` object, add (next to `"saveFailed"`):

```json
    "saving": "Saving…",
    "saved": "Saved",
```

In `packages/editor/src/lib/locales/fr.json`, inside the same `"kb"."page"` object:

```json
    "saving": "Enregistrement…",
    "saved": "Enregistré",
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests, including the updated bookmark tests and the new autosave `describe` block)

Also run the full frontend suite to catch any other test relying on the removed Save/Cancel/Edit buttons or the `saving` prop name:

Run: `cd packages/editor && npx vitest run`
Expected: PASS. If any other test file references `[title="Save"]`, `[title="Cancel"]`, or `[title="Edit"]` inside a KB context, update it the same way as Step 1 above (double-click to enter edit mode instead of clicking Edit; no Save/Cancel buttons to click — edits autosave, and the “Done editing” button, `[title="Done editing"]`, returns to preview).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): debounced autosave with status indicator, double-click-to-edit, Done button"
```

---

## Task 6: `KBPage.svelte` — flush pending saves before internal navigation

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `flushSave(): Promise<boolean>` from Task 5.
- Produces: `navigate(entry): Promise<boolean>` (was `void`-returning and synchronous; now async, returns whether the navigation actually happened).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/KBPage.test.ts`, inside (or after) the new `describe("KBPage — autosave", ...)` block from Task 5:

```ts
  it("flushes a pending save before switching to a different page, and the new page shows the saved content", async () => {
    const entries = [
      makeEntry({ id: "e1", title: "Page A", content: "hello" }),
      makeEntry({ id: "e2", title: "Page B", order: 1 }),
    ];
    const { target, comp, store } = await setup(entries, { selectedItemId: "e1" });
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const rows = target.querySelectorAll(".tree-row");
    const pageBRow = Array.from(rows).find((r) => r.textContent?.includes("Page B")) as HTMLElement;
    pageBRow.click();
    await tick(); flushSync(); await tick(); flushSync();
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    expect(target.querySelector(".content-title")?.textContent).toBe("Page B");
  });
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — clicking Page B's row while Page A has a pending (not-yet-debounced) edit currently discards the edit instead of saving it first.

- [ ] **Step 3: Await a flush before every internal navigation/mode switch**

In `packages/editor/src/lib/components/KBPage.svelte`, change `navigate` (currently synchronous, around line 91-95) to:

```ts
  async function navigate(entry: KBEntry): Promise<boolean> {
    const ok = await flushSave();
    if (!ok) return false;
    selectEntry(entry);
    pendingNavigateId = entry.id;
    onnavigate?.(entry.id);
    return true;
  }
```

Change `handleTreeSelect` (currently around line 97-100) to:

```ts
  async function handleTreeSelect(entry: KBEntry): Promise<void> {
    await navigate(entry);
    sidebarExpanded = false;
  }
```

Change `handleNewPage` (currently around line 134-143) to flush before creating the new page:

```ts
  async function handleNewPage(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    try {
      const entry = await store.createEntry({ title: $_('kb.page.newPageTitle'), content: "" });
      await navigate(entry);
      editing = true;
      sidebarExpanded = false;
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.createFailed');
    }
  }
```

Change `handleCreateChild` (currently around line 152-165) the same way:

```ts
  async function handleCreateChild(parentId: string): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    try {
      const entry = await store.createEntry({ title: $_('kb.page.newPageTitle'), content: "", parentId });
      await appendChildLink(parentId, entry);
      const next = new Set(collapsedIds);
      next.delete(parentId);
      collapsedIds = next;
      await navigate(entry);
      editing = true;
      sidebarExpanded = false;
    } catch (e) {
      error = e instanceof Error ? e.message : $_('kb.page.createFailed');
    }
  }
```

Change `openTrash` (currently around line 363-369):

```ts
  async function openTrash(): Promise<void> {
    const ok = await flushSave();
    if (!ok) return;
    contentMode = "trash";
    selectedId = null;
    sidebarExpanded = false;
    try { await store.loadTrash(); }
    catch (e) { error = e instanceof Error ? e.message : $_('kb.page.loadTrashFailed'); }
  }
```

The Task 4 redirect effect calls `navigate(found);` without awaiting — that's still valid since `navigate` now returns a `Promise<boolean>` rather than `void`; the effect doesn't need the result, so no change is needed there.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): flush pending autosave before switching pages, creating pages, or opening trash"
```

---

## Task 7: `KBPage.svelte` — register the nav guard + `beforeunload` warning

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `setNavGuard` from Task 1's `packages/editor/src/lib/navGuard.ts`; `flushSave` from Task 5.
- Produces: while `KBPage` is mounted, `getNavGuard()` returns a function that flushes KB's pending save; on unmount, the guard is cleared.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/KBPage.test.ts` (new top-level `describe`, after the autosave block):

```ts
import { setNavGuard, getNavGuard } from "../src/lib/navGuard";

describe("KBPage — nav guard registration", () => {
  it("registers a nav guard while mounted and clears it on unmount", async () => {
    const { target, comp } = await setup([]);
    expect(getNavGuard()).not.toBeNull();
    unmount(comp); target.remove();
    expect(getNavGuard()).toBeNull();
  });

  it("the registered guard flushes a pending autosave and returns true on success", async () => {
    const { target, comp, store } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    (target.querySelector(".md-preview") as HTMLElement).dispatchEvent(
      new MouseEvent("dblclick", { bubbles: true }),
    );
    flushSync();
    const textarea = target.querySelector("textarea.md-editor") as HTMLTextAreaElement;
    textarea.value = "hello world";
    textarea.dispatchEvent(new Event("input", { bubbles: true }));
    flushSync();
    const guard = getNavGuard()!;
    const ok = await guard();
    expect(ok).toBe(true);
    expect(store.entries.find((e) => e.id === "e1")?.content).toBe("hello world");
    unmount(comp); target.remove();
  });
});
```

Add `import { setNavGuard, getNavGuard } from "../src/lib/navGuard";` at the top of the test file if not already imported by an earlier task's edits (Task 1's own `navGuard.test.ts` is a separate file, so this import is new here).

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: FAIL — `getNavGuard()` returns `null` both before and after mount (KBPage doesn't register anything yet).

- [ ] **Step 3: Register the guard and add the `beforeunload` listener**

In `packages/editor/src/lib/components/KBPage.svelte`, add the import (next to the `kbLastPage` import added in Task 4):

```ts
  import { setNavGuard } from "../navGuard";
```

Add two new `$effect`s, placed after the last-page-redirect effect from Task 4:

```ts
  $effect(() => {
    setNavGuard(flushSave);
    return () => { setNavGuard(null); };
  });

  $effect(() => {
    function handleBeforeUnload(e: BeforeUnloadEvent): void {
      if (saveStatus === "pending" || saveStatus === "saving" || saveStatus === "error") {
        e.preventDefault();
        e.returnValue = "";
      }
    }
    window.addEventListener("beforeunload", handleBeforeUnload);
    return () => window.removeEventListener("beforeunload", handleBeforeUnload);
  });
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests)

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): register a nav guard and warn on tab close while a save is pending"
```

---

## Task 8: `App.svelte` — wire the guarded hash router

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.routing.test.ts`

**Interfaces:**
- Consumes: `createGuardedHashRouter` from Task 1's `packages/editor/src/lib/navGuard.ts`.
- Produces: `App.svelte`'s `currentRoute` state now only changes hash-navigation when no guard blocks it (or after the guard resolves).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/App.routing.test.ts`:

```ts
import { setNavGuard } from "../src/lib/navGuard";

describe("App — nav guard integration", () => {
  beforeEach(() => {
    stubFetch404();
  });

  it("stays on the KB route when a registered nav guard rejects navigation, then navigates once the guard is cleared", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const app = await mountAndLoad(target, "#/kb");

    let resolveGuard!: (ok: boolean) => void;
    setNavGuard(() => new Promise((resolve) => { resolveGuard = resolve; }));

    // jsdom dispatches "hashchange" as a queued task, not synchronously —
    // give it a turn before asserting (same pattern as
    // CommandPalette.integration.test.ts's hashchange-dependent assertions).
    window.location.hash = "#/costs";
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(window.location.hash).toBe("#/kb");

    resolveGuard(true);
    await new Promise((r) => setTimeout(r, 0));
    await tick();
    flushSync();

    expect(window.location.hash).toBe("#/costs");

    setNavGuard(null);
    unmount(app);
    target.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd packages/editor && npx vitest run test/App.routing.test.ts`
Expected: FAIL — `App.svelte`'s current hash listener has no guard awareness, so the hash changes to `#/costs` immediately and never reverts.

- [ ] **Step 3: Swap in the guarded hash router**

In `packages/editor/src/App.svelte`, add the import near the other `./lib/*` imports (e.g. right after the `createKBStore`/`KBPage` imports around line 65-66):

```ts
  import { createGuardedHashRouter } from "./lib/navGuard";
```

Replace the existing hash-routing block (currently lines 345-350):

```ts
  let currentRoute = $state(window.location.hash || "#/");
  $effect(() => {
    const onHashChange = () => { currentRoute = window.location.hash || "#/"; };
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  });
```

with:

```ts
  let currentRoute = $state(window.location.hash || "#/");
  const hashRouter = createGuardedHashRouter({
    getHash: () => window.location.hash || "#/",
    setHash: (hash) => { window.location.hash = hash; },
    onRoute: (hash) => { currentRoute = hash; },
  });
  $effect(() => {
    window.addEventListener("hashchange", hashRouter.handleHashChange);
    return () => window.removeEventListener("hashchange", hashRouter.handleHashChange);
  });
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd packages/editor && npx vitest run test/App.routing.test.ts`
Expected: PASS (all tests, including the pre-existing routing tests and the new guard-integration test)

Then run the full suite once to confirm nothing else regressed:

Run: `cd packages/editor && npx vitest run`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.routing.test.ts
git commit -m "feat(app): route hash navigation through the guarded router so KB can block leaving with unsaved changes"
```

---

## Manual verification (after all tasks)

Automated tests cover the logic, but the following should be checked by running the app in a browser before considering this done (per this project's practice of browser-checking editor UI changes):

1. Open a KB page, type in the content editor, wait ~1.5s without touching anything else — confirm "Saving…" then "Saved" appear and disappear near the header, with no Save/Cancel buttons visible.
2. Start typing, then immediately click a different page in the tree before the debounce fires — confirm the first page's edit is saved (revisit it to check) before the second page's content loads.
3. Start typing in a KB page, then click a different top-level module in the left nav (e.g. Costs) before the debounce fires — confirm the app stays on the KB page briefly, then proceeds to Costs once the save completes.
4. Clear the title field entirely while editing — confirm an error is shown and the page does not accept navigating away until a non-empty title is restored.
5. Double-click a page's rendered preview — confirm it enters edit mode; click "✓ Done editing" — confirm it returns to preview.
6. Close and reopen the KB module (navigate to another module and back to `#/kb`) — confirm it reopens on the page you were last viewing, not the empty-state placeholder.
