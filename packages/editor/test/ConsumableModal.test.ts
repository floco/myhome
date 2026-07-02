import { describe, it, expect, vi, afterEach } from "vitest";
import { mount, unmount, flushSync, tick } from "svelte";
import ConsumableModal from "../src/lib/components/ConsumableModal.svelte";
import { createConsumableStore } from "../src/lib/consumableStore.svelte";

const emptyDoc = { version: 1, consumables: [], transactions: [] };
const sampleConsumable = {
  id: "c1",
  name: "AA Batteries",
  emoji: "🔋",
  unit: "count",
  quantity: 6.0,
  minQuantity: 4.0,
  categoryId: null,
  description: "",
  placement: null,
};
const sampleDoc = {
  version: 1,
  consumables: [sampleConsumable],
  transactions: [
    {
      id: "t1",
      consumableId: "c1",
      delta: 6.0,
      quantityAfter: 6.0,
      note: "restock",
      timestamp: "2026-07-02T10:00:00Z",
    },
  ],
};

async function makeTick(): Promise<void> {
  await new Promise((r) => setTimeout(r, 0));
}
afterEach(() => vi.unstubAllGlobals());

function makeStore(doc = sampleDoc) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }),
  );
  return createConsumableStore();
}

describe("ConsumableModal — create mode", () => {
  it("renders details fields in create mode", async () => {
    const store = makeStore(emptyDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: null,
        store,
        settingsStore: { consumableUnits: ["count", "L"], consumableCategories: [] },
        onclose: vi.fn(),
      },
    });
    await tick();
    flushSync();
    const inputs = target.querySelectorAll("input, select, textarea");
    expect(inputs.length).toBeGreaterThan(0);
    unmount(comp);
    target.remove();
  });

  it("does not show Stock tab in create mode", async () => {
    const store = makeStore(emptyDoc);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: null,
        store,
        settingsStore: { consumableUnits: ["count"], consumableCategories: [] },
        onclose: vi.fn(),
      },
    });
    await tick();
    flushSync();
    const tabs = target.querySelectorAll(".tab-btn");
    const tabText = Array.from(tabs)
      .map((t) => t.textContent ?? "")
      .join(" ");
    expect(tabText).not.toContain("Stock");
    unmount(comp);
    target.remove();
  });
});

describe("ConsumableModal — edit mode", () => {
  it("shows Stock tab in edit mode", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: sampleConsumable,
        store,
        settingsStore: { consumableUnits: ["count"], consumableCategories: [] },
        onclose: vi.fn(),
      },
    });
    await tick();
    flushSync();
    const tabs = target.querySelectorAll(".tab-btn");
    const tabText = Array.from(tabs)
      .map((t) => t.textContent ?? "")
      .join(" ");
    expect(tabText).toContain("Stock");
    unmount(comp);
    target.remove();
  });

  it("shows transaction history in Stock tab", async () => {
    const store = makeStore();
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: sampleConsumable,
        store,
        settingsStore: { consumableUnits: ["count"], consumableCategories: [] },
        onclose: vi.fn(),
      },
    });
    await tick();
    flushSync();
    const stockTab = Array.from(target.querySelectorAll(".tab-btn")).find((b) =>
      b.textContent?.includes("Stock"),
    );
    stockTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(target.textContent).toContain("restock");
    unmount(comp);
    target.remove();
  });

  it("calls onclose when cancel is clicked", async () => {
    const store = makeStore();
    await makeTick();
    const onclose = vi.fn();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: sampleConsumable,
        store,
        settingsStore: { consumableUnits: ["count"], consumableCategories: [] },
        onclose,
      },
    });
    await tick();
    flushSync();
    const cancelBtn = Array.from(target.querySelectorAll("button")).find((b) =>
      b.textContent?.includes("Cancel"),
    );
    cancelBtn?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();
    expect(onclose).toHaveBeenCalledOnce();
    unmount(comp);
    target.remove();
  });
});
