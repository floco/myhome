import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import LocationsPage from "../src/lib/components/LocationsPage.svelte";
import { createLocationsStore } from "../src/lib/locationsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeFetch(status: number, body?: unknown) {
  return vi.fn().mockResolvedValue({ ok: status >= 200 && status < 300, status, json: async () => body });
}
async function tick(): Promise<void> { await new Promise((r) => setTimeout(r, 0)); }
function target(): HTMLElement {
  const el = document.createElement("div");
  document.body.appendChild(el);
  return el;
}

afterEach(() => vi.unstubAllGlobals());

describe("LocationsPage", () => {
  it("shows an empty state when there are no locations yet, but still shows the matrix to add one", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, criteria: [], locations: [], ratings: [] }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    expect(el.querySelector(".empty-state")).not.toBeNull();
    expect(el.querySelector(".matrix-card-wrap")).not.toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows the ranking chart once at least one location exists", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1,
      criteria: [{ id: "c1", name: "Cost", description: "", weight: "medium" }],
      locations: [{ id: "l1", name: "Nantes", emoji: "🇫🇷" }],
      ratings: [],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    expect(el.querySelector(".empty-state")).toBeNull();
    expect(el.querySelector(".ranking")).not.toBeNull();
    unmount(comp);
    el.remove();
  });
});
