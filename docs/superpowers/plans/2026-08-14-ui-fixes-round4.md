# UI Fixes Round 4 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix seven reported UI/UX issues across the KB, Chores, and Floor Plan modules, and fix a real data-loss bug where deleting a wall can silently drop an unrelated nested room and orphan its assignments.

**Architecture:** Each fix is scoped to the component(s) that own the reported behavior — no new abstractions or shared components are introduced. The floor-plan bug fix adds one pure dry-run function to `houseStore.svelte.ts` (mirrors the existing `detectRooms`/`matchRooms` recompute path without mutating state) and wires a confirmation `Modal` into `App.svelte`'s existing delete flow.

**Tech Stack:** Svelte 5 (runes), TypeScript, Vitest, svelte-i18n (`en.json`/`fr.json`).

## Global Constraints

- No new npm dependencies (this repo has no icon library — all icons are Unicode/emoji glyphs; keep using that pattern).
- Every new user-facing string needs both an `en.json` and `fr.json` entry under the correct existing nested key.
- Follow existing CSS conventions: `var(--space-N)`, `var(--radius-*)`, `var(--text*)`, `var(--accent*)` design tokens — no hardcoded colors/sizes where a token exists already in the touched file.
- Run the affected package's test file after every task (`npx vitest run <file>` from `/projects/myhome/packages/editor` or `/projects/myhome/packages/geometry` as appropriate) before moving to the next task.
- Scope note on Task 3 (room-disappear confirmation): it only guards the wall-deletion path (`removeWall`, the only place a room can currently disappear per investigation — furniture/opening deletion never touch `floor.rooms`). Wall-endpoint dragging (`moveSharedPoint`) is out of scope — that's a continuous drag interaction, not a discrete delete action, and popping a confirm dialog mid-drag isn't viable UX.
- Scope note on Task 3's "worth warning about" heuristic: only rooms with a customized label (not the auto-generated `"Room N"` default) or a set `haAreaId` trigger the confirmation. This is deliberate — deleting the last wall of a freshly-drawn, never-named room is normal editing, not data loss, and must not interrupt that flow (see the existing `App.test.ts` "selects a wall and deletes it with the Delete key" test, which draws a plain never-renamed rectangle and expects immediate deletion).

---

## Task 1: Floor plan — always center room/zone labels (remove nested-zone special placement)

**Files:**
- Modify: `packages/geometry/src/geometry.ts:246-279` (delete the nested-zone label-placement helpers, simplify `computeLabelPosition`)
- Modify: `packages/editor/src/lib/components/RoomShape.svelte:33-36` (update the one call site)
- Modify: `packages/geometry/test/geometry.test.ts:202-237` (rewrite the `computeLabelPosition` describe block)
- Modify: `packages/editor/test/RoomShape.test.ts:39-56` (rewrite the "moves the label off a contained child" test)

**Context:** `computeLabelPosition(room, allRooms)` currently grid-samples for the "most open point" of a zone polygon when it substantially contains other rooms' polygons (added in commits `ab71397`/`d080e8c`), instead of always using the plain centroid. The user wants this reverted — the title should always sit in the middle of the zone. `roomContainsOtherRooms`/`estimateContainmentRatio` (also in `geometry.ts:246-260`) must **stay** — `RoomShape.svelte`'s `isContainerZone` still uses it to keep zone clicks passing through to the nested room, which is unrelated to label placement and not part of this request. The helpers `findOpenPoint`, `distanceToPolygon`, `distanceToSegment`, and `LABEL_GRID_STEPS` (`geometry.ts:202-244`) are used **only** by the code being removed — verified via repo-wide grep, no other call sites — so delete them too rather than leaving dead code.

**Interfaces:**
- Produces: `computeLabelPosition(room: Room): Point` — signature drops the now-unused `allRooms` parameter.

- [ ] **Step 1: Write the failing geometry tests**

Replace the `describe("computeLabelPosition", ...)` block in `packages/geometry/test/geometry.test.ts` (currently lines 202-237) with:

```typescript
describe("computeLabelPosition", () => {
  const outerSquare: Point[] = [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }];

  it("returns the polygon centroid", () => {
    const room = makeRoom("outer", outerSquare);
    const pos = computeLabelPosition(room);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("returns the centroid even when another room's polygon fully contains it", () => {
    const room = makeRoom("zone", outerSquare);
    // Previously this would have pushed the label off (5,5); it must not anymore.
    const pos = computeLabelPosition(room);
    expect(pos.x).toBeCloseTo(5, 5);
    expect(pos.y).toBeCloseTo(5, 5);
  });

  it("returns {x:0,y:0} when the room has no polygon", () => {
    const room = makeRoom("unresolved", null);
    expect(computeLabelPosition(room)).toEqual({ x: 0, y: 0 });
  });
});
```

- [ ] **Step 2: Run the geometry test suite to confirm it fails to compile/fails**

Run: `cd /projects/myhome/packages/geometry && npx vitest run test/geometry.test.ts`
Expected: FAIL — `computeLabelPosition` still requires a second argument / old assertions no longer match, or a TS error about the call signature.

- [ ] **Step 3: Simplify `computeLabelPosition` and delete the now-dead helpers**

In `packages/geometry/src/geometry.ts`, delete lines 202-244 (`distanceToSegment`, `distanceToPolygon`, `LABEL_GRID_STEPS`, `findOpenPoint`) entirely, and replace the `computeLabelPosition` function (originally lines 262-279, now shifted up since the deleted block precedes it) with:

```typescript
/** Where to draw a room's label — always the polygon centroid. */
export function computeLabelPosition(room: Room): Point {
  if (!room.polygon) return { x: 0, y: 0 };
  return polygonCentroid(room.polygon);
}
```

Leave `estimateContainmentRatio`, `CONTAINMENT_GRID_STEPS`, `CONTAINMENT_THRESHOLD`, and `roomContainsOtherRooms` (lines 180-200, 246-260) untouched — they're still used for zone click-passthrough.

- [ ] **Step 4: Update the one call site in `RoomShape.svelte`**

In `packages/editor/src/lib/components/RoomShape.svelte`, replace:

```svelte
  const labelWorldPos = $derived.by(() => {
    if (!room.polygon) return { x: 0, y: 0 };
    return computeLabelPosition(room, allRooms);
  });
```

with:

```svelte
  const labelWorldPos = $derived.by(() => computeLabelPosition(room));
```

- [ ] **Step 5: Run the geometry test suite again**

Run: `cd /projects/myhome/packages/geometry && npx vitest run test/geometry.test.ts`
Expected: PASS

- [ ] **Step 6: Update and run the `RoomShape` component test**

Replace the second test in `packages/editor/test/RoomShape.test.ts` (currently lines 39-56, `"moves the label off a fully-contained child room"`) with:

```typescript
  it("places the label at the plain centroid even when another room is fully contained inside it", () => {
    const zone: Room = {
      id: "zone", label: "Zone", haAreaId: null, areaM2: 100,
      polygon: [{ x: 0, y: 0 }, { x: 10, y: 0 }, { x: 10, y: 10 }, { x: 0, y: 10 }],
    };
    const child: Room = {
      id: "child", label: "Child", haAreaId: null, areaM2: 16,
      polygon: [{ x: 3, y: 3 }, { x: 7, y: 3 }, { x: 7, y: 7 }, { x: 3, y: 7 }],
    };
    const comp = mount(RoomShape, { target, props: { room: zone, allRooms: [zone, child], viewport: identityViewport() } });
    flushSync();
    const text = target.querySelector("text.room-label") as SVGTextElement;
    expect(Number(text.getAttribute("x"))).toBeCloseTo(5, 5);
    expect(Number(text.getAttribute("y"))).toBeCloseTo(5, 5);
    unmount(comp);
  });
```

Run: `cd /projects/myhome/packages/editor && npx vitest run test/RoomShape.test.ts`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add packages/geometry/src/geometry.ts packages/geometry/test/geometry.test.ts \
  packages/editor/src/lib/components/RoomShape.svelte packages/editor/test/RoomShape.test.ts
git commit -m "fix(floorplan): always center zone/room labels, remove nested-zone label placement"
```

---

## Task 2: Floor plan — dry-run helper to detect rooms a wall deletion would drop

**Files:**
- Modify: `packages/editor/src/lib/houseStore.svelte.ts:82-91` (add `roomsAtRiskFromWallRemoval`), `:362-396` (expose it)
- Test: `packages/editor/test/houseStore.test.ts` (new `describe` block)

**Context:** Investigation traced the reported bug to a specific, reproducible mechanism: rooms are never explicitly "deleted" — they're derived every time walls change, via `detectRooms(floor.walls)` → `matchRooms(detected, floor.rooms)` (`houseStore.svelte.ts:82-87`). When a wall is shared between an outer zone's boundary and a T-junction where an inner room's own divider walls attach, deleting that one wall makes `detectRooms` produce **zero** faces for that whole area in a single pass — so `matchRooms`'s per-polygon smallest-area tie-break (which normally protects a nested room, see the "courtyard case" test in `roomMatching.test.ts:113-147`) never even runs, and the inner room silently gets swept into `unresolved` and dropped from `floor.rooms` (`houseStore.svelte.ts:86`), even though the user only touched the outer wall. Chore/inventory/consumable/cost records referencing that room's `roomId` aren't deleted, but every UI surface that resolves `roomId → floor.rooms.find(...)` now fails silently, which is what the user perceives as the room and its assignments vanishing.

This task adds a **pure, non-mutating** dry-run of that same detect+match logic, so the caller can know in advance which rooms a given wall deletion would drop — Task 3 wires it into a confirmation prompt.

**Interfaces:**
- Produces: `roomsAtRiskFromWallRemoval(id: string): Room[]` on the object returned by `createHouseStore()` — returns the subset of `floor.rooms` that would end up without a polygon if wall `id` were removed right now. Returns `[]` if `id` isn't a wall on the current floor.

- [ ] **Step 1: Write the failing test**

Add this new `describe` block to `packages/editor/test/houseStore.test.ts` (after the existing `describe("houseStore — floor management", ...)` block, so after line 144):

```typescript
describe("houseStore — roomsAtRiskFromWallRemoval", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  /** Builds a 10x10 outer zone with a 2x2 inner room T-junctioned into two
   *  of the zone's own boundary walls (south and west) — the exact shape
   *  that triggers the reported bug: the inner room's divider walls never
   *  get touched, but it still depends on the shared wall. */
  async function buildZoneWithTJunctionedInnerRoom() {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "z-south", start: { x: 0, y: 0 }, end: { x: 10, y: 0 }, type: "wall" });
    store.addWall({ id: "z-east", start: { x: 10, y: 0 }, end: { x: 10, y: 10 }, type: "wall" });
    store.addWall({ id: "z-north", start: { x: 10, y: 10 }, end: { x: 0, y: 10 }, type: "wall" });
    store.addWall({ id: "z-west", start: { x: 0, y: 10 }, end: { x: 0, y: 0 }, type: "wall" });
    store.addWall({ id: "i-east", start: { x: 2, y: 0 }, end: { x: 2, y: 2 }, type: "wall" });
    store.addWall({ id: "i-north", start: { x: 2, y: 2 }, end: { x: 0, y: 2 }, type: "wall" });
    expect(store.floor.rooms).toHaveLength(2);
    return store;
  }

  it("flags the inner room as at-risk when deleting the shared wall it's T-junctioned into", async () => {
    const store = await buildZoneWithTJunctionedInnerRoom();
    const innerRoom = store.floor.rooms.find((r) => r.areaM2 === 4);
    expect(innerRoom).toBeDefined();

    const atRisk = store.roomsAtRiskFromWallRemoval("z-south");
    expect(atRisk.some((r) => r.id === innerRoom!.id)).toBe(true);
  });

  it("does not flag the inner room when deleting a wall it doesn't depend on", async () => {
    const store = await buildZoneWithTJunctionedInnerRoom();
    const innerRoom = store.floor.rooms.find((r) => r.areaM2 === 4);
    expect(innerRoom).toBeDefined();

    const atRisk = store.roomsAtRiskFromWallRemoval("z-east");
    expect(atRisk.some((r) => r.id === innerRoom!.id)).toBe(false);
  });

  it("is a pure dry-run — does not mutate walls or rooms", async () => {
    const store = await buildZoneWithTJunctionedInnerRoom();
    const wallsBefore = store.floor.walls.length;
    const roomsBefore = store.floor.rooms.length;
    store.roomsAtRiskFromWallRemoval("z-south");
    expect(store.floor.walls.length).toBe(wallsBefore);
    expect(store.floor.rooms.length).toBe(roomsBefore);
  });

  it("returns an empty array for a wall id that doesn't exist", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.roomsAtRiskFromWallRemoval("nope")).toEqual([]);
  });
});
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/houseStore.test.ts -t "roomsAtRiskFromWallRemoval"`
Expected: FAIL — `store.roomsAtRiskFromWallRemoval is not a function`

- [ ] **Step 3: Implement the dry-run function**

In `packages/editor/src/lib/houseStore.svelte.ts`, insert immediately after `commitWalls` (after line 91, before the `// Floor management` comment on line 93):

```typescript
  function roomsAtRiskFromWallRemoval(id: string): Room[] {
    const floor = currentFloor();
    if (!floor.walls.some((w) => w.id === id)) return [];
    const wallsAfter = floor.walls.filter((w) => w.id !== id);
    const detected = detectRooms(wallsAfter);
    const { rooms } = matchRooms(detected, floor.rooms);
    const survivingIds = new Set(rooms.filter((r) => r.polygon !== null).map((r) => r.id));
    return floor.rooms.filter((r) => !survivingIds.has(r.id));
  }
```

Then add `roomsAtRiskFromWallRemoval,` to the returned object, right after `removeWall,` (line 381).

- [ ] **Step 4: Run the test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/houseStore.test.ts -t "roomsAtRiskFromWallRemoval"`
Expected: PASS (all 4 new tests)

- [ ] **Step 5: Run the full houseStore suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/houseStore.test.ts test/houseStore.furniture.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.test.ts
git commit -m "feat(floorplan): add roomsAtRiskFromWallRemoval dry-run to houseStore"
```

---

## Task 3: Floor plan — confirm before a wall deletion drops a named room

**Files:**
- Modify: `packages/editor/src/App.svelte:4` (type import), `:443` (new state), `:554-563` (`handleDelete`), template (new confirmation `Modal`)
- Modify: `packages/editor/src/lib/locales/en.json:222-234`, `packages/editor/src/lib/locales/fr.json:222-234` (new `floorPlan.deleteWallConfirm` keys)
- Test: `packages/editor/test/App.test.ts` (new tests)

**Context:** `handleDelete()` (`App.svelte:554-563`) is the single choke point for wall deletion — it's called by the keyboard `Delete`/`Backspace` handler (`App.svelte:759-760`), the floating-toolbar delete button (`App.svelte:1407`), and the delete popover row (`App.svelte:1439`) — so gating it here covers every trigger. Per the Global Constraints scope note, only rooms with a customized label or an assigned HA area trigger the prompt, so the existing "selects a wall and deletes it with the Delete key" test (which uses a never-renamed `SAMPLE_RECT_CORNERS` rectangle) keeps passing unchanged.

**Interfaces:**
- Consumes: `floorStore.roomsAtRiskFromWallRemoval(id: string): Room[]` from Task 2.
- Produces: nothing new consumed by later tasks — this is a leaf UI wiring task.

- [ ] **Step 1: Write the failing App-level test**

Add this test to `packages/editor/test/App.test.ts`, right after the existing `"selects a wall and deletes it with the Delete key"` test (after line 286):

```typescript
  it("confirms before deleting a wall that would drop a named room, and can be cancelled", async () => {
    target = document.createElement("div");
    document.body.appendChild(target);

    app = await mountAndLoad(target);
    drawWalls(target, SAMPLE_RECT_CORNERS);

    // Name the room so it counts as "customized" and triggers the guard.
    (target.querySelector("polygon.room") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    const labelInput = target.querySelector(".room-panel input[type='text']") as HTMLInputElement;
    labelInput.value = "Kitchen";
    labelInput.dispatchEvent(new Event("input", { bubbles: true }));
    labelInput.dispatchEvent(new FocusEvent("blur", { bubbles: true }));
    flushSync();

    const wall = target.querySelector("polygon.wall")!;
    wall.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    const wallsBefore = target.querySelectorAll("polygon.wall").length;
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
    flushSync();

    // Deletion is held pending — wall still present, confirmation shown.
    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore);
    expect(target.textContent).toContain("Kitchen");

    // Cancel: nothing is deleted.
    const cancelBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Cancel",
    ) as HTMLButtonElement;
    cancelBtn.click();
    flushSync();
    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore);

    // Re-select and delete again, this time confirm.
    target.querySelector("polygon.wall")!.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    window.dispatchEvent(new KeyboardEvent("keydown", { key: "Delete" }));
    flushSync();
    const confirmBtn = Array.from(target.querySelectorAll("button")).find(
      (b) => b.textContent?.trim() === "Delete anyway",
    ) as HTMLButtonElement;
    confirmBtn.click();
    flushSync();
    expect(target.querySelectorAll("polygon.wall").length).toBe(wallsBefore - 1);
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/App.test.ts -t "confirms before deleting a wall"`
Expected: FAIL — wall is deleted immediately, no "Kitchen" text / no "Delete anyway" button found.

- [ ] **Step 3: Add the i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside the `"floorPlan"` object, add a new `"deleteWallConfirm"` key right after `"tools"` (after the closing `},` on line 234):

```json
    "deleteWallConfirm": {
      "title": "Delete this wall?",
      "message": "This will also remove the following room(s), and any chores, inventory, consumables, or costs assigned to them will no longer show a room:",
      "note": "You can undo this afterwards with Ctrl+Z.",
      "confirm": "Delete anyway",
      "unnamedRoom": "Unnamed room"
    },
```

In `packages/editor/src/lib/locales/fr.json`, in the same position:

```json
    "deleteWallConfirm": {
      "title": "Supprimer ce mur ?",
      "message": "Cela supprimera également la ou les pièces suivantes, et les tâches, éléments d'inventaire, consommables ou coûts qui leur sont associés n'afficheront plus de pièce :",
      "note": "Vous pourrez annuler cette action ensuite avec Ctrl+Z.",
      "confirm": "Supprimer quand même",
      "unnamedRoom": "Pièce sans nom"
    },
```

- [ ] **Step 4: Wire the state, filter, and handlers in `App.svelte`**

Change the type import on line 4 from:

```svelte
  import type { Point, WallType } from "@myhome/geometry";
```

to:

```svelte
  import type { Point, WallType, Room } from "@myhome/geometry";
```

Add new state right after `let selectedFurnitureId = $state<string | null>(null);` (line 443):

```svelte
  let pendingWallDeleteId = $state<string | null>(null);
  let roomsAtRisk = $state<Room[]>([]);

  function isCustomizedRoom(room: Room): boolean {
    const hasCustomLabel = !!room.label && !/^Room \d+$/.test(room.label);
    return hasCustomLabel || room.haAreaId !== null;
  }
```

Replace `handleDelete` (lines 554-563):

```svelte
  function handleDelete(): void {
    if (selectedFurnitureId) {
      floorStore.removeFurniture(selectedFurnitureId);
      selectedFurnitureId = null;
      return;
    }
    const { selectedId, selectedOpeningId } = toolStore.state;
    if (selectedId) {
      const atRisk = floorStore.roomsAtRiskFromWallRemoval(selectedId).filter(isCustomizedRoom);
      if (atRisk.length > 0) {
        pendingWallDeleteId = selectedId;
        roomsAtRisk = atRisk;
        return;
      }
      floorStore.removeWall(selectedId);
      toolStore.select(null);
    }
    else if (selectedOpeningId) { floorStore.removeOpening(selectedOpeningId); toolStore.selectOpening(null); }
  }

  function confirmWallDelete(): void {
    if (pendingWallDeleteId) {
      floorStore.removeWall(pendingWallDeleteId);
      toolStore.select(null);
    }
    pendingWallDeleteId = null;
    roomsAtRisk = [];
  }

  function cancelWallDelete(): void {
    pendingWallDeleteId = null;
    roomsAtRisk = [];
  }
```

- [ ] **Step 5: Add the confirmation modal to the template**

In `packages/editor/src/App.svelte`, add this block right after the `{#if showChangePassword}...{/if}` block (after line 1594):

```svelte
  {#if pendingWallDeleteId}
    <Modal open={true} title={$_('floorPlan.deleteWallConfirm.title')} onclose={cancelWallDelete}>
      <div style="display:flex;flex-direction:column;gap:8px">
        <p style="margin:0;font-size:13px;color:var(--text-muted)">{$_('floorPlan.deleteWallConfirm.message')}</p>
        <ul style="margin:0;padding-left:20px;font-size:13px">
          {#each roomsAtRisk as room (room.id)}
            <li>{room.label || $_('floorPlan.deleteWallConfirm.unnamedRoom')}</li>
          {/each}
        </ul>
        <p style="margin:0;font-size:11px;color:var(--text-faint)">{$_('floorPlan.deleteWallConfirm.note')}</p>
      </div>
      {#snippet footer()}
        <Button variant="secondary" onclick={cancelWallDelete}>{$_('common.cancel')}</Button>
        <Button variant="danger" onclick={confirmWallDelete}>{$_('floorPlan.deleteWallConfirm.confirm')}</Button>
      {/snippet}
    </Modal>
  {/if}
```

- [ ] **Step 6: Run the new test to verify it passes**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/App.test.ts -t "confirms before deleting a wall"`
Expected: PASS

- [ ] **Step 7: Run the full App test suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/App.test.ts test/App.furniture.test.ts test/App.toolbarOrder.test.ts test/App.badgeDetails.test.ts test/App.routing.test.ts test/App.viewportAutoFit.test.ts`
Expected: PASS — in particular, `"selects a wall and deletes it with the Delete key"` and `"view mode hides editing tools..."` must still pass unchanged.

- [ ] **Step 8: Commit**

```bash
git add packages/editor/src/App.svelte packages/editor/src/lib/locales/en.json \
  packages/editor/src/lib/locales/fr.json packages/editor/test/App.test.ts
git commit -m "fix(floorplan): confirm before a wall deletion drops a named room"
```

---

## Task 4: KB — nest the autosave status icon inside the save button

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:562-574` (markup), `:755-757` (CSS)
- Test: `packages/editor/test/KBPage.test.ts` (new test in the `"KBPage — autosave"` describe block)

**Context:** The autosave indicator (`↻`/`✓`/`⚠`) is currently a `<span class="save-status">` sitting as a **sibling** immediately before the black "Done editing" `Button`, and it renders nothing at all while `saveStatus === "idle"` (the resting state). The user wants the indicator visually part of the save button rather than a separate element next to it. The fix nests the same span inside the `Button`'s children and adds an `idle` fallback of `✓` (the button already always showed a `✓` in that slot before, so this doesn't add a new glyph, it just makes the merged element behave consistently). The button's own `title` must stay the static `$_('works.modal.doneEditing')` ("Done editing") — the existing test `"the Done button flushes any pending save..."` selects it via `[title="Done editing"]` immediately after typing, before the debounce settles, so the title cannot become dynamic. The inner span keeps its own dynamic `title` (`"Saving…"`/`"Saved"`/`"Save failed"`), which is what the existing `"shows a spinning save-status icon"` / `"shows a Saved indicator"` tests assert on via `.save-status`.

**Interfaces:** None — purely internal markup/CSS to `KBPage.svelte`.

- [ ] **Step 1: Write the failing test**

Add this test to the `describe("KBPage — autosave", ...)` block in `packages/editor/test/KBPage.test.ts`, after the `"shows an Edit icon button..."` test (after line 514):

```typescript
  it("nests the autosave status indicator inside the Done-editing save button", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    enterEditMode(target);
    const saveBtn = target.querySelector('[title="Done editing"]');
    expect(saveBtn?.querySelector(".save-status")).not.toBeNull();
    unmount(comp); target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "nests the autosave status indicator"`
Expected: FAIL — `.save-status` is a sibling of the button, not a descendant.

- [ ] **Step 3: Merge the markup**

In `packages/editor/src/lib/components/KBPage.svelte`, replace lines 562-574:

```svelte
          {#if contentTab === "content" && editing}
            <span
              class="save-status"
              class:save-status-saving={saveStatus === "saving" || saveStatus === "pending"}
              class:save-status-error={saveStatus === "error"}
              title={saveStatus === "saving" || saveStatus === "pending" ? $_('kb.page.saving') : saveStatus === "saved" ? $_('kb.page.saved') : saveStatus === "error" ? $_('kb.page.saveFailed') : undefined}
            >
              {#if saveStatus === "saving" || saveStatus === "pending"}↻
              {:else if saveStatus === "saved"}✓
              {:else if saveStatus === "error"}⚠
              {/if}
            </span>
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>✓</Button>
          {:else if contentTab === "content" && !editing}
```

with:

```svelte
          {#if contentTab === "content" && editing}
            <Button variant="primary" onclick={handleDoneEditing} title={$_('works.modal.doneEditing')}>
              <span
                class="save-status"
                class:save-status-saving={saveStatus === "saving" || saveStatus === "pending"}
                class:save-status-error={saveStatus === "error"}
                title={saveStatus === "saving" || saveStatus === "pending" ? $_('kb.page.saving') : saveStatus === "saved" ? $_('kb.page.saved') : saveStatus === "error" ? $_('kb.page.saveFailed') : undefined}
              >
                {#if saveStatus === "saving" || saveStatus === "pending"}↻
                {:else if saveStatus === "error"}⚠
                {:else}✓
                {/if}
              </span>
            </Button>
          {:else if contentTab === "content" && !editing}
```

- [ ] **Step 4: Adjust the CSS so the icon inherits the button's contrast color**

In `packages/editor/src/lib/components/KBPage.svelte`, replace (currently around line 755):

```css
  .save-status { font-size: 13px; color: var(--text-muted); white-space: nowrap; display: inline-flex; align-items: center; }
```

with:

```css
  .save-status { font-size: 13px; white-space: nowrap; display: inline-flex; align-items: center; }
```

(leave `.save-status-saving` and `.save-status-error` untouched — the error state still needs its explicit red override).

- [ ] **Step 5: Run the new test and the full autosave describe block**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "autosave"`
Expected: PASS (all tests in that describe block, including the new one)

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "fix(kb): nest autosave status icon inside the save button"
```

---

## Task 5: KB — match expand/collapse-all button size to the "+" button

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:487-490` (markup), `:680-684` (CSS)
- Test: `packages/editor/test/KBPage.test.ts` (new test)

**Context:** Neither the expand/collapse-all `Button` nor the "+" (`New Page`) `Button` passes `iconOnly`, so both fall back to the default `8px 18px` pill padding (`Button.svelte:32`) instead of the fixed `36×36px` square (`Button.svelte:37-42`, class `.ui-button-icon`). On top of that, the expand/collapse glyph is wrapped in a `<span class="toggle-all-icon">` with its own explicit `font-size: 13px` (`KBPage.svelte:681`), while the "+" glyph inherits the button's `font-size: 12px` directly — two different sizes on top of the padding mismatch. Fixing both buttons to `iconOnly` (which sets `font-size: 15px` on the button itself) and dropping the span's own `font-size` override makes both icons render at the same size inside identically-sized square buttons.

**Interfaces:** None.

- [ ] **Step 1: Write the failing test**

Add this test to `packages/editor/test/KBPage.test.ts`, in the `describe("KBPage — empty state", ...)` block, after `"toolbar has a single New Page button..."` (after line 161):

```typescript
  it("gives the expand/collapse-all and new-page buttons matching icon-button sizing", async () => {
    const { target, comp } = await setup([]);
    const toolbarButtons = target.querySelectorAll(".sidebar-toolbar button");
    expect(toolbarButtons.length).toBe(2);
    for (const btn of toolbarButtons) {
      expect(btn.className).toContain("ui-button-icon");
    }
    unmount(comp); target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "matching icon-button sizing"`
Expected: FAIL — neither button has the `ui-button-icon` class.

- [ ] **Step 3: Add `iconOnly` to both buttons and drop the span's own font-size**

In `packages/editor/src/lib/components/KBPage.svelte`, replace lines 487-490:

```svelte
      <Button onclick={toggleAllTree} title={allParentsExpanded ? $_('kb.tree.collapseAll') : $_('kb.tree.expandAll')}>
        <span class="toggle-all-icon" class:open={allParentsExpanded}>▸</span>
      </Button>
      <Button onclick={handleNewPage} title={$_('kb.page.newPage')}>＋</Button>
```

with:

```svelte
      <Button iconOnly onclick={toggleAllTree} title={allParentsExpanded ? $_('kb.tree.collapseAll') : $_('kb.tree.expandAll')}>
        <span class="toggle-all-icon" class:open={allParentsExpanded}>▸</span>
      </Button>
      <Button iconOnly onclick={handleNewPage} title={$_('kb.page.newPage')}>＋</Button>
```

Then replace the `.toggle-all-icon` rule (currently around line 680):

```css
  .toggle-all-icon {
    display: inline-block; font-size: 13px; line-height: 1;
    transition: transform 0.15s ease;
  }
```

with:

```css
  .toggle-all-icon {
    display: inline-block; line-height: 1;
    transition: transform 0.15s ease;
  }
```

- [ ] **Step 4: Run the new test**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "matching icon-button sizing"`
Expected: PASS

- [ ] **Step 5: Run the full KBPage suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "fix(kb): match expand/collapse-all button size to the new-page button"
```

---

## Task 6: KB — recognizable edit icon matching the save button's style

**Files:**
- Modify: `packages/editor/src/lib/components/KBPage.svelte:576`
- Test: `packages/editor/test/KBPage.test.ts` (new test)

**Context:** The edit button currently uses `✏` (U+270F, no variation selector), which most platforms render as a thin monochrome dingbat rather than a recognizable pencil — and it uses `variant="ghost"` (transparent background) while the save button uses `variant="primary"` (solid black pill), the stylistic mismatch the user flagged. Switching to `✏️` (U+270F + U+FE0F, the emoji variation selector) forces the colorful, universally-recognized pencil emoji rendering, and switching to `variant="primary"` gives it the same solid-pill chrome as the save button. No icon library exists in this repo (verified via `package.json`) — this stays within the existing Unicode-glyph pattern used everywhere else in the file.

**Interfaces:** None.

- [ ] **Step 1: Write the failing test**

Add this test to the `describe("KBPage — autosave", ...)` block in `packages/editor/test/KBPage.test.ts`, after the `"shows an Edit icon button..."` test:

```typescript
  it("styles the Edit button to match the primary Save button instead of a ghost button", async () => {
    const { target, comp } = await setup([makeEntry({ content: "hello" })], { selectedItemId: "e1" });
    const editBtn = target.querySelector('[title="Edit"]') as HTMLElement;
    expect(editBtn.className).toContain("ui-button-primary");
    expect(editBtn.textContent).toContain("✏️");
    unmount(comp); target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "matches the primary Save button"`
Expected: FAIL — button has `ui-button-ghost`, glyph is `✏` without the variation selector.

- [ ] **Step 3: Update the button**

In `packages/editor/src/lib/components/KBPage.svelte`, replace line 576:

```svelte
            <Button variant="ghost" onclick={() => { editing = true; }} title={$_('common.edit')}>✏</Button>
```

with:

```svelte
            <Button variant="primary" onclick={() => { editing = true; }} title={$_('common.edit')}>✏️</Button>
```

- [ ] **Step 4: Run the new test**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts -t "matches the primary Save button"`
Expected: PASS

- [ ] **Step 5: Run the full KBPage suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/KBPage.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/KBPage.svelte packages/editor/test/KBPage.test.ts
git commit -m "fix(kb): use a recognizable pencil emoji for Edit, styled like Save"
```

---

## Task 7: Chores — show the Save button on every tab of the edit modal

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte:305-309`
- Test: `packages/editor/test/ChoreEditModal.test.ts` (new test)

**Context:** The modal's footer is a shared `{#snippet footer()}` passed once to `<Modal>` (so it does render on every tab), but the Save `Button` inside that footer is wrapped in `{#if activeTab === "info"}` (lines 305-309), so it's entirely absent from the DOM on the Assignments/Media/History tabs. "Place on Map" (line 302) stays gated to the info tab — that's unrelated to this request and the user didn't ask for it to change.

**Interfaces:** None.

- [ ] **Step 1: Write the failing test**

Add this test to the `describe("ChoreEditModal — tabs", ...)` block in `packages/editor/test/ChoreEditModal.test.ts`, after the `"disables Save when the recurrence picker is in an invalid state"` test (after line 167):

```typescript
  it("keeps the Save button visible when switching to non-info tabs", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore();
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: NO_ROOMS, onclose: vi.fn() },
    });
    flushSync();
    for (const tabText of ["Assignments", "Media", "History"]) {
      const tab = Array.from(target.querySelectorAll(".tab")).find(
        (t) => t.textContent?.includes(tabText),
      ) as HTMLButtonElement;
      tab.click();
      flushSync();
      const saveBtn = Array.from(target.querySelectorAll("button")).find(
        (b) => b.textContent?.trim() === "Save",
      );
      expect(saveBtn, `Save button missing on ${tabText} tab`).toBeDefined();
    }
    unmount(app);
    target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "non-info tabs"`
Expected: FAIL — Save button is `undefined` on the Assignments tab.

- [ ] **Step 3: Remove the tab gate on the Save button**

In `packages/editor/src/lib/components/ChoreEditModal.svelte`, replace lines 305-309:

```svelte
      {#if activeTab === "info"}
        <Button variant="primary" disabled={saving || !draftScheduleValid} onclick={handleSave}>
          {saving ? $_('settings.security.saving') : $_('common.save')}
        </Button>
      {/if}
```

with:

```svelte
      <Button variant="primary" disabled={saving || !draftScheduleValid} onclick={handleSave}>
        {saving ? $_('settings.security.saving') : $_('common.save')}
      </Button>
```

- [ ] **Step 4: Run the new test**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "non-info tabs"`
Expected: PASS

- [ ] **Step 5: Run the full ChoreEditModal suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/test/ChoreEditModal.test.ts
git commit -m "fix(chores): keep the Save button visible on every edit-modal tab"
```

---

## Task 8: Chores — keep the assignment row's action buttons on one line

**Files:**
- Modify: `packages/editor/src/lib/components/ChoreEditModal.svelte:245-247` (markup), `:360-364` (CSS)
- Test: `packages/editor/test/ChoreEditModal.test.ts` (new test)

**Context:** Each assignment row is a `flex-wrap: wrap` container (`.assignment-row`, `ChoreEditModal.svelte:354`) whose children are, in DOM order: `.assign-where` (flex:1), the label `<input>` (flex:1), `.assign-due` (nowrap), then three separate `.icon-btn` buttons (✓ mark-done, ⏭ delay, ✕ delete). Nothing groups the three buttons together or marks them `flex-shrink: 0`, so once the row's content overflows its width, the wrap can split the trailing button(s) — in particular the last one, delete (✕) — onto their own line separately from mark-done/delay. Wrapping all three in a dedicated `.assignment-actions` flex container with `flex-shrink: 0` makes them wrap as one unit, always staying together.

**Interfaces:** None. The existing `.assignment-row .icon-btn` selector (used by the existing test at `ChoreEditModal.test.ts:192`) still matches through the new wrapper `div`, since it's a descendant selector — no existing test needs updating.

- [ ] **Step 1: Write the failing test**

Add this test to the `describe("ChoreEditModal — Assignments tab", ...)` block in `packages/editor/test/ChoreEditModal.test.ts`, after the `"lists existing assignments..."` test (after line 204):

```typescript
  it("groups the assignment row's action buttons together so they wrap as a unit", async () => {
    const target = document.createElement("div");
    document.body.appendChild(target);
    const store = makeStore({
      assignments: [
        { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 1 }, nextDueDate: "2027-01-01T00:00:00Z", label: "Balcony plants" },
      ],
    });
    const app = mount(ChoreEditModal, {
      target,
      props: { chore: makeChore(), store, rooms: [SQUARE_ROOM], onclose: vi.fn() },
    });
    flushSync();
    (Array.from(target.querySelectorAll(".tab")).find((t) => t.textContent?.includes("Assignments")) as HTMLButtonElement).click();
    flushSync();

    const row = target.querySelector(".assignment-row")!;
    const actions = row.querySelector(".assignment-actions");
    expect(actions).not.toBeNull();
    expect(actions?.querySelectorAll(".icon-btn").length).toBe(3);

    unmount(app);
    target.remove();
  });
```

- [ ] **Step 2: Run the test to verify it fails**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "wrap as a unit"`
Expected: FAIL — `.assignment-actions` doesn't exist.

- [ ] **Step 3: Wrap the action buttons and add the CSS**

In `packages/editor/src/lib/components/ChoreEditModal.svelte`, replace lines 245-247:

```svelte
              <button class="icon-btn" title={$_('chores.row.markDone')} onclick={() => { completing = { id: a.id, title: `${chore.emoji} ${chore.name}` }; }}>✓</button>
              <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
              <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
```

with:

```svelte
              <div class="assignment-actions">
                <button class="icon-btn" title={$_('chores.row.markDone')} onclick={() => { completing = { id: a.id, title: `${chore.emoji} ${chore.name}` }; }}>✓</button>
                <button class="icon-btn" title={$_('chores.page.delayByWeek')} onclick={() => store.delayAssignment(a.id, 7)}>⏭</button>
                <button class="icon-btn danger" onclick={() => store.deleteAssignment(a.id)}>✕</button>
              </div>
```

Then add a new CSS rule right after `.assign-due` (currently around line 357):

```css
  .assign-due { color: var(--text-faint); font-size: 11px; white-space: nowrap; }
  .assignment-actions { display: flex; gap: 4px; flex-shrink: 0; }
```

- [ ] **Step 4: Run the new test**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts -t "wrap as a unit"`
Expected: PASS

- [ ] **Step 5: Run the full ChoreEditModal suite to confirm no regression**

Run: `cd /projects/myhome/packages/editor && npx vitest run test/ChoreEditModal.test.ts`
Expected: PASS — in particular `"lists existing assignments with their label and room, and completes/delays/deletes them"` (line 171), which relies on `.assignment-row .icon-btn` order.

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/ChoreEditModal.svelte packages/editor/test/ChoreEditModal.test.ts
git commit -m "fix(chores): group assignment row action buttons so they wrap together"
```

---

## Final verification

- [ ] Run the full editor and geometry suites once more from the repo root:

```bash
cd /projects/myhome/packages/geometry && npx vitest run
cd /projects/myhome/packages/editor && npx vitest run
```

Expected: PASS, no regressions.
