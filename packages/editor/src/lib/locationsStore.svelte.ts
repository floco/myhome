export type Weight = "low" | "medium" | "high";

export interface LocationCriterion {
  id: string;
  name: string;
  description: string;
  weight: Weight;
}

export interface Location {
  id: string;
  name: string;
  emoji: string;
}

export interface LocationRating {
  locationId: string;
  criterionId: string;
  score: number | null;
  note: string;
}

export interface LocationsDocument {
  version: number;
  criteria: LocationCriterion[];
  locations: Location[];
  ratings: LocationRating[];
}

export const WEIGHT_MULTIPLIER: Record<Weight, number> = { low: 1, medium: 2, high: 3 };

export function ratingFor(
  ratings: LocationRating[],
  locationId: string,
  criterionId: string,
): LocationRating | null {
  return ratings.find((r) => r.locationId === locationId && r.criterionId === criterionId) ?? null;
}

export function weightedScore(
  criteria: LocationCriterion[],
  ratings: LocationRating[],
  locationId: string,
): number | null {
  let sum = 0;
  let weightTotal = 0;
  for (const c of criteria) {
    const r = ratingFor(ratings, locationId, c.id);
    if (r?.score == null) continue;
    const w = WEIGHT_MULTIPLIER[c.weight];
    sum += r.score * w;
    weightTotal += w;
  }
  return weightTotal === 0 ? null : sum / weightTotal;
}

export function bestScoreForCriterion(
  locations: Location[],
  ratings: LocationRating[],
  criterionId: string,
): number | null {
  let best: number | null = null;
  for (const loc of locations) {
    const r = ratingFor(ratings, loc.id, criterionId);
    if (r?.score == null) continue;
    if (best === null || r.score > best) best = r.score;
  }
  return best;
}

export function createLocationsStore(getHomeId: () => string | null = () => null) {
  const criteria = $state<LocationCriterion[]>([]);
  const locations = $state<Location[]>([]);
  const ratings = $state<LocationRating[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);

  async function init(): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) { loaded = true; return; }
    try {
      const resp = await fetch(`/api/homes/${homeId}/locations`);
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const doc: LocationsDocument = await resp.json();
      criteria.length = 0;
      for (const c of doc.criteria) criteria.push(c);
      locations.length = 0;
      for (const l of doc.locations) locations.push(l);
      ratings.length = 0;
      for (const r of doc.ratings) ratings.push(r);
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createCriterion(data: Omit<LocationCriterion, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateCriterion(id: string, patch: Partial<Omit<LocationCriterion, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteCriterion(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderCriteria(orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/criteria/reorder`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function createLocation(data: Omit<Location, "id">): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations`, {
      method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(data),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function updateLocation(id: string, patch: Partial<Omit<Location, "id">>): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/${id}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(patch),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function deleteLocation(id: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/${id}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function reorderLocations(orderedIds: string[]): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/locations/reorder`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ orderedIds }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function setRating(locationId: string, criterionId: string, score: number | null, note: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/ratings/${locationId}/${criterionId}`, {
      method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ score, note }),
    });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  async function clearRating(locationId: string, criterionId: string): Promise<void> {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    const resp = await fetch(`/api/homes/${homeId}/locations/ratings/${locationId}/${criterionId}`, { method: "DELETE" });
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
    await init();
  }

  init();

  return {
    get criteria() { return criteria as LocationCriterion[]; },
    get locations() { return locations as Location[]; },
    get ratings() { return ratings as LocationRating[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    createCriterion,
    updateCriterion,
    deleteCriterion,
    reorderCriteria,
    createLocation,
    updateLocation,
    deleteLocation,
    reorderLocations,
    setRating,
    clearRating,
    reload: init,
  };
}
