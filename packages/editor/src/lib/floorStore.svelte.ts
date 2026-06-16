import { detectRooms, matchRooms, pointsEqual } from "@myhome/geometry";
import type { Floor, Wall, Point } from "@myhome/geometry";
import { createSampleFloor } from "./sampleFloor";

export const STORAGE_KEY = "myhome.editor.floor";
const PERSIST_DEBOUNCE_MS = 300;

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
    floor.walls.push(wall);
    commitWalls();
  }

  function removeWall(id: string): void {
    floor.walls = floor.walls.filter((w) => w.id !== id);
    commitWalls();
  }

  /**
   * Moves every wall endpoint equal to `from` (within @myhome/geometry's
   * EPSILON) to `to`, so segments sharing a corner stay joined.
   */
  function moveSharedPoint(from: Point, to: Point): void {
    for (const wall of floor.walls) {
      if (pointsEqual(wall.start, from)) wall.start = to;
      if (pointsEqual(wall.end, from)) wall.end = to;
    }
    commitWalls();
  }

  recomputeRooms();

  return {
    get floor() {
      return floor;
    },
    addWall,
    removeWall,
    moveSharedPoint,
  };
}
