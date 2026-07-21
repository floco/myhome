import type { Floor } from "@myhome/geometry";

export function createEmptyFloor(): Floor {
  return {
    id: "floor-1",
    name: "Ground Floor",
    order: 0,
    walls: [],
    openings: [],
    rooms: [],
    furnitureObjects: [],
  };
}

export interface HouseData {
  floors: Floor[];
  currentFloorId: string;
}

export function createEmptyHouse(): HouseData {
  const floor = createEmptyFloor();
  return { floors: [floor], currentFloorId: floor.id };
}
