import { _ } from "svelte-i18n";
import { get } from "svelte/store";
import type { Floor } from "@myhome/geometry";

export function createEmptyFloor(): Floor {
  return {
    id: "floor-1",
    name: get(_)("floorPlan.switcher.groundFloor"),
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
