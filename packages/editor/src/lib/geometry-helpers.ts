import type { Point, Wall } from "@myhome/geometry";
import { pointsEqual } from "@myhome/geometry";

/** World-space grid spacing in meters, matching Spec 1's House.gridSnap default. */
export const GRID_SIZE = 0.1;

/** Fixed screen-space snap radius in pixels, independent of zoom. */
export const SNAP_RADIUS_PX = 12;

/** Fixed screen-space hit radius for wall detection in pixels, independent of zoom. */
export const HIT_RADIUS_PX = 30;

function roundTo(value: number, decimals: number): number {
  const factor = 10 ** decimals;
  return Math.round(value * factor) / factor;
}

/** Snaps a world-space point to the nearest grid intersection. */
export function snapToGrid(p: Point, gridSize: number = GRID_SIZE): Point {
  return {
    x: roundTo(Math.round(p.x / gridSize) * gridSize, 6),
    y: roundTo(Math.round(p.y / gridSize) * gridSize, 6),
  };
}

export function distance(a: Point, b: Point): number {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

/**
 * Finds the closest point in `candidates` to `target` that is within
 * `radius` (world units). Returns null if none are within range.
 */
export function findSnapPoint(target: Point, candidates: Point[], radius: number): Point | null {
  let closest: Point | null = null;
  let closestDist = radius;
  for (const candidate of candidates) {
    const d = distance(target, candidate);
    if (d <= closestDist) {
      closest = candidate;
      closestDist = d;
    }
  }
  return closest;
}

/**
 * Projects `cursor` onto each "wall"-type segment. Returns the closest wall
 * and its grid-snapped offset if within `threshold` (world units), or null.
 */
export function hitTestWall(
  cursor: Point,
  walls: Wall[],
  threshold: number
): { wall: Wall; offset: number } | null {
  let bestDist = threshold;
  let bestWall: Wall | null = null;
  let bestOffset = 0;

  for (const wall of walls) {
    if (wall.type !== "wall") continue;
    const dx = wall.end.x - wall.start.x;
    const dy = wall.end.y - wall.start.y;
    const length = Math.hypot(dx, dy);
    if (length < 1e-9) continue;
    const dirX = dx / length;
    const dirY = dy / length;
    const cx = cursor.x - wall.start.x;
    const cy = cursor.y - wall.start.y;
    const t = Math.max(0, Math.min(length, cx * dirX + cy * dirY));
    const projX = wall.start.x + dirX * t;
    const projY = wall.start.y + dirY * t;
    const dist = Math.hypot(cursor.x - projX, cursor.y - projY);
    if (dist < bestDist) {
      bestDist = dist;
      bestWall = wall;
      bestOffset = Math.max(0, Math.min(length, Math.round(t / GRID_SIZE) * GRID_SIZE));
    }
  }

  return bestWall ? { wall: bestWall, offset: bestOffset } : null;
}

/**
 * Returns the single other wall-type wall that shares an endpoint with target.
 * Returns null if zero or more than one wall shares that endpoint
 * (T-junction / no connection → fall back to a flat cap).
 */
export function findAdjacentWall(walls: Wall[], target: Wall, atEnd: boolean): Wall | null {
  const P = atEnd ? target.end : target.start;
  let found: Wall | null = null;
  let count = 0;
  for (const w of walls) {
    if (w.id === target.id || w.type !== "wall") continue;
    if (pointsEqual(w.start, P) || pointsEqual(w.end, P)) {
      found = w;
      count++;
    }
  }
  return count === 1 ? found : null;
}
