// packages/editor/src/lib/propertySearchStore.svelte.ts
import type { Property, PropertyType } from "./propertiesStore.svelte";

export type SearchFrequency = "daily" | "weekly" | "monthly";
export type SuggestionStatus = "new" | "pinned" | "accepted" | "rejected";
export type RunStatus = "running" | "succeeded" | "failed" | "usage_limited";

export interface PropertySearch {
  id: string;
  name: string;
  prompt: string;
  enabled: boolean;
  frequency: SearchFrequency;
  time: string;
  dayOfWeek: number;
  dayOfMonth: number;
  maxResultsPerRun: number;
  maxListingAgeDays: number;
  createdAt: string;
  runRequestedAt: string | null;
  lastRunAt: string | null;
  lastRunStatus: RunStatus | null;
  lastRunError: string | null;
  lastRunNew?: number | null;
  lastRunDuplicates?: number | null;
  lastRunEmailError?: string | null;
}

export type PropertySearchInput = Pick<
  PropertySearch,
  "name" | "prompt" | "enabled" | "frequency" | "time" | "dayOfWeek" | "dayOfMonth" | "maxResultsPerRun" | "maxListingAgeDays"
>;

export interface PropertySuggestion {
  id: string;
  searchId: string;
  runId: string;
  title: string;
  type: PropertyType | null;
  price: number | null;
  currency: string | null;
  landSize: number | null;
  builtSize: number | null;
  bedrooms: number | null;
  bathrooms: number | null;
  location: string;
  country?: string | null;
  region?: string | null;
  city?: string | null;
  sourceSite: string;
  listingUrl: string;
  imageUrl: string | null;
  publishedAt: string | null;
  reason: string;
  status: SuggestionStatus;
  createdAt: string;
  acceptedPropertyId: string | null;
}

export interface SearchUsage {
  provider: string;
  tokensByModel: Record<string, number>;
  totalTokens: number;
  quotas: { label: string; usedPct: number | null }[];
}

export interface PropertySearchRun {
  id: string;
  searchId: string;
  slot: string;
  startedAt: string;
  finishedAt: string | null;
  status: RunStatus;
  error: string | null;
  emailError: string | null;
  sites: string[];
  searchQueries: string[];
  usage: SearchUsage | null;
  receivedCount: number;
  newCount: number;
  duplicateCount: number;
}

export interface PropertySearchConfig {
  retentionDays: number;
  brevoApiKeySet: boolean;
  senderEmail: string;
  senderName: string;
  recipients: string[];
  appBaseUrl: string;
}

export type PropertySearchConfigPatch = Partial<Omit<PropertySearchConfig, "brevoApiKeySet">> & { brevoApiKey?: string };

async function errorMessage(resp: Response): Promise<string> {
  try {
    const body = await resp.json();
    if (body && typeof body.detail === "string") return body.detail;
  } catch { /* not JSON */ }
  return `HTTP ${resp.status}`;
}

export function createPropertySearchStore(getHomeId: () => string | null = () => null) {
  const searches = $state<PropertySearch[]>([]);
  const suggestions = $state<PropertySuggestion[]>([]);
  let loaded = $state(false);
  let loadError = $state<string | null>(null);
  const newCount = $derived(suggestions.filter((s) => s.status === "new").length);

  function base(): string {
    const homeId = getHomeId();
    if (!homeId) throw new Error("No active home");
    return `/api/homes/${homeId}`;
  }

  async function request(path: string, init?: RequestInit): Promise<Response> {
    const resp = await fetch(`${base()}${path}`, init);
    if (!resp.ok) throw new Error(await errorMessage(resp));
    return resp;
  }

  function jsonInit(method: string, body: unknown): RequestInit {
    return { method, headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) };
  }

  async function loadSearches(): Promise<void> {
    const list: PropertySearch[] = await (await request("/property-searches")).json();
    searches.length = 0;
    searches.push(...list);
  }

  async function loadSuggestions(): Promise<void> {
    const list: PropertySuggestion[] = await (await request("/property-suggestions")).json();
    suggestions.length = 0;
    suggestions.push(...list);
  }

  async function init(): Promise<void> {
    if (!getHomeId()) { loaded = true; return; }
    try {
      await Promise.all([loadSearches(), loadSuggestions()]);
      loadError = null;
    } catch (e) {
      loadError = e instanceof Error ? e.message : String(e);
    } finally {
      loaded = true;
    }
  }

  async function createSearch(data: PropertySearchInput): Promise<void> {
    await request("/property-searches", jsonInit("POST", data));
    await loadSearches();
  }

  async function updateSearch(id: string, patch: Partial<PropertySearchInput>): Promise<void> {
    await request(`/property-searches/${id}`, jsonInit("PUT", patch));
    await loadSearches();
  }

  async function deleteSearch(id: string): Promise<void> {
    await request(`/property-searches/${id}`, { method: "DELETE" });
    await init();
  }

  async function runNow(id: string): Promise<void> {
    await request(`/property-searches/${id}/run-now`, { method: "POST" });
    await loadSearches();
  }

  async function listRuns(id: string): Promise<PropertySearchRun[]> {
    return (await request(`/property-searches/${id}/runs`)).json();
  }

  function removeLocal(id: string): void {
    const i = suggestions.findIndex((s) => s.id === id);
    if (i >= 0) suggestions.splice(i, 1);
  }

  async function accept(id: string): Promise<Property> {
    const prop: Property = await (await request(`/property-suggestions/${id}/accept`, { method: "POST" })).json();
    removeLocal(id);
    return prop;
  }

  async function reject(id: string): Promise<void> {
    await request(`/property-suggestions/${id}/reject`, { method: "POST" });
    removeLocal(id);
  }

  async function togglePin(id: string): Promise<void> {
    await request(`/property-suggestions/${id}/pin`, { method: "POST" });
    const s = suggestions.find((x) => x.id === id);
    if (s) s.status = s.status === "pinned" ? "new" : "pinned";
  }

  async function loadConfig(): Promise<PropertySearchConfig> {
    return (await request("/property-search-config")).json();
  }

  async function saveConfig(patch: PropertySearchConfigPatch): Promise<PropertySearchConfig> {
    return (await request("/property-search-config", jsonInit("PUT", patch))).json();
  }

  async function sendTestEmail(): Promise<void> {
    await request("/property-search-config/test-email", { method: "POST" });
  }

  init();

  return {
    get searches() { return searches as PropertySearch[]; },
    get suggestions() { return suggestions as PropertySuggestion[]; },
    get loaded() { return loaded; },
    get loadError() { return loadError; },
    get newCount() { return newCount; },
    init,
    reload: init,
    createSearch,
    updateSearch,
    deleteSearch,
    runNow,
    listRuns,
    accept,
    reject,
    togglePin,
    loadConfig,
    saveConfig,
    sendTestEmail,
  };
}
