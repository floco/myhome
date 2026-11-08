import { describe, it, expect, afterEach, vi } from "vitest";
import { createPropertySearchStore } from "../src/lib/propertySearchStore.svelte";
import { makeSearch, makeSuggestion } from "./fixtures/propertySearch";

const HOME = "home-1";

async function tick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

afterEach(() => vi.unstubAllGlobals());

function routedFetch(routes: Record<string, unknown>) {
  return vi.fn().mockImplementation(async (url: string, init?: RequestInit) => {
    const key = `${init?.method ?? "GET"} ${url}`;
    const match = Object.keys(routes).find((k) => key.startsWith(k));
    const body = match ? routes[match] : undefined;
    const status = match ? 200 : 404;
    return { ok: status === 200, status, json: async () => body };
  });
}

describe("propertySearchStore", () => {
  it("init loads searches and suggestions", async () => {
    vi.stubGlobal("fetch", routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [makeSearch()],
      [`GET /api/homes/${HOME}/property-suggestions`]: [makeSuggestion()],
    }));
    const store = createPropertySearchStore(() => HOME);
    await tick();
    expect(store.searches.map((s) => s.id)).toEqual(["s1"]);
    expect(store.suggestions.map((s) => s.id)).toEqual(["g1"]);
    expect(store.loaded).toBe(true);
  });

  it("newCount counts only new", async () => {
    vi.stubGlobal("fetch", routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [],
      [`GET /api/homes/${HOME}/property-suggestions`]: [
        makeSuggestion({ id: "a" }), makeSuggestion({ id: "b", status: "pinned" }), makeSuggestion({ id: "c" }),
      ],
    }));
    const store = createPropertySearchStore(() => HOME);
    await tick();
    expect(store.newCount).toBe(2);
  });

  it("accept removes suggestion locally and returns the property", async () => {
    const fetchFn = routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [],
      [`GET /api/homes/${HOME}/property-suggestions`]: [makeSuggestion()],
      [`POST /api/homes/${HOME}/property-suggestions/g1/accept`]: { id: "p1", name: "Nice plot" },
    });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertySearchStore(() => HOME);
    await tick();
    const prop = await store.accept("g1");
    expect(prop.id).toBe("p1");
    expect(store.suggestions).toEqual([]);
  });

  it("togglePin flips status locally", async () => {
    vi.stubGlobal("fetch", routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [],
      [`GET /api/homes/${HOME}/property-suggestions`]: [makeSuggestion()],
      [`POST /api/homes/${HOME}/property-suggestions/g1/pin`]: null,
    }));
    const store = createPropertySearchStore(() => HOME);
    await tick();
    await store.togglePin("g1");
    expect(store.suggestions[0].status).toBe("pinned");
  });

  it("saveConfig sends PUT", async () => {
    const fetchFn = routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [],
      [`GET /api/homes/${HOME}/property-suggestions`]: [],
      [`PUT /api/homes/${HOME}/property-search-config`]: { retentionDays: 9 },
    });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertySearchStore(() => HOME);
    await tick();
    const out = await store.saveConfig({ retentionDays: 9, recipients: ["a@b.si"] });
    expect(out.retentionDays).toBe(9);
    const call = fetchFn.mock.calls.find((c) => c[1]?.method === "PUT");
    expect(JSON.parse(call![1].body)).toEqual({ retentionDays: 9, recipients: ["a@b.si"] });
  });

  it("sendTestEmail throws with the server detail", async () => {
    vi.stubGlobal("fetch", vi.fn().mockImplementation(async (_url: string, init?: RequestInit) => {
      if (init?.method === "POST") return { ok: false, status: 502, json: async () => ({ detail: "Brevo error 401: Key not found" }) };
      return { ok: true, status: 200, json: async () => [] };
    }));
    const store = createPropertySearchStore(() => HOME);
    await tick();
    await expect(store.sendTestEmail()).rejects.toThrow("Key not found");
  });
});
