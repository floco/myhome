import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import HomeInventoryWidget from "../src/lib/components/HomeInventoryWidget.svelte";
import { createInventoryStore } from "../src/lib/inventoryStore.svelte";

const sampleDoc = {
  items: [
    { id: "i1", name: "Drill", emoji: "🔧", category: "Tools", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
    { id: "i2", name: "Saw", emoji: "🪚", category: "Tools", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
    { id: "i3", name: "Sofa", emoji: "🛋️", category: "Furniture", brand: null, model: null, serialNumber: null, purchaseDate: null, purchasePrice: null, warrantyExpiryDate: null, notes: "", attachments: [], placement: null },
  ],
};

const HOME = "home-123";
const getHomeId = () => HOME;

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}

function makeStore(empty = false) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => (empty ? { items: [] } : sampleDoc) })
  );
  return createInventoryStore(getHomeId);
}

afterEach(() => vi.unstubAllGlobals());

describe("HomeInventoryWidget", () => {
  it("renders a donut slice per category", async () => {
    const inventoryStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelectorAll("svg path")).toHaveLength(2);

    unmount(comp);
    target.remove();
  });

  it("shows per-category counts as chart labels", async () => {
    const inventoryStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    const text = target.querySelector("svg")!.textContent;
    expect(text).toContain("Tools");
    expect(text).toContain("2");
    expect(text).toContain("Furniture");
    expect(text).toContain("1");

    unmount(comp);
    target.remove();
  });

  it("shows an empty state with no items", async () => {
    const inventoryStore = makeStore(true);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate: vi.fn() } });
    await tick();
    flushSync();

    expect(target.querySelector(".empty")).not.toBeNull();

    unmount(comp);
    target.remove();
  });

  it("clicking the widget calls onnavigate", async () => {
    const inventoryStore = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onnavigate = vi.fn();
    const comp = mount(HomeInventoryWidget, { target, props: { inventoryStore, onnavigate } });
    await tick();
    flushSync();

    (target.querySelector(".widget") as HTMLElement).dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    expect(onnavigate).toHaveBeenCalledOnce();

    unmount(comp);
    target.remove();
  });
});
