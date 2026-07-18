import { describe, it, expect, afterEach, vi } from "vitest";
import {
  createLocationsStore, ratingFor, weightedScore, bestScoreForCriterion, WEIGHT_MULTIPLIER,
} from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({
    ok: status >= 200 && status < 300,
    status,
    json: async () => body,
  });
}

const emptyDoc = { version: 1, criteria: [], locations: [], ratings: [] };

const sampleDoc = {
  version: 1,
  criteria: [
    { id: "c1", name: "Cost of Living", description: "", weight: "high" },
    { id: "c2", name: "Safety", description: "", weight: "medium" },
  ],
  locations: [
    { id: "l1", name: "Nantes", emoji: "🇫🇷" },
    { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
  ],
  ratings: [
    { locationId: "l1", criterionId: "c1", score: 2, note: "pricier" },
    { locationId: "l1", criterionId: "c2", score: 4, note: "" },
    { locationId: "l2", criterionId: "c1", score: 5, note: "cheap" },
  ],
};

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

describe("locationsStore — init", () => {
  it("loads criteria, locations, and ratings from API", async () => {
    vi.stubGlobal("fetch", makeFetch(200, sampleDoc));
    const store = createLocationsStore(getHomeId);
    await tick();
    expect(store.criteria.length).toBe(2);
    expect(store.locations.length).toBe(2);
    expect(store.ratings.length).toBe(3);
    expect(store.loaded).toBe(true);
  });

  it("marks loaded on fetch error", async () => {
    vi.stubGlobal("fetch", vi.fn().mockRejectedValue(new Error("Network")));
    const store = createLocationsStore(getHomeId);
    await tick();
    expect(store.loaded).toBe(true);
    expect(store.loadError).toMatch("Network");
  });

  it("does not fetch when no homeId provided", async () => {
    const fetchFn = vi.fn();
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(() => null);
    await tick();
    expect(fetchFn).not.toHaveBeenCalled();
    expect(store.loaded).toBe(true);
  });
});

describe("locationsStore — criteria CRUD", () => {
  it("createCriterion POSTs to /criteria and reloads", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.createCriterion({ name: "Healthcare", description: "", weight: "high" });
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria`,
      expect.objectContaining({ method: "POST" }),
    );
    expect(store.criteria.length).toBe(2);
  });

  it("deleteCriterion DELETEs /criteria/{id}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.deleteCriterion("c1");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria/c1`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });

  it("reorderCriteria PUTs ordered ids to /criteria/reorder", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.reorderCriteria(["c2", "c1"]);
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/criteria/reorder`,
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ orderedIds: ["c2", "c1"] }) }),
    );
  });
});

describe("locationsStore — locations CRUD", () => {
  it("createLocation POSTs to /locations/locations", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => emptyDoc })
      .mockResolvedValueOnce({ ok: true, status: 201, json: async () => ({}) })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.createLocation({ name: "Zagreb", emoji: "🇭🇷" });
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/locations`,
      expect.objectContaining({ method: "POST" }),
    );
  });
});

describe("locationsStore — ratings", () => {
  it("setRating PUTs score+note to /ratings/{locationId}/{criterionId}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.setRating("l1", "c1", 3, "revised");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/ratings/l1/c1`,
      expect.objectContaining({ method: "PUT", body: JSON.stringify({ score: 3, note: "revised" }) }),
    );
  });

  it("clearRating DELETEs /ratings/{locationId}/{criterionId}", async () => {
    const fetchFn = vi.fn()
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc })
      .mockResolvedValueOnce({ ok: true, status: 204, json: async () => undefined })
      .mockResolvedValueOnce({ ok: true, status: 200, json: async () => sampleDoc });
    vi.stubGlobal("fetch", fetchFn);
    const store = createLocationsStore(getHomeId);
    await tick();
    await store.clearRating("l1", "c1");
    expect(fetchFn).toHaveBeenCalledWith(
      `/api/homes/${HOME}/locations/ratings/l1/c1`,
      expect.objectContaining({ method: "DELETE" }),
    );
  });
});

describe("locationsStore — pure helpers", () => {
  it("ratingFor finds the matching rating", () => {
    const r = ratingFor(sampleDoc.ratings as any, "l1", "c1");
    expect(r?.score).toBe(2);
  });

  it("ratingFor returns null when no match", () => {
    expect(ratingFor(sampleDoc.ratings as any, "l2", "c2")).toBeNull();
  });

  it("weightedScore averages rated criteria by weight, ignoring unrated ones", () => {
    // l1: c1 score=2 weight=high(3), c2 score=4 weight=medium(2) => (2*3+4*2)/(3+2) = 2.8
    const score = weightedScore(sampleDoc.criteria as any, sampleDoc.ratings as any, "l1");
    expect(score).toBeCloseTo(2.8);
  });

  it("weightedScore returns null when the location has no ratings", () => {
    const score = weightedScore(sampleDoc.criteria as any, [], "l1");
    expect(score).toBeNull();
  });

  it("bestScoreForCriterion returns the highest rated score for a criterion", () => {
    const best = bestScoreForCriterion(sampleDoc.locations as any, sampleDoc.ratings as any, "c1");
    expect(best).toBe(5);
  });

  it("bestScoreForCriterion returns null when no location has been rated", () => {
    expect(bestScoreForCriterion(sampleDoc.locations as any, [], "c1")).toBeNull();
  });

  it("WEIGHT_MULTIPLIER maps low/medium/high to 1/2/3", () => {
    expect(WEIGHT_MULTIPLIER).toEqual({ low: 1, medium: 2, high: 3 });
  });
});
