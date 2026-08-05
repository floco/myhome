# KB panel + floor plan panel fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ship six small UX fixes: a default-collapsed/icon-only/collapse-all KB tree toolbar, and a floor-plan wall-resize length label, HA-Area room-name auto-fill, and a movable/dismissible/frontmost room naming panel (via a new shared floating-drag helper also adopted by the three existing floor-plan floats).

**Architecture:** Pure frontend changes in `packages/editor`. KB fixes are confined to `KBPage.svelte`. Floor-plan fixes touch `RoomPanel.svelte`, `SelectionHandles.svelte`, `Canvas.svelte`, `App.svelte`, `ItemPickerPanel.svelte`, `FurnitureLibraryPanel.svelte`, plus a new non-visual reactive helper `floatingDrag.svelte.ts` (same factory-function-with-getters idiom as `toolStore.svelte.ts`/`kbStore.svelte.ts`) that replaces the duplicated `makeDragHandler` closure in `App.svelte`.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest + `svelte`'s `mount`/`unmount`/`flushSync` test helpers, svelte-i18n (en/fr locale JSON, both must stay in key-parity).

## Global Constraints

- Every user-visible string goes through `svelte-i18n`'s `$_()`; any new string needs a key added to **both** `packages/editor/src/lib/locales/en.json` and `fr.json` (a smoke test enforces EN/FR key parity).
- Svelte 5 component tests: `target` must be `document.createElement("div")` appended to `document.body` before `mount()`, and dispatched DOM events need `{ bubbles: true }` — handlers otherwise silently never fire (jsdom + Svelte 5 event delegation).
- Follow the existing test conventions in `packages/editor/test/*.test.ts`: `mount`/`unmount`/`flushSync` from `"svelte"`, `describe`/`it`/`expect`/`vi` from `"vitest"`, target cleanup via `unmount(comp); target.remove();` at the end of each test.
- No new UI-kit abstractions beyond what's specified (no icon-only `Button` variant, no generic `Panel`/`FloatingPanel` wrapper component — see Task 4 for why a plain reactive helper was chosen instead).
- Run `cd /projects/myhome/packages/editor && npx vitest run <file>` (not the whole suite) after each task's own test file(s); run the full `npx vitest run` at the end of the plan.

---

### Task 1: KB tree — default-collapsed on mount

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:41` (the `collapsedIds` declaration) and its surrounding `<script>` block.
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `store.entries: KBEntry[]` (already available as a prop-derived value in `KBPage.svelte`; each `KBEntry` has `id: string` and `parentId: string | null`).
- Produces: no new exports. `collapsedIds` (existing `$state<Set<string>>`) now initializes non-empty on each entries-load rather than always starting empty. `toggleTree(id)` (existing, `KBPage.svelte:285`) is unchanged and still the only way to flip an individual node.

Today `collapsedIds` is declared as `$state<Set<string>>(new Set())` (line 41) and never auto-populated, so every parent node renders expanded. It must instead default to "every entry that has at least one child" — but only once, the first time each entry set becomes available (store loads asynchronously), not on every reactive re-run (which would fight the user's own per-node toggles after that).

- [ ] **Step 1: Write the failing test**

Add to `packages/editor/test/KBPage.test.ts` (find the existing `describe("KBPage — empty state", ...)` block area and add a new describe near it — check the top of the file for the existing `setup()`/`makeEntry()` helpers and reuse them):

```ts
describe("KBPage — default tree collapse state", () => {
  it("parent pages start collapsed; leaf pages have no disclosure state to worry about", async () => {
    const entries = [
      makeEntry({ id: "p", title: "Parent" }),
      makeEntry({ id: "c", title: "Child", parentId: "p", order: 0 }),
    ];
    const { target, comp } = await setup(entries);
    // A collapsed parent shows the ▶ triangle and hides its child row.
    expect(target.querySelector(".disclosure")?.textContent).toBe("▶");
    expect(target.querySelectorAll(".tree-row").length).toBe(1);
    unmount(comp); target.remove();
  });

  it("clicking the disclosure on a default-collapsed parent still expands it", async () => {
    const entries = [
      makeEntry({ id: "p", title: "Parent" }),
      makeEntry({ id: "c", title: "Child", parentId: "p", order: 0 }),
    ];
    const { target, comp } = await setup(entries);
    (target.querySelector(".disclosure") as HTMLElement).click();
    flushSync();
    expect(target.querySelectorAll(".tree-row").length).toBe(2);
    unmount(comp); target.remove();
  });
});
```

Check the file's existing `setup()` helper signature (it wraps `mount` and returns `{ target, comp, store }` per the patterns already visible around the "child page creation" describe block) and match its calling convention exactly — do not invent a different helper.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "default tree collapse state"`
Expected: FAIL — both tests currently see an expanded tree (`▼` and 2 `.tree-row`s) because `collapsedIds` starts empty.

- [ ] **Step 3: Implement the default-collapse initialization**

In `KBPage.svelte`, replace the plain `$state` initializer with logic that seeds the set once when entries first arrive. Add near the other `$effect`/`$derived` declarations (after the `collapsedIds` declaration at line 41, and after `store` is available — place it right after the `selectedEntry`/`mediaItems` derived block, e.g. after line 62):

```ts
let collapseDefaultApplied = $state(false);

$effect(() => {
  if (collapseDefaultApplied) return;
  if (store.entries.length === 0) return;
  const parents = new Set(store.entries.filter((e) => e.parentId !== null).map((e) => e.parentId as string));
  collapsedIds = parents;
  collapseDefaultApplied = true;
});
```

This runs once (guarded by `collapseDefaultApplied`) the first time `store.entries` is non-empty, computing "every id that appears as some entry's `parentId`" (equivalent to "has at least one child" — matches `KBTree.svelte`'s own `hasChildren()` check) and seeding `collapsedIds` with it. After that, only `toggleTree()` (individual) and the Task 2 collapse/expand-all toggle mutate `collapsedIds`; this effect never runs again for the lifetime of the mounted component (matching the "session-only, resets on remount" requirement — a fresh mount gets a fresh `collapseDefaultApplied = false`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "default tree collapse state"`
Expected: PASS

- [ ] **Step 5: Run the full KBPage test file to check for regressions**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (all tests, including any that relied on children being visible immediately after creating a page — `handleCreateChild`/`handleSlashPage` in `KBPage.svelte` already explicitly `.delete(parentId)` from `collapsedIds` when creating a child, at lines 146-148 and 161-163, so newly-created children remain visible; this should still hold).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): default-collapse tree nodes with children on load"
```

---

### Task 2: KB tree — collapse/expand-all toggle button

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte` (`.sidebar-toolbar` markup, around lines 371-374, plus a new derived/handler in `<script>`)
- Modify: `packages/editor/src/lib/locales/en.json` and `packages/editor/src/lib/locales/fr.json` (new `kb.tree.collapseAll`/`kb.tree.expandAll` keys)
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Consumes: `collapsedIds` and `store.entries` (from Task 1), `toggleTree`'s sibling state.
- Produces: a new handler `toggleAllTree(): void` in `KBPage.svelte` and a new derived boolean/string used only within that file — no other file depends on this.

- [ ] **Step 1: Add the locale keys**

In `packages/editor/src/lib/locales/en.json`, inside the `"kb": { "tree": { ... } }` block (currently lines 1147-1154), add two keys right after `"expand": "Expand",`:

```json
      "collapse": "Collapse",
      "expand": "Expand",
      "collapseAll": "Collapse all",
      "expandAll": "Expand all",
```

In `packages/editor/src/lib/locales/fr.json`, in the matching block (currently lines 1147-1154), add:

```json
      "collapse": "Réduire",
      "expand": "Développer",
      "collapseAll": "Tout réduire",
      "expandAll": "Tout développer",
```

- [ ] **Step 2: Write the failing test**

Add to `packages/editor/test/KBPage.test.ts`:

```ts
describe("KBPage — collapse/expand all", () => {
  it("shows a collapse-all control when a parent is expanded, and it collapses every parent", async () => {
    const entries = [
      makeEntry({ id: "p1", title: "Parent 1" }),
      makeEntry({ id: "c1", title: "Child 1", parentId: "p1", order: 0 }),
      makeEntry({ id: "p2", title: "Parent 2", order: 1 }),
      makeEntry({ id: "c2", title: "Child 2", parentId: "p2", order: 0 }),
    ];
    const { target, comp } = await setup(entries);
    // Default state (Task 1): both parents collapsed -> control offers "expand all".
    const toggleBtn = () => target.querySelector('[title="Expand all"], [title="Collapse all"]') as HTMLElement;
    expect(toggleBtn().title).toBe("Expand all");
    toggleBtn().click();
    flushSync();
    expect(target.querySelectorAll(".tree-row").length).toBe(4);
    expect(toggleBtn().title).toBe("Collapse all");
    toggleBtn().click();
    flushSync();
    expect(target.querySelectorAll(".tree-row").length).toBe(2);
    expect(toggleBtn().title).toBe("Expand all");
    unmount(comp); target.remove();
  });
});
```

- [ ] **Step 3: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "collapse/expand all"`
Expected: FAIL — no such button exists yet.

- [ ] **Step 4: Implement the toggle**

In `KBPage.svelte`, add a derived + handler near `toggleTree` (after line 289):

```ts
const allParentsExpanded = $derived(
  store.entries.some((e) => e.parentId !== null) &&
  store.entries.filter((e) => e.parentId !== null).every((e) => !collapsedIds.has(e.parentId as string)),
);

function toggleAllTree(): void {
  if (allParentsExpanded) {
    collapsedIds = new Set(store.entries.filter((e) => e.parentId !== null).map((e) => e.parentId as string));
  } else {
    collapsedIds = new Set();
  }
}
```

`allParentsExpanded` is `true` only when there's at least one parent and none of them are in `collapsedIds` — i.e., fully expanded. `toggleAllTree` flips between "collapse every parent" and "clear the whole set" (equivalent to Task 1's default-seed computation, duplicated here as a plain expression since it's two lines and pulling it into a shared function would be over-abstraction for two call sites — but keep the two computations textually identical so they can't drift silently apart in a future edit).

Update the toolbar markup (lines 371-374):

```svelte
<div class="sidebar-toolbar">
  <Input placeholder={$_('floorPlan.itemPicker.search')} bind:value={searchQuery} />
  <Button onclick={toggleAllTree} title={allParentsExpanded ? $_('kb.tree.collapseAll') : $_('kb.tree.expandAll')}>
    {allParentsExpanded ? "⊟" : "⊞"}
  </Button>
  <Button onclick={handleNewPage} title={$_('kb.page.newPage')}>＋</Button>
</div>
```

(The New Page button's text→icon-only change and `title` addition is also this task's toolbar edit since it's the same markup block; Task 3 covers the *other* icon-only buttons in `.header-actions`.)

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "collapse/expand all"`
Expected: PASS

- [ ] **Step 6: Fix the now-broken "single New Page button" test**

The existing test at `KBPage.test.ts` (currently `it("toolbar has a single New Page button (no separate Folder button)", ...)`, around lines 148-153) asserts `buttons` (an array of `textContent`) contains `"＋ New Page"`. That string no longer appears since New Page is now icon-only. Replace its body:

```ts
  it("toolbar has a single New Page button (no separate Folder button)", async () => {
    const { target, comp } = await setup([]);
    expect(target.querySelector('[title="New Page"]')).not.toBeNull();
    const titles = Array.from(target.querySelectorAll(".sidebar-toolbar button")).map((b) => b.getAttribute("title"));
    expect(titles).not.toContain("＋ Folder");
    unmount(comp); target.remove();
  });
```

- [ ] **Step 7: Run the full KBPage test file, plus the i18n parity smoke test**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts test/i18nFrenchSmoke.test.ts`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): add collapse/expand-all toggle to the page tree toolbar"
```

---

### Task 3: KB content header — icon-only Save/Cancel/Edit buttons

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte` (`.header-actions` markup, lines 444-454)
- Test: `packages/editor/test/KBPage.test.ts`

**Interfaces:** none beyond existing `handleSave`, `handleCancel`, `editing` state, `common.save`/`common.cancel`/`common.edit` locale keys (all already exist — reused as `title`, no new keys needed).

- [ ] **Step 1: Fix the two tests that will break, alongside the change (icon-only buttons have no discoverable text, so the test-first cycle here is: change markup, then fix the two assertions that depended on old text — there's no meaningful "write a failing test for icon-only rendering" step beyond confirming the title attribute)**

First, locate and update the two existing assertions in `packages/editor/test/KBPage.test.ts` that find buttons by `textContent === "Edit"` (currently at two call sites, both reading `Array.from(target.querySelectorAll("button")).find((b) => b.textContent === "Edit")`). Change each to:

```ts
const editBtn = target.querySelector('[title="Edit"]') as HTMLElement;
```

- [ ] **Step 2: Run those two tests to confirm they currently pass (baseline) before changing the markup**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts`
Expected: the two edited tests now FAIL (title attribute doesn't exist yet — `Edit` button currently has no `title` prop), everything else PASS. This confirms the edit-lookup change is exercising real markup, not a typo.

- [ ] **Step 3: Implement icon-only Save/Cancel/Edit**

Replace `.header-actions` content (`KBPage.svelte` lines 445-452):

```svelte
{#if contentTab === "content" && editing}
  <Button variant="primary" disabled={saving} onclick={handleSave} title={saving ? $_('settings.security.saving') : $_('common.save')}>
    💾
  </Button>
  <Button variant="secondary" onclick={handleCancel} title={$_('common.cancel')}>✕</Button>
{:else if contentTab === "content" && !editing}
  <Button variant="secondary" onclick={() => { editing = true; }} title={$_('common.edit')}>✏️</Button>
{/if}
```

(Delete's `<Button variant="ghost" ...>🗑</Button>` on line 453 is unchanged — already icon-only.)

- [ ] **Step 4: Run the full KBPage test file**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS (the two `title="Edit"` lookups now succeed; no other test referenced Save/Cancel/Edit's *content-header* text — the `"Cancel"`/`"Delete"` lookups elsewhere in the file target Modal footer buttons, a separate, unchanged part of the DOM).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): icon-only Save/Cancel/Edit buttons in the page header"
```

---

### Task 4: Floor plan — extract `createFloatingDrag` and adopt it for the 3 existing floats

**Files:**
- Create: `packages/editor/src/lib/floatingDrag.svelte.ts`
- Modify: `packages/editor/src/App.svelte` (remove `ftPos`/`fpPos`/`ipPos`/`makeDragHandler`/`startFtDrag`/`startFpDrag`/`startIpDrag`, replace with `createFloatingDrag` calls; update the 3 style-attr expressions and the 3 `onstartdrag`/`onmousedown` wiring sites)
- Test: `packages/editor/test/floatingDrag.test.ts` (new), run `packages/editor/test/App.test.ts` + `App.furniture.test.ts` for regressions

**Interfaces:**
- Produces: `createFloatingDrag(selector: string): { readonly pos: { x: number; y: number } | null; startDrag: (e: MouseEvent) => void }` — a factory function (not a component), matching the existing `createToolStore`/`createHouseStore`/`createKBStore` idiom (getter-based reactive object). `pos` starts `null` (caller falls back to its own default CSS position, exactly as today); after a drag, `pos` holds clamped `{x, y}` relative to `selector`'s nearest ancestor matched via `.closest(selector)`'s `.parentElement`.
- Consumes: nothing external — pure DOM + Svelte runes.

This task is a behavior-preserving refactor: today's `App.svelte:293-316` `makeDragHandler(selector, pos, setPos)` factory is called 3 times (`.floating-toolbar`, `.furniture-float`, `.picker-float`), each producing a `startDrag` closure and mutating a separate `$state` variable via `setPos`. Note the existing `pos` *parameter* to `makeDragHandler` is actually dead code today (the closure never reads it — position comes from `getBoundingClientRect()` at drag-start time) — `createFloatingDrag` drops that unused parameter entirely rather than preserving it.

- [ ] **Step 1: Write the failing test for the new helper**

Create `packages/editor/test/floatingDrag.test.ts`:

```ts
import { describe, it, expect } from "vitest";
import { createFloatingDrag } from "../src/lib/floatingDrag.svelte";

function setUpDom(): { container: HTMLElement; panel: HTMLElement } {
  const container = document.createElement("div");
  container.style.cssText = "position:relative;width:800px;height:600px;";
  document.body.appendChild(container);
  const panel = document.createElement("div");
  panel.className = "test-panel";
  panel.style.cssText = "width:100px;height:50px;";
  container.appendChild(panel);
  vi_mockRects(container, panel);
  return { container, panel };
}

// jsdom returns all-zero rects by default; stub both so the clamping math is exercisable.
function vi_mockRects(container: HTMLElement, panel: HTMLElement): void {
  container.getBoundingClientRect = () => ({ left: 0, top: 0, width: 800, height: 600, right: 800, bottom: 600, x: 0, y: 0, toJSON() {} });
  panel.getBoundingClientRect = () => ({ left: 700, top: 500, width: 100, height: 50, right: 800, bottom: 550, x: 700, y: 500, toJSON() {} });
}

describe("createFloatingDrag", () => {
  it("pos starts null", () => {
    const drag = createFloatingDrag(".test-panel");
    expect(drag.pos).toBeNull();
  });

  it("dragging moves pos by the mouse delta, clamped to the container bounds", () => {
    const { panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const mousedown = new MouseEvent("mousedown", { bubbles: true, clientX: 750, clientY: 525 });
    Object.defineProperty(mousedown, "currentTarget", { value: panel });
    drag.startDrag(mousedown);
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 760, clientY: 530 }));
    // initX=700, initY=500, delta=(10,20) -> (710, 520), well within the 800x600 container.
    expect(drag.pos).toEqual({ x: 710, y: 520 });
    window.dispatchEvent(new MouseEvent("mouseup"));
    panel.remove();
  });

  it("clamps to the container's bottom-right when dragged past it", () => {
    const { panel } = setUpDom();
    const drag = createFloatingDrag(".test-panel");
    const mousedown = new MouseEvent("mousedown", { bubbles: true, clientX: 750, clientY: 525 });
    Object.defineProperty(mousedown, "currentTarget", { value: panel });
    drag.startDrag(mousedown);
    window.dispatchEvent(new MouseEvent("mousemove", { clientX: 2000, clientY: 2000 }));
    // container width(800) - panel width(100) = 700 max x; height(600) - 50 = 550 max y.
    expect(drag.pos).toEqual({ x: 700, y: 550 });
    window.dispatchEvent(new MouseEvent("mouseup"));
    panel.remove();
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/floatingDrag.test.ts`
Expected: FAIL with a module-not-found error for `../src/lib/floatingDrag.svelte`.

- [ ] **Step 3: Implement `floatingDrag.svelte.ts`**

Create `packages/editor/src/lib/floatingDrag.svelte.ts`:

```ts
export function createFloatingDrag(selector: string) {
  let pos = $state<{ x: number; y: number } | null>(null);

  function startDrag(e: MouseEvent): void {
    e.preventDefault();
    const el = (e.currentTarget as HTMLElement).closest(selector) as HTMLElement;
    const rect = el.getBoundingClientRect();
    const canvasRect = (el.parentElement as HTMLElement).getBoundingClientRect();
    const initX = rect.left - canvasRect.left;
    const initY = rect.top - canvasRect.top;
    const startX = e.clientX;
    const startY = e.clientY;
    function onMove(me: MouseEvent): void {
      pos = {
        x: Math.max(0, Math.min(canvasRect.width - rect.width, initX + me.clientX - startX)),
        y: Math.max(0, Math.min(canvasRect.height - rect.height, initY + me.clientY - startY)),
      };
    }
    function onUp(): void {
      window.removeEventListener("mousemove", onMove);
      window.removeEventListener("mouseup", onUp);
    }
    window.addEventListener("mousemove", onMove);
    window.addEventListener("mouseup", onUp);
  }

  return {
    get pos() { return pos; },
    startDrag,
  };
}
```

This is a line-for-line port of `App.svelte`'s current `makeDragHandler` body (lines 294-315), just returning a reactive-getter object instead of taking a `setPos` callback.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/floatingDrag.test.ts`
Expected: PASS

- [ ] **Step 5: Adopt it in `App.svelte` for the 3 existing floats**

In `App.svelte`, delete lines 290-291 (`let ftPos`, `let fpPos`), the `makeDragHandler` function (lines 293-316), and lines 318-321 (`startFtDrag`/`startFpDrag`/`startIpDrag`/`ipPos`). Replace with:

```ts
import { createFloatingDrag } from "./lib/floatingDrag.svelte";
// ...(near the top import block, alongside the other lib imports)

const ftDrag = createFloatingDrag(".floating-toolbar");
const fpDrag = createFloatingDrag(".furniture-float");
const ipDrag = createFloatingDrag(".picker-float");
```

Update the 3 usage sites:
- Line 1136: `<div class="picker-float" style={ipDrag.pos ? \`left:${ipDrag.pos.x}px;top:${ipDrag.pos.y}px;right:auto;transform:none\` : ''}>`
- Line 1141: `onstartdrag={ipDrag.startDrag}`
- Line 1148: `<div class="furniture-float" style={fpDrag.pos ? \`left:${fpDrag.pos.x}px;top:${fpDrag.pos.y}px;right:auto;transform:none\` : ''}>`
- Line 1149: `<FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} />`
- Line 1158: `style={ftDrag.pos ? \`left:${ftDrag.pos.x}px;top:${ftDrag.pos.y}px;right:auto;transform:none\` : ''}`
- Line 1161: `<div class="ft-handle" onmousedown={ftDrag.startDrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>`

- [ ] **Step 6: Run the App test suite for regressions**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/App.test.ts test/App.furniture.test.ts`
Expected: PASS — no behavior change, only the internal position-state mechanism changed.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/floatingDrag.svelte.ts packages/editor/test/floatingDrag.test.ts packages/editor/src/App.svelte
git commit -m "refactor(floorplan): extract createFloatingDrag, dedupe 3 floating-panel drag handlers"
```

---

### Task 5: Floor plan — dismiss buttons on the item-picker and furniture-library panels

**Files:**
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte` (props + `.panel-header` markup)
- Modify: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte` (props + `.panel-header` markup)
- Modify: `packages/editor/src/App.svelte` (wire `ondismiss` for both, closing `pickerOpen`/`furnitureLibraryOpen`)
- Test: `packages/editor/test/ItemPickerPanel.test.ts`, `packages/editor/test/FurnitureLibraryPanel.test.ts`

**Interfaces:**
- Produces: both components gain an optional prop `ondismiss?: () => void`. When provided, a `✕` button renders in `.panel-header`, calling `ondismiss()` on click.
- Consumes: existing `common.close` locale key (already present in both `en.json`/`fr.json` — no new keys needed).

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/ItemPickerPanel.test.ts`:

```ts
it("renders a dismiss button when ondismiss is provided, and calls it on click", async () => {
  const ondismiss = vi.fn();
  const app = mount(ItemPickerPanel, {
    target,
    props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn(), ondismiss },
  });
  flushSync();
  const btn = target.querySelector('.panel-header [title="Close"]') as HTMLElement;
  expect(btn).not.toBeNull();
  btn.click();
  expect(ondismiss).toHaveBeenCalled();
  unmount(app);
});

it("renders no dismiss button when ondismiss is omitted", async () => {
  const app = mount(ItemPickerPanel, {
    target,
    props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
  });
  flushSync();
  expect(target.querySelector('.panel-header [title="Close"]')).toBeNull();
  unmount(app);
});
```

Add the mirror pair to `packages/editor/test/FurnitureLibraryPanel.test.ts`, which already has its own `setup(props: Record<string, unknown> = {})` helper (declared inside the top-level `describe` block, returns the mounted `target`, tracks `app` in an outer variable, cleaned up via `afterEach`) — reuse it exactly as the file's existing tests do:

```ts
it("renders a dismiss button when ondismiss is provided, and calls it on click", () => {
  const ondismiss = vi.fn();
  setup({ ondismiss });
  const btn = target.querySelector('.panel-header [title="Close"]') as HTMLElement;
  expect(btn).not.toBeNull();
  btn.click();
  expect(ondismiss).toHaveBeenCalled();
});

it("renders no dismiss button when ondismiss is omitted", () => {
  setup();
  expect(target.querySelector('.panel-header [title="Close"]')).toBeNull();
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ItemPickerPanel.test.ts test/FurnitureLibraryPanel.test.ts -t "dismiss"`
Expected: FAIL — no `ondismiss` prop or dismiss button exists yet.

- [ ] **Step 3: Implement in `ItemPickerPanel.svelte`**

Add `ondismiss?: () => void;` to the `Props` interface and destructuring (near `onstartdrag`). Update the `.panel-header` markup:

```svelte
<div class="panel-header">
  {#if onstartdrag}
    <!-- svelte-ignore a11y_no_static_element_interactions -->
    <div class="drag-handle" onmousedown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
  {/if}
  <input class="search" placeholder={$_('floorPlan.itemPicker.search')} bind:value={query} />
  {#if ondismiss}
    <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
  {/if}
</div>
```

Add a `.dismiss-btn` style rule near the existing `.drag-handle`/`.search` rules (matching their sizing conventions — `background: none; border: none; cursor: pointer; color: var(--text-muted); flex-shrink: 0; padding: 2px 4px; border-radius: var(--radius-sm);` with a `:hover { background: var(--surface-hover); color: var(--text); }`).

- [ ] **Step 4: Implement in `FurnitureLibraryPanel.svelte`**

Same pattern: add `ondismiss?: () => void;` to the props destructuring, add the `{#if ondismiss}<button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>{/if}` after the search `<input>` in `.panel-header`, and the matching `.dismiss-btn` style rule.

- [ ] **Step 5: Wire `ondismiss` in `App.svelte`**

At the `ItemPickerPanel` call site (`App.svelte:1137-1144`), add `ondismiss={() => { pickerOpen = false; }}`. At the `FurnitureLibraryPanel` call site (`App.svelte:1149`), add `ondismiss={() => { furnitureLibraryOpen = false; }}`.

- [ ] **Step 6: Run the affected test files**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ItemPickerPanel.test.ts test/FurnitureLibraryPanel.test.ts test/App.test.ts test/App.furniture.test.ts`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ItemPickerPanel.svelte packages/editor/src/lib/components/FurnitureLibraryPanel.svelte packages/editor/src/App.svelte packages/editor/test/ItemPickerPanel.test.ts packages/editor/test/FurnitureLibraryPanel.test.ts
git commit -m "feat(floorplan): add dismiss buttons to item-picker and furniture-library panels"
```

---

### Task 6: Floor plan — HA Area → room name auto-fill

**Files:**
- Modify: `packages/editor/src/lib/components/RoomPanel.svelte` (`handleAreaChange`)
- Test: create `packages/editor/test/RoomPanel.test.ts`

**Interfaces:**
- Consumes: existing `onupdate: (patch: { label?: string; haAreaId?: string | null }) => void` prop — unchanged signature, now sometimes called with both keys in one patch.
- Produces: nothing new.

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/RoomPanel.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import RoomPanel from "../src/lib/components/RoomPanel.svelte";
import type { Room } from "@myhome/geometry";

function makeRoom(overrides: Partial<Room> = {}): Room {
  return { id: "r1", label: "", haAreaId: null, polygon: null, areaM2: 12.5, ...overrides };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("div");
  document.body.appendChild(target);
  const props = { room: makeRoom(), haAreas: [{ area_id: "a1", name: "Living Room" }], onupdate: vi.fn(), ...overrides };
  const comp = mount(RoomPanel, { target, props });
  flushSync();
  return { target, comp, props };
}

describe("RoomPanel — HA Area auto-fill", () => {
  it("fills the room label from the area name when the label is empty", () => {
    const onupdate = vi.fn();
    const { target } = setup({ room: makeRoom({ label: "" }), onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "a1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith(expect.objectContaining({ haAreaId: "a1", label: "Living Room" }));
  });

  it("does not touch an existing custom label when the area changes", () => {
    const onupdate = vi.fn();
    const { target } = setup({ room: makeRoom({ label: "My Office" }), onupdate });
    const select = target.querySelector("select") as HTMLSelectElement;
    select.value = "a1";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ haAreaId: "a1" });
  });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/RoomPanel.test.ts`
Expected: FAIL on the first test (`onupdate` called with only `{ haAreaId: "a1" }`, missing `label`).

- [ ] **Step 3: Implement the auto-fill**

In `RoomPanel.svelte`, replace `handleAreaChange` (lines 26-30):

```ts
function handleAreaChange(e: Event): void {
  const val = (e.target as HTMLSelectElement).value;
  const next = val === "" ? null : val;
  if (next === room.haAreaId) return;
  const patch: { haAreaId: string | null; label?: string } = { haAreaId: next };
  if (next !== null && room.label.trim() === "") {
    const area = haAreas.find((a) => a.area_id === next);
    if (area) patch.label = area.name;
  }
  onupdate(patch);
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/RoomPanel.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/RoomPanel.svelte packages/editor/test/RoomPanel.test.ts
git commit -m "feat(floorplan): auto-fill empty room name from selected HA Area"
```

---

### Task 7: Floor plan — movable, dismissible, frontmost room naming panel

**Files:**
- Modify: `packages/editor/src/lib/components/RoomPanel.svelte` (add drag-handle + dismiss to a new `.panel-header`, move CSS positioning out of `.room-panel` into a caller-supplied wrapper)
- Modify: `packages/editor/src/App.svelte` (wrap `<RoomPanel>` in a `.room-panel-float` div using `createFloatingDrag`, wire `ondismiss`)
- Test: `packages/editor/test/RoomPanel.test.ts`, `packages/editor/test/App.test.ts`

**Interfaces:**
- Consumes: `createFloatingDrag` from Task 4 (`packages/editor/src/lib/floatingDrag.svelte.ts`).
- Produces: `RoomPanel.svelte` gains two new optional props: `onstartdrag?: (e: MouseEvent) => void` and `ondismiss?: () => void`, matching `ItemPickerPanel`/`FurnitureLibraryPanel`'s existing prop shape exactly (same names, same optionality) for consistency across the 3 content-owning floats.

**Design note:** `RoomPanel`'s root `<aside class="room-panel">` currently carries its own `position: absolute; right: 120px; top: 50%; ...; z-index: 20;` (lines 68-84). This moves to a new wrapper `<div class="room-panel-float">` in `App.svelte` — exactly mirroring how `.picker-float`/`.furniture-float` already wrap `ItemPickerPanel`/`FurnitureLibraryPanel` — so `RoomPanel.svelte`'s own root becomes an unpositioned content box, and gains a `.panel-header` (title + drag handle + dismiss) matching the other two panels' header row.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/RoomPanel.test.ts`:

```ts
describe("RoomPanel — header controls", () => {
  it("renders a drag handle when onstartdrag is provided", () => {
    const { target } = setup({ onstartdrag: vi.fn() });
    expect(target.querySelector(".drag-handle")).not.toBeNull();
  });

  it("renders no drag handle when onstartdrag is omitted", () => {
    const { target } = setup();
    expect(target.querySelector(".drag-handle")).toBeNull();
  });

  it("calls ondismiss when the close button is clicked", () => {
    const ondismiss = vi.fn();
    const { target } = setup({ ondismiss });
    (target.querySelector('[title="Close"]') as HTMLElement).click();
    expect(ondismiss).toHaveBeenCalled();
  });
});
```

Also add to `packages/editor/test/App.test.ts`, inside the existing `describe("App — room panel", ...)` block (currently lines 360-375, containing one `it()` with locally-scoped `target`/`app` — match that inline style, don't introduce `beforeEach`/`afterEach` for this describe block). The file already has a `drawWalls(target, worldCorners)` helper (draws a closed wall loop via simulated clicks, which auto-detects a room, then switches the tool back to "Select") and a `SAMPLE_RECT_CORNERS` constant — reuse both instead of re-deriving the coordinate math. `RoomShape.svelte`'s `polygon.room` element has a plain `onclick={handleClick}` (gated on `tool === "select"`, which `drawWalls` already leaves active) that calls `onselectroom?.(room.id)` — so `(target.querySelector("polygon.room") as HTMLElement).click()` selects it directly, the same way other tests in this file click `.tree-row`/toolbar buttons:

```ts
it("room panel renders inside a draggable, dismissible float once a room is selected", async () => {
  stubFetch404();
  const target = document.createElement("div");
  document.body.appendChild(target);
  const app = await mountAndLoad(target);
  drawWalls(target, SAMPLE_RECT_CORNERS);
  (target.querySelector("polygon.room") as HTMLElement).click();
  flushSync();
  expect(target.querySelector(".room-panel-float")).not.toBeNull();
  expect(target.querySelector('.room-panel-float [title="Close"]')).not.toBeNull();
  unmount(app);
  target.remove();
});
```

(A separate assertion on the *numeric* `z-index` value is deliberately not included — jsdom's computed-style support for stacking context is unreliable in tests; the `.room-panel-float` CSS rule added in Step 5 below is the actual source of truth for that requirement.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/RoomPanel.test.ts test/App.test.ts`
Expected: FAIL on the new `RoomPanel` header tests (no `.drag-handle`/dismiss exist) and the new `App.test.ts` case (no `.room-panel-float` exists).

- [ ] **Step 3: Restructure `RoomPanel.svelte`**

Add `onstartdrag?: (e: MouseEvent) => void;` and `ondismiss?: () => void;` to `Props` and destructuring. Replace the markup (lines 33-65):

```svelte
<aside class="room-panel">
  <div class="panel-header">
    {#if onstartdrag}
      <!-- svelte-ignore a11y_no_static_element_interactions -->
      <div class="drag-handle" onmousedown={onstartdrag} title={$_('floorPlan.itemPicker.dragToReposition')}>⠿</div>
    {/if}
    <h2>{$_('floorPlan.roomPanel.title')}</h2>
    {#if ondismiss}
      <button class="dismiss-btn" onclick={ondismiss} title={$_('common.close')}>✕</button>
    {/if}
  </div>

  <label>
    <span>{$_('floorPlan.roomPanel.label')}</span>
    <input
      type="text"
      bind:value={labelDraft}
      onblur={commitLabel}
      onkeydown={(e) => {
        if (e.key === "Enter") {
          commitLabel();
          (e.target as HTMLInputElement).blur();
        }
      }}
    />
  </label>

  <label>
    <span>{$_('floorPlan.roomPanel.haArea')}</span>
    <select value={room.haAreaId ?? ""} onchange={handleAreaChange}>
      <option value="">{$_('floorPlan.roomPanel.none')}</option>
      {#each haAreas as area (area.area_id)}
        <option value={area.area_id}>{area.name}</option>
      {/each}
      {#if room.haAreaId && !haAreas.some((a) => a.area_id === room.haAreaId)}
        <option value={room.haAreaId}>{$_('floorPlan.roomPanel.unknownSuffix', { values: { id: room.haAreaId } })}</option>
      {/if}
    </select>
  </label>

  <p class="area-display">{room.areaM2} m²</p>
</aside>
```

Replace the `<style>` block's `.room-panel` rule (lines 68-84) — drop the positioning properties (`position`, `right`, `top`, `transform`, `z-index`), keep the rest:

```css
.room-panel {
  width: 200px;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: var(--radius-md);
  box-shadow: var(--shadow-md);
  padding: var(--space-3);
  display: flex;
  flex-direction: column;
  gap: var(--space-3);
  overflow-y: auto;
}
```

Replace the `h2` rule and add `.panel-header`/`.drag-handle`/`.dismiss-btn` rules (matching `ItemPickerPanel.svelte`'s equivalents for visual consistency, but without the padding/border-bottom since `RoomPanel`'s body already has its own `padding: var(--space-3)` on the root and inter-field `gap`):

```css
.panel-header {
  display: flex;
  align-items: center;
  gap: var(--space-2);
}
h2 {
  flex: 1;
  min-width: 0;
  margin: 0;
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
}
.drag-handle {
  cursor: grab;
  color: var(--text-muted);
  font-size: 14px;
  letter-spacing: 3px;
  opacity: 0.5;
  padding: 2px 0;
  flex-shrink: 0;
  border-radius: var(--radius-sm);
  user-select: none;
}
.drag-handle:hover { opacity: 1; background: var(--surface-hover); }
.drag-handle:active { cursor: grabbing; }
.dismiss-btn {
  background: none;
  border: none;
  cursor: pointer;
  color: var(--text-muted);
  flex-shrink: 0;
  padding: 2px 4px;
  border-radius: var(--radius-sm);
}
.dismiss-btn:hover { background: var(--surface-hover); color: var(--text); }
```

- [ ] **Step 4: Run the `RoomPanel` test file**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/RoomPanel.test.ts`
Expected: PASS

- [ ] **Step 5: Wrap `RoomPanel` in `App.svelte`**

Add a 4th `createFloatingDrag` call alongside the other 3 (Task 4's `ftDrag`/`fpDrag`/`ipDrag`):

```ts
const rpDrag = createFloatingDrag(".room-panel-float");
```

Replace the `RoomPanel` render block (`App.svelte:919-925`):

```svelte
{#if selectedRoom}
  <div class="room-panel-float" style={rpDrag.pos ? `left:${rpDrag.pos.x}px;top:${rpDrag.pos.y}px;right:auto;transform:none` : ''}>
    <RoomPanel
      room={selectedRoom}
      {haAreas}
      onupdate={(patch) => floorStore.updateRoom(selectedRoom.id, patch)}
      onstartdrag={rpDrag.startDrag}
      ondismiss={() => toolStore.selectRoom(null)}
    />
  </div>
{/if}
```

Add a `.room-panel-float` style rule near `.picker-float`/`.furniture-float` (`App.svelte`, currently lines 1456-1474) — same default position as those two (so pre-drag it lands in the same spot it does today), but a higher `z-index` so it renders in front when they overlap, and no `overflow: hidden`/`max-height` clamp since `RoomPanel`'s own root already handles its `overflow-y: auto`:

```css
.room-panel-float {
  position: absolute; right: 120px; top: 50%; transform: translateY(-50%);
  z-index: 21;
}
```

- [ ] **Step 6: Run the affected test files**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/App.test.ts test/RoomPanel.test.ts`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/RoomPanel.svelte packages/editor/src/App.svelte packages/editor/test/RoomPanel.test.ts packages/editor/test/App.test.ts
git commit -m "feat(floorplan): make the room naming panel movable, dismissible, and frontmost"
```

---

### Task 8: Floor plan — length label while resizing a wall

**Files:**
- Modify: `packages/editor/src/lib/components/SelectionHandles.svelte` (add length label rendering)
- Modify: `packages/editor/src/lib/components/Canvas.svelte` (add `draggingPoint` prop, pass through to `SelectionHandles`)
- Modify: `packages/editor/src/App.svelte` (pass `draggingPoint={toolStore.state.draggingPoint}` to `<Canvas>`)
- Test: create `packages/editor/test/SelectionHandles.test.ts`

**Interfaces:**
- `SelectionHandles` gains a new prop `draggingPoint: Point | null` (required, matching the component's existing style of required props with no defaults — `wall`, `viewport`, `ondragstart` are all required today).
- `Canvas` gains a new optional prop `draggingPoint?: Point | null = null` (optional with a default, matching its existing optional-prop style e.g. `selectedId = null`).

- [ ] **Step 1: Write the failing test**

Create `packages/editor/test/SelectionHandles.test.ts`:

```ts
import { describe, it, expect, vi } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import SelectionHandles from "../src/lib/components/SelectionHandles.svelte";
import type { Wall } from "@myhome/geometry";
import { DEFAULT_VIEWPORT } from "../src/lib/viewportStore.svelte";

function makeWall(overrides: Partial<Wall> = {}): Wall {
  return { id: "w1", start: { x: 0, y: 0 }, end: { x: 3, y: 0 }, type: "wall", thickness: 0.1, ...overrides };
}

function setup(overrides: Record<string, unknown> = {}) {
  const target = document.createElement("svg");
  document.body.appendChild(target);
  const props = { wall: makeWall(), viewport: DEFAULT_VIEWPORT, ondragstart: vi.fn(), draggingPoint: null, ...overrides };
  const comp = mount(SelectionHandles, { target, props });
  flushSync();
  return { target, comp };
}

describe("SelectionHandles — resize length label", () => {
  it("shows no length label when not dragging", () => {
    const { target, comp } = setup({ draggingPoint: null });
    expect(target.querySelector(".length-label")).toBeNull();
    unmount(comp); target.remove();
  });

  it("shows the wall's live length when a drag is in progress", () => {
    const { target, comp } = setup({ draggingPoint: { x: 0, y: 0 } });
    expect(target.querySelector(".length-label")?.textContent?.trim()).toBe("3.00 m");
    unmount(comp); target.remove();
  });
});
```

`DEFAULT_VIEWPORT` (`{ panX: 400, panY: 300, zoom: 100 }`) and `ViewportState`'s `panX`/`panY`/`zoom` fields (not a nested `pan` object) are both exported from `packages/editor/src/lib/viewportStore.svelte.ts:14` and `:3-7` respectively — import and use them directly, no need to hand-roll a viewport object. `Wall` requires a `type: WallType` field (`"wall" | "divider"`) in addition to `id`/`start`/`end`/optional `thickness`.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/SelectionHandles.test.ts`
Expected: FAIL — `draggingPoint` prop doesn't exist yet, no `.length-label` renders.

- [ ] **Step 3: Implement in `SelectionHandles.svelte`**

```svelte
<script lang="ts">
  import type { Point, Wall } from "@myhome/geometry";
  import { worldToScreen, type ViewportState } from "../viewportStore.svelte";
  import { distance } from "../geometry-helpers";

  let {
    wall,
    viewport,
    draggingPoint,
    ondragstart,
  }: {
    wall: Wall;
    viewport: ViewportState;
    draggingPoint: Point | null;
    ondragstart: (point: Point, event: MouseEvent) => void;
  } = $props();

  function toScreen(p: Point): Point {
    return worldToScreen(p, viewport);
  }

  const startScreen = $derived(toScreen(wall.start));
  const endScreen = $derived(toScreen(wall.end));
  const midScreen = $derived(toScreen({ x: (wall.start.x + wall.end.x) / 2, y: (wall.start.y + wall.end.y) / 2 }));
  const length = $derived(distance(wall.start, wall.end));
</script>

<g class="selection-handles">
  <circle
    class="handle"
    cx={startScreen.x}
    cy={startScreen.y}
    r="5"
    onmousedown={(e) => ondragstart(wall.start, e)}
  />
  <circle
    class="handle"
    cx={endScreen.x}
    cy={endScreen.y}
    r="5"
    onmousedown={(e) => ondragstart(wall.end, e)}
  />
  {#if draggingPoint}
    <text class="length-label" x={midScreen.x} y={midScreen.y - 6} text-anchor="middle">
      {length.toFixed(2)} m
    </text>
  {/if}
</g>

<style>
  .handle {
    fill: var(--canvas-wall-selected);
    stroke: var(--text);
    stroke-width: 1;
    cursor: grab;
  }
  .length-label {
    fill: var(--canvas-label);
    font-size: 11px;
  }
</style>
```

(`draggingPoint`'s value isn't inspected beyond truthiness — `SelectionHandles` is only ever rendered for the currently-*selected* wall, and `toolStore.state.draggingPoint` is only ever set by this same component's own `ondragstart` callback chain — see the "Global Constraints"-adjacent note in Task's Interfaces section above; no other interaction sets it. So "some drag is active while this wall's handles are showing" is unambiguous.)

- [ ] **Step 4: Add the `draggingPoint` prop to `Canvas.svelte`**

In the `Props` destructuring/type (lines 19-79), add `draggingPoint = null,` to the destructured list and `draggingPoint?: Point | null;` to the type. Update the `SelectionHandles` render call (line 310):

```svelte
{#if selectedWall}
  <SelectionHandles wall={selectedWall} {viewport} {draggingPoint} ondragstart={handleDragStart} />
{/if}
```

- [ ] **Step 5: Pass it through from `App.svelte`**

At the `<Canvas ...>` call site (`App.svelte:889-918`), add `draggingPoint={toolStore.state.draggingPoint}` alongside the other `toolStore.state.*` props already passed (e.g. next to `drawPoints={toolStore.state.drawPoints}`).

- [ ] **Step 6: Run test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/SelectionHandles.test.ts`
Expected: PASS

- [ ] **Step 7: Run the Canvas and App test suites for regressions**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/Canvas.test.ts test/App.test.ts`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/lib/components/SelectionHandles.svelte packages/editor/src/lib/components/Canvas.svelte packages/editor/src/App.svelte packages/editor/test/SelectionHandles.test.ts
git commit -m "feat(floorplan): show live length label while resizing a wall"
```

---

### Task 9: Full suite + i18n parity check

**Files:** none (verification only)

- [ ] **Step 1: Run the entire editor test suite**

Run: `cd /projects/myhome/packages/editor && npx vitest run`
Expected: PASS, 0 failures.

- [ ] **Step 2: Run the i18n French smoke test explicitly (already covered by Step 1, called out for visibility)**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/i18nFrenchSmoke.test.ts test/localization.test.ts`
Expected: PASS.

- [ ] **Step 3: Typecheck**

Run: `cd /projects/myhome/packages/editor && npm run typecheck` (defined in `package.json` as `svelte-check --tsconfig ./tsconfig.json`).
Expected: no errors.

No commit for this task — it's a verification-only checkpoint before wrapping up the branch.
