# Double / French door Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Add a `"double"` `DoorKind` (French door: two independent hinges, one per jamb, symmetric leaves swinging the same direction) to the canvas renderer, the opening panel UI, and both static SVG exporters — and while touching the SVG exporters, fix their pre-existing bug where every `doorKind` renders as a plain single hinged leaf+arc regardless of the actual kind.

**Architecture:** `DoorKind` gains `"double"`; `DoorSwing` gains `"in"`/`"out"` (used only by `"double"`, since both jambs are used symmetrically and there's no left/right axis). No new `Opening` fields, no persistence change. The canvas (`OpeningShape.svelte`) extends its existing `hingedOrSwingingData` derived block — which already produces a `{ variants: [...] }` shape reused unchanged by the template's `{#each}` loop — with a `"double"` case that yields two hinge variants (`wp1`, `wp2`) each swinging toward the same face and each arcing from its own hinge to the *opening's midpoint* (not the far jamb), so the two leaves visually meet in the middle when closed. `OpeningPanel.svelte` adds a `"double"` option and reuses the existing swing-direction select (writing `swing` directly as `"in"`/`"out"` instead of composing a side). Both static SVG exporters (`svg_render.py`, `svgRender.ts`) are rewritten to branch on `doorKind` the same way the canvas does, fixing the existing bug where they ignore it entirely.

**Tech Stack:** Svelte 5 runes + TypeScript (editor, geometry), FastAPI/Pydantic (backend), Vitest (frontend tests), pytest (backend tests).

## Global Constraints

- `doorKind: "double"` and `swing: "in" | "out"` are additive optional-field value changes — no data migration, no new `Opening` fields, existing saved floor plans deserialize unchanged.
- All new UI strings go through `svelte-i18n` (`$_(...)`), added to both `packages/editor/src/lib/locales/en.json` and `fr.json`, following the existing `doorKind*` key naming.
- Both static SVG exporters (`packages/backend/src/myhome/svg_render.py`, live behind `/api/homes/{home_id}/house/floors/{floor_id}/svg`; `packages/geometry/src/svgRender.ts`, currently unconsumed in production) must end up producing the same five per-`doorKind` visual treatments as the canvas (`OpeningShape.svelte`): `hinged` = single leaf+arc, `swinging` = two arcs sharing one hinge, `sliding` = thick offset bar/no arc, `garage` = perpendicular hatch ticks/no arc, `double` = two independent hinge leaf+arc pairs.
- Existing class names are preserved: canvas emits `door-leaf`/`door-arc`/`door-sliding`/`door-garage`; both SVG exporters emit `door-leaf`/`door-swing`/`door-sliding`/`door-garage` (the exporters' arc class is `door-swing`, not `door-arc` — a pre-existing naming difference from the canvas, left as-is since this plan doesn't touch canvas class names).

---

### Task 1: Data model — `"double"` DoorKind + `"in"`/`"out"` DoorSwing

**Files:**
- Modify: `packages/geometry/src/types.ts`
- Modify: `packages/backend/src/myhome/models.py`
- Test: `packages/geometry/test/types.test.ts`
- Test: `packages/backend/tests/test_persistence.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `DoorKind` includes `"double"`; `DoorSwing` includes `"in" | "out"`. `houseStore.svelte.ts`'s `updateOpening` needs no change — its `Pick<Opening, ... | "doorKind" | "swing" | ...>` whitelist already covers both fields; only the underlying type union widens.

- [x] **Step 1: Write the failing tests**

Add to `packages/geometry/test/types.test.ts`, inside `describe("Opening HA fields", ...)` (after the existing `"allows an opening with doorKind and windowSide set"` test):

```ts
  it("allows an opening with doorKind double and swing in/out", () => {
    const doorIn: Opening = { id: "o5", wallId: "w1", type: "door", offset: 0, width: 1.6, doorKind: "double", swing: "in" };
    const doorOut: Opening = { id: "o6", wallId: "w1", type: "door", offset: 0, width: 1.6, doorKind: "double", swing: "out" };
    expect(doorIn.doorKind).toBe("double");
    expect(doorIn.swing).toBe("in");
    expect(doorOut.swing).toBe("out");
  });
```

Add to `packages/backend/tests/test_persistence.py`, directly after the existing `test_round_trip_preserves_opening_door_kind` test (which already covers `doorKind="sliding"`):

```python
def test_round_trip_preserves_double_door_kind_and_swing(tmp_path, monkeypatch):
    _setup(tmp_path, monkeypatch)
    doc = make_doc()
    doc.floors[0].walls = [
        Wall(id="w1", type="wall", start={"x": 0, "y": 0}, end={"x": 4, "y": 0}, thickness=0.1)
    ]
    doc.floors[0].openings = [
        Opening(id="o1", wallId="w1", type="door", offset=1, width=1.6, doorKind="double", swing="out"),
    ]
    save_house(HOME_ID, doc)
    loaded = load_house(HOME_ID)
    assert loaded.floors[0].openings[0].doorKind == "double"
    assert loaded.floors[0].openings[0].swing == "out"
```

(Uses the file's existing `_setup(tmp_path, monkeypatch)` fixture, `HOME_ID` constant, and `make_doc()` helper — same pattern as `test_round_trip_preserves_opening_door_kind` right above it. No new imports needed; `Wall`, `Opening`, `save_house`, `load_house` are already imported at the top of the file.)

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/geometry && npx tsc --noEmit`
Expected: FAIL — `Type '"double"' is not assignable to type 'DoorKind'` and `Type '"in"' is not assignable to type 'DoorSwing'`.

Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v -k double_door`
Expected: FAIL — Pydantic validation error: `swing` Literal currently only allows `"left-in"|"right-in"|"left-out"|"right-out"`, so `swing="out"` is rejected; `doorKind` Literal doesn't allow `"double"` either.

- [x] **Step 3: Widen the types**

In `packages/geometry/src/types.ts`, replace:

```ts
export type DoorSwing = "left-in" | "right-in" | "left-out" | "right-out";

export type DoorKind = "hinged" | "swinging" | "sliding" | "garage";
```

with:

```ts
/**
 * Which corner of the opening the door hinges on, and which side of the
 * wall it swings into. "left"/"right" refer to the corner closer to the
 * wall's `start` vs `end` point; "in"/"out" refer to the two sides of the
 * wall, split by the wall's direction vector (start -> end). The plain
 * "in"/"out" values are only used by doorKind "double", which hinges at
 * both jambs and so has no left/right axis.
 */
export type DoorSwing = "left-in" | "right-in" | "left-out" | "right-out" | "in" | "out";

export type DoorKind = "hinged" | "swinging" | "sliding" | "garage" | "double";
```

In `packages/backend/src/myhome/models.py`, replace the `Opening` model's `swing` and `doorKind` lines:

```python
    swing: Literal["left-in", "right-in", "left-out", "right-out", "in", "out"] | None = None
    doorKind: Literal["hinged", "swinging", "sliding", "garage", "double"] | None = None
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run test/types.test.ts`
Run: `cd packages/backend && python -m pytest tests/test_persistence.py -v`
Expected: PASS

- [x] **Step 5: Commit**

```bash
git add packages/geometry/src/types.ts packages/geometry/test/types.test.ts packages/backend/src/myhome/models.py packages/backend/tests/test_persistence.py
git commit -m "feat(geometry): add double DoorKind and in/out DoorSwing values"
```

---

### Task 2: Canvas rendering — `OpeningShape.svelte` double door

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte:120-148` (`doorKind`, `hingedOrSwingingData`)
- Test: `packages/editor/test/OpeningShape.test.ts`

**Interfaces:**
- Consumes: `Opening.doorKind === "double"`, `Opening.swing` (`"in" | "out"`) from Task 1; existing `chooseSweepFlag` import.
- Produces: no prop changes — rendering-only. `hingedOrSwingingData` keeps its existing `{ variants: [{ hinge, other, openEnd, radius, sweep }, ...] }` shape, so the template's `{:else if opening.type === "door" && hingedOrSwingingData}` branch (lines 225-252) needs **no changes at all** — it already renders however many variants the derived block returns.

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningShape.test.ts`, inside `describe("OpeningShape — door kind rendering", ...)` (after the existing `"colors sliding and garage doors..."` test):

```ts
  it("renders two independent leaf/arc pairs for double doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(2);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(2);
  });

  it("hinges the double door's two leaves at the opening's own start and end points", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    // wall (0,0)->(4,0), DEFAULT_VIEWPORT panX:400 panY:300 zoom:100 -> world x=1 -> screen x=500, world x=2.6 -> screen x=660.
    const x1s = [Number(leaves[0].getAttribute("x1")), Number(leaves[1].getAttribute("x1"))].sort((a, b) => a - b);
    expect(x1s[0]).toBeCloseTo(500, 5);
    expect(x1s[1]).toBeCloseTo(660, 5);
  });

  it("swings both double-door leaves outward when swing is out", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6, swing: "out" }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    // "out" perpendicular for a wall along +x is world -y (screen y decreases from the 300 baseline).
    for (const leaf of leaves) {
      expect(Number((leaf as SVGLineElement).getAttribute("y2"))).toBeLessThan(300);
    }
  });

  it("defaults double door swing to in when unset", () => {
    setup({ opening: makeDoor({ doorKind: "double", offset: 1, width: 1.6 }) });
    const leaves = target.querySelectorAll("line.door-leaf");
    for (const leaf of leaves) {
      expect(Number((leaf as SVGLineElement).getAttribute("y2"))).toBeGreaterThan(300);
    }
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts -t "double"`
Expected: FAIL — `doorKind: "double"` doesn't match any branch in `hingedOrSwingingData`'s guard, so `hingedOrSwingingData` is `null` and nothing renders (`querySelectorAll("line.door-leaf")` returns 0, not 2).

- [x] **Step 3: Implement**

In `packages/editor/src/lib/components/OpeningShape.svelte`, replace the `hingedOrSwingingData` block (lines 122-148) with:

```ts
  const hingedOrSwingingData = $derived.by(() => {
    if (opening.type !== "door" || (doorKind !== "hinged" && doorKind !== "swinging" && doorKind !== "double")) return null;
    const width = clampedTo - clampedFrom;
    if (width < 1e-9) return null;
    const perpIn = { x: -dir.y, y: dir.x };
    const perpOut = { x: dir.y, y: -dir.x };

    if (doorKind === "double") {
      const halfWidth = width / 2;
      const perp = opening.swing === "out" ? perpOut : perpIn;
      const midWorld = { x: (wp1.x + wp2.x) / 2, y: (wp1.y + wp2.y) / 2 };
      const mid = worldToScreen(midWorld, viewport);
      const radius = halfWidth * viewport.zoom;
      const leaf = (hingeWorld: { x: number; y: number }) => {
        const openEndWorld = { x: hingeWorld.x + perp.x * halfWidth, y: hingeWorld.y + perp.y * halfWidth };
        const hinge = worldToScreen(hingeWorld, viewport);
        const openEnd = worldToScreen(openEndWorld, viewport);
        const sweep = chooseSweepFlag(mid, openEnd, radius, hinge);
        return { hinge, other: mid, openEnd, radius, sweep };
      };
      return { variants: [leaf(wp1), leaf(wp2)] };
    }

    const swing = opening.swing ?? "left-in";
    const isLeft = swing === "left-in" || swing === "left-out";
    const hingeWorld = isLeft ? wp1 : wp2;
    const otherWorld = isLeft ? wp2 : wp1;
    const other = worldToScreen(otherWorld, viewport);
    const radius = width * viewport.zoom;

    const variant = (perp: { x: number; y: number }) => {
      const openEndWorld = { x: hingeWorld.x + perp.x * width, y: hingeWorld.y + perp.y * width };
      const hinge = worldToScreen(hingeWorld, viewport);
      const openEnd = worldToScreen(openEndWorld, viewport);
      const sweep = chooseSweepFlag(other, openEnd, radius, hinge);
      return { hinge, other, openEnd, radius, sweep };
    };

    if (doorKind === "swinging") {
      return { variants: [variant(perpIn), variant(perpOut)] };
    }
    const isIn = swing === "left-in" || swing === "right-in";
    return { variants: [variant(isIn ? perpIn : perpOut)] };
  });
```

(No other changes — the template's `{:else if opening.type === "door" && hingedOrSwingingData}` branch already iterates `hingedOrSwingingData.variants` generically.)

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts`
Expected: PASS (all existing hinged/swinging/sliding/garage cases still pass since their code paths are untouched — only a new `if (doorKind === "double")` branch was inserted before the existing logic, and the guard condition gained `|| doorKind === "double"`).

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts test/App.test.ts`
Expected: PASS — no regressions (neither test sets `doorKind: "double"`).

- [x] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/OpeningShape.svelte packages/editor/test/OpeningShape.test.ts
git commit -m "feat(editor): render double/French doors on the floor plan canvas"
```

---

### Task 3: Panel UI — `OpeningPanel.svelte` double door controls

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningPanel.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/OpeningPanel.test.ts`

**Interfaces:**
- Consumes: `Opening.doorKind === "double"`, `Opening.swing` (`"in" | "out"`) from Task 1.
- Produces: no change to `onupdate`'s patch type (already includes `doorKind?: DoorKind` and `swing?: DoorSwing`, and those unions widened in Task 1).

- [x] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningPanel.test.ts`, inside `describe("OpeningPanel — door kind and orientation", ...)` (after the existing `"updates doorKind when the door kind select changes"` test):

```ts
  it("includes double in the door kind select", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    const values = [...select.options].map((o) => o.value);
    expect(values).toContain("double");
  });

  it("shows the swing-direction toggle but not hinge-side for a double door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "double", swing: "out" }) });
    expect(target.querySelector("select.hinge-side")).toBeNull();
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(direction).not.toBeNull();
    expect(direction.value).toBe("out");
  });

  it("defaults the double door swing-direction toggle to in when swing is unset", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "double" }) });
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(direction.value).toBe("in");
  });

  it("writes swing directly as in/out (no side) when the direction toggle changes on a double door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor({ doorKind: "double", swing: "in" }), onupdate });
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    direction.value = "out";
    direction.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ swing: "out" });
  });
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts -t "double"`
Expected: FAIL — the door-kind `<select>` has no `"double"` `<option>`, and the swing-direction select is hidden for `doorKind === "double"` (its visibility condition is currently `doorKind === "hinged"` only), so `direction` is `null` and the test throws.

- [x] **Step 3: Add i18n keys**

In `packages/editor/src/lib/locales/en.json`, after `"doorKindGarage": "Garage",` (line 276):

```json
    "doorKindDouble": "French door",
```

In `packages/editor/src/lib/locales/fr.json`, after `"doorKindGarage": "Garage",` (line 276):

```json
    "doorKindDouble": "Porte-fenêtre",
```

- [x] **Step 4: Implement**

In `packages/editor/src/lib/components/OpeningPanel.svelte`, add a `<option>` to the door-kind select (line 147, after the `garage` option):

```svelte
        <option value="double">{$_('floorPlan.openingPanel.doorKindDouble')}</option>
```

Change the swing-direction select's visibility condition (line 161) from:

```svelte
    {#if doorKind === "hinged"}
```

to:

```svelte
    {#if doorKind === "hinged" || doorKind === "double"}
```

Update `handleSwingDirectionChange` (lines 102-105) to write `swing` directly for a double door, since there's no hinge side to compose:

```ts
  function handleSwingDirectionChange(e: Event): void {
    const direction = (e.target as HTMLSelectElement).value as "in" | "out";
    onupdate({ swing: doorKind === "double" ? direction : composeSwing(hingeSide, direction) });
  }
```

(No changes needed to the `swingDirection` derived value at line 87 — `(opening.swing ?? "left-in").endsWith("in") ? "in" : "out"` already evaluates correctly for the new plain `"in"`/`"out"` values: `"out".endsWith("in")` is `false` ⇒ `"out"`; `"in".endsWith("in")` is `true` ⇒ `"in"`; unset defaults to `"left-in"` ⇒ `"in"`. No changes needed to the `hinge-side` select's visibility condition either — it stays `doorKind === "hinged" || doorKind === "swinging"`, correctly excluding `"double"`.)

- [x] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts`
Expected: PASS

- [x] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/OpeningPanel.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/OpeningPanel.test.ts
git commit -m "feat(editor): add double door kind option and swing-direction control to OpeningPanel"
```

---

### Task 4: Python SVG export — per-`doorKind` rendering in `svg_render.py`

**Files:**
- Modify: `packages/backend/src/myhome/svg_render.py:134-175` (`_render_opening`, `_render_door`)
- Test: `packages/backend/tests/test_svg_render.py`

**Interfaces:**
- Consumes: `Opening.doorKind`, `Opening.swing`, `Wall.thickness` (already on the model).
- Produces: `_render_door` signature changes from `(p1, p2, dir_x, dir_y, swing, width)` to `(thickness, p1, p2, dir_x, dir_y, door_kind, swing, width)`; new private helper `_door_leaf_and_arc(hinge, other, perp, width) -> str`. Both are module-internal — nothing outside `svg_render.py` calls them directly (confirmed: only `render_floor_svg` is imported elsewhere, per the route in `packages/backend/src/myhome/routes/svg.py`).

- [x] **Step 1: Write the failing tests**

Replace the existing `test_door_opening_renders_leaf_and_arc` test in `packages/backend/tests/test_svg_render.py` with a parametrized version covering all five kinds, plus dedicated double-door assertions. Replace:

```python
def test_door_opening_renders_leaf_and_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in")
    )
    svg = render_floor_svg(floor)
    assert 'class="door-leaf"' in svg
    assert 'class="door-swing"' in svg
```

with:

```python
def test_door_opening_renders_leaf_and_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in")
    )
    svg = render_floor_svg(floor)
    assert 'class="door-leaf"' in svg
    assert 'class="door-swing"' in svg


@pytest.mark.parametrize("door_kind", ["hinged", None])
def test_hinged_door_renders_one_leaf_and_arc(door_kind):
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in", doorKind=door_kind)
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 1
    assert svg.count('class="door-swing"') == 1


def test_swinging_door_renders_two_leaves_and_arcs_from_one_hinge():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, swing="left-in", doorKind="swinging")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 2
    assert svg.count('class="door-swing"') == 2
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="([^"]+)" y1="([^"]+)"', svg)
    assert leaves[0] == leaves[1]  # both leaves share the same hinge point


def test_sliding_door_renders_a_bar_with_no_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, doorKind="sliding")
    )
    svg = render_floor_svg(floor)
    assert 'class="door-sliding"' in svg
    assert 'class="door-leaf"' not in svg
    assert 'class="door-swing"' not in svg


def test_garage_door_renders_five_ticks_with_no_arc():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=0.9, doorKind="garage")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-garage"') == 5
    assert 'class="door-swing"' not in svg


def test_double_door_renders_two_independent_leaves_and_arcs():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=1.6, doorKind="double")
    )
    svg = render_floor_svg(floor)
    assert svg.count('class="door-leaf"') == 2
    assert svg.count('class="door-swing"') == 2
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="([\d.-]+)" y1="([\d.-]+)"', svg)
    hinge_xs = sorted(float(x) for x, _ in leaves)
    assert hinge_xs[0] == pytest.approx(1.0)
    assert hinge_xs[1] == pytest.approx(2.6)


def test_double_door_swings_out_when_swing_is_out():
    floor = empty_floor()
    floor.walls.append(make_wall("w1", 0, 0, 5, 0))
    floor.openings.append(
        Opening(id="o1", wallId="w1", type="door", offset=1.0, width=1.6, doorKind="double", swing="out")
    )
    svg = render_floor_svg(floor)
    import re
    leaves = re.findall(r'<line class="door-leaf" x1="[\d.-]+" y1="[\d.-]+" x2="[\d.-]+" y2="([\d.-]+)"', svg)
    # wall is horizontal along +x; "out" perpendicular is -y for this convention.
    for y2 in leaves:
        assert float(y2) < 0
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_svg_render.py -v`
Expected: FAIL on every new test — today's `_render_door` always draws exactly one leaf+arc regardless of `doorKind`, so `swinging`/`double` counts of 2 fail, `sliding`/`garage` never produce `door-sliding`/`door-garage` classes at all (and incorrectly still produce a `door-leaf`/`door-swing` pair).

- [x] **Step 3: Implement**

In `packages/backend/src/myhome/svg_render.py`, replace `_render_opening` (lines 134-147):

```python
def _render_opening(wall: Wall, opening: Opening) -> str:
    dir_x, dir_y, length = _wall_direction(wall)
    from_ = _clamp(opening.offset, 0.0, length)
    to = _clamp(opening.offset + opening.width, from_, length)
    render_width = to - from_
    p1 = _point_along(wall.start, dir_x, dir_y, from_)
    p2 = _point_along(wall.start, dir_x, dir_y, to)
    if opening.type == "window":
        return (
            f'<line class="window" '
            f'x1="{_fmt(p1.x)}" y1="{_fmt(p1.y)}" '
            f'x2="{_fmt(p2.x)}" y2="{_fmt(p2.y)}" />'
        )
    thickness = wall.thickness if wall.thickness is not None else 0.1
    door_kind = opening.doorKind or "hinged"
    default_swing = "in" if door_kind == "double" else "left-in"
    swing = opening.swing or default_swing
    return _render_door(thickness, p1, p2, dir_x, dir_y, door_kind, swing, render_width)
```

Replace `_render_door` (lines 150-175):

```python
def _render_door(
    thickness: float,
    p1: Point,
    p2: Point,
    dir_x: float,
    dir_y: float,
    door_kind: str,
    swing: str,
    width: float,
) -> str:
    if width < 1e-9:
        return ""
    perp_left = Point(x=-dir_y, y=dir_x)
    perp_right = Point(x=dir_y, y=-dir_x)

    if door_kind == "sliding":
        mag = (thickness / 2) * 0.5
        a = Point(x=p1.x + perp_right.x * mag, y=p1.y + perp_right.y * mag)
        b = Point(x=p2.x + perp_right.x * mag, y=p2.y + perp_right.y * mag)
        return (
            f'<line class="door-sliding" '
            f'x1="{_fmt(a.x)}" y1="{_fmt(a.y)}" '
            f'x2="{_fmt(b.x)}" y2="{_fmt(b.y)}" />'
        )

    if door_kind == "garage":
        tick_count = 5
        half_thick = thickness / 2
        perp_full = Point(x=-dir_y * half_thick, y=dir_x * half_thick)
        parts = []
        for i in range(tick_count):
            t = i / (tick_count - 1)
            cx = p1.x + (p2.x - p1.x) * t
            cy = p1.y + (p2.y - p1.y) * t
            a = Point(x=cx + perp_full.x, y=cy + perp_full.y)
            b = Point(x=cx - perp_full.x, y=cy - perp_full.y)
            parts.append(
                f'<line class="door-garage" '
                f'x1="{_fmt(a.x)}" y1="{_fmt(a.y)}" '
                f'x2="{_fmt(b.x)}" y2="{_fmt(b.y)}" />'
            )
        return "\n".join(parts)

    if door_kind == "double":
        perp = perp_right if swing == "out" else perp_left
        half_width = width / 2
        mid = Point(x=(p1.x + p2.x) / 2, y=(p1.y + p2.y) / 2)
        return (
            f"{_door_leaf_and_arc(p1, mid, perp, half_width)}\n"
            f"{_door_leaf_and_arc(p2, mid, perp, half_width)}"
        )

    if door_kind == "swinging":
        is_left_hinge = swing in ("left-in", "left-out")
        hinge = p1 if is_left_hinge else p2
        other = p2 if is_left_hinge else p1
        return (
            f"{_door_leaf_and_arc(hinge, other, perp_left, width)}\n"
            f"{_door_leaf_and_arc(hinge, other, perp_right, width)}"
        )

    # hinged (default)
    is_left_hinge = swing in ("left-in", "left-out")
    is_in_swing = swing in ("left-in", "right-in")
    hinge = p1 if is_left_hinge else p2
    other = p2 if is_left_hinge else p1
    perp = perp_left if is_in_swing else perp_right
    return _door_leaf_and_arc(hinge, other, perp, width)


def _door_leaf_and_arc(hinge: Point, other: Point, perp: Point, width: float) -> str:
    open_end = Point(x=hinge.x + perp.x * width, y=hinge.y + perp.y * width)
    leaf = (
        f'<line class="door-leaf" '
        f'x1="{_fmt(hinge.x)}" y1="{_fmt(hinge.y)}" '
        f'x2="{_fmt(open_end.x)}" y2="{_fmt(open_end.y)}" />'
    )
    sweep = _choose_sweep_flag(other, open_end, width, hinge)
    arc = (
        f'<path class="door-swing" '
        f'd="M {_fmt(other.x)} {_fmt(other.y)} '
        f'A {_fmt(width)} {_fmt(width)} 0 0 {sweep} '
        f'{_fmt(open_end.x)} {_fmt(open_end.y)}" />'
    )
    return f"{leaf}\n{arc}"
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_svg_render.py -v`
Expected: PASS

Run: `cd packages/backend && python -m pytest -v`
Expected: PASS (full backend suite, no regressions in `test_svg.py`-style route tests or elsewhere).

- [x] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/svg_render.py packages/backend/tests/test_svg_render.py
git commit -m "fix(backend): render doorKind-specific symbols (incl. double) in SVG export"
```

---

### Task 5: TS twin renderer — per-`doorKind` rendering in `svgRender.ts`

**Files:**
- Modify: `packages/geometry/src/svgRender.ts:194-241` (`renderOpening`, `renderDoor`)
- Test: `packages/geometry/test/svgRender.test.ts`

**Interfaces:**
- Consumes: `Opening.doorKind`, `Opening.swing`, `Wall.thickness`, `DoorKind` type (already exported from `./types`).
- Produces: `renderDoor`'s signature changes from `(p1, p2, dirX, dirY, swing, width)` to `(thickness, p1, p2, dirX, dirY, doorKind, swing, width)`; new private helper `doorLeafAndArc(hinge, other, perp, width): string`. Both are module-internal (not exported) — only `renderFloorSvg` and `chooseSweepFlag` are exported from this file, per its current `export` statements.

- [x] **Step 1: Write the failing tests**

Add to `packages/geometry/test/svgRender.test.ts`, as a new `describe` block after the existing `describe("door swing rendering", ...)` block:

```ts
describe("door kind rendering", () => {
  const wall: Wall = {
    id: "w1",
    start: { x: 0, y: 0 },
    end: { x: 5, y: 0 },
    thickness: 0.2,
    type: "wall",
  };

  function doorSvg(overrides: Partial<Opening> = {}): string {
    const opening: Opening = {
      id: "op1",
      wallId: "w1",
      type: "door",
      offset: 1,
      width: 0.9,
      swing: "left-in",
      ...overrides,
    };
    return renderFloorSvg(baseFloor({ walls: [wall], openings: [opening] }));
  }

  it("renders exactly one leaf and arc for hinged (default) doorKind", () => {
    const svg = doorSvg();
    expect((svg.match(/class="door-leaf"/g) ?? []).length).toBe(1);
    expect((svg.match(/class="door-swing"/g) ?? []).length).toBe(1);
  });

  it("renders two leaves and arcs sharing one hinge for swinging doorKind", () => {
    const svg = doorSvg({ doorKind: "swinging" });
    expect((svg.match(/class="door-leaf"/g) ?? []).length).toBe(2);
    expect((svg.match(/class="door-swing"/g) ?? []).length).toBe(2);
    const leaves = [...svg.matchAll(/<line class="door-leaf" x1="([^"]+)" y1="([^"]+)"/g)];
    expect(leaves[0][1]).toBe(leaves[1][1]);
    expect(leaves[0][2]).toBe(leaves[1][2]);
  });

  it("renders a bar with no arc for sliding doorKind", () => {
    const svg = doorSvg({ doorKind: "sliding" });
    expect(svg).toContain('class="door-sliding"');
    expect(svg).not.toContain('class="door-leaf"');
    expect(svg).not.toContain('class="door-swing"');
  });

  it("renders five ticks with no arc for garage doorKind", () => {
    const svg = doorSvg({ doorKind: "garage" });
    expect((svg.match(/class="door-garage"/g) ?? []).length).toBe(5);
    expect(svg).not.toContain('class="door-swing"');
  });

  it("renders two independent leaves and arcs, hinged at each jamb, for double doorKind", () => {
    const svg = doorSvg({ offset: 1, width: 1.6, doorKind: "double", swing: undefined });
    expect((svg.match(/class="door-leaf"/g) ?? []).length).toBe(2);
    expect((svg.match(/class="door-swing"/g) ?? []).length).toBe(2);
    const hingeXs = [...svg.matchAll(/<line class="door-leaf" x1="([\d.-]+)"/g)]
      .map((m) => Number(m[1]))
      .sort((a, b) => a - b);
    expect(hingeXs[0]).toBeCloseTo(1, 5);
    expect(hingeXs[1]).toBeCloseTo(2.6, 5);
  });

  it("swings a double door outward when swing is out", () => {
    const svg = doorSvg({ offset: 1, width: 1.6, doorKind: "double", swing: "out" });
    const y2s = [...svg.matchAll(/<line class="door-leaf" x1="[\d.-]+" y1="[\d.-]+" x2="[\d.-]+" y2="([\d.-]+)"/g)]
      .map((m) => Number(m[1]));
    for (const y2 of y2s) expect(y2).toBeLessThan(0);
  });
});
```

- [x] **Step 2: Run tests to verify they fail**

Run: `cd packages/geometry && npx vitest run test/svgRender.test.ts -t "door kind rendering"`
Expected: FAIL — same reason as the Python tests: `renderDoor` currently ignores `doorKind` entirely.

- [x] **Step 3: Implement**

In `packages/geometry/src/svgRender.ts`, update the import at the top (line 1):

```ts
import type { Floor, Wall, Opening, Room, Point, DoorSwing, DoorKind } from "./types";
```

Replace `renderOpening` (lines 194-208):

```ts
function renderOpening(wall: Wall, opening: Opening): string {
  const { dirX, dirY, length } = wallDirection(wall);
  const from = clamp(opening.offset, 0, length);
  const to = clamp(opening.offset + opening.width, from, length);
  const renderWidth = to - from;

  const p1 = pointAlong(wall.start, dirX, dirY, from);
  const p2 = pointAlong(wall.start, dirX, dirY, to);

  if (opening.type === "window") {
    return `<line class="window" x1="${fmt(p1.x)}" y1="${fmt(p1.y)}" x2="${fmt(p2.x)}" y2="${fmt(p2.y)}" />`;
  }

  const thickness = wall.thickness ?? 0.1;
  const doorKind = opening.doorKind ?? "hinged";
  const defaultSwing = doorKind === "double" ? "in" : "left-in";
  const swing = opening.swing ?? defaultSwing;
  return renderDoor(thickness, p1, p2, dirX, dirY, doorKind, swing, renderWidth);
}
```

Replace `renderDoor` (lines 210-241):

```ts
function renderDoor(
  thickness: number,
  p1: Point,
  p2: Point,
  dirX: number,
  dirY: number,
  doorKind: DoorKind,
  swing: DoorSwing,
  width: number
): string {
  if (width < 1e-9) return "";

  const perpLeft: Point = { x: -dirY, y: dirX };
  const perpRight: Point = { x: dirY, y: -dirX };

  if (doorKind === "sliding") {
    const mag = (thickness / 2) * 0.5;
    const a: Point = { x: p1.x + perpRight.x * mag, y: p1.y + perpRight.y * mag };
    const b: Point = { x: p2.x + perpRight.x * mag, y: p2.y + perpRight.y * mag };
    return `<line class="door-sliding" x1="${fmt(a.x)}" y1="${fmt(a.y)}" x2="${fmt(b.x)}" y2="${fmt(b.y)}" />`;
  }

  if (doorKind === "garage") {
    const tickCount = 5;
    const halfThick = thickness / 2;
    const perpFull: Point = { x: -dirY * halfThick, y: dirX * halfThick };
    const parts: string[] = [];
    for (let i = 0; i < tickCount; i++) {
      const t = i / (tickCount - 1);
      const cx = p1.x + (p2.x - p1.x) * t;
      const cy = p1.y + (p2.y - p1.y) * t;
      const a: Point = { x: cx + perpFull.x, y: cy + perpFull.y };
      const b: Point = { x: cx - perpFull.x, y: cy - perpFull.y };
      parts.push(`<line class="door-garage" x1="${fmt(a.x)}" y1="${fmt(a.y)}" x2="${fmt(b.x)}" y2="${fmt(b.y)}" />`);
    }
    return parts.join("\n");
  }

  if (doorKind === "double") {
    const perp = swing === "out" ? perpRight : perpLeft;
    const halfWidth = width / 2;
    const mid: Point = { x: (p1.x + p2.x) / 2, y: (p1.y + p2.y) / 2 };
    return `${doorLeafAndArc(p1, mid, perp, halfWidth)}\n${doorLeafAndArc(p2, mid, perp, halfWidth)}`;
  }

  if (doorKind === "swinging") {
    const isLeftHinge = swing === "left-in" || swing === "left-out";
    const hinge = isLeftHinge ? p1 : p2;
    const other = isLeftHinge ? p2 : p1;
    return `${doorLeafAndArc(hinge, other, perpLeft, width)}\n${doorLeafAndArc(hinge, other, perpRight, width)}`;
  }

  const isLeftHinge = swing === "left-in" || swing === "left-out";
  const isInSwing = swing === "left-in" || swing === "right-in";
  const hinge = isLeftHinge ? p1 : p2;
  const other = isLeftHinge ? p2 : p1;
  const perp = isInSwing ? perpLeft : perpRight;
  return doorLeafAndArc(hinge, other, perp, width);
}

function doorLeafAndArc(hinge: Point, other: Point, perp: Point, width: number): string {
  const openEnd: Point = { x: hinge.x + perp.x * width, y: hinge.y + perp.y * width };
  const leaf = `<line class="door-leaf" x1="${fmt(hinge.x)}" y1="${fmt(hinge.y)}" x2="${fmt(openEnd.x)}" y2="${fmt(openEnd.y)}" />`;
  const sweepFlag = chooseSweepFlag(other, openEnd, width, hinge);
  const arc = `<path class="door-swing" d="M ${fmt(other.x)} ${fmt(other.y)} A ${fmt(width)} ${fmt(width)} 0 0 ${sweepFlag} ${fmt(openEnd.x)} ${fmt(openEnd.y)}" />`;
  return `${leaf}\n${arc}`;
}
```

- [x] **Step 4: Run tests to verify they pass**

Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run test/svgRender.test.ts`
Expected: PASS (including the pre-existing `describe("door swing rendering", ...)` block — `renderDoor`'s hinged-path logic is byte-for-byte the same as before, just reached through the new `doorKind` branch structure and the extracted `doorLeafAndArc` helper).

- [x] **Step 5: Run the full geometry suite**

Run: `cd packages/geometry && npx vitest run`
Expected: PASS — no regressions elsewhere in the package.

- [x] **Step 6: Commit**

```bash
git add packages/geometry/src/svgRender.ts packages/geometry/test/svgRender.test.ts
git commit -m "fix(geometry): render doorKind-specific symbols (incl. double) in the TS SVG renderer"
```

---

## Final verification

- [x] Run: `cd packages/backend && python -m pytest -v` — full backend suite passes.
- [x] Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run` — full geometry suite passes.
- [x] Run: `cd packages/editor && npx tsc --noEmit && npx vitest run` — full editor suite passes.
- [x] Manually verify in a running dev instance: create a door, set its kind to the new French-door option in the panel, confirm two independent leaves render on the canvas and meet in the middle when the swing-direction toggle is changed between in/out.
