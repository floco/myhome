import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync } from "svelte";
import HomeLocationsWidget from "../src/lib/components/HomeLocationsWidget.svelte";
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

describe("HomeLocationsWidget", () => {
  it("renders nothing when there are no locations", async () => {
    vi.stubGlobal("fetch", makeFetch(200, { version: 1, criteria: [], locations: [], ratings: [] }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".widget")).toBeNull();
    unmount(comp);
    el.remove();
  });

  it("shows the top-ranked location", async () => {
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
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate: vi.fn() } });
    flushSync();
    expect(el.querySelector(".top-pick .name")?.textContent).toBe("Ljubljana");
    unmount(comp);
    el.remove();
  });

  it("calls onnavigate when clicked", async () => {
    vi.stubGlobal("fetch", makeFetch(200, {
      version: 1, criteria: [], locations: [{ id: "l1", name: "Nantes", emoji: "🇫🇷" }], ratings: [],
    }));
    const store = createLocationsStore(getHomeId);
    await tick();
    const el = target();
    const onnavigate = vi.fn();
    const comp = mount(HomeLocationsWidget, { target: el, props: { locationsStore: store, onnavigate } });
    flushSync();
    (el.querySelector(".widget") as HTMLElement).click();
    expect(onnavigate).toHaveBeenCalled();
    unmount(comp);
    el.remove();
  });
});
