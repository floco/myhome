import { describe, it, expect } from "vitest";
import type { HouseDocument } from "../src/types";

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
