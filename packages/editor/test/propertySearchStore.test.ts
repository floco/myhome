import { describe, it, expect, afterEach, vi } from "vitest";
import { locale } from "svelte-i18n";
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
  it("sends the current UI language when creating and updating a search", async () => {
    const fetchFn = routedFetch({
      [`GET /api/homes/${HOME}/property-searches`]: [],
      [`GET /api/homes/${HOME}/property-suggestions`]: [],
      [`POST /api/homes/${HOME}/property-searches`]: makeSearch(),
      [`PUT /api/homes/${HOME}/property-searches/s1`]: {},
    });
    vi.stubGlobal("fetch", fetchFn);
    const store = createPropertySearchStore(() => HOME);
    await tick();
    locale.set("fr");
    await store.createSearch({ name: "A", prompt: "p", enabled: true, frequency: "daily", time: "08:00",
      dayOfWeek: 1, dayOfMonth: 1, maxResultsPerRun: 10, maxListingAgeDays: 7 });
    locale.set("en");
    await store.updateSearch("s1", { enabled: false });
    const bodies = fetchFn.mock.calls
      .filter(([, init]) => init?.method === "POST" || init?.method === "PUT")
      .map(([, init]) => JSON.parse(init.body));
    expect(bodies[0].language).toBe("fr");
    expect(bodies[1]).toEqual({ enabled: false, language: "en" });
  });

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

  describe("stale reloads", () => {
    type Pending = { url: string; resolve: (body: unknown) => void };

    // GET suggestions calls are held until released; everything else answers immediately.
    function heldFetch(routes: Record<string, unknown>) {
      const held: Pending[] = [];
      const fn = vi.fn().mockImplementation((url: string, init?: RequestInit) => {
        const method = init?.method ?? "GET";
        if (method === "GET" && url.endsWith("/property-suggestions")) {
          return new Promise((resolve) => {
            held.push({ url, resolve: (body) => resolve({ ok: true, status: 200, json: async () => body }) });
          });
        }
        const key = `${method} ${url}`;
        const match = Object.keys(routes).find((k) => key.startsWith(k));
        return Promise.resolve({ ok: !!match, status: match ? 200 : 404, json: async () => (match ? routes[match] : undefined) });
      });
      return { fn, held };
    }

    async function loadedStore(held: Pending[], initial: unknown[]) {
      const store = createPropertySearchStore(() => HOME);
      await tick();
      held.shift()!.resolve(initial);
      await tick();
      return store;
    }

    it("a reload started before accept does not bring the suggestion back", async () => {
      const { fn, held } = heldFetch({
        [`GET /api/homes/${HOME}/property-searches`]: [],
        [`POST /api/homes/${HOME}/property-suggestions/g1/accept`]: { id: "p1" },
      });
      vi.stubGlobal("fetch", fn);
      const store = await loadedStore(held, [makeSuggestion()]);
      const reloading = store.reload();
      await tick();
      await store.accept("g1");
      held.shift()!.resolve([makeSuggestion()]);
      await reloading;
      expect(store.suggestions).toEqual([]);
      expect(store.newCount).toBe(0);
    });

    it("a reload started before reject does not bring the suggestion back", async () => {
      const { fn, held } = heldFetch({
        [`GET /api/homes/${HOME}/property-searches`]: [],
        [`POST /api/homes/${HOME}/property-suggestions/g1/reject`]: {},
      });
      vi.stubGlobal("fetch", fn);
      const store = await loadedStore(held, [makeSuggestion()]);
      const reloading = store.reload();
      await tick();
      await store.reject("g1");
      held.shift()!.resolve([makeSuggestion()]);
      await reloading;
      expect(store.suggestions).toEqual([]);
    });

    it("a reload started before pin does not undo the pin", async () => {
      const { fn, held } = heldFetch({
        [`GET /api/homes/${HOME}/property-searches`]: [],
        [`POST /api/homes/${HOME}/property-suggestions/g1/pin`]: {},
      });
      vi.stubGlobal("fetch", fn);
      const store = await loadedStore(held, [makeSuggestion()]);
      const reloading = store.reload();
      await tick();
      await store.togglePin("g1");
      held.shift()!.resolve([makeSuggestion()]);
      await reloading;
      expect(store.suggestions[0].status).toBe("pinned");
    });

    it("an older reload finishing last does not overwrite a newer one", async () => {
      const { fn, held } = heldFetch({ [`GET /api/homes/${HOME}/property-searches`]: [] });
      vi.stubGlobal("fetch", fn);
      const store = await loadedStore(held, []);
      const first = store.reload();
      await tick();
      const second = store.reload();
      await tick();
      const [older, newer] = held.splice(0, 2);
      newer.resolve([makeSuggestion({ id: "fresh" })]);
      await second;
      older.resolve([]);
      await first;
      expect(store.suggestions.map((s) => s.id)).toEqual(["fresh"]);
    });
  });
});

