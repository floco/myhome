import type { Point } from "@myhome/geometry";

/** World-space grid spacing in meters, matching Spec 1's House.gridSnap default. */
export const GRID_SIZE = 0.1;

/** Fixed screen-space snap radius in pixels, independent of zoom. */
export const SNAP_RADIUS_PX = 12;

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
