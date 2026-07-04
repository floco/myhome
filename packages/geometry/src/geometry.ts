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

/** Signed area via the shoelace formula. Positive = counter-clockwise winding. */
export function polygonSignedArea(points: Point[]): number {
  let sum = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];
    sum += a.x * b.y - b.x * a.y;
  }
  return sum / 2;
}

export function polygonArea(points: Point[]): number {
  return Math.abs(polygonSignedArea(points));
}

/** Area-weighted centroid of a simple polygon. */
export function polygonCentroid(points: Point[]): Point {
  let cx = 0;
  let cy = 0;
  let area = 0;
  const n = points.length;
  for (let i = 0; i < n; i++) {
    const a = points[i];
    const b = points[(i + 1) % n];
    const cross = a.x * b.y - b.x * a.y;
    area += cross;
    cx += (a.x + b.x) * cross;
    cy += (a.y + b.y) * cross;
  }
  area = area / 2;
  if (Math.abs(area) < 1e-12) {
    const avgX = points.reduce((s, p) => s + p.x, 0) / n;
    const avgY = points.reduce((s, p) => s + p.y, 0) / n;
    return { x: avgX, y: avgY };
  }
  cx /= 6 * area;
  cy /= 6 * area;
  return { x: cx, y: cy };
}

/**
 * Computes the two miter corner points where two walls share endpoint P.
 * dirA and dirB are unit vectors along each wall's centerline (start → end).
 * halfThickA / halfThickB are wall.thickness / 2 for each wall.
 *
 * Returns { plus, minus } — intersections of the +perp and -perp edge lines —
 * or null if walls are parallel, or if the miter would spike further than
 * 8 × max(halfThickA, halfThickB) from P (very acute angle fallback).
 */
export function computeMiterCorners(
  P: Point,
  dirA: Point,
  halfThickA: number,
  dirB: Point,
  halfThickB: number,
): { plus: Point; minus: Point } | null {
  const pAx = -dirA.y * halfThickA;
  const pAy = dirA.x * halfThickA;
  const pBx = -dirB.y * halfThickB;
  const pBy = dirB.x * halfThickB;

  const plus = _linesIntersect(
    { x: P.x + pAx, y: P.y + pAy }, dirA,
    { x: P.x + pBx, y: P.y + pBy }, dirB,
  );
  const minus = _linesIntersect(
    { x: P.x - pAx, y: P.y - pAy }, dirA,
    { x: P.x - pBx, y: P.y - pBy }, dirB,
  );
  if (!plus || !minus) return null;

  const limit = 8 * Math.max(halfThickA, halfThickB);
  if (Math.hypot(plus.x - P.x, plus.y - P.y) > limit) return null;

  return { plus, minus };
}

/** Intersection of two infinite lines (point + direction). Internal helper. */
function _linesIntersect(p1: Point, d1: Point, p2: Point, d2: Point): Point | null {
  const det = d1.x * (-d2.y) - d1.y * (-d2.x);
  if (Math.abs(det) < 1e-9) return null;
  const dx = p2.x - p1.x;
  const dy = p2.y - p1.y;
  const t = (dx * (-d2.y) - dy * (-d2.x)) / det;
  return { x: p1.x + t * d1.x, y: p1.y + t * d1.y };
}

/** Ray-casting point-in-polygon test. */
export function pointInPolygon(point: Point, polygon: Point[]): boolean {
  let inside = false;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;
    if (
      yi > point.y !== yj > point.y &&
      point.x < ((xj - xi) * (point.y - yi)) / (yj - yi) + xi
    ) {
      inside = !inside;
    }
  }
  return inside;
}
