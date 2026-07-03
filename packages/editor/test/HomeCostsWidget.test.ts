import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeCostsWidget from "../src/lib/components/HomeCostsWidget.svelte";
import { createCostsStore } from "../src/lib/costsStore.svelte";
import { createSettingsStore } from "../src/lib/settingsStore.svelte";

const HOME = "home-123";
const getHomeId = () => HOME;
const lastYear = new Date().getFullYear() - 1;

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStores(withEntries: boolean) {
  const costsDoc = {
    version: 1,
    entries: withEntries
      ? [{ id: "e1", categoryId: "cat1", date: `${lastYear}-03-01`, totalAmount: 300, quantity: null, unitPrice: null, supplierId: null, notes: "", roomId: null }]
      : [],
  };
  const settingsDoc = {
    version: 1,
    costCategories: [{ id: "cat1", name: "Fuel", emoji: "⛽", unit: "L", color: "#e76f51" }],
    inventoryCategories: [],
    workCategories: [],
    suppliers: [],
  };
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation((url: string) => {
      if (url === `/api/homes/${HOME}/costs`) return Promise.resolve({ ok: true, status: 200, json: async () => costsDoc });
      if (url === `/api/homes/${HOME}/settings`) return Promise.resolve({ ok: true, status: 200, json: async () => settingsDoc });
      return Promise.resolve({ ok: false, status: 404, json: async () => undefined });
    })
  );
  return { costsStore: createCostsStore(getHomeId), settingsStore: createSettingsStore(getHomeId) };
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeCostsWidget", () => {
  it("renders a donut chart when there are entries", async () => {
    const stores = makeStores(true);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll("svg path")).toHaveLength(1);

    unmount(comp);
    target.remove();
  });

  it("shows an empty state when there are no entries", async () => {
    const stores = makeStores(false);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".empty")).not.toBeNull();
    expect(target.querySelectorAll("svg path")).toHaveLength(0);

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const stores = makeStores(true);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeCostsWidget, { target, props: { ...stores, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
