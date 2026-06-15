import type { Point, Wall, WallType } from "@myhome/geometry";
import { pointsEqual } from "@myhome/geometry";
import { snapToGrid, findSnapPoint } from "./geometry-helpers";

export interface SnapResult {
  point: Point;
  snappedToExisting: boolean;
  closesLoop: boolean;
}

/**
 * Computes the snapped placement point for the cursor during wall/divider
 * drawing: snaps to an existing wall endpoint or the current chain's own
 * points first (within `snapRadiusWorld`), falling back to the grid. Also
 * reports whether this point would close the in-progress chain.
 */
export function computeSnap(
  cursorWorld: Point,
  existingPoints: Point[],
  chainPoints: Point[],
  snapRadiusWorld: number,
): SnapResult {
  const candidates = [...existingPoints, ...chainPoints];
  const snapped = findSnapPoint(cursorWorld, candidates, snapRadiusWorld);
  const point = snapped ?? snapToGrid(cursorWorld);
  const closesLoop = chainPoints.length > 0 && pointsEqual(point, chainPoints[0]);
  return { point, snappedToExisting: snapped !== null, closesLoop };
}

/**
 * Given the current chain and a newly-placed point, returns the new wall
 * segment to add (or null if the click should be ignored as the first
 * point of a chain or a zero-length segment) and whether the chain should
 * end because the loop closed.
 */
export function placePoint(
  chainPoints: Point[],
  newPoint: Point,
  type: WallType,
  idFactory: () => string,
): { segment: Wall | null; chainEnds: boolean } {
  if (chainPoints.length === 0) {
    return { segment: null, chainEnds: false };
  }

  const prev = chainPoints[chainPoints.length - 1];
  if (pointsEqual(prev, newPoint)) {
    return { segment: null, chainEnds: false };
  }

  const segment: Wall = {
    id: idFactory(),
    type,
    start: prev,
    end: newPoint,
    ...(type === "wall" ? { thickness: 0.1 } : {}),
  };

  const chainEnds = pointsEqual(newPoint, chainPoints[0]);
  return { segment, chainEnds };
}

/** All wall/divider endpoints in the floor, for point-snapping. */
export function allEndpoints(walls: Wall[]): Point[] {
  const points: Point[] = [];
  for (const w of walls) {
    points.push(w.start, w.end);
  }
  return points;
}
