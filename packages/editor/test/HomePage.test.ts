import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomePage from "../src/lib/components/HomePage.svelte";
import { createHouseStore } from "../src/lib/houseStore.svelte";
import { createChoreStore } from "../src/lib/choreStore.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createWorksStore } from "../src/lib/worksStore.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;

function makeStores() {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue({ ok: false, status: 404, json: async () => undefined }));
  return {
    floorStore: createHouseStore(getHomeId),
    choreStore: createChoreStore(getHomeId),
    inventoryStore: createInventoryStore(getHomeId),
    settingsStore: createSettingsStore(getHomeId),
    costsStore: createCostsStore(getHomeId),
    worksStore: createWorksStore(getHomeId),
    consumableStore: createConsumableStore(getHomeId),
  };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomePage", () => {
  it("renders all five widgets", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomePage, { target, props: stores });
    await tick();
    flushSync();

    expect(target.querySelector(".home-page")).not.toBeNull();
    expect(target.querySelector(".map-area")).not.toBeNull();
    expect(target.textContent).toContain("Chores");
    expect(target.textContent).toContain("Costs");
    expect(target.textContent).toContain("Inventory");
    expect(target.textContent).toContain("Works");

    unmount(comp);
    target.remove();
  });

  it("navigates to #/chores when the chores widget is clicked", async () => {
    const stores = makeStores();
    const target = document.createElement("div");
    document.body.appendChild(target);
    window.location.hash = "";
    const comp = mount(HomePage, { target, props: stores });
    await tick();
    flushSync();

    const choresWidget = Array.from(target.querySelectorAll(".widget")).find((w) =>
      w.textContent?.includes("Chores")
    ) as HTMLElement;
    choresWidget.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(window.location.hash).toBe("#/chores");

    unmount(comp);
    target.remove();
  });
});
