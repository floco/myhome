import { describe, it, expect } from "vitest";
import type { HouseDocument, Opening } from "../src/types";

describe("HouseDocument shape", () => {
  it("accepts a minimal valid document", () => {
    const doc: HouseDocument = {
      version: 1,
      house: { name: "My House", units: "m", gridSnap: 0.1 },
      floors: [
        {
          id: "floor-ground",
          name: "Ground Floor",
          order: 0,
          walls: [],
          openings: [],
          rooms: [],
        },
      ],
    };

    expect(doc.version).toBe(1);
    expect(doc.floors[0].name).toBe("Ground Floor");
  });
});

describe("Opening HA fields", () => {
  it("allows an opening with HA sensor and shutter links", () => {
    const opening: Opening = {
      id: "o1", wallId: "w1", type: "window", offset: 1, width: 1,
      haEntityId: "binary_sensor.front_window",
      hasShutter: true,
      shutterEntityId: "cover.front_window_shutter",
    };
    expect(opening.hasShutter).toBe(true);
  });

  it("allows an opening with the HA fields omitted", () => {
    const opening: Opening = { id: "o2", wallId: "w1", type: "door", offset: 0, width: 0.9 };
    expect(opening.haEntityId).toBeUndefined();
  });

  it("allows an opening with doorKind and windowSide set", () => {
    const door: Opening = { id: "o3", wallId: "w1", type: "door", offset: 0, width: 0.9, doorKind: "sliding" };
    const window: Opening = { id: "o4", wallId: "w1", type: "window", offset: 0, width: 1, windowSide: "out" };
    expect(door.doorKind).toBe("sliding");
    expect(window.windowSide).toBe("out");
  });
});
