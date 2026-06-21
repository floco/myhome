# Generic Item Picker + "All" Floor — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the per-module `ChorePanel` and `InventoryPickerPanel` with a single generic `ItemPickerPanel` that any future module can use; add an "All" virtual floor to FloorSwitcher so chores can be assigned house-wide by dragging (replacing the per-row 🏠 button).

**Architecture:**
- New `ItemPickerPanel.svelte` receives a `PickerLayer[]` — one entry per active layer — and renders collapsible sections with search and placed/unplaced grouping.
- App.svelte derives `PickerLayer[]` data from the active layer flags and the store contents; drag state is unified into `draggingItemId` + `draggingLayerId`.
- Drag format changed to a layer-agnostic pair: `dataTransfer.setData("pickerLayer", layerId)` + `setData("pickerId", itemId)`. `handleDrop` reads these and routes accordingly.
- "All" floor: a virtual tab in FloorSwitcher (constant `"__all__"`). When selected, App.svelte sets `allFloorsMode = true`, shows a house-wide canvas overlay (no floor plan) where chore drops create assignments with `roomId: null, position: null`.
- Old `ChorePanel.svelte` and `InventoryPickerPanel.svelte` are deleted after their usage in App.svelte is replaced.

**Tech Stack:** Svelte 5 runes, TypeScript, Vitest + jsdom

---

## Shared type definitions

Throughout this plan the following types are used (defined in `ItemPickerPanel.svelte` and exported):

```typescript
export interface PickerItem {
  id: string;
  name: string;    // display name without leading emoji
  emoji: string;
  placed: boolean; // true if placed on ANY floor (or house-wide for chores)
}

export interface PickerLayer {
  id: string;      // "chores" | "inventory" | future…
  label: string;   // "Chores", "Inventory", …
  emoji: string;   // section header icon
  items: PickerItem[];
}
```

---

## Task 1 — `ItemPickerPanel.svelte` + tests

**Files:**
- Create: `packages/editor/src/lib/components/ItemPickerPanel.svelte`
- Create: `packages/editor/test/ItemPickerPanel.test.ts`

### Component spec

```svelte
<script lang="ts">
  export interface PickerItem {
    id: string; name: string; emoji: string; placed: boolean;
  }
  export interface PickerLayer {
    id: string; label: string; emoji: string; items: PickerItem[];
  }
  interface Props {
    layers: PickerLayer[];
    draggingId: string | null;
    ondragstart: (layerId: string, itemId: string, event: DragEvent) => void;
    ondragend: () => void;
  }
  let { layers, draggingId, ondragstart, ondragend }: Props = $props();

  let query = $state("");
  // open sections: auto-derived; one layer → open it; multiple → all closed
  let openSections = $state<Set<string>>(new Set());
  $effect(() => {
    openSections = layers.length === 1 ? new Set([layers[0].id]) : new Set();
  });

  function toggleSection(id: string): void {
    const next = new Set(openSections);
    if (next.has(id)) next.delete(id); else next.add(id);
    openSections = next;
  }

  function filteredItems(items: PickerItem[]): PickerItem[] {
    if (!query.trim()) return items;
    const q = query.toLowerCase();
    return items.filter(i => i.name.toLowerCase().includes(q) || i.emoji.includes(q));
  }

  function startDrag(layerId: string, item: PickerItem, event: DragEvent): void {
    // emoji-only drag image
    const el = document.createElement("div");
    el.textContent = item.emoji;
    el.style.cssText = "font-size:28px;position:absolute;top:-100px;pointer-events:none";
    document.body.appendChild(el);
    event.dataTransfer?.setDragImage(el, 14, 14);
    setTimeout(() => document.body.removeChild(el), 0);

    event.dataTransfer?.setData("pickerLayer", layerId);
    event.dataTransfer?.setData("pickerId", item.id);
    ondragstart(layerId, item.id, event);
  }
</script>

<div class="panel">
  <input class="search" placeholder="Search…" bind:value={query} />
  {#each layers as layer (layer.id)}
    {@const filtered = filteredItems(layer.items)}
    {@const unplaced = filtered.filter(i => !i.placed)}
    {@const placed = filtered.filter(i => i.placed)}
    {@const open = openSections.has(layer.id)}
    <div class="section">
      <button class="section-header" onclick={() => toggleSection(layer.id)}>
        <span class="section-icon">{layer.emoji}</span>
        <span class="section-label">{layer.label}</span>
        <span class="section-count">{layer.items.length}</span>
        <span class="chevron">{open ? "▴" : "▾"}</span>
      </button>
      {#if open}
        <div class="section-body">
          {#if unplaced.length > 0}
            <div class="group-title">Unplaced</div>
            {#each unplaced as item (item.id)}
              <div
                class="item-row"
                class:dragging={draggingId === item.id}
                draggable={true}
                ondragstart={(e) => startDrag(layer.id, item, e)}
                ondragend={() => ondragend()}
                role="button"
                tabindex="0"
              >
                <span class="item-emoji">{item.emoji}</span>
                <span class="item-name">{item.name}</span>
              </div>
            {/each}
          {/if}
          {#if placed.length > 0}
            <div class="group-title">Placed</div>
            {#each placed as item (item.id)}
              <div
                class="item-row placed"
                class:dragging={draggingId === item.id}
                draggable={true}
                ondragstart={(e) => startDrag(layer.id, item, e)}
                ondragend={() => ondragend()}
                role="button"
                tabindex="0"
              >
                <span class="item-emoji">{item.emoji}</span>
                <span class="item-name">{item.name}</span>
              </div>
            {/each}
          {/if}
          {#if filtered.length === 0}
            <div class="empty">No items match</div>
          {/if}
        </div>
      {/if}
    </div>
  {/each}
</div>

<style>
  .panel {
    width: 220px; height: 100%; background: #1e1e2e; border-left: 1px solid #333;
    display: flex; flex-direction: column; font-size: 12px; color: #ccc;
    flex-shrink: 0; overflow: hidden;
  }
  .search {
    margin: 6px 8px; padding: 4px 7px; background: #0a0a20;
    border: 1px solid #2a2a4a; color: #bbb; border-radius: 4px;
    font-size: 11px; flex-shrink: 0;
  }
  .section { border-bottom: 1px solid #2a2a3a; }
  .section-header {
    width: 100%; display: flex; align-items: center; gap: 6px;
    padding: 6px 10px; background: #252535; border: none; color: #aaf;
    cursor: pointer; font-size: 11px; font-weight: 600; text-align: left;
  }
  .section-header:hover { background: #2a2a45; }
  .section-count { margin-left: auto; color: #556; font-size: 10px; }
  .chevron { color: #556; font-size: 9px; flex-shrink: 0; }
  .section-body { overflow-y: auto; }
  .group-title {
    color: #556; font-size: 9px; text-transform: uppercase;
    letter-spacing: .05em; padding: 4px 10px 2px;
  }
  .item-row {
    display: flex; align-items: center; gap: 8px; padding: 5px 10px;
    cursor: grab; user-select: none; border-radius: 3px; margin: 1px 4px;
  }
  .item-row:hover { background: #2a2a4a; }
  .item-row.placed { opacity: .45; }
  .item-row.dragging { opacity: .5; background: #2a2a4a; }
  .item-emoji { font-size: 14px; flex-shrink: 0; }
  .item-name { font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
  .empty { color: #445; font-size: 10px; padding: 8px 10px; }
</style>
```

### Tests

- [ ] **Step 1: Write the failing tests**

Create `packages/editor/test/ItemPickerPanel.test.ts`:

```typescript
import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { mount, unmount } from "svelte";
import ItemPickerPanel from "../src/lib/components/ItemPickerPanel.svelte";
import type { PickerLayer } from "../src/lib/components/ItemPickerPanel.svelte";

const CHORES_LAYER: PickerLayer = {
  id: "chores", label: "Chores", emoji: "✅",
  items: [
    { id: "c1", name: "Vacuum", emoji: "🧹", placed: false },
    { id: "c2", name: "Dishes", emoji: "🍽", placed: true },
  ],
};
const INV_LAYER: PickerLayer = {
  id: "inventory", label: "Inventory", emoji: "📦",
  items: [
    { id: "i1", name: "TV", emoji: "📺", placed: true },
    { id: "i2", name: "Lamp", emoji: "💡", placed: false },
  ],
};

let target: HTMLElement;

beforeEach(() => {
  target = document.createElement("div");
  document.body.appendChild(target);
});
afterEach(() => {
  target.remove();
});

describe("ItemPickerPanel", () => {
  it("renders a section per layer", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const headers = target.querySelectorAll(".section-header");
    expect(headers.length).toBe(2);
    expect(headers[0].textContent).toContain("Chores");
    expect(headers[1].textContent).toContain("Inventory");
    unmount(app);
  });

  it("single layer is expanded by default", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(1);
    unmount(app);
  });

  it("multiple layers are collapsed by default", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(0);
    unmount(app);
  });

  it("clicking a collapsed section header expands it", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER, INV_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const header = target.querySelector<HTMLButtonElement>(".section-header")!;
    header.click();
    await Promise.resolve();
    const bodies = target.querySelectorAll(".section-body");
    expect(bodies.length).toBe(1);
    unmount(app);
  });

  it("clicking an expanded section header collapses it", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const header = target.querySelector<HTMLButtonElement>(".section-header")!;
    // starts open (single layer), click to close
    header.click();
    await Promise.resolve();
    expect(target.querySelectorAll(".section-body").length).toBe(0);
    unmount(app);
  });

  it("items split into Unplaced and Placed groups", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const titles = Array.from(target.querySelectorAll(".group-title")).map(el => el.textContent?.trim());
    expect(titles).toContain("Unplaced");
    expect(titles).toContain("Placed");
    unmount(app);
  });

  it("placed items have the .placed class", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const rows = target.querySelectorAll(".item-row");
    const placedRows = Array.from(rows).filter(r => r.classList.contains("placed"));
    expect(placedRows.length).toBe(1); // only c2 is placed
    unmount(app);
  });

  it("search filters items by name", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const input = target.querySelector<HTMLInputElement>(".search")!;
    input.value = "vacuum";
    input.dispatchEvent(new Event("input"));
    await Promise.resolve();
    const names = Array.from(target.querySelectorAll(".item-name")).map(el => el.textContent);
    expect(names).toContain("Vacuum");
    expect(names).not.toContain("Dishes");
    unmount(app);
  });

  it("ondragstart called with layerId and itemId on drag", async () => {
    const ondragstart = vi.fn();
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, ondragstart, ondragend: vi.fn() },
    });
    const row = target.querySelector<HTMLElement>(".item-row")!;
    const dt = { setDragImage: vi.fn(), setData: vi.fn() };
    const evt = new MouseEvent("dragstart", { bubbles: true }) as unknown as DragEvent;
    Object.defineProperty(evt, "dataTransfer", { value: dt });
    row.dispatchEvent(evt);
    await Promise.resolve();
    expect(ondragstart).toHaveBeenCalledWith("chores", expect.any(String), expect.anything());
    unmount(app);
  });

  it("dragging item gets .dragging class", async () => {
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: "c1", ondragstart: vi.fn(), ondragend: vi.fn() },
    });
    const rows = target.querySelectorAll(".item-row");
    const draggingRow = Array.from(rows).find(r => r.classList.contains("dragging"));
    expect(draggingRow).toBeTruthy();
    expect(draggingRow?.querySelector(".item-emoji")?.textContent).toBe("🧹");
    unmount(app);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

```
cd packages/editor && npx vitest run test/ItemPickerPanel.test.ts
```
Expected: FAIL (file doesn't exist yet)

- [ ] **Step 3: Create `ItemPickerPanel.svelte`**

Use the component spec shown above verbatim. Save to `packages/editor/src/lib/components/ItemPickerPanel.svelte`.

- [ ] **Step 4: Run tests — expect all to pass**

```
cd packages/editor && npx vitest run test/ItemPickerPanel.test.ts
```
Expected: 9 tests passing.

- [ ] **Step 5: Run full suite to check for regressions**

```
cd packages/editor && npm test
```
Expected: all tests still pass (111 + 9 = 120).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ItemPickerPanel.svelte packages/editor/test/ItemPickerPanel.test.ts
git commit -m "feat: add generic ItemPickerPanel component with section collapse and search"
```

---

## Task 2 — Update App.svelte to use generic picker

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Delete: `packages/editor/src/lib/components/ChorePanel.svelte`
- Delete: `packages/editor/src/lib/components/InventoryPickerPanel.svelte`

### What changes in App.svelte

**Imports (top of `<script>`):**
- Remove: `import ChorePanel from "./lib/components/ChorePanel.svelte";`
- Remove: `import InventoryPickerPanel from "./lib/components/InventoryPickerPanel.svelte";`
- Add: `import ItemPickerPanel from "./lib/components/ItemPickerPanel.svelte";`
- Add: `import type { PickerLayer } from "./lib/components/ItemPickerPanel.svelte";`

**State (replace split drag state with unified):**
Remove:
```typescript
let draggingInventoryItemId = $state<string | null>(null);
let draggingChoreId = $state<string | null>(null);
```
Add:
```typescript
let draggingItemId = $state<string | null>(null);
let draggingLayerId = $state<string | null>(null);
```

Also add the `ALL_FLOOR_ID` constant and `allFloorsMode` state:
```typescript
const ALL_FLOOR_ID = "__all__";
let allFloorsMode = $state(false);
```

**Helper to strip leading emoji from chore name (add near the top of script):**
```typescript
function choreDisplayName(name: string, emoji: string): string {
  const trimmed = name.trim();
  return (emoji && trimmed.startsWith(emoji)) ? trimmed.slice(emoji.length).trim() : trimmed;
}
```

**Derived picker layers (add near the activeLayers block):**
```typescript
const chorePickerLayer = $derived<PickerLayer>({
  id: "chores",
  label: "Chores",
  emoji: "✅",
  items: choreStore.chores.map(c => ({
    id: c.id,
    name: choreDisplayName(c.name, c.emoji),
    emoji: c.emoji,
    placed: choreStore.assignments.some(a => a.choreId === c.id),
  })),
});

const inventoryPickerLayer = $derived<PickerLayer>({
  id: "inventory",
  label: "Inventory",
  emoji: "📦",
  items: inventoryStore.items.map(i => ({
    id: i.id,
    name: i.name,
    emoji: i.emoji,
    placed: i.placement !== null,
  })),
});

const pickerLayers = $derived<PickerLayer[]>([
  ...(choreLayerActive ? [chorePickerLayer] : []),
  ...(inventoryLayerActive ? [inventoryPickerLayer] : []),
]);
```

**`handleDragOver` — replace the condition:**
Old: `if (!draggingChoreId && !draggingInventoryItemId) return;`
New: `if (!draggingItemId) return;`

**`handleDrop` — full replacement:**
```typescript
function handleDrop(e: DragEvent): void {
  e.preventDefault();
  const layerId = e.dataTransfer?.getData("pickerLayer") ?? draggingLayerId;
  const itemId = e.dataTransfer?.getData("pickerId") ?? draggingItemId;
  draggingItemId = null;
  draggingLayerId = null;
  if (!layerId || !itemId) return;

  if (allFloorsMode) {
    if (layerId !== "chores") return; // only chores can be house-wide
    const chore = choreStore.chores.find(c => c.id === itemId);
    choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "" });
    return;
  }

  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
  const screenX = e.clientX - rect.left, screenY = e.clientY - rect.top;
  const worldX = (screenX - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
  const worldY = (screenY - viewportStore.viewport.panY) / viewportStore.viewport.zoom;

  if (layerId === "inventory") {
    const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
    inventoryStore.setPlacement(itemId, {
      floorId: floorStore.currentFloorId,
      roomId: room?.id ?? null,
      position: { x: worldX, y: worldY },
    });
    return;
  }

  if (layerId === "chores") {
    const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
    if (!room) return;
    const chore = choreStore.chores.find(c => c.id === itemId);
    choreStore.createAssignment({ choreId: itemId, roomId: room.id, position: { x: worldX, y: worldY }, nextDueDate: chore?.nextDueDate ?? "" });
  }
}
```

**FloorSwitcher call — update `onswitchfloor` and add `currentFloorId` with allFloorsMode awareness:**
Old:
```svelte
<FloorSwitcher
  floors={floorStore.floors}
  currentFloorId={floorStore.currentFloorId}
  onswitchfloor={(id) => { floorStore.switchFloor(id); toolStore.select(null); toolStore.selectRoom(null); toolStore.selectOpening(null); }}
  ...
```
New:
```svelte
<FloorSwitcher
  floors={floorStore.floors}
  currentFloorId={allFloorsMode ? ALL_FLOOR_ID : floorStore.currentFloorId}
  onswitchfloor={(id) => {
    if (id === ALL_FLOOR_ID) { allFloorsMode = true; return; }
    allFloorsMode = false;
    floorStore.switchFloor(id);
    toolStore.select(null);
    toolStore.selectRoom(null);
    toolStore.selectOpening(null);
  }}
  ...
```

**Canvas area — add allFloorsMode branch:**
The canvas area currently always renders `<Canvas>`. When `allFloorsMode` is true, show a drop-zone overlay instead:

Replace:
```svelte
<div class="canvas-area" ... ondragover={handleDragOver} ondrop={handleDrop}>
  {#if !floorStore.loaded}
    <div class="loading">Loading…</div>
  {:else}
    <Canvas .../>
    ...
  {/if}
</div>
```

With:
```svelte
<div class="canvas-area" ... ondragover={handleDragOver} ondrop={handleDrop}>
  {#if allFloorsMode}
    <div class="all-floor-canvas">
      <div class="all-floor-hint">
        <span class="all-floor-icon">🏠</span>
        <span class="all-floor-title">House-wide</span>
        <span class="all-floor-sub">Drag chores here to assign to the whole house</span>
      </div>
      {#each choreStore.houseAssignments() as a (a.id)}
        {@const chore = choreStore.chores.find(c => c.id === a.choreId)}
        {#if chore}
          <div class="house-badge">
            <span>{chore.emoji}</span>
            <span>{choreDisplayName(chore.name, chore.emoji)}</span>
            <button
              class="house-badge-remove"
              onclick={() => choreStore.deleteAssignment(a.id)}
              title="Remove house-wide assignment"
            >✕</button>
          </div>
        {/if}
      {/each}
    </div>
  {:else}
    {#if !floorStore.loaded}
      <div class="loading">Loading…</div>
    {:else}
      <Canvas .../>
      <!-- all existing overlays, picker, etc. -->
    {/if}
  {/if}
</div>
```

**CSS additions for all-floor view (in the `<style>` block):**
```css
.all-floor-canvas {
  flex: 1; display: flex; flex-direction: column; align-items: center;
  padding: 40px 24px; gap: 12px; background: #111122;
}
.all-floor-hint {
  display: flex; flex-direction: column; align-items: center; gap: 6px;
  margin-bottom: 24px;
}
.all-floor-icon { font-size: 40px; }
.all-floor-title { font-size: 18px; color: #eee; font-weight: 600; }
.all-floor-sub { font-size: 12px; color: #667; }
.house-badge {
  display: flex; align-items: center; gap: 10px; padding: 8px 16px;
  background: #1e1e2e; border: 1px solid #333; border-radius: 6px;
  color: #ccc; font-size: 13px; min-width: 200px;
}
.house-badge-remove {
  margin-left: auto; border: none; background: transparent; color: #666;
  cursor: pointer; font-size: 11px; padding: 2px 5px;
}
.house-badge-remove:hover { color: #f66; }
```

**Replace ItemPickerPanel usage (inside the `{#if pickerOpen && ...}` block):**
Old:
```svelte
{#if inventoryLayerActive}
  <InventoryPickerPanel ... />
{/if}
{#if choreLayerActive}
  <ChorePanel ... />
{/if}
```
New (single component, order: inventory left, chores right):
```svelte
<ItemPickerPanel
  layers={pickerLayers}
  draggingId={draggingItemId}
  ondragstart={(layerId, itemId) => { draggingLayerId = layerId; draggingItemId = itemId; }}
  ondragend={() => { draggingLayerId = null; draggingItemId = null; }}
/>
```

**Also update the `{#if pickerOpen && (choreLayerActive || inventoryLayerActive)}` condition** to handle the allFloorsMode: when allFloorsMode, only show the chore picker if choreLayerActive:

The picker visibility condition stays the same (no change needed — when allFloorsMode you can still open the picker).

**Remove old ChoreOverlay call's `ondragend={handleBadgeDragEnd}` reference** — check that `handleBadgeDragEnd` still exists and is correct (it handles reposition of badges via pointer capture, nothing to do with the picker drag).

- [ ] **Step 1: Make all the changes to App.svelte described above**

Read the current App.svelte to see exact line numbers before editing. Make each edit carefully. Do NOT accidentally remove the existing overlay components (ChoreOverlay, InventoryOverlay, BadgePopup, InventoryPinPopup) — those are separate from the picker panel.

- [ ] **Step 2: Delete old files**

```bash
rm packages/editor/src/lib/components/ChorePanel.svelte
rm packages/editor/src/lib/components/InventoryPickerPanel.svelte
```

- [ ] **Step 3: Run the test suite**

```bash
cd packages/editor && npm test
```
Expected: all tests pass (the deleted files had no tests).

- [ ] **Step 4: Commit**

```bash
git add -A
git commit -m "feat: wire ItemPickerPanel into App.svelte; unify drag state; add All floor handling"
```

---

## Task 3 — "All" floor tab in FloorSwitcher

**Files:**
- Modify: `packages/editor/src/lib/components/FloorSwitcher.svelte`

### What changes

Add `ALL_FLOOR_ID` constant inside FloorSwitcher and render a non-removable, non-renameable "All" tab **before** the real floors:

The prop `currentFloorId` already gets `"__all__"` from App.svelte when allFloorsMode is active — FloorSwitcher just needs to render the tab.

```svelte
<script lang="ts">
  // add at top of script:
  const ALL_FLOOR_ID = "__all__";
  // ... rest of existing code unchanged ...
</script>

<div class="floor-switcher">
  <!-- NEW: All virtual floor tab -->
  <div class="floor-btn all-btn" class:active={currentFloorId === ALL_FLOOR_ID}>
    <button
      class="floor-label"
      onclick={() => onswitchfloor(ALL_FLOOR_ID)}
      title="House-wide assignments"
    >🏠 All</button>
  </div>

  {#each floors as floor (floor.id)}
    <!-- existing markup unchanged -->
  {/each}
  <button class="add-btn" onclick={handleAddFloor}>+ Floor</button>
</div>
```

Add CSS for the all-btn:
```css
.all-btn .floor-label { color: #aaf; }
```

- [ ] **Step 1: Make the changes to FloorSwitcher.svelte**

- [ ] **Step 2: Run the test suite**

```bash
cd packages/editor && npm test
```
Expected: all tests pass.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/FloorSwitcher.svelte
git commit -m "feat: add All virtual floor tab to FloorSwitcher for house-wide assignments"
```

---

## Done

After all tasks:

1. Run `cd packages/editor && npm test` — all tests green
2. Push the branch and open a PR against main
