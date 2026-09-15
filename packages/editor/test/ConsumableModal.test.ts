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

const HOME = "home-123";
const getHomeId = () => HOME;

function makeStore(doc = sampleDoc) {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue({ ok: true, status: 200, json: async () => doc }),
  );
  return createConsumableStore(getHomeId);
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

  it("shows a link icon for transactions tied to a cost entry and navigates on click", async () => {
    const docWithLink = {
      version: 1,
      consumables: [sampleConsumable],
      transactions: [
        { id: "t1", consumableId: "c1", delta: 1000, quantityAfter: 1006, note: "", timestamp: "2026-07-02T10:00:00Z", costEntryId: "ce1" },
        { id: "t2", consumableId: "c1", delta: -6, quantityAfter: 1000, note: "used", timestamp: "2026-07-03T10:00:00Z", costEntryId: null },
      ],
    };
    const store = makeStore(docWithLink);
    await makeTick();
    const target = document.createElement("div");
    document.body.appendChild(target);
    const onviewcostentry = vi.fn();
    const comp = mount(ConsumableModal, {
      target,
      props: {
        consumable: sampleConsumable,
        store,
        settingsStore: { consumableUnits: ["count"], consumableCategories: [] },
        onclose: vi.fn(),
        onviewcostentry,
      },
    });
    await tick();
    flushSync();
    const stockTab = Array.from(target.querySelectorAll(".tab-btn")).find((b) =>
      b.textContent?.includes("Stock"),
    );
    stockTab?.dispatchEvent(new MouseEvent("click", { bubbles: true }));
    flushSync();

    // Every row renders a .tx-link slot (disabled/hidden when unlinked) so
    // the column layout stays identical whether or not a row has a link --
    // only actually-linked rows should be enabled and clickable.
    const links = target.querySelectorAll<HTMLButtonElement>(".tx-link");
    expect(links.length).toBe(2);
    const enabledLinks = Array.from(links).filter((b) => !b.disabled);
    expect(enabledLinks.length).toBe(1);
    enabledLinks[0].click();
    expect(onviewcostentry).toHaveBeenCalledWith("ce1");

    unmount(comp);
    target.remove();
  });

  it("sorts the history by date descending regardless of insertion order, and hides the time", async () => {
    // Backdated transactions can be inserted in any order (e.g. a cost entry
    // linked to a past date, added after a more recent manual update), so
    // display order must come from the timestamp, not array order.
    const jumbledDoc = {
      version: 1,
      consumables: [sampleConsumable],
      transactions: [
        { id: "old", consumableId: "c1", delta: 1000, quantityAfter: 1000, note: "", timestamp: "2023-12-02T05:25:00Z", costEntryId: "ce-old" },
        { id: "newest", consumableId: "c1", delta: 360, quantityAfter: 360, note: "niveau ce jour", timestamp: "2026-09-14T19:07:00Z", costEntryId: null },
        { id: "middle", consumableId: "c1", delta: 500, quantityAfter: 1500, note: "", timestamp: "2025-05-02T06:24:00Z", costEntryId: "ce-mid" },
      ],
    };
    const store = makeStore(jumbledDoc);
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

    const rows = Array.from(target.querySelectorAll(".tx-row"));
    const notes = rows.map((r) => r.querySelector(".tx-note")?.textContent);
    expect(notes).toEqual(["niveau ce jour", "—", "—"]);

    const timestamps = rows.map((r) => r.querySelector(".tx-ts")?.textContent ?? "");
    expect(timestamps.every((t) => !/\d+:\d+/.test(t))).toBe(true);

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
