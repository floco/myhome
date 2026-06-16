import { detectRooms, matchRooms, pointsEqual } from "@myhome/geometry";
import type { Floor, Wall, Opening, Room, Point } from "@myhome/geometry";
import { createSampleFloor } from "./sampleFloor";

export const STORAGE_KEY = "myhome.editor.floor";
const PERSIST_DEBOUNCE_MS = 300;
const MAX_HISTORY = 50;

function cloneFloor(f: Floor): Floor {
  return JSON.parse(JSON.stringify(f));
}

function loadFloor(): Floor {
  if (typeof localStorage === "undefined") return createSampleFloor();
  const raw = localStorage.getItem(STORAGE_KEY);
  if (!raw) return createSampleFloor();
  try {
    const parsed = JSON.parse(raw);
    if (
      !parsed ||
      typeof parsed !== "object" ||
      !Array.isArray(parsed.walls) ||
      !Array.isArray(parsed.rooms) ||
      !Array.isArray(parsed.openings)
    ) {
      return createSampleFloor();
    }
    return parsed as Floor;
  } catch {
    return createSampleFloor();
  }
}

export function createFloorStore() {
  const floor = $state<Floor>(loadFloor());
  let persistTimer: ReturnType<typeof setTimeout> | undefined;

  const undoStack: Floor[] = [];
  const redoStack: Floor[] = [];
  let undoCount = $state(0);
  let redoCount = $state(0);

  function saveSnapshot(): void {
    undoStack.push(cloneFloor(floor));
    if (undoStack.length > MAX_HISTORY) undoStack.shift();
    redoStack.length = 0;
    undoCount = undoStack.length;
    redoCount = 0;
  }

  function applyFloor(snapshot: Floor): void {
    floor.walls = snapshot.walls;
    floor.openings = snapshot.openings;
    floor.rooms = snapshot.rooms;
  }

  function undo(): void {
    const prev = undoStack.pop();
    if (!prev) return;
    redoStack.push(cloneFloor(floor));
    applyFloor(prev);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function redo(): void {
    const next = redoStack.pop();
    if (!next) return;
    undoStack.push(cloneFloor(floor));
    applyFloor(next);
    undoCount = undoStack.length;
    redoCount = redoStack.length;
    persist();
  }

  function recomputeRooms(): void {
    const detected = detectRooms(floor.walls);
    const { rooms } = matchRooms(detected, floor.rooms);
    floor.rooms = rooms.filter((r) => r.polygon !== null);
  }

  function persist(): void {
    if (typeof localStorage === "undefined") return;
    if (persistTimer) clearTimeout(persistTimer);
    persistTimer = setTimeout(() => {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(floor));
    }, PERSIST_DEBOUNCE_MS);
  }

  function commitWalls(): void {
    recomputeRooms();
    persist();
  }

  function addWall(wall: Wall): void {
    saveSnapshot();
    floor.walls.push(wall);
    commitWalls();
  }

  function removeWall(id: string): void {
    saveSnapshot();
    floor.walls = floor.walls.filter((w) => w.id !== id);
    floor.openings = floor.openings.filter((o) => o.wallId !== id);
    commitWalls();
  }

  /**
   * Moves every wall endpoint equal to `from` (within @myhome/geometry's
   * EPSILON) to `to`, so segments sharing a corner stay joined.
   */
  function moveSharedPoint(from: Point, to: Point, opts?: { skipHistory?: boolean }): void {
    if (!opts?.skipHistory) saveSnapshot();
    for (const wall of floor.walls) {
      if (pointsEqual(wall.start, from)) wall.start = to;
      if (pointsEqual(wall.end, from)) wall.end = to;
    }
    commitWalls();
  }

  function addOpening(opening: Opening): void {
    saveSnapshot();
    floor.openings.push(opening);
    persist();
  }

  function removeOpening(id: string): void {
    saveSnapshot();
    floor.openings = floor.openings.filter((o) => o.id !== id);
    persist();
  }

  function updateOpening(
    id: string,
    patch: Partial<Pick<Opening, "offset" | "width" | "swing">>,
    opts?: { skipHistory?: boolean }
  ): void {
    if (!opts?.skipHistory) saveSnapshot();
    const opening = floor.openings.find((o) => o.id === id);
    if (!opening) return;
    if (patch.offset !== undefined) opening.offset = patch.offset;
    if (patch.width !== undefined) opening.width = patch.width;
    if (patch.swing !== undefined) opening.swing = patch.swing;
    persist();
  }

  function updateRoom(id: string, patch: Partial<Pick<Room, "label" | "haAreaId">>): void {
    saveSnapshot();
    const room = floor.rooms.find((r) => r.id === id);
    if (!room) return;
    if (patch.label !== undefined) room.label = patch.label;
    if (patch.haAreaId !== undefined) room.haAreaId = patch.haAreaId;
    persist();
  }

  function openingOverlaps(
    wallId: string,
    excludeId: string | null,
    from: number,
    to: number
  ): boolean {
    return floor.openings.some(
      (o) =>
        o.wallId === wallId &&
        o.id !== excludeId &&
        from < o.offset + o.width &&
        to > o.offset
    );
  }

  recomputeRooms();

  return {
    get floor() { return floor; },
    get hasUndo() { return undoCount > 0; },
    get hasRedo() { return redoCount > 0; },
    saveSnapshot,
    undo,
    redo,
    addWall,
    removeWall,
    moveSharedPoint,
    addOpening,
    removeOpening,
    updateOpening,
    updateRoom,
    openingOverlaps,
  };
}
