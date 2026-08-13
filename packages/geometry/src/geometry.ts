import type { Point, Room } from "./types";

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

interface Bounds {
  minX: number;
  maxX: number;
  minY: number;
  maxY: number;
}

function polygonBounds(polygon: Point[]): Bounds {
  let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
  for (const p of polygon) {
    if (p.x < minX) minX = p.x;
    if (p.x > maxX) maxX = p.x;
    if (p.y < minY) minY = p.y;
    if (p.y > maxY) maxY = p.y;
  }
  return { minX, maxX, minY, maxY };
}

const CONTAINMENT_GRID_STEPS = 12;
const CONTAINMENT_THRESHOLD = 0.5;

/** Fraction (0-1) of `inner`'s own area, estimated via grid sampling, that lies inside `outer`. */
function estimateContainmentRatio(outer: Point[], inner: Point[]): number {
  const b = polygonBounds(inner);
  let total = 0;
  let contained = 0;
  for (let i = 0; i <= CONTAINMENT_GRID_STEPS; i++) {
    for (let j = 0; j <= CONTAINMENT_GRID_STEPS; j++) {
      const point = {
        x: b.minX + ((b.maxX - b.minX) * i) / CONTAINMENT_GRID_STEPS,
        y: b.minY + ((b.maxY - b.minY) * j) / CONTAINMENT_GRID_STEPS,
      };
      if (!pointInPolygon(point, inner)) continue;
      total++;
      if (pointInPolygon(point, outer)) contained++;
    }
  }
  return total === 0 ? 0 : contained / total;
}

function distanceToSegment(p: Point, a: Point, b: Point): number {
  const dx = b.x - a.x;
  const dy = b.y - a.y;
  const lenSq = dx * dx + dy * dy;
  if (lenSq < EPSILON) return Math.hypot(p.x - a.x, p.y - a.y);
  let t = ((p.x - a.x) * dx + (p.y - a.y) * dy) / lenSq;
  t = Math.max(0, Math.min(1, t));
  return Math.hypot(p.x - (a.x + t * dx), p.y - (a.y + t * dy));
}

function distanceToPolygon(point: Point, polygon: Point[]): number {
  let min = Infinity;
  const n = polygon.length;
  for (let i = 0, j = n - 1; i < n; j = i++) {
    min = Math.min(min, distanceToSegment(point, polygon[j], polygon[i]));
  }
  return min;
}

const LABEL_GRID_STEPS = 20;

/** Grid-samples `outer` for the point farthest (in min-distance terms) from every polygon in `children`, skipping points inside any child. Returns null if no valid point survives. */
function findOpenPoint(outer: Point[], children: Point[][]): Point | null {
  const b = polygonBounds(outer);
  let best: Point | null = null;
  let bestScore = -Infinity;
  for (let i = 0; i <= LABEL_GRID_STEPS; i++) {
    for (let j = 0; j <= LABEL_GRID_STEPS; j++) {
      const point = {
        x: b.minX + ((b.maxX - b.minX) * i) / LABEL_GRID_STEPS,
        y: b.minY + ((b.maxY - b.minY) * j) / LABEL_GRID_STEPS,
      };
      if (!pointInPolygon(point, outer)) continue;
      if (children.some((c) => pointInPolygon(point, c))) continue;
      const score = children.reduce((min, c) => Math.min(min, distanceToPolygon(point, c)), Infinity);
      if (score > bestScore) {
        bestScore = score;
        best = point;
      }
    }
  }
  return best;
}

/**
 * True if other rooms' polygons are substantially contained inside this
 * room's polygon (e.g. a garden boundary with a shed or pool drawn inside
 * it). Such a room's fill overlaps its children's, so callers should avoid
 * treating the whole fill as this room's click target.
 */
export function roomContainsOtherRooms(room: Room, allRooms: Room[]): boolean {
  if (!room.polygon) return false;
  return allRooms.some(
    (other) =>
      other.id !== room.id &&
      other.polygon &&
      estimateContainmentRatio(room.polygon!, other.polygon!) >= CONTAINMENT_THRESHOLD,
  );
}

/**
 * Where to draw a room's label. If other rooms' polygons are substantially
 * contained inside this room's polygon (a "zone" spanning child rooms), the
 * label is moved to the most open point of the zone's polygon that isn't
 * covered by any child room, instead of the zone's own (likely obscured)
 * centroid.
 */
export function computeLabelPosition(room: Room, allRooms: Room[]): Point {
  if (!room.polygon) return { x: 0, y: 0 };
  const children = allRooms
    .filter((other) => other.id !== room.id && other.polygon)
    .filter((other) => estimateContainmentRatio(room.polygon!, other.polygon!) >= CONTAINMENT_THRESHOLD)
    .map((other) => other.polygon!);

  if (children.length === 0) return polygonCentroid(room.polygon);

  return findOpenPoint(room.polygon, children) ?? polygonCentroid(room.polygon);
}
