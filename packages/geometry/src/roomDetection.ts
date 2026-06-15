import type { Point, Wall } from "./types";
import { buildPlanarGraph } from "./planarGraph";
import { polygonSignedArea } from "./geometry";

export interface DetectedRoom {
  polygon: Point[];
  areaM2: number;
}

const MIN_AREA_M2 = 1e-4; // 1 cm^2 - filters degenerate/zero-area faces

/**
 * Detects enclosed room faces from a floor's wall + divider centerlines.
 * Returns one polygon per interior face (positive signed area). The
 * unbounded exterior face(s) - which always have non-positive signed area
 * under this traversal - are discarded.
 */
export function detectRooms(walls: Wall[]): DetectedRoom[] {
  const segments = walls.map((w) => ({ start: w.start, end: w.end }));
  const graph = buildPlanarGraph(segments);
  return findInteriorFaces(graph.nodes, graph.adjacency);
}

function findInteriorFaces(nodes: Point[], adjacency: number[][]): DetectedRoom[] {
  const visited = new Set<string>();
  const faces: DetectedRoom[] = [];
  const totalHalfEdges = adjacency.reduce((sum, a) => sum + a.length, 0);

  for (let startU = 0; startU < nodes.length; startU++) {
    for (const startV of adjacency[startU]) {
      const startKey = `${startU}-${startV}`;
      if (visited.has(startKey)) continue;

      const faceNodeIndices: number[] = [];
      let u = startU;
      let v = startV;
      let steps = 0;

      do {
        visited.add(`${u}-${v}`);
        faceNodeIndices.push(u);

        const neighbors = adjacency[v];
        const k = neighbors.indexOf(u);
        const nextIdx = (k - 1 + neighbors.length) % neighbors.length;
        const w = neighbors[nextIdx];

        u = v;
        v = w;
        steps++;
        if (steps > totalHalfEdges + 1) {
          throw new Error("Face trace did not terminate - invalid planar graph");
        }
      } while (!(u === startU && v === startV));

      if (faceNodeIndices.length < 3) continue;

      const polygon = faceNodeIndices.map((i) => nodes[i]);
      const signedArea = polygonSignedArea(polygon);
      if (signedArea > MIN_AREA_M2) {
        faces.push({ polygon, areaM2: Math.round(signedArea * 100) / 100 });
      }
    }
  }

  return faces;
}
