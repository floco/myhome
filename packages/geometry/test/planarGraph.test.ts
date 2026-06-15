import { describe, it, expect } from "vitest";
import { buildPlanarGraph } from "../src/planarGraph";

describe("buildPlanarGraph", () => {
  it("builds 4 nodes with degree 2 for a simple rectangle", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 4, y: 0 } },
      { start: { x: 4, y: 0 }, end: { x: 4, y: 2 } },
      { start: { x: 4, y: 2 }, end: { x: 0, y: 2 } },
      { start: { x: 0, y: 2 }, end: { x: 0, y: 0 } },
    ];
    const graph = buildPlanarGraph(segments);

    expect(graph.nodes).toHaveLength(4);
    for (const adj of graph.adjacency) {
      expect(adj).toHaveLength(2);
    }
  });

  it("splits a segment at a T-intersection from another segment's endpoint", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 4, y: 0 } }, // long bottom wall
      { start: { x: 2, y: 0 }, end: { x: 2, y: 2 } }, // divider touching its midpoint
    ];
    const graph = buildPlanarGraph(segments);

    // nodes: (0,0), (4,0), (2,0) [split point], (2,2) = 4 nodes
    expect(graph.nodes).toHaveLength(4);

    const splitIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 0);
    expect(splitIdx).toBeGreaterThanOrEqual(0);
    // the split node connects to 3 others: (0,0), (4,0), (2,2)
    expect(graph.adjacency[splitIdx]).toHaveLength(3);
  });

  it("splits both segments at a proper X crossing", () => {
    const segments = [
      { start: { x: 0, y: 2 }, end: { x: 4, y: 2 } },
      { start: { x: 2, y: 0 }, end: { x: 2, y: 4 } },
    ];
    const graph = buildPlanarGraph(segments);

    // 4 original endpoints + 1 crossing point = 5 nodes
    expect(graph.nodes).toHaveLength(5);

    const crossIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 2);
    expect(crossIdx).toBeGreaterThanOrEqual(0);
    expect(graph.adjacency[crossIdx]).toHaveLength(4);
  });

  it("sorts each node's adjacency by angle ascending", () => {
    // A '+' shape centered at the origin: 4 segments from center to N/E/S/W
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 1, y: 0 } }, // East, angle 0
      { start: { x: 0, y: 0 }, end: { x: 0, y: 1 } }, // North, angle pi/2
      { start: { x: 0, y: 0 }, end: { x: -1, y: 0 } }, // West, angle pi
      { start: { x: 0, y: 0 }, end: { x: 0, y: -1 } }, // South, angle -pi/2
    ];
    const graph = buildPlanarGraph(segments);

    const centerIdx = graph.nodes.findIndex((p) => p.x === 0 && p.y === 0);
    const neighborAngles = graph.adjacency[centerIdx].map((i) => {
      const p = graph.nodes[i];
      return Math.atan2(p.y, p.x);
    });
    const sorted = [...neighborAngles].sort((a, b) => a - b);
    expect(neighborAngles).toEqual(sorted);
  });

  it("deduplicates coincident endpoints into a single node", () => {
    const segments = [
      { start: { x: 0, y: 0 }, end: { x: 2, y: 0 } },
      { start: { x: 2, y: 0 }, end: { x: 2, y: 2 } },
    ];
    const graph = buildPlanarGraph(segments);

    // (0,0), (2,0), (2,2) - the shared (2,0) endpoint is one node, not two
    expect(graph.nodes).toHaveLength(3);
    const sharedIdx = graph.nodes.findIndex((p) => p.x === 2 && p.y === 0);
    expect(graph.adjacency[sharedIdx]).toHaveLength(2);
  });
});
