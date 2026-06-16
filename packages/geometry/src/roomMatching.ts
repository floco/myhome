import type { Point, Room } from "./types";
import { polygonArea, polygonCentroid, pointInPolygon } from "./geometry";
import type { DetectedRoom } from "./roomDetection";

export interface RoomMatchResult {
  /** All rooms after matching: previously-existing rooms that matched a
   *  detected polygon (keeping id/label/haAreaId, updated polygon+areaM2),
   *  newly-created rooms for unmatched detected polygons, and previously
   *  -existing rooms whose polygon disappeared (polygon: null). */
  rooms: Room[];
  /** Subset of `rooms` whose polygon disappeared in this pass. */
  unresolved: Room[];
}

/**
 * Matches newly-detected room polygons against the previous room list.
 *
 * A detected polygon matches an existing room if the detected polygon's
 * centroid falls inside that room's previous polygon. Matched rooms keep
 * their id/label/haAreaId. Unmatched detected polygons become new rooms
 * with a default label and no HA area. Existing rooms with no match keep
 * their id/label/haAreaId but get `polygon: null` and are reported in
 * `unresolved`.
 */
export function matchRooms(detected: DetectedRoom[], existing: Room[]): RoomMatchResult {
  const matchedExistingIds = new Set<string>();
  const rooms: Room[] = [];
  let newRoomCount = 0;

  for (const det of detected) {
    const centroid = polygonCentroid(det.polygon);
    const match = existing.find(
      (r) =>
        !matchedExistingIds.has(r.id) &&
        r.polygon !== null &&
        pointInPolygon(centroid, r.polygon)
    );

    if (match) {
      matchedExistingIds.add(match.id);
      rooms.push({
        ...match,
        polygon: det.polygon,
        areaM2: roundArea(det.polygon),
      });
    } else {
      newRoomCount++;
      rooms.push({
        id: crypto.randomUUID?.() ?? Math.random().toString(36).slice(2) + Date.now().toString(36),
        label: `Room ${newRoomCount}`,
        haAreaId: null,
        polygon: det.polygon,
        areaM2: roundArea(det.polygon),
      });
    }
  }

  const unresolved: Room[] = existing
    .filter((r) => !matchedExistingIds.has(r.id))
    .map((r) => ({ ...r, polygon: null }));

  return { rooms: [...rooms, ...unresolved], unresolved };
}

function roundArea(polygon: Point[]): number {
  return Math.round(polygonArea(polygon) * 100) / 100;
}
