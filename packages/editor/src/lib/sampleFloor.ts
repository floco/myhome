import type { Floor } from "@myhome/geometry";

export const SAMPLE_FLOOR: Floor = {
  id: "floor-1",
  name: "Ground Floor",
  order: 0,
  walls: [
    { id: "wall-1", type: "wall", start: { x: 0, y: 0 }, end: { x: 4, y: 0 }, thickness: 0.1 },
    { id: "wall-2", type: "wall", start: { x: 4, y: 0 }, end: { x: 4, y: 3 }, thickness: 0.1 },
    { id: "wall-3", type: "wall", start: { x: 4, y: 3 }, end: { x: 0, y: 3 }, thickness: 0.1 },
    { id: "wall-4", type: "wall", start: { x: 0, y: 3 }, end: { x: 0, y: 0 }, thickness: 0.1 },
    { id: "divider-1", type: "divider", start: { x: 2, y: 0 }, end: { x: 2, y: 3 } },
  ],
  openings: [],
  rooms: [],
};

export function createSampleFloor(): Floor {
  return structuredClone(SAMPLE_FLOOR);
}
