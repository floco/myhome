import { describe, it, expect, afterEach, vi } from "vitest";
import { createChoreStore } from "../src/lib/choreStore.svelte";

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, chores: [], assignments: [] };

const sampleDoc = {
  version: 1,
  chores: [
    { id: "c1", donetickId: null, name: "🧹 Sweep", emoji: "🧹", periodDays: 14, nextDueDate: new Date(Date.now() + 7 * 86400000).toISOString(), description: "" },
    { id: "c2", donetickId: null, name: "🪟 Windows", emoji: "🪟", periodDays: 365, nextDueDate: new Date(Date.now() - 5 * 86400000).toISOString(), description: "" },
  ],
  assignments: [
    { id: "a1", choreId: "c1", roomId: "r1", position: { x: 1, y: 2 } },
    { id: "a2", choreId: "c2", roomId: null, position: null },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("choreStore — init", () => {
  it("starts empty and loads from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    expect(store.chores.length).toBe(2);
    expect(store.assignments.length).toBe(2);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded even on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network error")));
    const store = createChoreStore();
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network error");
  });

  it("returns empty arrays when API returns empty doc", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.chores).toEqual([]);
    expect(store.assignments).toEqual([]);
  });
});

describe("choreStore — getProgress", () => {
  it("returns ~0.5 when half period remains", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const halfRemaining = new Date(Date.now() + 7 * 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: halfRemaining, description: "" });
    expect(pct).toBeCloseTo(0.5, 1);
  });

  it("returns 0 when overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const overdue = new Date(Date.now() - 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: overdue, description: "" });
    expect(pct).toBe(0);
  });

  it("returns 1 when just scheduled", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    const fullRemaining = new Date(Date.now() + 14 * 86400000).toISOString();
    const pct = store.getProgress({ id: "x", donetickId: null, name: "", emoji: "", periodDays: 14, nextDueDate: fullRemaining, description: "" });
    expect(pct).toBeCloseTo(1, 1);
  });
});

describe("choreStore — getColor", () => {
  it("returns green for >50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.8)).toBe("#4caf50");
  });

  it("returns orange for 25-50%", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.4)).toBe("#ff9800");
  });

  it("returns red for <25% or overdue", async () => {
    vi.stubGlobal("fetch", makeFetch(200, emptyDoc));
    const store = createChoreStore();
    await tick();
    expect(store.getColor(0.1)).toBe("#f44336");
    expect(store.getColor(0)).toBe("#f44336");
  });
});

describe("choreStore — assignmentsForRoom", () => {
  it("returns only assignments for the specified room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.length).toBe(1);
    expect(forR1[0].id).toBe("a1");
  });

  it("returns empty array for unknown room", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    expect(store.assignmentsForRoom("unknown")).toEqual([]);
  });

  it("does not include house-level assignments", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createChoreStore();
    await tick();
    const forR1 = store.assignmentsForRoom("r1");
    expect(forR1.every((a) => a.roomId !== null)).toBe(true);
  });
});
