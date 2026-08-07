# Opening sensor filter + door kinds + orientation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix the HA sensor picker to only offer sensors HA flags as the matching device class (window/door), and add door kinds (pivotante/battante/coulissante/garage) with per-kind floor-plan rendering plus editable orientation for both doors and windows.

**Architecture:** Backend gains a `device_classes` filter on the existing `/api/ha/entities` endpoint. The `Opening` geometry type gains two new optional fields (`doorKind`, `windowSide`) that default when absent, exactly like the existing `swing` field does. `OpeningPanel.svelte` gains new controls wired through the existing `onupdate` patch callback and `houseStore.updateOpening`. `OpeningShape.svelte` gains per-`doorKind` SVG geometry and a double-line window symbol, both still driven by the existing `strokeColor` (selection / HA sensor-state) derivation.

**Tech Stack:** FastAPI + httpx (backend), Svelte 5 runes + TypeScript (editor), pytest/respx (backend tests), Vitest (frontend tests).

## Global Constraints

- `doorKind` and `windowSide` are optional `Opening` fields; `undefined` must behave as `"hinged"` / `"in"` respectively — no data migration for existing saved floor plans.
- Door-kind UI labels are French: Pivotante (hinged, default) / Battante (swinging) / Coulissante (sliding) / Garage.
- `packages/geometry/src/svgRender.ts` (`renderFloorSvg`) is explicitly OUT OF SCOPE — it has no production consumer today, and this plan does not touch it.
- All new UI strings go through `svelte-i18n` (`$_(...)`), added to both `packages/editor/src/lib/locales/en.json` and `fr.json`.

---

### Task 1: Backend — filter `/api/ha/entities` by `device_class`

**Files:**
- Modify: `packages/backend/src/myhome/routes/ha.py:79-108` (`get_ha_entities`)
- Test: `packages/backend/tests/test_ha.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `GET /api/ha/entities?area_id=...&domain=...&device_classes=a,b` (optional param; omitted = today's unfiltered behavior). Response shape unchanged: `[{"entity_id": str, "name": str}, ...]`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/backend/tests/test_ha.py` (after `test_get_ha_entities_lists_matching_domain`):

```python
def test_get_ha_entities_filters_by_device_class(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/template").mock(
            return_value=Response(200, text=json.dumps([
                {"entity_id": "binary_sensor.front_window", "name": "Front Window", "device_class": "window"},
                {"entity_id": "binary_sensor.hallway_motion", "name": "Hallway Motion", "device_class": "motion"},
            ]))
        )
        resp = client.get(
            "/api/ha/entities",
            params={"area_id": "entryway", "domain": "binary_sensor", "device_classes": "window"},
        )
    assert resp.status_code == 200
    assert resp.json() == [{"entity_id": "binary_sensor.front_window", "name": "Front Window"}]


def test_get_ha_entities_filters_by_multiple_device_classes(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/template").mock(
            return_value=Response(200, text=json.dumps([
                {"entity_id": "binary_sensor.front_door", "name": "Front Door", "device_class": "door"},
                {"entity_id": "binary_sensor.garage_door", "name": "Garage Door", "device_class": "garage_door"},
                {"entity_id": "binary_sensor.front_window", "name": "Front Window", "device_class": "window"},
            ]))
        )
        resp = client.get(
            "/api/ha/entities",
            params={"area_id": "entryway", "domain": "binary_sensor", "device_classes": "door,garage_door"},
        )
    assert resp.status_code == 200
    assert resp.json() == [
        {"entity_id": "binary_sensor.front_door", "name": "Front Door"},
        {"entity_id": "binary_sensor.garage_door", "name": "Garage Door"},
    ]


def test_get_ha_entities_no_filter_when_device_classes_omitted(client, monkeypatch):
    monkeypatch.setenv("SUPERVISOR_TOKEN", "test-token")
    with respx.mock:
        respx.post("http://supervisor/core/api/template").mock(
            return_value=Response(200, text=json.dumps([
                {"entity_id": "binary_sensor.hallway_motion", "name": "Hallway Motion", "device_class": "motion"},
            ]))
        )
        resp = client.get("/api/ha/entities", params={"area_id": "entryway", "domain": "binary_sensor"})
    assert resp.status_code == 200
    assert resp.json() == [{"entity_id": "binary_sensor.hallway_motion", "name": "Hallway Motion"}]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v -k device_class`
Expected: FAIL (mock JSON now includes an extra `device_class` key the endpoint doesn't yet strip/filter — `test_get_ha_entities_filters_by_device_class` and `..._multiple_device_classes` fail because the response still includes the unfiltered/unfiltered-shape list).

- [ ] **Step 3: Implement the filter**

Replace `get_ha_entities` in `packages/backend/src/myhome/routes/ha.py`:

```python
@router.get("/api/ha/entities")
async def get_ha_entities(area_id: str, domain: str, device_classes: str | None = None) -> list[dict]:
    if domain not in _ALLOWED_ENTITY_DOMAINS:
        raise HTTPException(status_code=400, detail="unsupported domain")
    token = os.environ.get("SUPERVISOR_TOKEN")
    if not token:
        return []
    # area_id/domain are passed as Jinja `variables`, not string-interpolated into
    # the template source -- interpolating user-controlled query params directly
    # into the template text would be a server-side template injection hole.
    template = (
        "[{%- for e in area_entities(area_id) if e.startswith(domain + '.') -%}"
        "{%- if not loop.first -%},{%- endif -%}"
        '{"entity_id":"{{ e }}","name":"{{ (state_attr(e, \'friendly_name\') or e) '
        "| replace('\"', '\\\\\"') }}\",\"device_class\":\"{{ (state_attr(e, 'device_class') or '') "
        "| replace('\"', '\\\\\"') }}\"}"
        "{%- endfor -%}]"
    )
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                f"{_HA_BASE}/template",
                headers=_auth_headers(token),
                json={"template": template, "variables": {"area_id": area_id, "domain": domain}},
                timeout=5.0,
            )
            if resp.status_code == 200:
                entities = json.loads(resp.text)
                if device_classes:
                    allowed = {d.strip() for d in device_classes.split(",") if d.strip()}
                    entities = [e for e in entities if e.get("device_class") in allowed]
                return [{"entity_id": e["entity_id"], "name": e["name"]} for e in entities]
    except Exception:
        pass
    return []
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/backend && python -m pytest tests/test_ha.py -v`
Expected: PASS (all tests in the file, including the pre-existing ones — `test_get_ha_entities_lists_matching_domain`'s mock has no `device_class` key, which is fine since `device_classes` isn't passed and filtering is skipped).

- [ ] **Step 5: Commit**

```bash
git add packages/backend/src/myhome/routes/ha.py packages/backend/tests/test_ha.py
git commit -m "fix(backend): filter /api/ha/entities by device_class"
```

---

### Task 2: Geometry — `doorKind`/`windowSide` fields + `houseStore.updateOpening` plumbing

**Files:**
- Modify: `packages/geometry/src/types.ts`
- Modify: `packages/editor/src/lib/houseStore.svelte.ts:170-185` (`updateOpening`)
- Test: `packages/geometry/test/types.test.ts`
- Test: `packages/editor/test/houseStore.test.ts`

**Interfaces:**
- Produces: `export type DoorKind = "hinged" | "swinging" | "sliding" | "garage";`, `export type WallSide = "in" | "out";`, `Opening.doorKind?: DoorKind`, `Opening.windowSide?: WallSide`. `houseStore.updateOpening(id, patch)` accepts `doorKind`/`windowSide` in `patch`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/geometry/test/types.test.ts`, inside `describe("Opening HA fields", ...)`:

```ts
  it("allows an opening with doorKind and windowSide set", () => {
    const door: Opening = { id: "o3", wallId: "w1", type: "door", offset: 0, width: 0.9, doorKind: "sliding" };
    const window: Opening = { id: "o4", wallId: "w1", type: "window", offset: 0, width: 1, windowSide: "out" };
    expect(door.doorKind).toBe("sliding");
    expect(window.windowSide).toBe("out");
  });
```

Add to `packages/editor/test/houseStore.test.ts`, inside `describe("houseStore — updateOpening HA fields", ...)`:

```ts
  it("persists doorKind and windowSide", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addOpening({ id: "o1", wallId: "w1", type: "door", offset: 0, width: 0.9 });
    store.updateOpening("o1", { doorKind: "sliding" });
    expect(store.floor.openings[0].doorKind).toBe("sliding");

    store.addOpening({ id: "o2", wallId: "w1", type: "window", offset: 1, width: 1 });
    store.updateOpening("o2", { windowSide: "out" });
    expect(store.floor.openings[1].windowSide).toBe("out");
  });
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/geometry && npx tsc --noEmit` — expected: FAIL (`doorKind`/`windowSide` don't exist on `Opening`).
Run: `cd packages/editor && npx vitest run test/houseStore.test.ts` — expected: FAIL (`updateOpening` patch type rejects `doorKind`/`windowSide`, or the fields are silently not applied).

- [ ] **Step 3: Add the types**

In `packages/geometry/src/types.ts`, after the `DoorSwing` type (line 25):

```ts
export type DoorKind = "hinged" | "swinging" | "sliding" | "garage";

export type WallSide = "in" | "out";
```

In the `Opening` interface, after `swing?: DoorSwing;`:

```ts
  /** Only meaningful for type "door". Undefined behaves as "hinged". */
  doorKind?: DoorKind;
```

After `shutterEntityId?: string | null;`:

```ts
  /** Only meaningful for type "window". Undefined behaves as "in". */
  windowSide?: WallSide;
```

- [ ] **Step 4: Wire `updateOpening`**

In `packages/editor/src/lib/houseStore.svelte.ts`, update the `updateOpening` signature and body:

```ts
  function updateOpening(
    id: string,
    patch: Partial<Pick<Opening, "offset" | "width" | "swing" | "haEntityId" | "hasShutter" | "shutterEntityId" | "doorKind" | "windowSide">>,
    opts?: { skipHistory?: boolean }
  ): void {
    const opening = currentFloor().openings.find((o) => o.id === id);
    if (!opening) return;
    if (!opts?.skipHistory) saveSnapshot();
    else generation++;
    if (patch.offset !== undefined) opening.offset = patch.offset;
    if (patch.width !== undefined) opening.width = patch.width;
    if (patch.swing !== undefined) opening.swing = patch.swing;
    if (patch.haEntityId !== undefined) opening.haEntityId = patch.haEntityId;
    if (patch.hasShutter !== undefined) opening.hasShutter = patch.hasShutter;
    if (patch.shutterEntityId !== undefined) opening.shutterEntityId = patch.shutterEntityId;
    if (patch.doorKind !== undefined) opening.doorKind = patch.doorKind;
    if (patch.windowSide !== undefined) opening.windowSide = patch.windowSide;
  }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run test/types.test.ts`
Run: `cd packages/editor && npx vitest run test/houseStore.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/geometry/src/types.ts packages/geometry/test/types.test.ts packages/editor/src/lib/houseStore.svelte.ts packages/editor/test/houseStore.test.ts
git commit -m "feat(geometry): add Opening.doorKind and Opening.windowSide fields"
```

---

### Task 3: `OpeningPanel` — scope sensor fetch by `device_classes`

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningPanel.svelte:25-46` (`fetchEntities`, sensor `$effect`)
- Test: `packages/editor/test/OpeningPanel.test.ts`

**Interfaces:**
- Consumes: `GET /api/ha/entities` now accepts `device_classes` (Task 1).
- Produces: no change to `OpeningPanel`'s own props/exports — internal fetch behavior only.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningPanel.test.ts`, inside `describe("OpeningPanel — sensor picker", ...)`:

```ts
  it("scopes the sensor fetch to device_class=window for a window opening", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeWindow() });
    await new Promise((r) => setTimeout(r, 0));
    const url = new URL((fetchMock.mock.calls[0][0] as string), "http://x");
    expect(url.searchParams.get("device_classes")).toBe("window");
  });

  it("scopes the sensor fetch to device_class=door,garage_door for a door opening", async () => {
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, json: async () => [] });
    vi.stubGlobal("fetch", fetchMock);
    setup({ opening: makeDoor() });
    await new Promise((r) => setTimeout(r, 0));
    const url = new URL((fetchMock.mock.calls[0][0] as string), "http://x");
    expect(url.searchParams.get("device_classes")).toBe("door,garage_door");
  });
```

(`makeDoor` is already defined at the top of the test file.)

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts -t "scopes the sensor fetch"`
Expected: FAIL (`device_classes` param not present, `searchParams.get` returns `null`).

- [ ] **Step 3: Implement**

Replace `fetchEntities` and the sensor `$effect` in `packages/editor/src/lib/components/OpeningPanel.svelte`:

```ts
  async function fetchEntities(domain: string, deviceClasses?: string): Promise<HaEntity[]> {
    if (areaIds.length === 0) return [];
    const lists = await Promise.all(
      areaIds.map((areaId) => {
        const params = new URLSearchParams({ area_id: areaId, domain });
        if (deviceClasses) params.set("device_classes", deviceClasses);
        return fetch(`/api/ha/entities?${params.toString()}`)
          .then((r) => (r.ok ? r.json() : []))
          .catch(() => [] as HaEntity[]);
      })
    );
    const byId = new Map<string, HaEntity>();
    for (const list of lists as HaEntity[][]) for (const e of list) byId.set(e.entity_id, e);
    return [...byId.values()];
  }

  $effect(() => {
    const deviceClasses = opening.type === "window" ? "window" : "door,garage_door";
    fetchEntities("binary_sensor", deviceClasses).then((list) => { sensorEntities = list; });
  });
```

(The `coverEntities` `$effect` below it is unchanged — no `device_classes` filter for the shutter/`cover` picker.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts`
Expected: PASS (including the pre-existing "fetches binary_sensor entities scoped to the given area(s)" test, which only checks `.toContain("domain=binary_sensor")` — still true regardless of param order).

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/OpeningPanel.svelte packages/editor/test/OpeningPanel.test.ts
git commit -m "fix(editor): scope opening sensor picker by HA device_class"
```

---

### Task 4: `OpeningPanel` — door kind + orientation controls

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningPanel.svelte`
- Modify: `packages/editor/src/lib/locales/en.json`
- Modify: `packages/editor/src/lib/locales/fr.json`
- Test: `packages/editor/test/OpeningPanel.test.ts`

**Interfaces:**
- Consumes: `Opening.doorKind`, `Opening.windowSide`, `DoorKind`, `WallSide`, `DoorSwing` from `@myhome/geometry` (Task 2).
- Produces: `onupdate` patch shape grows to include `doorKind?: DoorKind`, `windowSide?: WallSide`, `swing?: DoorSwing`.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningPanel.test.ts`, as a new `describe` block:

```ts
describe("OpeningPanel — door kind and orientation", () => {
  it("shows a door kind select for a door, defaulting to hinged", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor() });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    expect(select).not.toBeNull();
    expect(select.value).toBe("hinged");
  });

  it("does not show a door kind select for a window", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    expect(target.querySelector("select.door-kind")).toBeNull();
  });

  it("shows hinge-side and swing-direction toggles for a hinged door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ swing: "right-out" }) });
    const hinge = target.querySelector("select.hinge-side") as HTMLSelectElement;
    const direction = target.querySelector("select.swing-direction") as HTMLSelectElement;
    expect(hinge.value).toBe("right");
    expect(direction.value).toBe("out");
  });

  it("shows only the hinge-side toggle for a swinging door", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "swinging" }) });
    expect(target.querySelector("select.hinge-side")).not.toBeNull();
    expect(target.querySelector("select.swing-direction")).toBeNull();
  });

  it("shows no orientation toggle for sliding or garage doors", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeDoor({ doorKind: "sliding" }) });
    expect(target.querySelector("select.hinge-side")).toBeNull();
    expect(target.querySelector("select.swing-direction")).toBeNull();
  });

  it("updates swing when the hinge-side toggle changes, preserving direction", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor({ swing: "left-out" }), onupdate });
    const hinge = target.querySelector("select.hinge-side") as HTMLSelectElement;
    hinge.value = "right";
    hinge.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ swing: "right-out" });
  });

  it("updates doorKind when the door kind select changes", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeDoor(), onupdate });
    const select = target.querySelector("select.door-kind") as HTMLSelectElement;
    select.value = "garage";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ doorKind: "garage" });
  });

  it("shows a window-side toggle for a window, defaulting to in", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    setup({ opening: makeWindow() });
    const select = target.querySelector("select.window-side") as HTMLSelectElement;
    expect(select).not.toBeNull();
    expect(select.value).toBe("in");
  });

  it("updates windowSide when the window-side toggle changes", () => {
    vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: true, json: async () => [] }));
    const onupdate = vi.fn();
    setup({ opening: makeWindow(), onupdate });
    const select = target.querySelector("select.window-side") as HTMLSelectElement;
    select.value = "out";
    select.dispatchEvent(new Event("change", { bubbles: true }));
    expect(onupdate).toHaveBeenCalledWith({ windowSide: "out" });
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts -t "door kind and orientation"`
Expected: FAIL (none of `select.door-kind` / `.hinge-side` / `.swing-direction` / `.window-side` exist yet).

- [ ] **Step 3: Add i18n keys**

In `packages/editor/src/lib/locales/en.json`, inside `floorPlan.openingPanel`, add (after `"noArea"`):

```json
    "doorKind": "Door kind",
    "doorKindHinged": "Hinged",
    "doorKindSwinging": "Double-action",
    "doorKindSliding": "Sliding",
    "doorKindGarage": "Garage",
    "hingeSide": "Hinge side",
    "swingDirection": "Opens",
    "left": "Left",
    "right": "Right",
    "in": "In",
    "out": "Out",
    "windowSide": "Orientation",
```

In `packages/editor/src/lib/locales/fr.json`, inside `floorPlan.openingPanel`, add (after `"noArea"`):

```json
    "doorKind": "Type de porte",
    "doorKindHinged": "Pivotante",
    "doorKindSwinging": "Battante",
    "doorKindSliding": "Coulissante",
    "doorKindGarage": "Garage",
    "hingeSide": "Côté charnière",
    "swingDirection": "Ouvre",
    "left": "Gauche",
    "right": "Droite",
    "in": "Vers l'intérieur",
    "out": "Vers l'extérieur",
    "windowSide": "Orientation",
```

- [ ] **Step 4: Implement the controls**

In `packages/editor/src/lib/components/OpeningPanel.svelte`, update the import and props type:

```ts
  import type { Opening, DoorKind, DoorSwing, WallSide } from "@myhome/geometry";
```

```ts
    onupdate: (patch: {
      haEntityId?: string | null;
      hasShutter?: boolean;
      shutterEntityId?: string | null;
      doorKind?: DoorKind;
      swing?: DoorSwing;
      windowSide?: WallSide;
    }) => void;
```

Add derived values and handlers (near the other handler functions):

```ts
  const doorKind = $derived.by((): DoorKind => opening.type === "door" ? (opening.doorKind ?? "hinged") : "hinged");
  const hingeSide = $derived.by((): "left" | "right" => (opening.swing ?? "left-in").startsWith("left") ? "left" : "right");
  const swingDirection = $derived.by((): "in" | "out" => (opening.swing ?? "left-in").endsWith("in") ? "in" : "out");

  function composeSwing(side: "left" | "right", direction: "in" | "out"): DoorSwing {
    return `${side}-${direction}` as DoorSwing;
  }

  function handleDoorKindChange(e: Event): void {
    onupdate({ doorKind: (e.target as HTMLSelectElement).value as DoorKind });
  }

  function handleHingeSideChange(e: Event): void {
    const side = (e.target as HTMLSelectElement).value as "left" | "right";
    onupdate({ swing: composeSwing(side, swingDirection) });
  }

  function handleSwingDirectionChange(e: Event): void {
    const direction = (e.target as HTMLSelectElement).value as "in" | "out";
    onupdate({ swing: composeSwing(hingeSide, direction) });
  }

  function handleWindowSideChange(e: Event): void {
    onupdate({ windowSide: (e.target as HTMLSelectElement).value as WallSide });
  }
```

Add markup, replacing the existing `{#if opening.type === "window"}` shutter block's opening (keep the shutter block as-is, just add new blocks around it):

```svelte
  {#if opening.type === "door"}
    <label>
      <span>{$_('floorPlan.openingPanel.doorKind')}</span>
      <select class="door-kind" value={doorKind} onchange={handleDoorKindChange}>
        <option value="hinged">{$_('floorPlan.openingPanel.doorKindHinged')}</option>
        <option value="swinging">{$_('floorPlan.openingPanel.doorKindSwinging')}</option>
        <option value="sliding">{$_('floorPlan.openingPanel.doorKindSliding')}</option>
        <option value="garage">{$_('floorPlan.openingPanel.doorKindGarage')}</option>
      </select>
    </label>

    {#if doorKind === "hinged" || doorKind === "swinging"}
      <label>
        <span>{$_('floorPlan.openingPanel.hingeSide')}</span>
        <select class="hinge-side" value={hingeSide} onchange={handleHingeSideChange}>
          <option value="left">{$_('floorPlan.openingPanel.left')}</option>
          <option value="right">{$_('floorPlan.openingPanel.right')}</option>
        </select>
      </label>
    {/if}

    {#if doorKind === "hinged"}
      <label>
        <span>{$_('floorPlan.openingPanel.swingDirection')}</span>
        <select class="swing-direction" value={swingDirection} onchange={handleSwingDirectionChange}>
          <option value="in">{$_('floorPlan.openingPanel.in')}</option>
          <option value="out">{$_('floorPlan.openingPanel.out')}</option>
        </select>
      </label>
    {/if}
  {/if}

  {#if opening.type === "window"}
    <label>
      <span>{$_('floorPlan.openingPanel.windowSide')}</span>
      <select class="window-side" value={opening.windowSide ?? "in"} onchange={handleWindowSideChange}>
        <option value="in">{$_('floorPlan.openingPanel.in')}</option>
        <option value="out">{$_('floorPlan.openingPanel.out')}</option>
      </select>
    </label>
  {/if}
```

Place this new block right after the sensor `<label>` block and before the existing `{#if opening.type === "window"}` shutter block.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningPanel.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/OpeningPanel.svelte packages/editor/src/lib/locales/en.json packages/editor/src/lib/locales/fr.json packages/editor/test/OpeningPanel.test.ts
git commit -m "feat(editor): add door kind and orientation controls to OpeningPanel"
```

---

### Task 5: `OpeningShape` — double-line window symbol with in/out offset

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte`
- Test: `packages/editor/test/OpeningShape.test.ts`

**Interfaces:**
- Consumes: `Opening.windowSide` (Task 2).
- Produces: no prop changes — rendering-only.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningShape.test.ts`, as a new `describe` block (uses the existing `wall` = `(0,0)`→`(4,0)`, `thickness: 0.1`, and `DEFAULT_VIEWPORT` = `{ panX: 400, panY: 300, zoom: 100 }`):

```ts
describe("OpeningShape — window glazing symbol", () => {
  it("renders two window-sym lines offset toward the interior by default", () => {
    setup({ opening: makeWindow({ offset: 1, width: 1 }) });
    const lines = target.querySelectorAll("line.window-sym");
    expect(lines).toHaveLength(2);
    // wall runs along +x, thickness 0.1 -> "in" perpendicular is world +y (screen y increases).
    expect(Number((lines[0] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(303, 5);
    expect(Number((lines[1] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(301, 5);
  });

  it("offsets both lines toward the exterior when windowSide is out", () => {
    setup({ opening: makeWindow({ offset: 1, width: 1, windowSide: "out" }) });
    const lines = target.querySelectorAll("line.window-sym");
    expect(Number((lines[0] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(297, 5);
    expect(Number((lines[1] as SVGLineElement).getAttribute("y1"))).toBeCloseTo(299, 5);
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts -t "window glazing symbol"`
Expected: FAIL (only one `.window-sym` line exists today, at the centerline).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/OpeningShape.svelte`, add a new `$derived.by` block near `shutterOverlayPoints` (after it, before `gapPoints` or `doorData` — placement doesn't matter, just keep it with the other derived geometry):

```ts
  const windowGlazingLines = $derived.by(() => {
    if (opening.type !== "window" || dir.length < 1e-9) return null;
    const perpIn = { x: -dir.y, y: dir.x };
    const perpOut = { x: dir.y, y: -dir.x };
    const side = opening.windowSide ?? "in";
    const perp = side === "out" ? perpOut : perpIn;
    const majorOffset = thickness * 0.3;
    const minorOffset = thickness * 0.1;
    const offsetLine = (mag: number) => {
      const a = { x: wp1.x + perp.x * mag, y: wp1.y + perp.y * mag };
      const b = { x: wp2.x + perp.x * mag, y: wp2.y + perp.y * mag };
      return { p1: worldToScreen(a, viewport), p2: worldToScreen(b, viewport) };
    };
    return { major: offsetLine(majorOffset), minor: offsetLine(minorOffset) };
  });
```

Replace the window branch in the template:

```svelte
  {#if opening.type === "window" && windowGlazingLines}
    <line
      class="window-sym"
      x1={windowGlazingLines.major.p1.x}
      y1={windowGlazingLines.major.p1.y}
      x2={windowGlazingLines.major.p2.x}
      y2={windowGlazingLines.major.p2.y}
      stroke={strokeColor}
      stroke-width="3"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
    <line
      class="window-sym"
      x1={windowGlazingLines.minor.p1.x}
      y1={windowGlazingLines.minor.p1.y}
      x2={windowGlazingLines.minor.p2.x}
      y2={windowGlazingLines.minor.p2.y}
      stroke={strokeColor}
      stroke-width="1.5"
      onclick={handleClick}
      role="button"
      tabindex="0"
    />
    {#if shutterOverlayPoints}
      <polygon points={shutterOverlayPoints} fill="var(--canvas-shutter-fill)" class="shutter-overlay" />
    {/if}
  {:else if opening.type === "door" && doorData}
```

(Only the window branch changes; leave the `{:else if opening.type === "door" && doorData}` branch and everything after it as-is for this task — Task 6 rewrites the door branch.)

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts`
Expected: PASS — including all pre-existing "HA sensor color" and "shutter overlay" tests, since they only call `target.querySelector("line.window-sym")` (first match = the major line, same `stroke`/`title` logic as before) and don't count elements or check exact coordinates.

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts test/App.test.ts`
Expected: PASS — these also only use `querySelector`/`querySelectorAll(...).length > 0` against `.window-sym`, not exact counts or coordinates.

- [ ] **Step 5: Commit**

```bash
git add packages/editor/src/lib/components/OpeningShape.svelte packages/editor/test/OpeningShape.test.ts
git commit -m "feat(editor): render window glazing as a double line offset by in/out"
```

---

### Task 6: `OpeningShape` — per-`doorKind` door rendering

**Files:**
- Modify: `packages/editor/src/lib/components/OpeningShape.svelte`
- Test: `packages/editor/test/OpeningShape.test.ts`

**Interfaces:**
- Consumes: `Opening.doorKind` (Task 2), `chooseSweepFlag` (already imported from `@myhome/geometry`).
- Produces: no prop changes — rendering-only.

- [ ] **Step 1: Write the failing tests**

Add to `packages/editor/test/OpeningShape.test.ts`. First add a `makeDoor` helper near `makeWindow` (top of file):

```ts
function makeDoor(overrides: Partial<Opening> = {}): Opening {
  return { id: "o2", wallId: "w1", type: "door", offset: 1, width: 0.9, ...overrides };
}
```

Then a new `describe` block:

```ts
describe("OpeningShape — door kind rendering", () => {
  it("renders one leaf/arc pair for hinged (default) doorKind", () => {
    setup({ opening: makeDoor({ swing: "left-in" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(1);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(1);
  });

  it("renders two leaf/arc pairs for swinging (battante) doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "swinging", swing: "left-in" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(2);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(2);
  });

  it("renders a sliding bar with no arc for sliding doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "sliding" }) });
    expect(target.querySelectorAll("line.door-leaf")).toHaveLength(0);
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(0);
    expect(target.querySelectorAll("line.door-sliding")).toHaveLength(1);
  });

  it("renders hatch ticks with no arc for garage doorKind", () => {
    setup({ opening: makeDoor({ doorKind: "garage" }) });
    expect(target.querySelectorAll("path.door-arc")).toHaveLength(0);
    expect(target.querySelectorAll("line.door-garage")).toHaveLength(5);
  });

  it("colors sliding and garage doors with the same strokeColor logic as hinged", () => {
    setup({ opening: makeDoor({ doorKind: "sliding" }), selected: true });
    const line = target.querySelector("line.door-sliding") as SVGLineElement;
    expect(line.getAttribute("stroke")).toBe("var(--canvas-wall-selected)");
  });
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts -t "door kind rendering"`
Expected: FAIL (`doorKind` is ignored today; every door renders exactly one `.door-leaf`/`.door-arc` pair regardless of kind, and `.door-sliding`/`.door-garage` don't exist).

- [ ] **Step 3: Implement**

In `packages/editor/src/lib/components/OpeningShape.svelte`, replace the existing `doorData` derived block with:

```ts
  const doorKind = $derived.by(() => opening.type === "door" ? (opening.doorKind ?? "hinged") : "hinged");

  const hingedOrSwingingData = $derived.by(() => {
    if (opening.type !== "door" || (doorKind !== "hinged" && doorKind !== "swinging")) return null;
    const width = clampedTo - clampedFrom;
    if (width < 1e-9) return null;
    const swing = opening.swing ?? "left-in";
    const isLeft = swing === "left-in" || swing === "left-out";
    const hingeWorld = isLeft ? wp1 : wp2;
    const otherWorld = isLeft ? wp2 : wp1;
    const other = worldToScreen(otherWorld, viewport);
    const radius = width * viewport.zoom;
    const perpIn = { x: -dir.y, y: dir.x };
    const perpOut = { x: dir.y, y: -dir.x };

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

  const slidingBarData = $derived.by(() => {
    if (opening.type !== "door" || doorKind !== "sliding" || dir.length < 1e-9) return null;
    const perpOut = { x: dir.y, y: -dir.x };
    const mag = (thickness / 2) * 0.5;
    const a = { x: wp1.x + perpOut.x * mag, y: wp1.y + perpOut.y * mag };
    const b = { x: wp2.x + perpOut.x * mag, y: wp2.y + perpOut.y * mag };
    return { p1: worldToScreen(a, viewport), p2: worldToScreen(b, viewport) };
  });

  const garageTicksData = $derived.by(() => {
    if (opening.type !== "door" || doorKind !== "garage" || dir.length < 1e-9) return null;
    const tickCount = 5;
    const halfThick = thickness / 2;
    const perpFull = { x: -dir.y * halfThick, y: dir.x * halfThick };
    const ticks: { p1: { x: number; y: number }; p2: { x: number; y: number } }[] = [];
    for (let i = 0; i < tickCount; i++) {
      const t = i / (tickCount - 1);
      const cx = wp1.x + (wp2.x - wp1.x) * t;
      const cy = wp1.y + (wp2.y - wp1.y) * t;
      ticks.push({
        p1: worldToScreen({ x: cx + perpFull.x, y: cy + perpFull.y }, viewport),
        p2: worldToScreen({ x: cx - perpFull.x, y: cy - perpFull.y }, viewport),
      });
    }
    return ticks;
  });
```

Replace the door branch in the template (the `{:else if opening.type === "door" && doorData}` block from Task 5):

```svelte
  {:else if opening.type === "door" && hingedOrSwingingData}
    {#each hingedOrSwingingData.variants as v}
      <line
        class="door-leaf"
        x1={v.hinge.x}
        y1={v.hinge.y}
        x2={v.openEnd.x}
        y2={v.openEnd.y}
        stroke={strokeColor}
        stroke-width="2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      >
        {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
      </line>
      <path
        class="door-arc"
        d="M {v.other.x} {v.other.y} A {v.radius} {v.radius} 0 0 {v.sweep} {v.openEnd.x} {v.openEnd.y}"
        fill="none"
        stroke={strokeColor}
        stroke-width="1"
        stroke-dasharray="4 2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      />
    {/each}
  {:else if opening.type === "door" && slidingBarData}
    <line
      class="door-sliding"
      x1={slidingBarData.p1.x}
      y1={slidingBarData.p1.y}
      x2={slidingBarData.p2.x}
      y2={slidingBarData.p2.y}
      stroke={strokeColor}
      stroke-width="4"
      onclick={handleClick}
      role="button"
      tabindex="0"
    >
      {#if sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
    </line>
  {:else if opening.type === "door" && garageTicksData}
    {#each garageTicksData as t, i (i)}
      <line
        class="door-garage"
        x1={t.p1.x}
        y1={t.p1.y}
        x2={t.p2.x}
        y2={t.p2.y}
        stroke={strokeColor}
        stroke-width="2"
        onclick={handleClick}
        role="button"
        tabindex="0"
      >
        {#if i === 0 && sensorStatus === "unavailable"}<title>{$_('floorPlan.openingPanel.sensorUnavailable')}</title>{/if}
      </line>
    {/each}
  {/if}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd packages/editor && npx vitest run test/OpeningShape.test.ts`
Expected: PASS

Run: `cd packages/editor && npx vitest run test/Canvas.test.ts test/App.test.ts`
Expected: PASS — `Canvas.test.ts`'s door test uses `swing: "left-in"` with no `doorKind`, which still hits the `hingedOrSwingingData` branch with exactly one variant, so `line.door-leaf`/`path.door-arc` still render as before.

- [ ] **Step 5: Run full editor and geometry test suites**

Run: `cd packages/editor && npx vitest run`
Run: `cd packages/geometry && npx vitest run`
Expected: PASS (no regressions elsewhere).

- [ ] **Step 6: Commit**

```bash
git add packages/editor/src/lib/components/OpeningShape.svelte packages/editor/test/OpeningShape.test.ts
git commit -m "feat(editor): render door symbols per doorKind (hinged/swinging/sliding/garage)"
```

---

## Final verification

- [ ] Run: `cd packages/backend && python -m pytest -v` — full backend suite passes.
- [ ] Run: `cd packages/geometry && npx tsc --noEmit && npx vitest run` — full geometry suite passes.
- [ ] Run: `cd packages/editor && npx tsc --noEmit && npx vitest run` — full editor suite passes.
