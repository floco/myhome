import type { Opening, Room, Wall } from "./types";
import { pointInPolygon } from "./geometry";

/** How far (meters) to offset from the wall centerline when probing which room an opening borders. */
const ADJACENCY_EPSILON = 0.05;

/**
 * Finds the room(s) adjacent to an opening's position on its wall, by testing
 * points just off each side of the opening's midpoint against every room's
 * polygon. Returns 0 rooms for an opening on an unenclosed wall, 1 for the
 * common case (e.g. an exterior window), or 2 for an interior door shared by
 * two rooms.
 */
export function findAdjacentRooms(opening: Opening, wall: Wall, rooms: Room[]): Room[] {
  const dx = wall.end.x - wall.start.x;
  const dy = wall.end.y - wall.start.y;
  const length = Math.hypot(dx, dy);
  if (length < 1e-9) return [];
  const dirX = dx / length;
  const dirY = dy / length;

  const midAlongWall = opening.offset + opening.width / 2;
  const midWorld = { x: wall.start.x + dirX * midAlongWall, y: wall.start.y + dirY * midAlongWall };

  const perpX = -dirY * ADJACENCY_EPSILON;
  const perpY = dirX * ADJACENCY_EPSILON;
  const sideA = { x: midWorld.x + perpX, y: midWorld.y + perpY };
  const sideB = { x: midWorld.x - perpX, y: midWorld.y - perpY };

  const found: Room[] = [];
  for (const room of rooms) {
    if (!room.polygon) continue;
    if (pointInPolygon(sideA, room.polygon) || pointInPolygon(sideB, room.polygon)) {
      found.push(room);
    }
  }
  return found;
}
