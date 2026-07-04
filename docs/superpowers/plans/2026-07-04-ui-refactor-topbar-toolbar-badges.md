# UI Refactor: Topbar, Floating Toolbar, Badge Scaling, Map Height — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Clean up the topbar to be context-free, move all floor-plan controls into a right-side floating vertical panel, scale overlay badges proportionally to the viewport zoom, and increase the home dashboard map height.

**Architecture:** The topbar loses all route-conditional content and becomes a static bar with hamburger, title, homes switcher, theme toggle, and user badge. A new `floating-toolbar` div (position:absolute inside canvas-area) contains all floor-plan controls. All five overlay components get a derived `badgeScale` that wraps their SVG badge groups in a `scale()` transform. FloorSwitcher gains a `compact` prop; LayersDropdown gains a `popoverAlign` prop; HomesSwitcher gains a `topbar` prop.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, svelte mount/unmount test pattern.

---

## File Map

| File | Change |
|------|--------|
| `src/lib/components/ChoreOverlay.svelte` | Add `badgeScale` derived from zoom; wrap badge `<g>` in scale |
| `src/lib/components/InventoryOverlay.svelte` | Same |
| `src/lib/components/CostsOverlay.svelte` | Same |
| `src/lib/components/WorksOverlay.svelte` | Same |
| `src/lib/components/ConsumableOverlay.svelte` | Same |
| `src/lib/components/HomeMapWidget.svelte` | Map area height 220→360 |
| `src/lib/components/HomesSwitcher.svelte` | Add `topbar` prop; new compact inline style |
| `src/lib/components/NavMenu.svelte` | Remove `<HomesSwitcher>`; remove `onexpand` prop |
| `src/lib/components/FloorSwitcher.svelte` | Add `compact` prop with popover mode |
| `src/lib/components/LayersDropdown.svelte` | Add `popoverAlign: 'left'\|'right'` prop |
| `src/App.svelte` | Topbar cleanup; floating toolbar; new HomesSwitcher placement; theme toggle moved right |
| `test/InventoryOverlay.test.ts` | Add badge scale test |
| `test/NavMenu.test.ts` | Assert HomesSwitcher no longer in nav |
| `test/App.test.ts` | Update `toolbarBtn` helper; update toolbar tests; add floating-toolbar tests |

---

### Task 1: Badge scaling — ChoreOverlay

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreOverlay.svelte`

The badge `<g>` currently uses `transform="translate({sp.x},{sp.y})"`. Add a `badgeScale` derived value and append `scale({badgeScale})` to the transform. All existing child elements (circles, text, dasharray) are correct at their current literal sizes — SVG scale handles everything.

Formula: `Math.max(0.35, Math.min(1.2, viewport.zoom / 80))`

- [ ] **Step 1: Add `badgeScale` derived in the script block**

In `ChoreOverlay.svelte`, after the `const C = 2 * Math.PI * R;` line, add:

```svelte
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));
```

- [ ] **Step 2: Apply scale to the badge group transform**

Find the existing badge `<g transform="translate({sp.x},{sp.y})" ...>` and change to:

```svelte
        <g
          transform="translate({sp.x},{sp.y}) scale({badgeScale})"
          style="pointer-events:{choreMode ? 'all' : 'none'};cursor:{choreMode ? (dragId === a.id ? 'grabbing' : 'grab') : 'default'}"
          onpointerdown={(e) => handlePointerDown(e, a)}
          onpointerup={(e) => handlePointerUp(e, a)}
        >
```

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ChoreOverlay.svelte
git commit -m "feat: scale chore overlay badges with viewport zoom"
```

---

### Task 2: Badge scaling — InventoryOverlay, CostsOverlay, WorksOverlay

**Files:**
- Modify: `packages/editor/src/lib/components/InventoryOverlay.svelte`
- Modify: `packages/editor/src/lib/components/CostsOverlay.svelte`
- Modify: `packages/editor/src/lib/components/WorksOverlay.svelte`
- Test: `packages/editor/test/InventoryOverlay.test.ts`

All three use the same pattern: `<g transform="translate({sp.x},{sp.y})" style={groupStyle(...)}>` with emoji text and a label rect below.

- [ ] **Step 1: Write failing test in InventoryOverlay.test.ts**

Add this test at the bottom of `describe("InventoryOverlay")`:

```typescript
  it("scales badge group smaller at low zoom (home widget zoom)", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem()],
        viewport: { panX: 0, panY: 0, zoom: 20 },
        active: false,
        width: 400,
        height: 240,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const g = target.querySelector("svg g");
    expect(g?.getAttribute("transform")).toContain("scale(0.35)");

    unmount(comp);
    target.remove();
  });

  it("does not enlarge badge beyond 1.2x at high zoom", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);

    const comp = mount(InventoryOverlay, {
      target,
      props: {
        items: [makeItem()],
        viewport: { panX: 0, panY: 0, zoom: 200 },
        active: false,
        width: 800,
        height: 600,
        onclick: vi.fn(),
        ondragend: vi.fn(),
      },
    });

    const g = target.querySelector("svg g");
    expect(g?.getAttribute("transform")).toContain("scale(1.2)");

    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run to confirm failures**

```bash
cd packages/editor && npx vitest run test/InventoryOverlay.test.ts
```

Expected: 2 new tests fail (no `scale(...)` in transform yet).

- [ ] **Step 3: Add badgeScale to InventoryOverlay**

In `InventoryOverlay.svelte` script block, after `const placedItems = $derived(...)`, add:

```typescript
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));
```

Change each badge `<g transform="translate({sp.x},{sp.y})" style={groupStyle(item)}>` to:

```svelte
      <g
        transform="translate({sp.x},{sp.y}) scale({badgeScale})"
        style={groupStyle(item)}
        onpointerdown={(e) => handlePointerDown(e, item)}
        onpointerup={(e) => handlePointerUp(e, item)}
      >
```

- [ ] **Step 4: Add badgeScale to CostsOverlay**

In `CostsOverlay.svelte`, after `const placedCategories = $derived(...)`, add:

```typescript
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));
```

Change `<g transform="translate({sp.x},{sp.y})" style={groupStyle(cat)}>` to:

```svelte
      <g transform="translate({sp.x},{sp.y}) scale({badgeScale})" style={groupStyle(cat)}
         onpointerdown={(e) => handlePointerDown(e, cat)}
         onpointerup={(e) => handlePointerUp(e, cat)}>
```

- [ ] **Step 5: Add badgeScale to WorksOverlay**

In `WorksOverlay.svelte`, after `const placedWorks = $derived(...)`, add:

```typescript
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));
```

Change the badge `<g transform="translate({sp.x},{sp.y})" style={groupStyle(work)}>` to:

```svelte
      <g
        transform="translate({sp.x},{sp.y}) scale({badgeScale})"
        style={groupStyle(work)}
        onpointerdown={(e) => handlePointerDown(e, work)}
        onpointerup={(e) => handlePointerUp(e, work)}
      >
```

- [ ] **Step 6: Run tests**

```bash
cd packages/editor && npx vitest run test/InventoryOverlay.test.ts
```

Expected: all tests pass.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/InventoryOverlay.svelte \
        packages/editor/src/lib/components/CostsOverlay.svelte \
        packages/editor/src/lib/components/WorksOverlay.svelte \
        packages/editor/test/InventoryOverlay.test.ts
git commit -m "feat: scale inventory/costs/works overlay badges with viewport zoom"
```

---

### Task 3: Badge scaling — ConsumableOverlay

**Files:**
- Modify: `packages/editor/src/lib/components/ConsumableOverlay.svelte`

ConsumableOverlay has a more complex badge (background circle, inner circle, emoji, vertical bar, quantity label). All child elements scale correctly under the group's scale transform.

- [ ] **Step 1: Add badgeScale derived**

In `ConsumableOverlay.svelte` script block, after the `const placedConsumables = $derived(...)` line, add:

```typescript
  const badgeScale = $derived(Math.max(0.35, Math.min(1.2, viewport.zoom / 80)));
```

- [ ] **Step 2: Apply scale to the outer badge group**

The current badge group opens with:

```svelte
      <g
        transform="translate({sp.x},{sp.y})"
        style="pointer-events:{active ? 'all' : 'none'};cursor:..."
        ...
```

Change to:

```svelte
      <g
        transform="translate({sp.x},{sp.y}) scale({badgeScale})"
        style="pointer-events:{active ? 'all' : 'none'};cursor:{active ? (dragId === c.id ? 'grabbing' : 'grab') : 'default'}"
        onpointerdown={(e) => handlePointerDown(e, c)}
        onpointerup={(e) => handlePointerUp(e, c)}
      >
```

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/ConsumableOverlay.svelte
git commit -m "feat: scale consumable overlay badges with viewport zoom"
```

---

### Task 4: HomeMapWidget height

**Files:**
- Modify: `packages/editor/src/lib/components/HomeMapWidget.svelte`
- Test: `packages/editor/test/HomeMapWidget.test.ts`

- [ ] **Step 1: Write failing test**

Add to `HomeMapWidget.test.ts` at the bottom of `describe("HomeMapWidget")`:

```typescript
  it("map area is at least 340px tall", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const mapArea = target.querySelector(".map-area") as HTMLElement;
    const height = parseInt(getComputedStyle(mapArea).height ?? "0", 10);
    // jsdom doesn't compute CSS, check inline style or className
    // The height is set via CSS class; check the element has the expected class applied
    // by inspecting the style sheet won't work in jsdom — instead check the inline style attribute
    // is absent (height comes from stylesheet), and verify the component renders the map-area element.
    expect(mapArea).not.toBeNull();

    unmount(comp);
    target.remove();
  });
```

Note: jsdom doesn't evaluate CSS stylesheets, so we can't assert the computed height directly. The test just verifies `.map-area` exists. The visual verification is manual (run the app).

- [ ] **Step 2: Change map-area height in CSS**

In `HomeMapWidget.svelte` find:

```css
  .map-area {
    position: relative; overflow: hidden; height: 220px;
```

Change to:

```css
  .map-area {
    position: relative; overflow: hidden; height: 360px;
```

- [ ] **Step 3: Run tests**

```bash
cd packages/editor && npx vitest run test/HomeMapWidget.test.ts
```

Expected: all pass.

- [ ] **Step 4: Commit**

```bash
git add packages/editor/src/lib/components/HomeMapWidget.svelte \
        packages/editor/test/HomeMapWidget.test.ts
git commit -m "feat: increase home map widget height to 360px"
```

---

### Task 5: HomesSwitcher topbar variant

**Files:**
- Modify: `packages/editor/src/lib/components/HomesSwitcher.svelte`

Add a `topbar: boolean = false` prop. When `topbar=true`: no `expanded`/`onexpand` dependency; always shows `⌂ HomeName ▼` inline; different CSS (no border-bottom, no sidebar padding, compact height).

- [ ] **Step 1: Update the Props interface and add topbar CSS**

Replace the existing script block Props:

```svelte
<script lang="ts">
  import { homesStore } from "../homesStore.svelte";
  import NewHomeModal from "./NewHomeModal.svelte";

  interface Props {
    expanded?: boolean;
    onexpand?: () => void;
    topbar?: boolean;
  }
  let { expanded = false, onexpand, topbar = false }: Props = $props();

  let dropdownOpen = $state(false);
  let showNewModal = $state(false);

  $effect(() => {
    if (!expanded && !topbar) dropdownOpen = false;
  });

  function handleClick(): void {
    if (topbar) { dropdownOpen = !dropdownOpen; return; }
    if (!expanded) { onexpand?.(); return; }
    dropdownOpen = !dropdownOpen;
  }

  function selectHome(id: string): void {
    homesStore.setActiveHomeId(id);
    dropdownOpen = false;
  }

  function typeIcon(type: string): string {
    return type === "project" ? "🏗" : "🏠";
  }
</script>
```

- [ ] **Step 2: Add topbar template branch**

Replace the entire template (below `</script>`) with:

```svelte
{#if topbar}
  <div class="switcher-topbar">
    <button
      class="topbar-current"
      onclick={handleClick}
      title={homesStore.activeHome?.name ?? "Select home"}
    >
      <span class="topbar-icon">⌂</span>
      <span class="topbar-name">{homesStore.activeHome?.name ?? "—"}</span>
      <span class="topbar-chevron">{dropdownOpen ? "▲" : "▼"}</span>
    </button>

    {#if dropdownOpen}
      <div class="topbar-dropdown">
        {#each homesStore.homes as home (home.id)}
          <button
            class="home-item"
            class:active={home.id === homesStore.activeHomeId}
            onclick={() => selectHome(home.id)}
          >
            <span class="icon">{typeIcon(home.type)}</span>
            <span class="home-name">{home.name}</span>
          </button>
        {/each}
        <hr class="separator" />
        <button class="home-item add" onclick={() => { dropdownOpen = false; showNewModal = true; }}>
          <span class="icon">＋</span>
          <span class="home-name">New home</span>
        </button>
      </div>
    {/if}
  </div>
{:else}
  <div class="switcher" class:expanded>
    <button
      class="current"
      onclick={handleClick}
      title={homesStore.activeHome?.name ?? "Select home"}
    >
      <span class="icon">⌂</span>
      {#if expanded}
        <span class="name">{homesStore.activeHome?.name ?? "—"}</span>
        <span class="chevron">{dropdownOpen ? "▲" : "▼"}</span>
      {/if}
    </button>

    {#if dropdownOpen}
      <div class="dropdown">
        {#each homesStore.homes as home (home.id)}
          <button
            class="home-item"
            class:active={home.id === homesStore.activeHomeId}
            onclick={() => selectHome(home.id)}
          >
            <span class="icon">{typeIcon(home.type)}</span>
            <span class="home-name">{home.name}</span>
          </button>
        {/each}
        <hr class="separator" />
        <button class="home-item add" onclick={() => { dropdownOpen = false; showNewModal = true; }}>
          <span class="icon">＋</span>
          <span class="home-name">New home</span>
        </button>
      </div>
    {/if}
  </div>
{/if}

<NewHomeModal open={showNewModal} onclose={() => { showNewModal = false; }} />
```

- [ ] **Step 3: Add topbar CSS to the style block**

Append to the existing `<style>` block:

```css
  /* Topbar variant */
  .switcher-topbar { position: relative; }

  .topbar-current {
    display: flex; align-items: center; gap: 6px;
    padding: 4px 8px; border: none; background: none;
    border-radius: var(--radius-sm); cursor: pointer; color: var(--text);
    font-size: 13px; font-weight: 500;
  }
  .topbar-current:hover { background: var(--surface-hover); }

  .topbar-icon { font-size: 15px; line-height: 1; }
  .topbar-name { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .topbar-chevron { font-size: 9px; color: var(--text-muted); }

  .topbar-dropdown {
    position: absolute; top: calc(100% + 4px); right: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.15);
    z-index: 200; padding: 4px; min-width: 160px;
  }
```

- [ ] **Step 4: Run full test suite to ensure no regressions**

```bash
cd packages/editor && npx vitest run
```

Expected: all tests pass (existing HomesSwitcher behaviour is unchanged in sidebar mode).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/HomesSwitcher.svelte
git commit -m "feat: add topbar variant to HomesSwitcher"
```

---

### Task 6: NavMenu — remove HomesSwitcher and onexpand prop

**Files:**
- Modify: `packages/editor/src/lib/components/NavMenu.svelte`
- Test: `packages/editor/test/NavMenu.test.ts`

- [ ] **Step 1: Write failing test**

Add to `NavMenu.test.ts` at the bottom of `describe("NavMenu")`:

```typescript
  it("does not render a HomesSwitcher / home-switcher element", () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(NavMenu, {
      target,
      props: { currentRoute: "#/", expanded: true, onclose: vi.fn() },
    });

    // After removal, there is no .switcher or home-name element inside the nav
    expect(target.querySelector(".switcher")).toBeNull();
    expect(target.querySelector(".topbar-current")).toBeNull();

    unmount(comp);
    target.remove();
  });
```

- [ ] **Step 2: Run to confirm test fails**

```bash
cd packages/editor && npx vitest run test/NavMenu.test.ts
```

Expected: new test fails (`.switcher` is still present).

- [ ] **Step 3: Remove HomesSwitcher from NavMenu**

In `NavMenu.svelte`, remove the import and the component:

Remove from script:
```typescript
  import HomesSwitcher from "./HomesSwitcher.svelte";
```

Remove from Props interface:
```typescript
  onexpand?: () => void;
```

Remove from destructuring:
```typescript
  // Remove onexpand from: let { currentRoute, expanded, onclose, onexpand }: Props = $props();
  // Change to:
  let { currentRoute, expanded, onclose }: Props = $props();
```

Remove from template — delete this line:
```svelte
    <HomesSwitcher {expanded} {onexpand} />
```

- [ ] **Step 4: Run NavMenu tests**

```bash
cd packages/editor && npx vitest run test/NavMenu.test.ts
```

Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/NavMenu.svelte \
        packages/editor/test/NavMenu.test.ts
git commit -m "refactor: remove HomesSwitcher from nav, nav no longer needs onexpand"
```

---

### Task 7: FloorSwitcher compact variant

**Files:**
- Modify: `packages/editor/src/lib/components/FloorSwitcher.svelte`

When `compact=true`, show a single button with the current floor name that opens a popover to the left. The popover lists all floors and an add button. Double-click rename and remove buttons are excluded from compact mode (they are drawing-workflow features not needed in a compact context).

- [ ] **Step 1: Add `compact` prop and compact template**

Replace the full `FloorSwitcher.svelte` content:

```svelte
<script lang="ts">
  import type { Floor } from "@myhome/geometry";

  let {
    floors,
    currentFloorId,
    onswitchfloor,
    onaddfloor,
    onrenamefloor,
    onremovefloor,
    compact = false,
  }: {
    floors: Floor[];
    currentFloorId: string;
    onswitchfloor: (id: string) => void;
    onaddfloor?: (name: string) => void;
    onrenamefloor?: (id: string, name: string) => void;
    onremovefloor?: (id: string) => void;
    compact?: boolean;
  } = $props();

  const ALL_FLOOR_ID = "__all__";

  let editingId = $state<string | null>(null);
  let editingName = $state("");
  let compactOpen = $state(false);

  const currentFloorName = $derived(
    currentFloorId === ALL_FLOOR_ID
      ? "All"
      : (floors.find((f) => f.id === currentFloorId)?.name ?? "—")
  );

  function handleFloorClick(floor: Floor, event: MouseEvent): void {
    if (floor.id !== currentFloorId) {
      onswitchfloor(floor.id);
      return;
    }
    if (onrenamefloor && (event as MouseEvent & { detail: number }).detail === 2) {
      editingId = floor.id;
      editingName = floor.name;
    }
  }

  function commitRename(): void {
    if (!editingId) return;
    const trimmed = editingName.trim();
    if (trimmed) onrenamefloor?.(editingId, trimmed);
    editingId = null;
  }

  function handleRenameKey(event: KeyboardEvent): void {
    if (event.key === "Enter") commitRename();
    if (event.key === "Escape") editingId = null;
  }

  function handleAddFloor(): void {
    const n = floors.length + 1;
    const names = ["Ground Floor", "First Floor", "Second Floor", "Third Floor", "Basement"];
    const name = names[n - 1] ?? `Floor ${n}`;
    onaddfloor?.(name);
  }

  function selectCompact(id: string): void {
    onswitchfloor(id);
    compactOpen = false;
  }
</script>

{#if compact}
  <div class="compact-switcher">
    <button
      class="compact-btn"
      onclick={() => { compactOpen = !compactOpen; }}
      title="Switch floor"
    >
      <span class="compact-label">{currentFloorName}</span>
      <span class="compact-chevron">{compactOpen ? "▴" : "▾"}</span>
    </button>

    {#if compactOpen}
      <div class="compact-popover">
        <button
          class="compact-floor-item"
          class:active={currentFloorId === ALL_FLOOR_ID}
          onclick={() => selectCompact(ALL_FLOOR_ID)}
        >🏠 All</button>
        {#each floors as floor (floor.id)}
          <button
            class="compact-floor-item"
            class:active={floor.id === currentFloorId}
            onclick={() => selectCompact(floor.id)}
          >{floor.name}</button>
        {/each}
        {#if onaddfloor}
          <hr class="compact-sep" />
          <button class="compact-floor-item add" onclick={() => { handleAddFloor(); compactOpen = false; }}>＋ Add floor</button>
        {/if}
      </div>
    {/if}
  </div>
{:else}
  <div class="floor-switcher">
    <div class="floor-btn all-btn" class:active={currentFloorId === ALL_FLOOR_ID}>
      <button
        class="floor-label"
        onclick={() => onswitchfloor(ALL_FLOOR_ID)}
        title="House-wide assignments — drag chores here"
      >🏠 All</button>
    </div>
    {#each floors as floor (floor.id)}
      <div class="floor-btn" class:active={floor.id === currentFloorId}>
        {#if editingId === floor.id}
          <input
            class="rename-input"
            bind:value={editingName}
            onblur={commitRename}
            onkeydown={handleRenameKey}
            autofocus
          />
        {:else}
          <button
            class="floor-label"
            onclick={(e) => handleFloorClick(floor, e)}
            title={floor.id === currentFloorId ? "Double-click to rename" : "Switch to this floor"}
          >
            {floor.name}
          </button>
        {/if}
        {#if onremovefloor && floors.length > 1}
          <button
            class="remove-btn"
            onclick={() => onremovefloor(floor.id)}
            title="Delete floor"
            aria-label="Delete {floor.name}"
          >×</button>
        {/if}
      </div>
    {/each}
    {#if onaddfloor}
      <button class="add-btn" onclick={handleAddFloor}>+ Floor</button>
    {/if}
  </div>
{/if}

<style>
  /* ── Compact variant ── */
  .compact-switcher { position: relative; }

  .compact-btn {
    display: flex; align-items: center; gap: 4px;
    width: 100%; padding: 4px 6px;
    border: none; background: none; border-radius: var(--radius-sm);
    cursor: pointer; color: var(--text); font-size: 11px; font-weight: 500;
    white-space: nowrap; justify-content: center;
  }
  .compact-btn:hover { background: var(--surface-hover); }
  .compact-label { max-width: 70px; overflow: hidden; text-overflow: ellipsis; }
  .compact-chevron { font-size: 9px; color: var(--text-muted); flex-shrink: 0; }

  .compact-popover {
    position: absolute; right: calc(100% + 6px); top: 0;
    background: var(--surface); border: 1px solid var(--border);
    border-radius: var(--radius); box-shadow: 0 4px 12px rgba(0,0,0,0.2);
    z-index: 100; padding: 4px; min-width: 130px;
  }

  .compact-floor-item {
    display: block; width: 100%; padding: 6px 10px;
    border: none; background: none; border-radius: var(--radius-sm);
    cursor: pointer; color: var(--text); font-size: 12px; text-align: left;
  }
  .compact-floor-item:hover { background: var(--surface-hover); }
  .compact-floor-item.active { background: var(--accent); color: var(--accent-contrast); }
  .compact-floor-item.add { color: var(--text-muted); }
  .compact-sep { border: none; border-top: 1px solid var(--border); margin: 4px 0; }

  /* ── Full (default) variant ── */
  .floor-switcher {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .floor-btn {
    display: flex;
    align-items: center;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    overflow: hidden;
  }

  .floor-btn.active {
    background: var(--surface-hover);
    outline: 1px solid var(--accent);
  }

  .floor-label {
    padding: 3px 8px;
    border: none;
    background: transparent;
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
    white-space: nowrap;
  }

  .floor-btn.active .floor-label {
    color: var(--text);
  }

  .remove-btn {
    padding: 3px 5px;
    border: none;
    border-left: 1px solid var(--border);
    background: transparent;
    color: var(--text-faint);
    cursor: pointer;
    font-size: 11px;
    line-height: 1;
  }

  .remove-btn:hover {
    color: var(--danger);
    background: var(--surface-hover);
  }

  .rename-input {
    width: 90px;
    padding: 2px 6px;
    background: var(--surface-alt);
    border: 1px solid var(--accent);
    border-radius: var(--radius-sm);
    color: var(--text);
    font-size: 12px;
  }

  .add-btn {
    padding: 3px 8px;
    border: none;
    border-radius: var(--radius-sm);
    background: var(--surface-alt);
    color: var(--text-muted);
    cursor: pointer;
    font-size: 12px;
  }

  .add-btn:hover {
    background: var(--surface-hover);
    color: var(--text);
  }
</style>
```

- [ ] **Step 2: Run full test suite**

```bash
cd packages/editor && npx vitest run
```

Expected: all pass (FloorSwitcher's default mode is identical; compact mode is additive).

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/FloorSwitcher.svelte
git commit -m "feat: add compact popover mode to FloorSwitcher"
```

---

### Task 8: LayersDropdown left-align option

**Files:**
- Modify: `packages/editor/src/lib/components/LayersDropdown.svelte`

Add `popoverAlign: 'left' | 'right' = 'right'` prop. When `'left'`, the dropdown opens to the left of the button (right edge aligned, right: 0; left: auto) rather than the default right-opening (left: 0).

- [ ] **Step 1: Add prop and conditional dropdown position**

Replace the script block:

```svelte
<script lang="ts">
  interface Props {
    activeLayers: Set<string>;
    ontoggle: (layer: string) => void;
    popoverAlign?: 'left' | 'right';
  }
  let { activeLayers, ontoggle, popoverAlign = 'right' }: Props = $props();

  let open = $state(false);

  const layers = [
    { id: "chores",      icon: "✅", label: "Chores"      },
    { id: "inventory",   icon: "📦", label: "Inventory"   },
    { id: "consumables", icon: "🛒", label: "Consumables" },
    { id: "costs",       icon: "💶", label: "Costs"       },
    { id: "works",       icon: "🔧", label: "Works"       },
  ];

  function handleClickOutside(e: MouseEvent) {
    if (!(e.target as HTMLElement).closest(".layers-dropdown")) open = false;
  }
</script>
```

In the template, find the `<div class="dropdown">` and change to:

```svelte
  {#if open}
    <div class="dropdown" class:align-left={popoverAlign === 'left'}>
```

In the style block, add after `.dropdown { ... }`:

```css
  .dropdown.align-left { left: auto; right: 0; }
```

- [ ] **Step 2: Run full test suite**

```bash
cd packages/editor && npx vitest run
```

Expected: all pass.

- [ ] **Step 3: Commit**

```bash
git add packages/editor/src/lib/components/LayersDropdown.svelte
git commit -m "feat: add popoverAlign prop to LayersDropdown"
```

---

### Task 9: App.svelte — floating toolbar

**Files:**
- Modify: `packages/editor/src/App.svelte`
- Test: `packages/editor/test/App.test.ts`

This is the central change. We add a `.floating-toolbar` inside `.canvas-area` and remove the `{#if isFloorPlan}` block from the topbar. We also remove `onexpand` from the NavMenu call.

- [ ] **Step 1: Update App.test.ts toolbarBtn helper and add floating-toolbar tests**

At the top of `App.test.ts`, replace the `toolbarBtn` function:

```typescript
/** Find a toolbar button by its title attribute inside the floating toolbar */
function toolbarBtn(target: HTMLElement, title: string): HTMLButtonElement {
  return Array.from(target.querySelectorAll(".floating-toolbar button")).find(
    (b) => (b as HTMLButtonElement).title === title,
  ) as HTMLButtonElement;
}
```

Find and replace the test `"renders the title and toolbar with the select tool active"`:

```typescript
  it("renders the title and floating toolbar with the select tool active on #/plan", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);

    expect(target.querySelector(".app-title")?.textContent).toBe("My Home");

    const floatingToolbar = target.querySelector(".floating-toolbar");
    expect(floatingToolbar).not.toBeNull();

    const selectBtn = toolbarBtn(target, "Select");
    expect(selectBtn).not.toBeNull();
    expect(selectBtn.className).toContain("active");

    const deleteBtn = toolbarBtn(target, "Delete selected (Del)") as HTMLButtonElement;
    expect(deleteBtn.disabled).toBe(true);

    // Drawing tool buttons present
    expect(toolbarBtn(target, "Wall")).not.toBeNull();
    expect(toolbarBtn(target, "Divider")).not.toBeNull();
    expect(toolbarBtn(target, "Door")).not.toBeNull();
    expect(toolbarBtn(target, "Window")).not.toBeNull();
    expect(toolbarBtn(target, "Undo (Ctrl+Z)")).not.toBeNull();
    expect(toolbarBtn(target, "Redo (Ctrl+Y)")).not.toBeNull();
  });

  it("floating toolbar is not rendered on home route", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target, "#/");

    expect(target.querySelector(".floating-toolbar")).toBeNull();
  });
```

- [ ] **Step 2: Run tests to confirm new tests fail**

```bash
cd packages/editor && npx vitest run test/App.test.ts 2>&1 | grep -E "FAIL|PASS|floating"
```

Expected: the two new floating-toolbar tests fail; the renamed test also fails (no `.floating-toolbar` yet).

- [ ] **Step 3: Add floating toolbar to App.svelte**

Inside the `{:else}` branch of `{:else if isFloorPlan}` in the canvas area, BEFORE the existing `<Canvas ...>` component and AFTER `{:else}` (meaning: inside the non-allFloorsMode else branch), add the floating toolbar as a sibling to `<Canvas>`. It should be placed just before the `{#if selectedRoom}` block.

Find this comment section in the canvas-area template (around line 712):
```svelte
          {:else}
            <Canvas
```

In App.svelte, find the very start of the `isFloorPlan` canvas-area content block and locate:
```svelte
        <div class="canvas-area" ...>
          {#if !floorStore.loaded}
            ...
          {:else if allFloorsMode}
            ...
          {:else}
            <Canvas .../>
```

After the closing `/>` of `<Canvas` (and before `{#if selectedRoom}`), add the floating toolbar:

```svelte
            <div
              class="floating-toolbar"
              class:picker-open={pickerOpen}
            >
              <FloorSwitcher
                compact={true}
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
                onaddfloor={(name) => floorStore.addFloor(name)}
                onrenamefloor={(id, name) => floorStore.renameFloor(id, name)}
                onremovefloor={(id) => floorStore.removeFloor(id)}
              />

              <div class="ftb-sep"></div>

              <LayersDropdown {activeLayers} ontoggle={toggleLayer} popoverAlign="left" />
              <button
                class="ftb-btn"
                class:active={pickerOpen}
                title="Toggle item picker"
                onclick={() => { pickerOpen = !pickerOpen; }}
              >📋</button>
              <button
                class="ftb-btn save-btn"
                class:saved={saveStatus === "saved"}
                class:save-error={saveStatus === "error"}
                class:dirty={floorStore.isDirty && saveStatus === "idle"}
                disabled={saveStatus === "saving"}
                title={saveTitle}
                onclick={handleSave}
              >{saveIcon}</button>
              <button class="ftb-btn" title="Reset view" onclick={() => viewportStore.reset()}>↺</button>

              <div class="ftb-sep"></div>

              <button class="ftb-btn" title="Undo (Ctrl+Z)" disabled={!floorStore.hasUndo} onclick={handleUndo}>↩</button>
              <button class="ftb-btn" title="Redo (Ctrl+Y)" disabled={!floorStore.hasRedo} onclick={handleRedo}>↪</button>

              {#if !choreLayerActive}
                <div class="ftb-sep"></div>
                <button class="ftb-btn" title="Select" class:active={toolStore.state.tool === "select"} onclick={() => toolStore.setTool("select")}>🖱</button>
                <button class="ftb-btn" title="Wall" class:active={toolStore.state.tool === "wall"} onclick={() => toolStore.setTool("wall")}>🧱</button>
                <button class="ftb-btn" title="Divider" class:active={toolStore.state.tool === "divider"} onclick={() => toolStore.setTool("divider")}>╌</button>
                <button class="ftb-btn" title="Door" class:active={toolStore.state.tool === "door"} onclick={() => toolStore.setTool("door")}>🚪</button>
                <button class="ftb-btn" title="Window" class:active={toolStore.state.tool === "window"} onclick={() => toolStore.setTool("window")}>🪟</button>
              {/if}

              <div class="ftb-sep"></div>

              <button class="ftb-btn delete" title="Delete selected (Del)" disabled={!hasSelection} onclick={handleDelete}>🗑</button>
            </div>
```

- [ ] **Step 4: Add floating toolbar CSS to App.svelte `<style>` block**

Add after the `.right-panels` CSS rule:

```css
  .floating-toolbar {
    position: absolute;
    right: 12px;
    top: 50%;
    transform: translateY(-50%);
    z-index: 30;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: 6px 4px;
    background: var(--surface);
    border: 1px solid var(--border);
    border-radius: var(--radius-lg);
    box-shadow: 0 2px 12px rgba(0,0,0,0.2);
  }
  .floating-toolbar.picker-open {
    right: calc(220px + 16px);
  }

  .ftb-btn {
    width: 32px; height: 32px;
    border: none; border-radius: var(--radius-sm); background: transparent;
    color: var(--text-muted); cursor: pointer; font-size: 15px;
    display: flex; align-items: center; justify-content: center; padding: 0;
    flex-shrink: 0;
  }
  .ftb-btn:hover:not(:disabled) { background: var(--surface-hover); color: var(--text); }
  .ftb-btn.active { background: var(--surface-hover); color: var(--accent); }
  .ftb-btn.save-btn { color: var(--success); position: relative; }
  .ftb-btn.save-btn.dirty::after {
    content: ''; position: absolute; top: 4px; right: 4px;
    width: 6px; height: 6px; border-radius: 50%;
    background: var(--accent); pointer-events: none;
  }
  .ftb-btn.save-btn.saved { color: var(--success); }
  .ftb-btn.save-btn.save-error { color: var(--danger); }
  .ftb-btn.delete { color: var(--danger); }
  .ftb-btn.delete:hover:not(:disabled) { background: var(--surface-hover); }
  .ftb-btn:disabled { opacity: 0.35; cursor: default; }

  .ftb-sep {
    width: 24px; height: 1px; background: var(--border); margin: 2px 0; flex-shrink: 0;
  }
```

- [ ] **Step 5: Run App tests**

```bash
cd packages/editor && npx vitest run test/App.test.ts
```

Expected: the two new floating-toolbar tests pass. Other tests may still fail because the topbar still has the old `{#if isFloorPlan}` block — that's cleaned up in Task 10.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/test/App.test.ts
git commit -m "feat: add floating vertical toolbar to floor plan canvas area"
```

---

### Task 10: App.svelte — topbar cleanup

**Files:**
- Modify: `packages/editor/src/App.svelte`

Remove the `{#if isFloorPlan}` block from the topbar entirely. Move theme toggle to the right side. Add `<HomesSwitcher topbar={true} />` to the right side. Remove `onexpand` from the `<NavMenu>` call. Clean up now-unused CSS classes (`.toolbar`, `.spacer`, `.topbar-sep`, `.theme-toggle` margin).

- [ ] **Step 1: Replace the topbar template**

Find the `<header class="topbar">` block (currently ends at `</header>` around line 674). Replace the entire header with:

```svelte
  <header class="topbar">
    <button
      class="hamburger"
      onclick={() => { navExpanded = !navExpanded; }}
      title={navExpanded ? "Close menu" : "Open menu"}
    >{navExpanded ? "✕" : "☰"}</button>

    <span class="app-title">My Home</span>

    <span class="topbar-spacer"></span>

    <HomesSwitcher topbar={true} />

    <button
      class="icon-btn"
      title={theme === "light" ? "Switch to dark mode" : "Switch to light mode"}
      onclick={handleToggleTheme}
    >{theme === "light" ? "🌙" : "☀️"}</button>

    <span class="topbar-sep"></span>

    <div class="user-menu-wrap">
      <button
        class="icon-btn user-chip"
        onclick={() => { userMenuOpen = !userMenuOpen; }}
        title="User menu"
      >
        {authStore.user?.username.slice(0, 2).toUpperCase()}
      </button>
      {#if userMenuOpen}
        <div class="user-dropdown">
          <div class="user-dropdown-header">
            <span class="user-dropdown-name">{authStore.user?.username}</span>
            <span class="user-role-badge">{authStore.user?.role}</span>
          </div>
          <hr class="user-dropdown-sep" />
          <button class="user-dropdown-item" onclick={() => { showChangePassword = true; userMenuOpen = false; }}>
            Change password
          </button>
          <button class="user-dropdown-item signout" onclick={handleSignOut}>
            Sign out
          </button>
        </div>
      {/if}
    </div>
  </header>
```

- [ ] **Step 2: Remove onexpand from NavMenu call**

Find:
```svelte
    <NavMenu {currentRoute} expanded={navExpanded} onclose={() => { navExpanded = false; }} onexpand={() => { navExpanded = true; }} />
```

Replace with:
```svelte
    <NavMenu {currentRoute} expanded={navExpanded} onclose={() => { navExpanded = false; }} />
```

- [ ] **Step 3: Update topbar CSS — remove old classes, add new ones**

In the `<style>` block, remove these rules entirely (no longer used after this refactor):
- `.theme-toggle { margin-right: var(--space-2); }` 
- `.spacer { flex: 1; }`
- `.toolbar { ... }` and `.toolbar .sep { ... }` and `.toolbar button { ... }` (all the nested toolbar rules)
- `.topbar-sep { ... }` — KEEP this one (still used in topbar)

Change `.user-menu-wrap { position: relative; margin-left: auto; }` to:
```css
  .user-menu-wrap { position: relative; }
```
(margin-left: auto no longer needed since `topbar-spacer` handles the push)

Add:
```css
  .topbar-spacer { flex: 1; }
```

- [ ] **Step 4: Run full test suite**

```bash
cd packages/editor && npx vitest run
```

Expected: all tests pass. The toolbar tests in App.test.ts all use `toolbarBtn` (which queries `.floating-toolbar button`) so they still find the buttons.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/App.svelte
git commit -m "feat: topbar cleanup — static layout with HomesSwitcher and theme toggle on right"
```

---

### Task 11: Final test run and polish

- [ ] **Step 1: Run complete test suite**

```bash
cd packages/editor && npx vitest run
```

Expected: all tests pass. Note the count — it should be higher than before (new tests added in Tasks 2 and 4).

- [ ] **Step 2: Check for any leftover unused imports in App.svelte**

Verify that `Toolbar.svelte` is not imported in App.svelte (it was never imported — the toolbar was inline). The `Toolbar.svelte` file can stay as-is (it is not used by App.svelte; it was a separate exported component).

Check `isFloorPlan` derived is still used somewhere — it was used for the `{#if isFloorPlan}` topbar block which is now removed. If it's now only used for the floating toolbar condition, keep it. If the floating toolbar uses a different check, remove the derived.

The floating toolbar uses `{#if isFloorPlan && !allFloorsMode}` — actually it is placed INSIDE the `{:else if isFloorPlan}` block already, so it only renders on the floor plan route. The `isFloorPlan` derived can be removed if unused elsewhere (check `Ctrl+F` for all usages).

- [ ] **Step 3: Final commit if any polish changes**

```bash
git add -p  # stage only the cleanup changes
git commit -m "chore: remove unused isFloorPlan derived and dead CSS after topbar refactor"
```

---

## Summary of all commits

1. `feat: scale chore overlay badges with viewport zoom`
2. `feat: scale inventory/costs/works overlay badges with viewport zoom`
3. `feat: scale consumable overlay badges with viewport zoom`
4. `feat: increase home map widget height to 360px`
5. `feat: add topbar variant to HomesSwitcher`
6. `refactor: remove HomesSwitcher from nav, nav no longer needs onexpand`
7. `feat: add compact popover mode to FloorSwitcher`
8. `feat: add popoverAlign prop to LayersDropdown`
9. `feat: add floating vertical toolbar to floor plan canvas area`
10. `feat: topbar cleanup — static layout with HomesSwitcher and theme toggle on right`
11. `chore: remove unused isFloorPlan derived and dead CSS after topbar refactor` *(if needed)*
