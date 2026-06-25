import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeMapWidget from "../src/lib/components/HomeMapWidget.svelte";
import { createHouseStore } from "../src/lib/houseStore.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";

function makeFetch() {
  return vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => undefined });
}

function makeStores() {
  vi.stubGlobal("fetch", makeFetch());
  return {
    floorStore: createHouseStore(),
    choreStore: createChoreStore(),
    inventoryStore: createInventoryStore(),
    settingsStore: createSettingsStore(),
    costsStore: createCostsStore(),
    worksStore: createWorksStore(),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeMapWidget", () => {
  it("renders a read-only canvas with no grid lines", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    const svg = target.querySelector("svg.canvas");
    expect(svg).not.toBeNull();
    expect(svg!.querySelectorAll("line.grid-line")).toHaveLength(0);

    unmount(comp);
    target.remove();
  });

  it("renders a floor switcher and layers dropdown", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".floor-switcher")).not.toBeNull();
    expect(target.querySelector(".layers-dropdown")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the map area calls onnavigate", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".map-area") as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });

  it("clicking the floor switcher does not call onnavigate", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeMapWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".floor-switcher .floor-label") as HTMLElement).dispatchEvent(
      new MouseEvent("click", { bubbles: true })
    );
    flushSync();

    expect(onnavigate).not.toHaveBeenCalled();

    unmount(comp);
    target.remove();
  });
});
