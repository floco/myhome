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

  it("shows a no-ratings placeholder in the at-a-glance panel when nothing is rated yet", async () => {
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
    expect(el.querySelector(".no-leader")).not.toBeNull();
    expect(el.querySelectorAll(".leader-chip").length).toBe(0);
    unmount(comp);
    el.remove();
  });

  it("shows the crowned location in the at-a-glance panel, not in the ranking chart", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1,
      criteria: [{ id: "c1", name: "Cost", description: "", weight: "medium" }],
      locations: [
        { id: "l1", name: "Nantes", emoji: "🇫🇷" },
        { id: "l2", name: "Ljubljana", emoji: "🇸🇮" },
      ],
      ratings: [
        { locationId: "l1", criterionId: "c1", score: 2, note: "" },
        { locationId: "l2", criterionId: "c1", score: 5, note: "" },
      ],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    const chips = el.querySelectorAll(".leader-chip");
    expect(chips.length).toBe(1);
    expect(chips[0].querySelector(".leader-name")?.textContent).toBe("Ljubljana");
    expect(el.querySelector(".ranking .crown")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows every tied location in the at-a-glance panel", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1,
      criteria: [{ id: "c1", name: "Cost", description: "", weight: "medium" }],
      locations: [
        { id: "l1", name: "A", emoji: "📍" },
        { id: "l2", name: "B", emoji: "📍" },
      ],
      ratings: [
        { locationId: "l1", criterionId: "c1", score: 4, note: "" },
        { locationId: "l2", criterionId: "c1", score: 4, note: "" },
      ],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(LocationsPage, { target: el, props: { store } });
    flushSync();
    expect(el.querySelectorAll(".leader-chip").length).toBe(2);
    unmount(comp);
    el.remove();
  });
});
