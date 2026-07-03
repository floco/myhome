import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { createHouseStore } from "../src/lib/houseStore.svelte";
import type { HouseDocument } from "@myhome/geometry";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetchStub(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    statusText: status === 404 ? "Not Found" : "OK",
    json: async () => body,
  });
}

function makeDoc(floorId = "f1"): HouseDocument {
  return {
    version: 1,
    house: { name: "Test", units: "m", gridSnap: 0.1 },
    floors: [{ id: floorId, name: "Ground", order: 0, walls: [], openings: [], rooms: [] }],
  };
}

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("houseStore — initial state (no saved doc)", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  it("starts with the sample floor and detects rooms", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.floors.length).toBe(1);
    expect(store.floor.rooms.length).toBe(2);
  });

  it("currentFloorId matches the single floor id", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.currentFloorId).toBe(store.floors[0].id);
  });

  it("loaded becomes true after init", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
  });
});

describe("houseStore — loading from API", () => {
  it("replaces sample state with API data when fetch succeeds", async () => {
    vi.stubGlobal("fetch", makeFetchStub(200, makeDoc("api-floor")));
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.floors[0].id).toBe("api-floor");
    expect(store.currentFloorId).toBe("api-floor");
    expect(store.loaded).toBe(true);
    expect(store.loadError).toBeNull();
  });

  it("sets loadError on fetch failure, still marks loaded", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network error");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createHouseStore();
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("houseStore — floor management", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  it("addFloor adds a new empty floor and switches to it", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    const before = store.floors.length;
    store.addFloor("First Floor");
    expect(store.floors.length).toBe(before + 1);
    const newFloor = store.floors[store.floors.length - 1];
    expect(newFloor.name).toBe("First Floor");
    expect(store.currentFloorId).toBe(newFloor.id);
    expect(store.floor.walls.length).toBe(0);
  });

  it("switchFloor changes the active floor", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(groundId);
    expect(store.currentFloorId).toBe(groundId);
    store.switchFloor(upstairs);
    expect(store.currentFloorId).toBe(upstairs);
  });

  it("renameFloor changes the floor name", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    const id = store.floors[0].id;
    store.renameFloor(id, "Basement");
    expect(store.floors.find((f) => f.id === id)?.name).toBe("Basement");
  });

  it("removeFloor removes floor and switches to adjacent floor", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addFloor("Upstairs");
    const upstairs = store.floors[store.floors.length - 1].id;
    const groundId = store.floors[0].id;
    store.switchFloor(upstairs);
    store.removeFloor(upstairs);
    expect(store.floors.some((f) => f.id === upstairs)).toBe(false);
    expect(store.currentFloorId).toBe(groundId);
  });

  it("cannot remove the last floor", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    const id = store.floors[0].id;
    store.removeFloor(id);
    expect(store.floors.length).toBe(1);
  });
});

describe("houseStore — floor isolation", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  it("walls added on one floor do not appear on another floor", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    const groundId = store.floors[0].id;
    store.addFloor("Upstairs");
    store.switchFloor(groundId);
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    const upstairsId = store.floors[1].id;
    store.switchFloor(upstairsId);
    expect(store.floor.walls.length).toBe(0);
  });
});

describe("houseStore — undo/redo", () => {
  beforeEach(() => {
    vi.stubGlobal("fetch", makeFetchStub(404));
  });

  it("undo restores state before addWall", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    expect(store.floor.walls.length).toBeGreaterThan(0);
    store.undo();
    expect(store.floor.walls.find((w) => w.id === "w1")).toBeUndefined();
  });

  it("redo re-applies undone addWall", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    store.undo();
    store.redo();
    expect(store.floor.walls.find((w) => w.id === "w1")).toBeDefined();
  });

  it("hasUndo is false initially, true after mutation", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    expect(store.hasUndo).toBe(false);
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    expect(store.hasUndo).toBe(true);
  });

  it("hasRedo is true after undo", async () => {
    const store = createHouseStore(getHomeId);
    await tick();
    store.addWall({ id: "w1", start: { x: 0, y: 0 }, end: { x: 5, y: 0 }, type: "wall" });
    store.undo();
    expect(store.hasRedo).toBe(true);
  });
});

describe("houseStore — save", () => {
  it("save calls PUT /api/homes/{homeId}/house with current state", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();

    const putFetch = vi.fn().mockResolvedValue({ ok: true, status: 204 });
    vi.stubGlobal("fetch", putFetch);
    await store.save();

    expect(putFetch).toHaveBeenCalledWith(
      `/api/homes/${HOME}/house`,
      expect.objectContaining({ method: "PUT" })
    );
    const body = JSON.parse(putFetch.mock.calls[0][1].body);
    expect(body.version).toBe(1);
    expect(Array.isArray(body.floors)).toBe(true);
  });

  it("save throws on non-OK response", async () => {
    vi.stubGlobal("fetch", makeFetchStub(404));
    const store = createHouseStore(getHomeId);
    await tick();

    vi.stubGlobal("fetch", makeFetchStub(500));
    await expect(store.save()).rejects.toThrow();
  });

  it("save does nothing when no homeId provided", async () => {
    vi.stubGlobal("fetch", vi.fn());
    const store = createHouseStore();
    await tick();
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    await store.save();
    expect(fetchFn).not.toHaveBeenCalled();
  });
});
