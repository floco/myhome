import { detectRooms, matchRooms, pointsEqual } from "@myhome/geometry";
import type { Floor, Wall, Opening, Room, Point, House, HouseDocument } from "@myhome/geometry";
import { createSampleHouse } from "./sampleFloor";

const MAX_HISTORY = 50;

const DEFAULT_HOUSE: House = { name: "My Home", units: "m", gridSnap: 0.1 };

interface HouseState {
  floors: Floor[];
  currentFloorId: string;
}

function cloneState(s: HouseState): HouseState {
  return JSON.parse(JSON.stringify(s));
}

function genId(): string {
  return (crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36));
}

export function createHouseStore() {
  const sample = createSampleHouse();
  const floors = $state<Floor[]>(sample.floors);
  let currentFloorId = $state<string>(sample.currentFloorId);
  let house = $state<House>(DEFAULT_HOUSE);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  const undoStack: HouseState[] = [];
  const redoStack: HouseState[] = [];
  let undoCount = $state(0);
  let redoCount = $state(0);

  function getState(): HouseState {
    return { floors: floors as Floor[], currentFloorId };
  }

  function applyState(s: HouseState): void {
    if (s.floors.length === 0) return;
    floors.length = 0;
    for (const f of s.floors) floors.push(f);
    currentFloorId = s.currentFloorId;
  }

  function saveSnapshot(): void {
    undoStack.push(cloneState(getState()));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack.length = 0;
    undoCount = undoStack.length;
    redoCount = 0;
  }

  function undo(): void {
    const prev = undoStack.pop();
    if (!prev) return;
    redoStack.push(cloneState(getState()));
    applyState(prev);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
  }

  function redo(): void {
    const next = redoStack.pop();
    if (!next) return;
    undoStack.push(cloneState(getState()));
    applyState(next);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
  }

  function currentFloor(): Floor {
    return floors.find((f) => f.id === currentFloorId) ?? floors[0];
  }

  function recomputeRooms(): void {
    const floor = currentFloor();
    const detected = detectRooms(floor.walls);
    const { rooms } = matchRooms(detected, floor.rooms);
    floor.rooms = rooms.filter((r) => r.polygon !== null);
  }

  function commitWalls(): void {
    recomputeRooms();
  }

  // Floor management

  function addFloor(name: string): void {
    saveSnapshot();
    const maxOrder = floors.reduce((m, f) => Math.max(m, f.order), -1);
    const newFloor: Floor = {
      id: genId(),
      name,
      order: maxOrder + 1,
      walls: [],
      openings: [],
      rooms: [],
    };
    floors.push(newFloor);
    currentFloorId = newFloor.id;
  }

  function removeFloor(id: string): void {
    if (floors.length <= 1) return;
    saveSnapshot();
    const idx = floors.findIndex((f) => f.id === id);
    if (idx === -1) return;
    floors.splice(idx, 1);
    if (currentFloorId === id) {
      currentFloorId = floors[Math.max(0, idx - 1)].id;
    }
  }

  function renameFloor(id: string, name: string): void {
    const floor = floors.find((f) => f.id === id);
    if (!floor) return;
    saveSnapshot();
    floor.name = name;
  }

  function switchFloor(id: string): void {
    if (floors.some((f) => f.id === id)) {
      currentFloorId = id;
    }
  }

  // Floor mutations (forwarded to current floor)

  function addWall(wall: Wall): void {
    saveSnapshot();
    currentFloor().walls.push(wall);
    commitWalls();
  }

  function removeWall(id: string): void {
    saveSnapshot();
    const floor = currentFloor();
    floor.walls = floor.walls.filter((w) => w.id !== id);
    floor.openings = floor.openings.filter((o) => o.wallId !== id);
    commitWalls();
  }

  function moveSharedPoint(from: Point, to: Point, opts?: { skipHistory?: boolean }): void {
    if (!opts?.skipHistory) saveSnapshot();
    for (const wall of currentFloor().walls) {
      if (pointsEqual(wall.start, from)) wall.start = to;
      if (pointsEqual(wall.end, from)) wall.end = to;
    }
    commitWalls();
  }

  function addOpening(opening: Opening): void {
    saveSnapshot();
    currentFloor().openings.push(opening);
  }

  function removeOpening(id: string): void {
    saveSnapshot();
    const floor = currentFloor();
    floor.openings = floor.openings.filter((o) => o.id !== id);
  }

  function updateOpening(
    id: string,
    patch: Partial<Pick<Opening, "offset" | "width" | "swing">>,
    opts?: { skipHistory?: boolean }
  ): void {
    const opening = currentFloor().openings.find((o) => o.id === id);
    if (!opening) return;
    if (!opts?.skipHistory) saveSnapshot();
    if (patch.offset !== undefined) opening.offset = patch.offset;
    if (patch.width !== undefined) opening.width = patch.width;
    if (patch.swing !== undefined) opening.swing = patch.swing;
  }

  function updateRoom(id: string, patch: Partial<Pick<Room, "label" | "haAreaId">>): void {
    const room = currentFloor().rooms.find((r) => r.id === id);
    if (!room) return;
    saveSnapshot();
    if (patch.label !== undefined) room.label = patch.label;
    if (patch.haAreaId !== undefined) room.haAreaId = patch.haAreaId;
  }

  function openingOverlaps(wallId: string, excludeId: string | null, from: number, to: number): boolean {
    return currentFloor().openings.some(
      (o) => o.wallId === wallId && o.id !== excludeId && from < o.offset + o.width && to > o.offset
    );
  }

  // API load/save

  async function init(): Promise<void> {
    try {
      const resp = await fetch("/api/house");
      if (resp.status === 404) {
        // No saved document; keep sample house already in state
      } else if (!resp.ok) {
        throw new Error(`HTTP ${resp.status}`);
      } else {
        const doc: HouseDocument = await resp.json();
        house = doc.house;
        const newCurrentId = doc.floors[0]?.id ?? currentFloorId;
        applyState({ floors: doc.floors, currentFloorId: newCurrentId });
        for (const f of floors) {
          const detected = detectRooms(f.walls);
          const { rooms } = matchRooms(detected, f.rooms);
          f.rooms = rooms.filter((r) => r.polygon !== null);
        }
      }
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function save(): Promise<void> {
    const doc: HouseDocument = {
      version: 1,
      house: house as House,
      floors: floors as Floor[],
    };
    const resp = await fetch("/api/house", {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(doc),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
  }

  // Seed room detection on startup for sample floors
  for (const f of floors) {
    const detected = detectRooms(f.walls);
    const { rooms } = matchRooms(detected, f.rooms);
    f.rooms = rooms.filter((r) => r.polygon !== null);
  }

  // Start async load immediately
  init();

  return {
    get floor() { return currentFloor(); },
    get floors() { return floors as Floor[]; },
    get currentFloorId() { return currentFloorId; },
    get hasUndo() { return undoCount > 0; },
    get hasRedo() { return redoCount > 0; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    saveSnapshot,
    undo,
    redo,
    addFloor,
    removeFloor,
    renameFloor,
    switchFloor,
    addWall,
    removeWall,
    moveSharedPoint,
    addOpening,
    removeOpening,
    updateOpening,
    updateRoom,
    openingOverlaps,
    save,
    init,
  };
}
