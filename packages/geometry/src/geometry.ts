import type { Point } from "./types";

export const EPSILON = 1e-6;

export function pointsEqual(a: Point, b: Point, epsilon = EPSILON): boolean {
  return Math.abs(a.x - b.x) < epsilon && Math.abs(a.y - b.y) < epsilon;
}

/**
 * Returns the intersection point of segments (p1,p2) and (p3,p4) if they
 * cross at a point strictly interior to BOTH segments, else null.
 * Endpoint-touching and collinear-overlap cases are deliberately excluded
 * here; those are handled by pointOnSegmentInterior.
 */
export function segmentsIntersection(
  p1: Point,
  p2: Point,
  p3: Point,
  p4: Point
): Point | null {
  const d1x = p2.x - p1.x;
  const d1y = p2.y - p1.y;
  const d2x = p4.x - p3.x;
  const d2y = p4.y - p3.y;
  const denom = d1x * d2y - d1y * d2x;
  if (Math.abs(denom) < EPSILON) return null;

  const t = ((p3.x - p1.x) * d2y - (p3.y - p1.y) * d2x) / denom;
  const u = ((p3.x - p1.x) * d1y - (p3.y - p1.y) * d1x) / denom;
  const eps = 1e-9;
  if (t > eps && t < 1 - eps && u > eps && u < 1 - eps) {
    return { x: p1.x + t * d1x, y: p1.y + t * d1y };
  }
  return null;
}

/**
 * Returns true if point p lies strictly in the interior of segment [a,b]
 * (collinear with, and strictly between, the endpoints).
 */
export function pointOnSegmentInterior(p: Point, a: Point, b: Point): boolean {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < EPSILON) return false;

  const cross = dx * (p.y - a.y) - dy * (p.x - a.x);
  if (Math.abs(cross) > EPSILON * Math.sqrt(lenSq)) return false;

  const t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  const eps = 1e-9;
  return t > eps && t < 1 - eps;
}
