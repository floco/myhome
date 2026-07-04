export interface Point {
  x: number;
  y: number;
}

export type WallType = "wall" | "divider";

export interface Wall {
  id: string;
  start: Point;
  end: Point;
  /** Meters. Only meaningful for type "wall"; dividers have no thickness. */
  thickness?: number;
  type: WallType;
}

export type OpeningType = "door" | "window";

/**
 * Which corner of the opening the door hinges on, and which side of the
 * wall it swings into. "left"/"right" refer to the corner closer to the
 * wall's `start` vs `end` point; "in"/"out" refer to the two sides of the
 * wall, split by the wall's direction vector (start -> end).
 */
export type DoorSwing = "left-in" | "right-in" | "left-out" | "right-out";

export interface Opening {
  id: string;
  wallId: string;
  type: OpeningType;
  /** Distance in meters along the wall from `wall.start`, clamped to the wall's length. */
  offset: number;
  /** Meters. */
  width: number;
  /** Only meaningful for type "door". */
  swing?: DoorSwing;
}

export interface Room {
  id: string;
  label: string;
  haAreaId: string | null;
  /** Cached centerline-based polygon, or null if the room is "unresolved" (see roomMatching). */
  polygon: Point[] | null;
  areaM2: number;
}

export interface FurnitureObject {
  id: string;
  templateId: string;
  x: number;       // world coords, meters, center of object
  y: number;
  width: number;   // meters
  height: number;  // meters
  rotation: number; // degrees, clockwise
}

export interface Floor {
  id: string;
  name: string;
  order: number;
  walls: Wall[];
  openings: Opening[];
  rooms: Room[];
  furnitureObjects?: FurnitureObject[];
}

export interface House {
  name: string;
  units: "m";
  gridSnap: number;
}

export interface HouseDocument {
  version: number;
  house: House;
  floors: Floor[];
}
