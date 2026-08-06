# Mobile Responsiveness Phase 5: HTML5 DnD → Pointer Events Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the two remaining native HTML5 drag-and-drop interactions — KB page tree reorder/nesting, and dragging an item/furniture-template from a floor-plan side panel onto the canvas — with Pointer Events, since native HTML5 DnD (`draggable`, `dragstart`/`dragover`/`drop`) has no touch support in any browser.

**Architecture:** Native DnD's automatic "retarget dragover/drop to whatever element is currently under the cursor" behavior turns out to have a direct, low-risk Pointer Events equivalent: as long as no element calls `setPointerCapture`, an uncaptured pointer's `pointermove`/`pointerup` events are dispatched via ordinary hit-testing to whatever element is currently under it — identical to how native `mousemove`/`click` already work, and identical to how native `dragover`/`drop` retargeting works. This means each interaction converts as a **direct one-for-one swap** (`draggable`+`dragstart`→`pointerdown`, `dragover`→`pointermove`, `drop`→`pointerup`, `dragleave`→`pointerleave`) with the underlying calculation logic (drop-position ratio, cycle detection, sibling reordering, world-coordinate placement) unchanged — no `document.elementFromPoint` polling or centralized hit-testing needed. This is spec Phase 5 of `docs/superpowers/specs/2026-08-05-mobile-responsive-audit-design.md`.

## Global Constraints

- No `setPointerCapture` calls anywhere in this phase — capturing the pointer to the source element would break the natural cross-element hit-testing this whole design relies on (a captured pointer's move/up events go to the capturing element regardless of where the pointer physically is, which is the opposite of what's needed here).
- `onpointerdown`-initiated "drag" state (`dragging` in `KBPage.svelte`, `draggingItemId`/`draggingLayerId`/the new furniture-template state in `App.svelte`) must always end cleanly even for a plain tap with no movement (no `dragover`/`pointermove` ever fires, so the only signal is the eventual `pointerup`) — every conversion in this plan resets its drag state unconditionally in the `pointerup` path, matching how native `dragend` unconditionally fires and cleans up regardless of whether a valid drop occurred.
- **Deliberately out of scope:** `touch-action: none` is *not* added to the draggable rows/items in this phase. Unlike the floor-plan canvas (Phase 4), these are items inside a scrollable list (`.entry-list`, `.picker-float`'s item list, `.furniture-float`'s item grid) — `touch-action: none` on every row would block the user from scrolling that list by touching directly on an item, which is most of its surface area. This is a known, accepted limitation carried over from before this phase (native HTML5 DnD had the exact same scroll/drag ambiguity on touch, in browsers that even attempt to support it) — flag it in the final report rather than solving it here; a proper fix (long-press-to-start-drag, or a movement-direction heuristic) is a larger UX design question than "make this work on touch," which is this phase's scope.
- A floating "ghost" visual (per the design spec) is added for the item/furniture-picker → canvas interaction (Task 2), where it's the only feedback the user gets about what's being placed and where. It is **not** added for KB tree reordering (Task 1) — that interaction already has clear feedback via the existing before/after/inside drop-indicator lines on target rows, so a ghost would be redundant there. This asymmetry is a deliberate scope decision, not an oversight.

---

### Task 1: Convert KB page tree reorder/nesting to Pointer Events

**Files:**
- Modify: `packages/editor/src/lib/components/ui/KBTree.svelte`
- Modify: `packages/editor/src/lib/components/KBPage.svelte`
- Modify: `packages/editor/test/KBTree.test.ts`
- Modify: `packages/editor/test/KBPage.test.ts`

**Interfaces:**
- Produces: no prop signature changes on `KBTree` (`onstartdrag: (id: string) => void`, `onenddrag: () => void`, `ondrop: (draggedId, targetParentId, orderedIds) => void` are unchanged — only the DOM events that trigger them change). `KBPage.svelte`'s `.trash-link` keeps the same `handleStartDrag`/`handleEndDrag`/`handleDropOnTrash` functions, retriggered by pointer events instead of drag events.

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/KBTree.test.ts`, in the `describe("KBTree — drag and drop", ...)` block, every `dragover`/`drop` dispatch converts to `pointermove`/`pointerup`, and the setup no longer needs `dragstart` at all (there's no dedicated dragstart test — `dragging` is passed directly as a prop in every test's `setup()` call, matching how the interaction is actually exercised). Replace all five tests' dispatch lines:

```ts
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
```
→
```ts
    targetRow.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientY: 10 }));
    targetRow.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, clientY: 10 }));
```

(apply the same `dragover`→`pointermove` / `drop`→`pointerup` swap, keeping each test's own `clientY` value, across all five occurrences — the two `clientY: 10` "middle band" tests, the two `clientY: 1` "top band" tests, and the "does not call ondrop when dropping onto own descendant" test's `clientY: 10` pair).

In `packages/editor/test/KBPage.test.ts`, in the two tests under `describe("KBPage — moving an existing page under another", ...)` and the one test under `describe("KBPage — delete with cascade confirmation modal", ...)` matching `"dragging a page onto the Trash link..."`, replace:

```ts
    sourceRow.dispatchEvent(new Event("dragstart", { bubbles: true }));
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new MouseEvent("dragover", { bubbles: true, clientY: 10 }));
    targetRow.dispatchEvent(new MouseEvent("drop", { bubbles: true, clientY: 10 }));
```
→
```ts
    sourceRow.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    vi.spyOn(targetRow, "getBoundingClientRect").mockReturnValue({ top: 0, height: 20 } as DOMRect);
    targetRow.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1, clientY: 10 }));
    targetRow.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1, clientY: 10 }));
```

(same swap for the `clientY: 1` variant in the "does not duplicate the link when only reordering" test, and for the Trash-link test — which drops with no explicit `clientY`, and drops onto `trashLink` rather than a `.tree-row`):

```ts
    row.dispatchEvent(new Event("dragstart", { bubbles: true }));
    trashLink.dispatchEvent(new MouseEvent("dragover", { bubbles: true }));
    trashLink.dispatchEvent(new MouseEvent("drop", { bubbles: true }));
```
→
```ts
    row.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    trashLink.dispatchEvent(new PointerEvent("pointermove", { bubbles: true, pointerId: 1 }));
    trashLink.dispatchEvent(new PointerEvent("pointerup", { bubbles: true, pointerId: 1 }));
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- KBTree KBPage --run`
Expected: FAIL — neither `KBTree.svelte` nor `KBPage.svelte`'s `.trash-link` listen for pointer events yet.

- [ ] **Step 3: Convert `KBTree.svelte`**

Rename `handleDragOver`/`handleDrop` and change their event parameter type:

```ts
  function handlePointerOver(e: PointerEvent, entry: KBEntry): void {
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id)) return;
    const rect = (e.currentTarget as HTMLElement).getBoundingClientRect();
    const ratio = (e.clientY - rect.top) / rect.height;
    const position = ratio < 0.25 ? "before" : ratio > 0.75 ? "after" : "inside";
    dropIndicator = { id: entry.id, position };
  }

  function handlePointerDrop(e: PointerEvent, entry: KBEntry): void {
    const indicator = dropIndicator;
    dropIndicator = null;
    onenddrag();
    if (!dragging || dragging === entry.id || wouldCreateCycle(dragging, entry.id) || !indicator) return;
    if (indicator.position === "inside") {
      ondrop(dragging, entry.id, null);
      return;
    }
    const siblings = entries
      .filter((s) => s.parentId === entry.parentId && s.id !== dragging)
      .sort((a, b) => a.order - b.order);
    const targetIndex = siblings.findIndex((s) => s.id === entry.id);
    const insertAt = indicator.position === "before" ? targetIndex : targetIndex + 1;
    const orderedIds = siblings.map((s) => s.id);
    orderedIds.splice(insertAt, 0, dragging);
    ondrop(dragging, entry.parentId, orderedIds);
  }
```

Note `onenddrag()` is now called unconditionally near the top of `handlePointerDrop` — it used to be called separately, from `ondragend`, which native DnD guarantees fires exactly once per drag regardless of outcome. Pointer Events have no equivalent second event, so this function has to do both jobs (this is also why a plain tap with no movement — `pointerdown` immediately followed by `pointerup` on the same row, so `dragging === entry.id` — still cleanly resets `dragging` via this same code path, even though the reorder logic below it is skipped).

Replace the row's event bindings:

```svelte
        draggable="true"
        ondragstart={(e) => { e.dataTransfer?.setData("text/plain", ""); onstartdrag(entry.id); }}
        ondragend={() => { dropIndicator = null; onenddrag(); }}
        ondragover={(e) => handleDragOver(e, entry)}
        ondragleave={() => { if (dropIndicator?.id === entry.id) dropIndicator = null; }}
        ondrop={(e) => handleDrop(e, entry)}
```
becomes:
```svelte
        onpointerdown={() => onstartdrag(entry.id)}
        onpointermove={(e) => handlePointerOver(e, entry)}
        onpointerleave={() => { if (dropIndicator?.id === entry.id) dropIndicator = null; }}
        onpointerup={(e) => handlePointerDrop(e, entry)}
```

- [ ] **Step 4: Convert `KBPage.svelte`'s `.trash-link`**

Replace:

```svelte
      ondragover={(e) => { if (dragging) { e.preventDefault(); trashDragOver = true; } }}
      ondragleave={() => { trashDragOver = false; }}
      ondrop={(e) => { e.preventDefault(); handleDropOnTrash(); }}
```
with:
```svelte
      onpointermove={() => { if (dragging) trashDragOver = true; }}
      onpointerleave={() => { trashDragOver = false; }}
      onpointerup={() => { if (dragging) handleDropOnTrash(); }}
```

- [ ] **Step 5: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- KBTree KBPage --run`
Expected: PASS

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS (full suite).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ui/KBTree.svelte packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBTree.test.ts packages/editor/test/KBPage.test.ts
git commit -m "feat(kb): convert page tree reorder/nesting to pointer events"
```

---

### Task 2: Convert item/furniture-picker → canvas placement to Pointer Events

**Files:**
- Modify: `packages/editor/src/lib/components/ItemPickerPanel.svelte`
- Modify: `packages/editor/src/lib/components/FurnitureLibraryPanel.svelte`
- Modify: `packages/editor/src/App.svelte`
- Modify: `packages/editor/test/ItemPickerPanel.test.ts`
- Modify: `packages/editor/test/FurnitureLibraryPanel.test.ts`

**Interfaces:**
- Produces: `ItemPickerPanel`'s `ondragstart`/`ondragend` props are replaced by a single `onitempointerdown: (layerId: string, item: PickerItem, event: PointerEvent) => void`. `FurnitureLibraryPanel` gains `onitempointerdown?: (templateId: string, event: PointerEvent) => void`. `App.svelte`'s existing `draggingItemId`/`draggingLayerId` state (already used for rendering, e.g. `ItemPickerPanel`'s `draggingId` prop) is now *set* from these new callbacks instead of from `ondragstart`; a new `pointerDragFurnitureTemplateId` state tracks an in-progress furniture placement the same way. `App.svelte`'s `handleDragOver`/`handleDrop` (`DragEvent`-based) are deleted entirely and replaced by `handleCanvasPointerUp`/`placeDraggedAt` — no more `.canvas-area` `ondragover` binding at all (it existed only to call `e.preventDefault()`, a native-DnD-specific requirement that doesn't apply to pointer events).

- [ ] **Step 1: Update the failing tests**

In `packages/editor/test/ItemPickerPanel.test.ts`, replace every occurrence of `ondragstart: vi.fn(), ondragend: vi.fn()` with `onitempointerdown: vi.fn()`:

```bash
sed -i 's/ondragstart: vi\.fn(), ondragend: vi\.fn()/onitempointerdown: vi.fn()/g' packages/editor/test/ItemPickerPanel.test.ts
```

Then replace the dedicated `"ondragstart called with layerId and itemId on drag"` test (it needs `ondragstart` as a separately-named local variable, so the sed above skipped it — find it manually) with:

```ts
  it("onitempointerdown called with layerId and item on pointerdown", async () => {
    const onitempointerdown = vi.fn();
    const app = mount(ItemPickerPanel, {
      target,
      props: { layers: [CHORES_LAYER], draggingId: null, onitempointerdown },
    });
    flushSync();
    const row = target.querySelector<HTMLElement>(".item-row")!;
    row.dispatchEvent(new PointerEvent("pointerdown", { bubbles: true, pointerId: 1 }));
    expect(onitempointerdown).toHaveBeenCalledWith("chores", expect.objectContaining({ id: expect.any(String) }), expect.anything());
    unmount(app);
  });
```

In `packages/editor/test/FurnitureLibraryPanel.test.ts`, the three tests using `"[draggable='true']"` as a selector for "every furniture item" need to select on the class instead, since `draggable` is being removed entirely:

```bash
sed -i "s/\"\[draggable='true'\]\"/\".furniture-item\"/g" packages/editor/test/FurnitureLibraryPanel.test.ts
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `npm test -w @myhome/editor -- ItemPickerPanel FurnitureLibraryPanel --run`
Expected: FAIL — neither component emits `onitempointerdown` yet; `ItemPickerPanel`/`FurnitureLibraryPanel`'s `Props` interfaces still require the old `ondragstart`/`ondragend`, so this step's mount calls (already updated to the new prop) also won't type-check cleanly until Step 3, but the *test failures* to look for here are runtime (`onitempointerdown` never called, `.furniture-item` selector already valid since that class already exists — that part passes) — the `.dragging` class test and most render tests were unaffected by the prop rename and should already pass; only the new pointerdown test and (transiently) every test relying on the now-mismatched `Props` shape are expected to show issues until Step 3 lands.

- [ ] **Step 3: Convert `ItemPickerPanel.svelte`**

Replace the `Props` interface's drag-related fields (currently `onstartdrag?: (e: PointerEvent) => void;` for the panel's own drag-handle — unrelated, keep that one — plus `ondragstart`/`ondragend`):

```ts
    ondragstart: (layerId: string, itemId: string, event: DragEvent) => void;
    ondragend: () => void;
```
becomes:
```ts
    onitempointerdown: (layerId: string, item: PickerItem, event: PointerEvent) => void;
```

Update the destructured props line accordingly (`ondragstart, ondragend` → `onitempointerdown`).

Delete the `startDrag` function entirely (its `dataTransfer`/custom-drag-image logic no longer applies):

```ts
  function startDrag(layerId: string, item: PickerItem, event: DragEvent): void {
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
```

Replace both `.item-row` blocks' bindings (unplaced and placed groups — identical change in both):

```svelte
                draggable={true}
                ondragstart={(e) => startDrag(layer.id, item, e)}
                ondragend={() => ondragend()}
```
becomes:
```svelte
                onpointerdown={(e) => onitempointerdown(layer.id, item, e)}
```

- [ ] **Step 4: Convert `FurnitureLibraryPanel.svelte`**

Add to the props type:
```ts
  let { onstartdrag, ondismiss, onitempointerdown }: { onstartdrag?: (e: PointerEvent) => void; ondismiss?: () => void; onitempointerdown?: (templateId: string, e: PointerEvent) => void } = $props();
```

Delete `onDragStart`:
```ts
  function onDragStart(e: DragEvent, templateId: string) {
    e.dataTransfer?.setData("furnitureTemplateId", templateId);
  }
```

Replace the `.furniture-item` binding:
```svelte
                draggable="true"
                data-template-id={template.id}
                ondragstart={(e) => onDragStart(e, template.id)}
```
becomes:
```svelte
                data-template-id={template.id}
                onpointerdown={(e) => onitempointerdown?.(template.id, e)}
```

- [ ] **Step 5: Convert `App.svelte`'s canvas-drop wiring**

Add new state near the existing `draggingItemId`/`draggingLayerId` declarations (line ~139-140):

```ts
  let pointerDragFurnitureTemplateId = $state<string | null>(null);
  let dragGhost = $state<{ x: number; y: number; emoji: string; label: string } | null>(null);
```

Replace `handleDragOver`/`handleDrop` (the full `DragEvent`-based block) with:

```ts
  function handleItemPointerDown(layerId: string, item: { id: string; name: string; emoji: string }, e: PointerEvent): void {
    draggingLayerId = layerId;
    draggingItemId = item.id;
    dragGhost = { x: e.clientX, y: e.clientY, emoji: item.emoji, label: item.name };
  }

  function handleFurniturePointerDown(templateId: string, e: PointerEvent): void {
    pointerDragFurnitureTemplateId = templateId;
    dragGhost = { x: e.clientX, y: e.clientY, emoji: "🪑", label: $_(`floorPlan.furnitureLibrary.items.${templateId}`) };
  }

  function cancelItemDrag(): void {
    draggingItemId = null;
    draggingLayerId = null;
    pointerDragFurnitureTemplateId = null;
    dragGhost = null;
  }

  function placeDraggedAt(clientX: number, clientY: number): void {
    const canvasEl = document.querySelector(".canvas-area") as HTMLElement | null;
    if (!canvasEl) return;
    const rect = canvasEl.getBoundingClientRect();
    if (clientX < rect.left || clientX > rect.right || clientY < rect.top || clientY > rect.bottom) return;

    if (pointerDragFurnitureTemplateId) {
      const template = getTemplate(pointerDragFurnitureTemplateId);
      if (template) {
        const worldX = (clientX - rect.left - viewportStore.viewport.panX) / viewportStore.viewport.zoom;
        const worldY = (clientY - rect.top - viewportStore.viewport.panY) / viewportStore.viewport.zoom;
        floorStore.addFurniture(pointerDragFurnitureTemplateId, worldX, worldY, template.defaultWidth, template.defaultHeight);
      }
      return;
    }

    const layerId = draggingLayerId;
    const itemId = draggingItemId;
    if (!layerId || !itemId) return;

    if (allFloorsMode) {
      if (layerId !== "chores") return;
      const chore = choreStore.chores.find(c => c.id === itemId);
      choreStore.createAssignment({ choreId: itemId, roomId: null, position: null, nextDueDate: chore?.nextDueDate ?? "" });
      return;
    }

    const screenX = clientX - rect.left, screenY = clientY - rect.top;
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

    if (layerId === "consumables") {
      const room = floorStore.floor.rooms.find(r => r.polygon && pointInPolygon({ x: worldX, y: worldY }, r.polygon));
      consumableStore.setPlacement(itemId, {
        floorId: floorStore.currentFloorId,
        roomId: room?.id ?? null,
        position: { x: worldX, y: worldY },
      });
      return;
    }

    if (layerId === "costs") {
      settingsStore.placeCostCategory(itemId, {
        floorId: floorStore.currentFloorId,
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

  function handleCanvasPointerUp(e: PointerEvent): void {
    placeDraggedAt(e.clientX, e.clientY);
  }
```

Update the `svelte:window` block (added onto the same one Phase 4 already modified) to track the ghost position and clean up on release:

```svelte
<svelte:window
  onkeydown={handleKeydown}
  onkeyup={handleKeyup}
  onblur={() => { spacePressed = false; }}
  onpointermove={(e) => { if (dragGhost) dragGhost = { ...dragGhost, x: e.clientX, y: e.clientY }; }}
  onpointerup={() => { handleDragEnd(); endFurnitureDrag(); cancelItemDrag(); }}
/>
```

Update `.canvas-area`'s binding:
```svelte
        <div class="canvas-area" bind:clientWidth={canvasWidth} bind:clientHeight={canvasHeight} ondragover={handleDragOver} ondrop={handleDrop}>
```
becomes:
```svelte
        <div class="canvas-area" bind:clientWidth={canvasWidth} bind:clientHeight={canvasHeight} onpointerup={handleCanvasPointerUp}>
```

Update the `ItemPickerPanel` and `FurnitureLibraryPanel` call sites:
```svelte
                onstartdrag={ipDrag.startDrag}
                ondismiss={() => { pickerOpen = false; }}
                ondragstart={(layerId, itemId, _e) => { draggingLayerId = layerId; draggingItemId = itemId; pickerHighlightId = null; }}
                ondragend={() => { draggingLayerId = null; draggingItemId = null; }}
```
becomes:
```svelte
                onstartdrag={ipDrag.startDrag}
                ondismiss={() => { pickerOpen = false; }}
                onitempointerdown={(layerId, item, e) => { pickerHighlightId = null; handleItemPointerDown(layerId, item, e); }}
```

```svelte
              <FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} ondismiss={() => { furnitureLibraryOpen = false; }} />
```
becomes:
```svelte
              <FurnitureLibraryPanel onstartdrag={fpDrag.startDrag} ondismiss={() => { furnitureLibraryOpen = false; }} onitempointerdown={handleFurniturePointerDown} />
```

Add the ghost's markup, near the end of the template (any top-level position works, since it's `position: fixed`):

```svelte
{#if dragGhost}
  <div class="drag-ghost" style="left:{dragGhost.x + 12}px; top:{dragGhost.y + 12}px;">
    {dragGhost.emoji} {dragGhost.label}
  </div>
{/if}
```

Add its CSS:

```css
  .drag-ghost {
    position: fixed; pointer-events: none; z-index: 999;
    background: var(--surface); border: 1px solid var(--accent);
    border-radius: var(--radius-sm); padding: 4px 8px; font-size: 12px;
    box-shadow: var(--shadow-md); white-space: nowrap;
  }
```

- [ ] **Step 6: Run the tests to verify they pass**

Run: `npm test -w @myhome/editor -- ItemPickerPanel FurnitureLibraryPanel --run`
Expected: PASS

Run: `npm test -w @myhome/editor -- --run`
Expected: PASS (full suite — confirmed during planning that no `App.test.ts` test exercises the canvas-drop path at all, so none need updating).

Run: `npm run build -w @myhome/editor`
Expected: succeeds.

- [ ] **Step 7: Commit**

```bash
git add packages/editor/src/lib/components/ItemPickerPanel.svelte packages/editor/src/lib/components/FurnitureLibraryPanel.svelte packages/editor/src/App.svelte packages/editor/test/ItemPickerPanel.test.ts packages/editor/test/FurnitureLibraryPanel.test.ts
git commit -m "feat(floor-plan): convert item/furniture picker placement to pointer events"
```

---

### Task 3: Real-browser verification

**Files:**
- None modified — verification-only, using the `webapp-testing` skill (Playwright), same isolated-instance recipe as Phases 1-4.

**Interfaces:**
- Consumes: Tasks 1-2.

- [ ] **Step 1: Start an isolated instance**

Log in, use (or create) a "Demo home" (pre-seeded with KB pages and a floor plan).

- [ ] **Step 2: Verify KB tree reorder via touch**

1. Navigate to the KB module. Dispatch real `PointerEvent`s (`pointerType: "touch"`) via `page.evaluate`: `pointerdown` on one page row, `pointermove` over another row's middle band, `pointerup` there — assert the dragged page's `parentId` changed (nested under the target) via a subsequent API check or by asserting the tree's rendered nesting changed.
2. Repeat with `pointermove` landing in a row's top/bottom band instead — assert a reorder (not a nest) occurred.
3. Verify dragging a page onto the Trash link opens the delete-confirmation modal.
4. Take screenshots.

- [ ] **Step 3: Verify item-picker and furniture-library placement via touch**

1. Open the floor-plan editor, enable a layer (e.g. Chores) via the Layers dropdown, open the Item Picker.
2. Dispatch `pointerdown` on an item row, `pointermove` toward the canvas (assert the ghost element appears and follows), `pointerup` over the canvas at a position inside a room — assert the item's placement (e.g. the chore assignment's `roomId`/`position`) was set.
3. Repeat with the Furniture Library: `pointerdown` on a furniture item, `pointermove` onto the canvas, `pointerup` — assert a new `g.furniture-object` appears at the expected world position.
4. Take screenshots.

- [ ] **Step 4: Fix any real issues found**

Same pattern as every prior phase's final task — diagnose with the systematic-debugging skill, commit fixes individually. Pay particular attention to whether the "no `setPointerCapture`, rely on natural hit-testing" assumption this whole phase is built on actually holds for real touch input in a real browser (it's the one piece of this plan that couldn't be verified in jsdom) — if a real touch drag doesn't retarget across elements the way the vitest tests assumed, that's the first thing to investigate.

- [ ] **Step 5: Clean up the isolated instance**

Revert `vite.config.ts`, kill only the PIDs started in Step 1, remove the temporary `DATA_DIR`.
