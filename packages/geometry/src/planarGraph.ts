import type { Point } from "./types";
import { pointsEqual, segmentsIntersection, pointOnSegmentInterior } from "./geometry";

export interface InputSegment {
  start: Point;
  end: Point;
}

export interface PlanarGraph {
  nodes: Point[];
  /** adjacency[i] = neighbor node indices, sorted by angle ascending (atan2) */
  adjacency: number[][];
}

function splitSegment(seg: InputSegment, splitPoints: Point[]): InputSegment[] {
  const dx = seg.end.x - seg.start.x;
  const dy = seg.end.y - seg.start.y;
  const lenSq = dx * dx + dy * dy;

  const unique: { p: Point; t: number }[] = [];
  for (const p of splitPoints) {
    if (unique.some((u) => pointsEqual(u.p, p))) continue;
    const t = ((p.x - seg.start.x) * dx + (p.y - seg.start.y) * dy) / lenSq;
    unique.push({ p, t });
  }
  unique.sort((a, b) => a.t - b.t);

  const chain: Point[] = [seg.start, ...unique.map((u) => u.p), seg.end];
  const result: InputSegment[] = [];
  for (let i = 0; i < chain.length - 1; i++) {
    if (!pointsEqual(chain[i], chain[i + 1])) {
      result.push({ start: chain[i], end: chain[i + 1] });
    }
  }
  return result;
}

/**
 * Builds a planar graph from a set of line segments: segments are split at
 * every point where they cross or touch another segment, then deduplicated
 * into a node/adjacency representation.
 */
export function buildPlanarGraph(segments: InputSegment[]): PlanarGraph {
  const splitPoints: Point[][] = segments.map(() => []);

  for (let i = 0; i < segments.length; i++) {
    for (let j = i + 1; j < segments.length; j++) {
      const a = segments[i];
      const b = segments[j];

      const cross = segmentsIntersection(a.start, a.end, b.start, b.end);
      if (cross) {
        splitPoints[i].push(cross);
        splitPoints[j].push(cross);
      }

      for (const p of [a.start, a.end]) {
        if (pointOnSegmentInterior(p, b.start, b.end)) splitPoints[j].push(p);
      }
      for (const p of [b.start, b.end]) {
        if (pointOnSegmentInterior(p, a.start, a.end)) splitPoints[i].push(p);
      }
    }
  }

  const subSegments: InputSegment[] = [];
  for (let i = 0; i < segments.length; i++) {
    subSegments.push(...splitSegment(segments[i], splitPoints[i]));
  }

  const nodes: Point[] = [];
  function getNodeIndex(p: Point): number {
    const idx = nodes.findIndex((n) => pointsEqual(n, p));
    if (idx !== -1) return idx;
    nodes.push(p);
    return nodes.length - 1;
  }

  const edgeSet = new Set<string>();
  const edges: [number, number][] = [];
  for (const seg of subSegments) {
    const ai = getNodeIndex(seg.start);
    const bi = getNodeIndex(seg.end);
    if (ai === bi) continue;
    const key = ai < bi ? `${ai}-${bi}` : `${bi}-${ai}`;
    if (edgeSet.has(key)) continue;
    edgeSet.add(key);
    edges.push([ai, bi]);
  }

  const adjacency: number[][] = nodes.map(() => []);
  for (const [a, b] of edges) {
    adjacency[a].push(b);
    adjacency[b].push(a);
  }
  for (let i = 0; i < nodes.length; i++) {
    adjacency[i].sort((p, q) => {
      const angleP = Math.atan2(nodes[p].y - nodes[i].y, nodes[p].x - nodes[i].x);
      const angleQ = Math.atan2(nodes[q].y - nodes[i].y, nodes[q].x - nodes[i].x);
      return angleP - angleQ;
    });
  }

  return { nodes, adjacency };
}
